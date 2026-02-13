from __future__ import annotations

import logging

import httpx
from config import get_settings
from fastapi import APIRouter
from models import RagSearchRequest, RagSearchResponse, RagSearchResult

router = APIRouter()
logger = logging.getLogger("xiaolei_api.rag")


def _model_dump(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)
    return model.dict(exclude_none=True)


def _coerce_result(item: dict) -> RagSearchResult:
    # RAG API returns: {category, filename, chunk_index, total_chunks, score, snippet}
    # Map to our model format
    filename = item.get("filename", "")
    # Extract title from filename (remove underscores, etc.)
    title = filename.replace("_", " ").rsplit(".", 1)[0] if filename else ""
    
    return RagSearchResult(
        title=title,
        authors=item.get("category", ""),  # Use category as "authors" placeholder
        year=None,  # RAG API doesn't provide year
        relevance=item.get("score"),
        snippet=item.get("snippet", ""),
    )


@router.post("/search", response_model=RagSearchResponse)
async def rag_search(request: RagSearchRequest) -> RagSearchResponse:
    settings = get_settings()
    
    # Map collection to RAG API endpoint
    collection = request.collection or "papers"
    valid_collections = ["papers", "interviews", "documents", "observations", "paper3", "all"]
    if collection not in valid_collections:
        collection = "papers"
    
    url = f"{settings.rag_api_base_url.rstrip('/')}/search/{collection}"
    
    # RAG API expects {query, top_k} format
    payload = {"query": request.query, "top_k": request.limit}

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_s) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.warning("RAG search failed (url=%s): %s", url, exc)
        return RagSearchResponse(results=[])

    raw_results = data.get("results", [])
    results = []
    for item in raw_results:
        if isinstance(item, dict):
            results.append(_coerce_result(item))
    return RagSearchResponse(results=results)
