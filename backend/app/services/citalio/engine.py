from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional
from uuid import uuid4

from app.logging_config import get_logger
from app.services.checker import classifier, extractor, splitter
from app.services.checker.engine import _default_llm_call
from app.services.checker.rag_searcher import SentenceRAGResults

from .citation_inserter import CitationInserter
from .citation_searcher import CitationCandidate, CitationSearcher
from .relevance_scorer import LLMCallFn, RelevanceScorer

logger = get_logger("citalio.engine")


async def run_citalio(
    text: str,
    session_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    llm_call: Optional[LLMCallFn] = None,
    progress_callback: Optional[Callable[..., Coroutine[Any, Any, None]]] = None,
) -> Dict[str, Any]:
    opts = {
        "min_confidence": 0.5,
        "max_citations_per_sentence": 3,
        "include_common_knowledge": False,
    }
    if options:
        opts.update(options)

    call_llm = llm_call or _default_llm_call
    run_id = f"citalio-{uuid4().hex[:8]}"

    async def _progress(current: int = 0, total: int = 0, step: str = ""):
        if progress_callback:
            await progress_callback(current=current, total=total, step=step)

    await _progress(step="splitting")
    sentences = splitter.split_sentences(text)
    if not sentences:
        return {
            "run_id": run_id,
            "status": "completed",
            "session_id": session_id,
            "sentences": [],
            "summary": {
                "total_sentences": 0,
                "cite_needed": 0,
                "auto_cited": 0,
                "maybe_cited": 0,
                "manual_needed": 0,
                "no_cite_needed": 0,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    await _progress(step="extracting", total=len(sentences))
    analyses = await extractor.extract_claims_batch(sentences, call_llm)

    empty_rag = {s.id: SentenceRAGResults(sentence_id=s.id) for s in sentences}
    await _progress(step="classifying", total=len(sentences))
    classifications = await classifier.classify_all_sentences(sentences, empty_rag, call_llm, progress_callback=progress_callback)
    cls_map = {c.sentence_id: c for c in classifications}

    searcher = CitationSearcher()
    scorer = RelevanceScorer(call_llm)
    inserter = CitationInserter()

    sentence_results: List[Dict[str, Any]] = []
    summary = {
        "total_sentences": len(sentences),
        "cite_needed": 0,
        "auto_cited": 0,
        "maybe_cited": 0,
        "manual_needed": 0,
        "no_cite_needed": 0,
    }

    for idx, sent in enumerate(sentences, start=1):
        await _progress(current=idx, total=len(sentences), step="citation_search")
        cls = cls_map.get(sent.id)
        cls_type = cls.type if cls else "COMMON"

        should_cite = cls_type == "CITE_NEEDED" or bool(opts.get("include_common_knowledge"))
        if cls_type == "CITE_NEEDED":
            summary["cite_needed"] += 1

        if not should_cite:
            action = "no_cite_needed"
            summary["no_cite_needed"] += 1
            sentence_results.append({
                "id": f"s{sent.id}",
                "text": sent.text,
                "classification": cls_type,
                "action": action,
                "candidates": [],
                "suggested_text": sent.text,
                "start_offset": sent.start_offset,
                "end_offset": sent.end_offset,
            })
            continue

        candidates = searcher.search(sent.text, top_k=5)
        scored = await scorer.score(sent.text, candidates)
        min_conf = float(opts.get("min_confidence", 0.5))
        kept = [c for c in scored if c.confidence >= min_conf]

        if kept and kept[0].confidence >= 0.8:
            action = "auto_cite"
            summary["auto_cited"] += 1
        elif kept:
            action = "maybe_cite"
            summary["maybe_cited"] += 1
        else:
            action = "manual_needed"
            summary["manual_needed"] += 1

        suggested_text = inserter.insert(sent.text, kept, max_citations=int(opts.get("max_citations_per_sentence", 3))) if kept else sent.text

        sentence_results.append({
            "id": f"s{sent.id}",
            "sentence_id": sent.id,
            "text": sent.text,
            "classification": cls_type,
            "action": action,
            "candidates": [
                {
                    "paper_id": c.paper_id,
                    "authors": c.authors,
                    "year": c.year,
                    "title": c.title,
                    "cited_for": c.cited_for,
                    "relevance_score": c.relevance_score,
                    "confidence": c.confidence,
                    "reason": c.reason,
                    "citation_text": c.citation_text,
                }
                for c in kept
            ],
            "suggested_text": suggested_text,
            "start_offset": sent.start_offset,
            "end_offset": sent.end_offset,
        })

    await _progress(current=len(sentences), total=len(sentences), step="completed")
    return {
        "run_id": run_id,
        "status": "completed",
        "session_id": session_id,
        "sentences": sentence_results,
        "summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
