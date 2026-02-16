"""
Centralized Qdrant client factory.

Uses Qdrant **server mode** (http://localhost:6333) instead of embedded mode.
This avoids .lock file conflicts and connection stability issues when multiple
processes (backend + batch scripts) access the same vector store.

Configuration:
  - Set QDRANT_URL env var to override (default: http://localhost:6333)
  - Qdrant server must be started separately before the backend.
    See docs/QUICKSTART_WINDOWS.md and TROUBLESHOOTING.md.

⚠️  NEVER use QdrantClient(path=...) anywhere in this project.
    Always use get_qdrant_client() from this module.
"""
import os

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")


def get_qdrant_client():
    """Return a QdrantClient connected to the Qdrant server.

    All Qdrant access in the project MUST go through this factory.
    """
    from qdrant_client import QdrantClient
    return QdrantClient(url=QDRANT_URL)
