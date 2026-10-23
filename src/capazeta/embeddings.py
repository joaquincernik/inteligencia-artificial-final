"""Embeddings para el RAG, alineado con el proveedor elegido en EMBEDDING_MODEL."""
from capazeta.config import EMBEDDING_MODEL


def get_embeddings():
    """Devuelve el modelo de embeddings configurado (Google Generative AI)."""
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
