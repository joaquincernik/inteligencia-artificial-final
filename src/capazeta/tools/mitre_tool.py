"""Herramientas MITRE ATT&CK: búsqueda RAG (FAISS) y mapeo de alertas de Wazuh a MITRE."""
import json
from collections import Counter

from langchain_core.tools import tool

from capazeta.rag import get_technique, search as _mitre_search
from capazeta.tools.report import (
    mitre_coverage_to_markdown,
    mitre_search_to_markdown,
    save_general_markdown_report,
)
from capazeta.tools.wazuh_tool import _indexer_search


@tool
def search_mitre_attack(query: str, k: int = 5, save_md: bool = False) -> str:
    """Busca técnicas de MITRE ATT&CK Enterprise por concepto o descripción (RAG FAISS).

    Args:
        query: Consulta en lenguaje natural (ej. "credential dumping", "pass the hash").
        k: Cantidad de técnicas a recuperar.
        save_md: Si es True, guarda un reporte Markdown en reports/.
    """
    print("consultando mitre...", flush=True)
    try:
        results = _mitre_search(query, k=k)
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    result_data = {"query": query, "results": results}
    if save_md:
        md_content = mitre_search_to_markdown(result_data)
        result_data["file"] = save_general_markdown_report(md_content, "mitre_search")
    return json.dumps(result_data, ensure_ascii=False)


def _coverage_body(hours: int, min_level: int, top: int, aggregate: bool) -> dict:
    body = {
        "size": 0 if aggregate else 500,
        "query": {
            "bool": {
                "filter": [
                    {"range": {"rule.level": {"gte": min_level}}},
                    {"range": {"@timestamp": {"gte": f"now-{hours}h"}}},
                    {"exists": {"field": "rule.mitre.id"}},
                ]
            }
        },
    }
    if aggregate:
        body["aggs"] = {
            "techniques": {"terms": {"field": "rule.mitre.id", "size": top}},
            "tactics": {"terms": {"field": "rule.mitre.tactic", "size": top}},
        }
    else:
        body["_source"] = ["rule.mitre.id", "rule.mitre.tactic"]
    return body


def _enrich(tech_counter: Counter, top: int) -> list[dict]:
    rows = []
    for tid, count in tech_counter.most_common(top):
        tech = get_technique(tid) or {}
        rows.append(
            {
                "id": tid,
                "name": tech.get("name"),
                "tactics": tech.get("tactics"),
                "url": tech.get("url"),
                "deprecated": tech.get("deprecated"),
                "count": count,
            }
        )
    return rows


@tool
def wazuh_mitre_coverage(
    hours: int = 24, min_level: int = 0, top: int = 20, save_md: bool = False
) -> str:
    """Indica qué técnicas y tácticas MITRE ATT&CK está reportando Wazuh (alertas recientes).

    Args:
        hours: Ventana temporal hacia atrás en horas.
        min_level: Nivel mínimo de la regla (0-15).
        top: Cantidad máxima de técnicas a devolver.
        save_md: Si es True, guarda un reporte Markdown en reports/.
    """
    print("consultando mitre...", flush=True)
    tactic_counter: Counter = Counter()
    tech_counter: Counter = Counter()
    try:
        payload = _indexer_search("wazuh-alerts-*", _coverage_body(hours, min_level, top, True))
        aggs = payload.get("aggregations", {})
        for bucket in aggs.get("techniques", {}).get("buckets", []):
            tech_counter[bucket["key"]] = bucket["doc_count"]
        for bucket in aggs.get("tactics", {}).get("buckets", []):
            tactic_counter[bucket["key"]] = bucket["doc_count"]
    except Exception:
        try:
            payload = _indexer_search("wazuh-alerts-*", _coverage_body(hours, min_level, top, False))
            for hit in payload.get("hits", {}).get("hits", []):
                rule = (hit.get("_source") or {}).get("rule", {})
                mitre = rule.get("mitre", {})
                for tid in mitre.get("id", []) or []:
                    tech_counter[tid] += 1
                for tactic in mitre.get("tactic", []) or []:
                    tactic_counter[tactic] += 1
        except Exception as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    if not tech_counter:
        res_empty = {
            "window_hours": hours,
            "min_level": min_level,
            "total_techniques": 0,
            "techniques": [],
            "tactics": [],
            "note": "No hay alertas con mapeo MITRE en la ventana indicada.",
        }
        if save_md:
            md_content = mitre_coverage_to_markdown(res_empty)
            res_empty["file"] = save_general_markdown_report(md_content, "mitre_coverage")
        return json.dumps(res_empty, ensure_ascii=False)

    result_data = {
        "window_hours": hours,
        "min_level": min_level,
        "total_techniques": len(tech_counter),
        "techniques": _enrich(tech_counter, top),
        "tactics": [{"tactic": t, "count": c} for t, c in tactic_counter.most_common(top)],
    }
    if save_md:
        md_content = mitre_coverage_to_markdown(result_data)
        result_data["file"] = save_general_markdown_report(md_content, "mitre_coverage")
    return json.dumps(result_data, ensure_ascii=False)

    return json.dumps(
        {
            "window_hours": hours,
            "min_level": min_level,
            "total_techniques": len(tech_counter),
            "techniques": _enrich(tech_counter, top),
            "tactics": [{"tactic": t, "count": c} for t, c in tactic_counter.most_common(top)],
        },
        ensure_ascii=False,
    )
