"""Report generator for checker results.

Produces two outputs:
- Annotated Markdown (human-readable)
- Structured JSON (for frontend annotation layer)
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.logging_config import get_logger

from .ai_detector import AIFlag
from .classifier import ClassificationResult, CitationVerification
from .flow_checker import FlowCheck
from .rag_searcher import SentenceRAGResults
from .splitter import Sentence

logger = get_logger("checker.report_generator")

# Colour mapping
TYPE_COLOURS = {
    "CITE_NEEDED": "#EF4444",   # Red
    "COMMON": "#22C55E",         # Green
    "OWN_EMPIRICAL": "#3B82F6",  # Blue
    "OWN_CONTRIBUTION": "#EAB308",  # Gold
}

TYPE_EMOJI = {
    "CITE_NEEDED": "🔴",
    "COMMON": "✅",
    "OWN_EMPIRICAL": "🔵",
    "OWN_CONTRIBUTION": "🟡",
}


def generate_markdown_report(
    sentences: List[Sentence],
    classifications: List[ClassificationResult],
    ai_flags: List[List[AIFlag]],
    flow_checks: List[FlowCheck],
    rag_results: List[SentenceRAGResults],
    run_id: str,
    artifact_name: str = "Unknown",
) -> str:
    """Generate annotated Markdown report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    # Compute summary
    summary = _compute_summary(classifications, ai_flags, flow_checks)

    lines = [
        f"# Sentence Checker Report: {artifact_name}",
        f"**Run Date:** {now}  ",
        f"**Sentences Analysed:** {summary['total_sentences']}  ",
        f"**Issues Found:** {summary['cite_needed']} citations needed, "
        f"{summary['ai_patterns']} AI patterns, {summary['flow_issues']} flow issues",
        "",
        "## Annotated Text",
        "",
    ]

    for i, sent in enumerate(sentences):
        cls = classifications[i] if i < len(classifications) else None
        flags = ai_flags[i] if i < len(ai_flags) else []
        flow = flow_checks[i] if i < len(flow_checks) else None
        rag = rag_results[i] if i < len(rag_results) else None

        cls_type = cls.type if cls else "COMMON"
        confidence = cls.confidence if cls else "LOW"
        emoji = TYPE_EMOJI.get(cls_type, "❓")

        lines.append(f'[{emoji} {cls_type} | {confidence}] "{sent.text}"')

        if cls and cls.reasoning:
            lines.append(f"> **Reasoning:** {cls.reasoning}")

        if cls and cls.suggested_citations:
            for cit in cls.suggested_citations:
                lines.append(f"> **Suggestion:** {cit}")

        if cls and cls.citation_verification:
            for v in cls.citation_verification:
                status_emoji = "✅" if v.status == "VERIFIED" else "🟠" if v.status == "MISATTRIBUTED" else "❓"
                lines.append(f"> {status_emoji} {v.citation}: {v.status} {v.note}")

        if rag and rag.results:
            top = rag.results[0]
            lines.append(f"> **RAG Match:** {top.source} (similarity: {top.score:.2f})")

        if flags:
            for f in flags:
                lines.append(f"> 🟣 AI Pattern: `{f.pattern_name}` — {f.note}")

        if flow and flow.prev_connection in ("WEAK", "MISSING"):
            lines.append(f"> ⚪ Flow: {flow.prev_connection} transition from previous sentence")
            if flow.suggestion:
                lines.append(f"> Suggest: {flow.suggestion}")

        lines.append("")

    return "\n".join(lines)


def generate_json_report(
    sentences: List[Sentence],
    classifications: List[ClassificationResult],
    ai_flags: List[List[AIFlag]],
    flow_checks: List[FlowCheck],
    rag_results: List[SentenceRAGResults],
    run_id: str,
    artifact_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate structured JSON report for frontend annotation layer."""
    summary = _compute_summary(classifications, ai_flags, flow_checks)
    
    annotations = []
    for i, sent in enumerate(sentences):
        cls = classifications[i] if i < len(classifications) else None
        flags = ai_flags[i] if i < len(ai_flags) else []
        flow = flow_checks[i] if i < len(flow_checks) else None
        rag = rag_results[i] if i < len(rag_results) else None

        cls_type = cls.type if cls else "COMMON"
        
        annotation = {
            "sentence_id": sent.id,
            "start_offset": sent.start_offset,
            "end_offset": sent.end_offset,
            "text": sent.text,
            "type": cls_type,
            "confidence": cls.confidence if cls else "LOW",
            "colour": TYPE_COLOURS.get(cls_type, "#9CA3AF"),
            "reasoning": cls.reasoning if cls else "",
            "suggested_citations": [
                {"ref": c, "source": "RAG"} for c in (cls.suggested_citations if cls else [])
            ],
            "existing_citations_status": [
                {"citation": v.citation, "status": v.status, "note": v.note}
                for v in (cls.citation_verification if cls else [])
            ],
            "ai_flags": [
                {"pattern": f.pattern_name, "matched": f.matched_text, "note": f.note, "severity": f.severity}
                for f in flags
            ],
            "flow": {
                "prev": flow.prev_connection if flow else None,
                "suggestion": flow.suggestion if flow else None,
                "topic_shift": flow.topic_shift if flow else False,
            },
        }
        annotations.append(annotation)

    return {
        "artifact_id": artifact_id or str(uuid4()),
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "annotations": annotations,
    }


def _compute_summary(
    classifications: List[ClassificationResult],
    ai_flags: List[List[AIFlag]],
    flow_checks: List[FlowCheck],
) -> Dict[str, int]:
    """Compute summary statistics."""
    summary = {
        "total_sentences": len(classifications),
        "cite_needed": 0,
        "common": 0,
        "own_empirical": 0,
        "own_contribution": 0,
        "ai_patterns": 0,
        "flow_issues": 0,
        "misattributed": 0,
        "verified_citations": 0,
    }

    for cls in classifications:
        if cls.type == "CITE_NEEDED":
            summary["cite_needed"] += 1
        elif cls.type == "COMMON":
            summary["common"] += 1
        elif cls.type == "OWN_EMPIRICAL":
            summary["own_empirical"] += 1
        elif cls.type == "OWN_CONTRIBUTION":
            summary["own_contribution"] += 1

        for v in cls.citation_verification:
            if v.status == "VERIFIED":
                summary["verified_citations"] += 1
            elif v.status == "MISATTRIBUTED":
                summary["misattributed"] += 1

    for flags in ai_flags:
        summary["ai_patterns"] += len(flags)

    for flow in flow_checks:
        if flow.prev_connection in ("WEAK", "MISSING"):
            summary["flow_issues"] += 1

    return summary
