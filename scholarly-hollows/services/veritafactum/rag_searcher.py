"""Per-sentence RAG search using existing Qdrant integration.

Reuses the search infrastructure from knowledge_routes.py.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger

from .extractor import SentenceAnalysis

logger = get_logger("checker.rag_searcher")

# Same paths as knowledge_routes.py
LIBRARY_RAG_PATH = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\qdrant_data")
COLLECTION_NAME = "academic_papers"


@dataclass
class RAGResult:
    """A single RAG search result."""
    text: str
    score: float
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    author: Optional[str] = None
    year: Optional[str] = None
    title: Optional[str] = None


@dataclass
class SentenceRAGResults:
    """RAG results for a single sentence."""
    sentence_id: int
    results: List[RAGResult] = field(default_factory=list)


# Cache for embedding model (heavy to load)
_model = None


def _get_model():
    """Lazy-load sentence transformer model."""
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("BAAI/bge-m3")
        return _model
    except ImportError:
        logger.error("sentence-transformers not installed")
        return None


def _search_qdrant_raw(query: str, top_k: int = 5) -> List[RAGResult]:
    """Search Qdrant collection directly (synchronous)."""
    try:
        from app.services.qdrant_factory import get_qdrant_client

        model = _get_model()
        if model is None:
            return []

        client = get_qdrant_client()
        query_vector = model.encode(query).tolist()

        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )

        results = []
        for hit in response.points:
            payload = hit.payload or {}
            text = payload.get("text") or payload.get("content") or payload.get("chunk") or ""
            source = payload.get("paper_name") or payload.get("filename") or payload.get("source")
            
            # Extract metadata
            author = payload.get("author") or payload.get("authors")
            year = payload.get("year") or payload.get("publication_year")
            title = payload.get("title") or payload.get("paper_name")

            results.append(RAGResult(
                text=str(text)[:2000],
                score=hit.score,
                source=str(source) if source else None,
                metadata={k: v for k, v in payload.items() if k not in ("text", "content", "chunk")},
                author=str(author) if author else None,
                year=str(year) if year else None,
                title=str(title) if title else None,
            ))

        return results

    except Exception as e:
        logger.error(f"Qdrant search error: {e}", exc_info=True)
        return []


def _deduplicate(results: List[RAGResult]) -> List[RAGResult]:
    """Deduplicate results by source + text similarity, keeping highest score."""
    seen: Dict[str, RAGResult] = {}
    for r in results:
        key = f"{r.source or ''}:{r.text[:100]}"
        if key not in seen or r.score > seen[key].score:
            seen[key] = r
    # Sort by score descending
    deduped = sorted(seen.values(), key=lambda x: x.score, reverse=True)
    return deduped[:10]  # Top 10


async def search_for_sentence(analysis: SentenceAnalysis) -> SentenceRAGResults:
    """Search RAG library for a single sentence's claims and terms.
    
    Runs searches for:
    1. Generated search queries
    2. Key terms
    3. Named scholars
    """
    all_results: List[RAGResult] = []
    loop = asyncio.get_event_loop()

    # Search by generated queries
    for query in analysis.search_queries:
        results = await loop.run_in_executor(None, _search_qdrant_raw, query, 5)
        all_results.extend(results)

    # Search by key terms
    for term in analysis.key_terms:
        results = await loop.run_in_executor(None, _search_qdrant_raw, term, 3)
        all_results.extend(results)

    # Search by scholar names
    for scholar in analysis.named_scholars:
        results = await loop.run_in_executor(None, _search_qdrant_raw, scholar, 3)
        all_results.extend(results)

    deduped = _deduplicate(all_results)

    return SentenceRAGResults(
        sentence_id=analysis.sentence.id,
        results=deduped,
    )


async def search_all_sentences(
    analyses: List[SentenceAnalysis],
    max_concurrent: int = 3,
) -> List[SentenceRAGResults]:
    """Search RAG for all sentences with limited concurrency.
    
    Args:
        analyses: List of SentenceAnalysis objects with search queries.
        max_concurrent: Max concurrent searches (Qdrant is local, so limited).
        
    Returns:
        List of SentenceRAGResults in same order as input.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _bounded_search(analysis: SentenceAnalysis) -> SentenceRAGResults:
        async with semaphore:
            return await search_for_sentence(analysis)

    tasks = [_bounded_search(a) for a in analyses]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    final: List[SentenceRAGResults] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error(f"RAG search failed for sentence {analyses[i].sentence.id}: {r}")
            final.append(SentenceRAGResults(sentence_id=analyses[i].sentence.id))
        else:
            final.append(r)

    return final
