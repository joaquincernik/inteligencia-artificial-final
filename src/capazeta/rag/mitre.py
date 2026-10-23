"""RAG de MITRE ATT&CK Enterprise sobre FAISS.

Construye un índice vectorial (FAISS) a partir del bundle STIX de MITRE y expone
búsqueda semántica + lookup por ID de técnica para enriquecer hallazgos.

Build:  uv run python -m capazeta.rag.build [--force]
"""
import json
import re
import time
from pathlib import Path

import httpx

from capazeta.config import MITRE_DATA_DIR, MITRE_STIX_URL
from capazeta.embeddings import get_embeddings

DATA_DIR = Path(MITRE_DATA_DIR)
STIX_FILE = DATA_DIR / "enterprise-attack.json"
FAISS_DIR = DATA_DIR / "faiss"
TECHNIQUES_FILE = DATA_DIR / "techniques.json"

_DESCRIPTION_LIMIT = 1200
_EMBED_BATCH_SIZE = 80
_EMBED_BATCH_SLEEP = 61.0

_store = None
_techniques = None


def _download_stix(force: bool = False) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if STIX_FILE.exists() and not force:
        return STIX_FILE
    print(f"descargando MITRE ATT&CK desde {MITRE_STIX_URL} ...", flush=True)
    response = httpx.get(MITRE_STIX_URL, timeout=120.0, follow_redirects=True)
    response.raise_for_status()
    STIX_FILE.write_bytes(response.content)
    return STIX_FILE


def _technique_url(tid: str) -> str:
    return f"https://attack.mitre.org/techniques/{tid.replace('.', '/')}/"


def _parse_techniques(bundle: dict) -> list[dict]:
    """Parsea las técnicas del bundle STIX, incluyendo revocadas/deprecadas.

    Las técnicas revocadas se incluyen con `deprecated=True` para poder enriquecer
    IDs que Wazuh siga reportando, pero se excluyen del corpus del FAISS.
    """
    techniques = []
    for obj in bundle.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue

        external_id = None
        for ref in obj.get("external_references", []):
            if ref.get("source_name") in ("mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"):
                external_id = ref.get("external_id")
                break
        if not external_id:
            continue

        tactics = []
        for phase in obj.get("kill_chain_phases", []):
            name = (phase.get("phase_name") or "").replace("-", " ").strip()
            if name and name not in tactics:
                tactics.append(name.title())

        description = (obj.get("description") or "").strip()
        techniques.append(
            {
                "id": external_id,
                "name": obj.get("name") or external_id,
                "tactics": tactics,
                "platforms": obj.get("x_mitre_platforms", []),
                "description": description[:_DESCRIPTION_LIMIT],
                "detection": (obj.get("x_mitre_detection") or "").strip()[:_DESCRIPTION_LIMIT],
                "url": _technique_url(external_id),
                "is_subtechnique": bool(obj.get("x_mitre_is_subtechnique")),
                "deprecated": bool(obj.get("revoked") or obj.get("x_mitre_deprecated")),
            }
        )
    return techniques


def _dedupe_by_id(techniques: list[dict]) -> dict[str, dict]:
    """Indexa por ID, prefiriendo la versión vigente sobre la revocada."""
    by_id: dict[str, dict] = {}
    for tech in techniques:
        current = by_id.get(tech["id"])
        if current is None or (current["deprecated"] and not tech["deprecated"]):
            by_id[tech["id"]] = tech
    return by_id


def _retry_delay(text: str, default: float = 35.0) -> float:
    match = re.search(r"retryDelay['\"]?\s*:\s*['\"](\d+)s", text)
    if match:
        return float(match.group(1)) + 3
    match = re.search(r"retry in (\d+)", text)
    if match:
        return float(match.group(1)) + 3
    return default


def _embed_batch(embeddings, texts: list[str], attempts: int = 8) -> list[list[float]]:
    for attempt in range(attempts):
        try:
            return embeddings.embed_documents(texts)
        except Exception as exc:
            message = str(exc)
            if "RESOURCE_EXHAUSTED" in message or "429" in message:
                wait = _retry_delay(message)
                print(
                    f"  rate limit alcanzado; esperando {wait:.0f}s "
                    f"(intento {attempt + 1}/{attempts}) ...",
                    flush=True,
                )
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("No se pudo generar embeddings tras varios intentos (rate limit).")


