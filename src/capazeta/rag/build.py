"""CLI para construir el índice FAISS de MITRE ATT&CK Enterprise.

Uso:  uv run python -m capazeta.rag.build [--force] [--no-download]
"""
import sys

from capazeta.rag.mitre import build_index

if __name__ == "__main__":
    argv = sys.argv[1:]
    build_index(
        force="--force" in argv or "-f" in argv,
        download="--no-download" not in argv,
    )
