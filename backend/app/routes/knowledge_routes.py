"""Knowledge Base / RAG routes for Agent-B Academic.

Provides endpoints to query existing RAG collections (Library, Empiricals).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.logging_config import get_logger

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
logger = get_logger("knowledge")

# Paths to Qdrant data directories
LIBRARY_RAG_PATH = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\qdrant_data")
INTERVIEWS_RAG_PATH = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\qdrant_interviews")


class CollectionStats(BaseModel):
    """Statistics for a RAG collection."""
    name: str
    display_name: str
    description: str
    vectors_count: int
    points_count: int
    status: str  # "ready" | "offline" | "error"
    path: Optional[str] = None
    error: Optional[str] = None


class KnowledgeSourcesResponse(BaseModel):
    """Response with all knowledge sources."""
    sources: list[CollectionStats]


class DocumentInfo(BaseModel):
    """Document info derived from Qdrant payload (best-effort)."""

    id: str
    filename: str
    chunks: int
    source_path: Optional[str] = None


class DocumentsResponse(BaseModel):
    documents: list[DocumentInfo]


def get_qdrant_stats(qdrant_path: Path, collection_name: str) -> dict:
    """Get stats from a local Qdrant collection."""
    try:
        from qdrant_client import QdrantClient

        if not qdrant_path.exists():
            return {"status": "offline", "error": f"Path not found: {qdrant_path}"}

        client = QdrantClient(path=str(qdrant_path))

        # Check if collection exists
        collections = client.get_collections().collections
        if not any(c.name == collection_name for c in collections):
            return {"status": "offline", "error": f"Collection '{collection_name}' not found"}

        # Get collection info
        info = client.get_collection(collection_name)

        # Handle different qdrant-client versions
        # Older versions: info.vectors_count
        # Newer versions: info.points_count (vectors_count removed)
        vectors_count = getattr(info, 'vectors_count', None)
        if vectors_count is None:
            vectors_count = getattr(info, 'points_count', 0) or 0
        points_count = getattr(info, 'points_count', 0) or 0

        return {
            "status": "ready",
            "vectors_count": vectors_count,
            "points_count": points_count,
        }
    except ImportError:
        return {"status": "error", "error": "qdrant-client not installed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _extract_filename_from_payload(payload: dict) -> tuple[str | None, str | None]:
    """Best-effort extraction of filename and source path from arbitrary RAG payload."""

    if not isinstance(payload, dict):
        return None, None

    # common keys (including paper_name for library-rag)
    for k in ["filename", "file_name", "file", "document", "doc", "paper_name", "name", "title"]:
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip(), payload.get("source") if isinstance(payload.get("source"), str) else None

    # sometimes stored under 'metadata'
    meta = payload.get("metadata")
    if isinstance(meta, dict):
        for k in ["filename", "file_name", "file", "document", "doc", "source"]:
            v = meta.get(k)
            if isinstance(v, str) and v.strip():
                # treat source as path
                if k == "source":
                    return Path(v).name, v
                return v.strip(), meta.get("source") if isinstance(meta.get("source"), str) else None

    # fallback to 'source' path
    src = payload.get("source")
    if isinstance(src, str) and src.strip():
        return Path(src).name, src

    return None, None


def get_qdrant_documents(qdrant_path: Path, collection_name: str, *, limit: int = 5000) -> list[DocumentInfo]:
    """Return unique document list by scanning Qdrant payloads.

    Note: Qdrant is chunk-based; this groups points by extracted filename.
    """

    try:
        from qdrant_client import QdrantClient

        if not qdrant_path.exists():
            return []

        client = QdrantClient(path=str(qdrant_path))

        # Ensure collection exists
        collections = client.get_collections().collections
        if not any(c.name == collection_name for c in collections):
            return []

        # Scroll through points (payload only) and group
        seen: dict[str, dict[str, Any]] = {}
        offset = None
        remaining = limit

        while remaining > 0:
            page_limit = min(256, remaining)
            points, next_offset = client.scroll(
                collection_name=collection_name,
                limit=page_limit,
                with_payload=True,
                with_vectors=False,
                offset=offset,
            )

            if not points:
                break

            for p in points:
                payload = getattr(p, "payload", None) or {}
                filename, source_path = _extract_filename_from_payload(payload)
                if not filename:
                    continue
                key = filename
                entry = seen.get(key)
                if not entry:
                    seen[key] = {
                        "id": str(getattr(p, "id", filename)),
                        "filename": filename,
                        "chunks": 1,
                        "source_path": source_path,
                    }
                else:
                    entry["chunks"] += 1
                    if not entry.get("source_path") and source_path:
                        entry["source_path"] = source_path

            remaining -= len(points)
            if next_offset is None:
                break
            offset = next_offset

        docs = [DocumentInfo(**v) for v in seen.values()]
        docs.sort(key=lambda d: d.filename.lower())
        return docs

    except ImportError:
        return []
    except Exception:
        return []


@router.get("/sources", response_model=KnowledgeSourcesResponse)
async def list_knowledge_sources():
    """List all available knowledge sources with their stats."""
    sources = []
    
    # 1. Library RAG (academic papers)
    library_stats = get_qdrant_stats(LIBRARY_RAG_PATH, "academic_papers")
    sources.append(CollectionStats(
        name="library",
        display_name="Library RAG",
        description="Academic papers (867 papers, audit/accounting/carbon markets)",
        vectors_count=library_stats.get("vectors_count", 0),
        points_count=library_stats.get("points_count", 0),
        status=library_stats.get("status", "offline"),
        path=str(LIBRARY_RAG_PATH) if LIBRARY_RAG_PATH.exists() else None,
        error=library_stats.get("error"),
    ))
    
    # 2. Interview Data (empiricals)
    interview_stats = get_qdrant_stats(INTERVIEWS_RAG_PATH, "interview_data")
    sources.append(CollectionStats(
        name="interviews",
        display_name="Empiricals RAG",
        description="Interview transcripts and empirical data (Paper 2 & 3)",
        vectors_count=interview_stats.get("vectors_count", 0),
        points_count=interview_stats.get("points_count", 0),
        status=interview_stats.get("status", "offline"),
        path=str(INTERVIEWS_RAG_PATH) if INTERVIEWS_RAG_PATH.exists() else None,
        error=interview_stats.get("error"),
    ))
    
    return KnowledgeSourcesResponse(sources=sources)


@router.get("/sources/{source_name}", response_model=CollectionStats)
async def get_knowledge_source(source_name: str):
    """Get details for a specific knowledge source."""
    sources = (await list_knowledge_sources()).sources

    for src in sources:
        if src.name == source_name:
            return src

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Knowledge source not found: {source_name}",
    )


@router.get("/sources/{source_name}/documents", response_model=DocumentsResponse)
async def list_source_documents(source_name: str, limit: int = 2000):
    """List documents inside a knowledge source (best-effort)."""

    # Map source name -> Qdrant collection and path
    if source_name == "library":
        collection = "academic_papers"
        qdrant_path = LIBRARY_RAG_PATH
    elif source_name == "interviews":
        collection = "interview_data"
        qdrant_path = INTERVIEWS_RAG_PATH
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown source")

    docs = get_qdrant_documents(qdrant_path, collection, limit=limit)
    return DocumentsResponse(documents=docs)


# =============================================================================
# RAG Search API
# =============================================================================


class SearchRequest(BaseModel):
    """Search request for RAG collections."""
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    """A single search result."""
    text: str
    score: float
    source: Optional[str] = None
    metadata: Optional[dict] = None


class SearchResponse(BaseModel):
    """Search response with results."""
    results: list[SearchResult]
    query: str
    source: str


def search_qdrant(
    qdrant_path: Path,
    collection_name: str,
    query: str,
    top_k: int = 5,
) -> list[SearchResult]:
    """Search a Qdrant collection using sentence-transformers embeddings."""
    try:
        from qdrant_client import QdrantClient
        from sentence_transformers import SentenceTransformer

        if not qdrant_path.exists():
            logger.warning(f"Qdrant path not found: {qdrant_path}")
            return []

        client = QdrantClient(path=str(qdrant_path))

        # Check collection exists
        collections = client.get_collections().collections
        if not any(c.name == collection_name for c in collections):
            logger.warning(f"Collection not found: {collection_name}")
            return []

        # Use the same embedding model as library-rag
        model = SentenceTransformer("all-MiniLM-L6-v2")
        query_vector = model.encode(query).tolist()

        # Search
        hits = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )

        results = []
        for hit in hits:
            payload = hit.payload or {}
            # Extract text content
            text = payload.get("text") or payload.get("content") or payload.get("chunk") or ""
            # Extract source/filename
            source, _ = _extract_filename_from_payload(payload)
            results.append(SearchResult(
                text=str(text)[:2000],  # Limit text length
                score=hit.score,
                source=source,
                metadata={k: v for k, v in payload.items() if k not in ("text", "content", "chunk")},
            ))

        return results

    except ImportError as e:
        logger.error(f"Import error during search: {e}")
        return []
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return []


@router.post("/sources/{source_name}/search", response_model=SearchResponse)
async def search_knowledge_source(source_name: str, request: SearchRequest):
    """Search a knowledge source using semantic similarity.
    
    This powers the Library RAG and Empiricals RAG features.
    Returns top-k relevant text chunks for the given query.
    """
    # Map source name -> Qdrant collection and path
    if source_name == "library":
        collection = "academic_papers"
        qdrant_path = LIBRARY_RAG_PATH
    elif source_name == "interviews":
        collection = "interview_data"
        qdrant_path = INTERVIEWS_RAG_PATH
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown source")

    results = search_qdrant(qdrant_path, collection, request.query, request.top_k)

    return SearchResponse(
        results=results,
        query=request.query,
        source=source_name,
    )