def build_index(force: bool = False) -> dict:
    """Descarga MITRE, arma el índice FAISS y persiste metadatos. Devuelve un resumen.

    Si el índice FAISS ya existe y no se pasa `force`, solo refresca `techniques.json`
    (útil para incorporar técnicas revocadas sin volver a generar embeddings).
    """
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stix_path = _download_stix(force=force)
    bundle = json.loads(stix_path.read_text(encoding="utf-8"))
    techniques = _parse_techniques(bundle)
    by_id = _dedupe_by_id(techniques)

    TECHNIQUES_FILE.write_text(
        json.dumps(by_id, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    if FAISS_DIR.exists() and not force:
        print(
            f"El índice FAISS ya existe en {FAISS_DIR}; metadatos actualizados "
            f"({len(by_id)} técnicas). Usá --force para reconstruir el índice.",
            flush=True,
        )
        return {"status": "metadata_refreshed", "path": str(FAISS_DIR), "count": len(by_id)}

    current = [t for t in by_id.values() if not t["deprecated"]]
    docs = []
    for tech in current:
        content = (
            f"{tech['id']} {tech['name']}\n"
            f"Tácticas: {', '.join(tech['tactics']) or 'N/D'}\n"
            f"Plataformas: {', '.join(tech['platforms']) or 'N/D'}\n\n"
            f"{tech['description']}"
        )
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "id": tech["id"],
                    "name": tech["name"],
                    "tactics": ", ".join(tech["tactics"]),
                    "url": tech["url"],
                },
            )
        )

    embeddings = get_embeddings()
    total = len(docs)
    print(
        f"generando embeddings para {total} técnicas vigentes "
        f"(lotes de {_EMBED_BATCH_SIZE}) ...",
        flush=True,
    )
    store = None
    for start in range(0, total, _EMBED_BATCH_SIZE):
        batch = docs[start : start + _EMBED_BATCH_SIZE]
        texts = [doc.page_content for doc in batch]
        metadatas = [doc.metadata for doc in batch]
        vectors = _embed_batch(embeddings, texts)
        pairs = list(zip(texts, vectors))
        if store is None:
            store = FAISS.from_embeddings(pairs, embeddings, metadatas=metadatas)
        else:
            store.add_embeddings(pairs, metadatas=metadatas)
        done = min(start + _EMBED_BATCH_SIZE, total)
        print(f"  embebidas {done}/{total}", flush=True)
        if done < total:
            time.sleep(_EMBED_BATCH_SLEEP)

    store.save_local(str(FAISS_DIR))
    print(f"índice FAISS guardado en {FAISS_DIR} ({total} técnicas vigentes).", flush=True)
    return {"status": "built", "path": str(FAISS_DIR), "count": total}


def load_store():
    global _store
    if _store is None:
        from langchain_community.vectorstores import FAISS

        if not FAISS_DIR.exists():
            raise RuntimeError(
                f"No hay índice FAISS en {FAISS_DIR}. Construilo con: "
                "uv run python -m capazeta.rag.build"
            )
        _store = FAISS.load_local(
            str(FAISS_DIR), get_embeddings(), allow_dangerous_deserialization=True
        )
    return _store


def load_techniques() -> dict:
    global _techniques
    if _techniques is None:
        if not TECHNIQUES_FILE.exists():
            raise RuntimeError(
                f"Falta {TECHNIQUES_FILE}. Construí el índice con: "
                "uv run python -m capazeta.rag.build"
            )
        _techniques = json.loads(TECHNIQUES_FILE.read_text(encoding="utf-8"))
    return _techniques


def get_technique(technique_id: str) -> dict | None:
    if not technique_id:
        return None
    return load_techniques().get(technique_id.strip().upper())


def search(query: str, k: int = 5) -> list[dict]:
    store = load_store()
    results = store.similarity_search(query, k=k)
    return [
        {
            "id": doc.metadata.get("id"),
            "name": doc.metadata.get("name"),
            "tactics": doc.metadata.get("tactics"),
            "url": doc.metadata.get("url"),
            "excerpt": doc.page_content[:500],
        }
        for doc in results
    ]
