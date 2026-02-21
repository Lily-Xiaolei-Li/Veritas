from __future__ import annotations

import asyncio
import re
from typing import List

from app.logging_config import get_logger
from app.services.checker.extractor import SentenceAnalysis
from app.services.checker.rag_searcher import RAGResult, SentenceRAGResults

from .metadata_index import VFMetadataIndex
from .profile_store import VFProfileStore

logger = get_logger("vf_middleware.profile_searcher")

_CITATION_RE = re.compile(r"\b([A-Z][A-Za-z\-']+)\s*\((\d{4})\)")

_index: VFMetadataIndex | None = None
_store: VFProfileStore | None = None


def _get_index() -> VFMetadataIndex:
    global _index
    if _index is None:
        _index = VFMetadataIndex()
    return _index


def _get_store() -> VFProfileStore:
    global _store
    if _store is None:
        _store = VFProfileStore()
    return _store


def _citations_from_sentence(text: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for m in _CITATION_RE.finditer(text or ""):
        try:
            out.append((m.group(1), int(m.group(2))))
        except Exception:
            continue
    return out


def _results_from_profile(paper_id: str) -> List[RAGResult]:
    profile = _get_store().get_profile(paper_id)
    if not profile:
        return []

    meta = profile.get("meta", {})
    source = meta.get("title") or paper_id
    author = ", ".join(meta.get("authors", [])) if isinstance(meta.get("authors"), list) else None
    year = str(meta.get("year")) if meta.get("year") else None
    title = meta.get("title")

    out: List[RAGResult] = []
    chunks = profile.get("chunks", {})

    for chunk_id, score in (("cited_for", 0.99), ("theory", 0.95), ("contributions", 0.92), ("abstract", 0.88)):
        text = str(chunks.get(chunk_id, "")).strip()
        if not text:
            continue
        out.append(
            RAGResult(
                text=text[:2500],
                score=score,
                source=str(source),
                metadata={
                    "search_mode": "vf_profile",
                    "paper_id": paper_id,
                    "chunk_id": chunk_id,
                    "in_library": bool(profile.get("in_library", False)),
                    "source_type": profile.get("source_type", "external"),
                },
                author=author,
                year=year,
                title=title,
            )
        )

    return out


async def search_for_sentence(analysis: SentenceAnalysis) -> SentenceRAGResults:
    """Phase 2 flow: metadata exact match -> cited_for/theory chunks -> fallback raw search."""

    citations = _citations_from_sentence(analysis.sentence.text)
    profile_results: List[RAGResult] = []

    for author, year in citations:
        matches = _get_index().exact_lookup(author=author, year=year)
        for match in matches:
            paper_id = match.get("paper_id")
            if not paper_id:
                continue
            profile_results.extend(_results_from_profile(str(paper_id)))

    if profile_results:
        seen = set()
        deduped: List[RAGResult] = []
        for r in profile_results:
            k = f"{r.metadata.get('paper_id')}:{r.metadata.get('chunk_id')}"
            if k in seen:
                continue
            seen.add(k)
            deduped.append(r)
        return SentenceRAGResults(sentence_id=analysis.sentence.id, results=deduped[:10])

    # Fallback to legacy raw semantic search when no middleware profile exists.
    from app.services.checker import rag_searcher as raw_rag_searcher

    return await raw_rag_searcher.search_for_sentence(analysis)


async def search_all_sentences(analyses: List[SentenceAnalysis], max_concurrent: int = 3) -> List[SentenceRAGResults]:
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _bounded(analysis: SentenceAnalysis) -> SentenceRAGResults:
        async with semaphore:
            return await search_for_sentence(analysis)

    tasks = [_bounded(a) for a in analyses]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    final: List[SentenceRAGResults] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error(f"VF profile search failed for sentence {analyses[i].sentence.id}: {r}")
            final.append(SentenceRAGResults(sentence_id=analyses[i].sentence.id))
        else:
            final.append(r)
    return final
