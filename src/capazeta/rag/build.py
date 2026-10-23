"""CLI para construir el índice FAISS de MITRE ATT&CK Enterprise.

Uso:  uv run python -m capazeta.rag.build [--force]
"""
import sys

from capazeta.rag.mitre import build_index

if __name__ == "__main__":
    build_index(force="--force" in sys.argv or "-f" in sys.argv)
