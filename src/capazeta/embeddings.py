"""Embeddings para el RAG, alineado con el proveedor elegido en EMBEDDING_MODEL."""
import os

from capazeta.config import EMBEDDING_MODEL

_RETRIEVAL_INSTRUCTION = (
    "Given a web search query, retrieve relevant passages that answer the query"
)


def _cloudflare_embeddings():
    """Cloudflare Workers AI usando el modo `queries` para las consultas."""
    import requests
    from langchain_community.embeddings.cloudflare_workersai import (
        CloudflareWorkersAIEmbeddings,
    )

    class _RetrievalEmbeddings(CloudflareWorkersAIEmbeddings):
        """Las consultas van por `queries`: mejora el retrieval de qwen3/bge."""

        def embed_query(self, text: str) -> list[float]:
            if self.strip_new_lines:
                text = text.replace("\n", " ")
            response = requests.post(
                f"{self.api_base_url}/{self.account_id}/ai/run/{self.model_name}",
                headers=self.headers,
                json={"queries": [text], "instruction": _RETRIEVAL_INSTRUCTION},
            )
            # Modelos que no soportan `queries` (p. ej. bge) usan el modo estándar.
            if response.status_code != 200:
                return super().embed_query(text)
            return response.json()["result"]["data"][0]

    account_id = (os.getenv("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    api_token = (os.getenv("CLOUDFLARE_API_TOKEN") or "").strip()
    if not account_id or not api_token:
        raise RuntimeError(
            "Faltan CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN para "
            f"EMBEDDING_MODEL={EMBEDDING_MODEL}"
        )

    return _RetrievalEmbeddings(
        account_id=account_id,
        api_token=api_token,
        model_name=EMBEDDING_MODEL,
    )


def get_embeddings():
    """Devuelve el modelo de embeddings configurado (Google o Cloudflare)."""
    if EMBEDDING_MODEL.startswith("@cf/"):
        return _cloudflare_embeddings()

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
