#!/usr/bin/env python3
"""Scholar Influence Analyzer - Integrated version for GP-Viz API.

Based on phase2_f5_scholar_influence.py from Veritas project.
Analyzes how a specific scholar (e.g., Power) is cited in the paper corpus.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import requests
from qdrant_client import QdrantClient

LOG = logging.getLogger(__name__)

CATEGORIES = [
    "name-dropping",
    "theoretical foundation",
    "framework",
    "methodological approach",
    "empirical support",
    "critique / opposition",
    "extension / application",
]

SECTION_HINTS = {
    "introduction": ["introduction", "background", "research question", "context", "motivation"],
    "theory": ["literature review", "theoretical", "theory", "framework"],
    "method": ["methodology", "method", "methodological", "data"],
    "results": ["results", "findings", "analysis", "evidence"],
    "discussion": ["discussion", "interpretation"],
    "conclusion": ["conclusion", "concluding remarks", "future"],
    "references": ["references", "bibliography", "reference list", "works cited"],
}


@dataclass
class CitationRecord:
    paper_id: str
    section: str
    cite_kind: str
    context: str
    category: str
    confidence: float
    year: Optional[int] = None


def build_name_aliases(name: str) -> List[str]:
    clean = re.sub(r"\s+", " ", name.strip())
    parts = [p for p in re.split(r"\s+", clean) if len(p) > 1]
    if not parts:
        return []
    aliases = {clean.lower()}
    if len(parts) >= 2:
        aliases.add(parts[-1].lower())
        aliases.add(" ".join(parts[-2:]).lower())
    aliases.update({p.lower() for p in parts})
    return sorted(aliases)


def _contains_alias(text: str, aliases: Sequence[str]) -> bool:
    l = text.lower()
    for a in aliases:
        if len(a) < 2:
            continue
        if a in l:
            return True
    return False


def search_qdrant_for_scholar(
    scholar: str,
    host: str = "host.docker.internal",
    port: int = 6333,
    collection: str = "vf_profiles_slr",
) -> Dict[str, List[Dict]]:
    """Scan all points and return matched paper ids with chunks."""
    client = QdrantClient(host=host, port=port)
    aliases = build_name_aliases(scholar)
    hits: Dict[str, List[Dict]] = defaultdict(list)

    offset = None
    total_scanned = 0
    while True:
        batch, next_offset = client.scroll(
            collection_name=collection,
            limit=128,
            offset=offset,
            with_payload=["paper_id", "chunk_id", "text", "year", "journal", "authors"],
            with_vectors=False,
        )
        if not batch:
            break

        for point in batch:
            total_scanned += 1
            p = point.payload or {}
            paper_id = str(p.get("paper_id") or "unknown")
            text = str(p.get("text") or "")
            
            if _contains_alias(text, aliases):
                hits[paper_id].append({
                    "chunk_id": str(p.get("chunk_id") or ""),
                    "text": " ".join(text.split())[:500],
                    "year": p.get("year"),
                    "journal": p.get("journal"),
                    "authors": p.get("authors"),
                })

        if next_offset is None:
            break
        offset = next_offset

    LOG.info("Qdrant scan completed", extra={"scanned": total_scanned, "hits": len(hits)})
    return dict(hits)


def classify_citation(context: str, scholar: str) -> Tuple[str, float]:
    """Classify citation nature using local heuristics (fast, no external API)."""
    ctx = context.lower()
    
    # Check for specific patterns
    if any(k in ctx for k in ["framework", "theory of", "theoretical lens", "based on", "drawing on"]):
        return "theoretical foundation", 0.75
    if any(k in ctx for k in ["framework", "conceptual framework", "analytical framework"]):
        return "framework", 0.72
    if any(k in ctx for k in ["method", "methodology", "approach", "using", "adopt"]):
        return "methodological approach", 0.68
    if any(k in ctx for k in ["empirical", "evidence", "findings support", "consistent with"]):
        return "empirical support", 0.65
    if any(k in ctx for k in ["critique", "criticism", "limitation", "challenge", "against", "however", "but"]):
        return "critique / opposition", 0.62
    if any(k in ctx for k in ["extend", "application", "apply", "building on", " Drawing on"]):
        return "extension / application", 0.58
    if any(k in ctx for k in ["cite", "according to", "as noted by", "as argued by"]):
        return "name-dropping", 0.45
    
    return "name-dropping", 0.3


def analyze_citations(qdrant_matches: Dict[str, List[Dict]], scholar: str) -> Dict:
    """Analyze citations from Qdrant chunks."""
    aliases = build_name_aliases(scholar)
    mentions: List[CitationRecord] = []
    
    for paper_id, chunks in qdrant_matches.items():
        paper_year = None
        for chunk in chunks:
            if chunk.get("year"):
                try:
                    paper_year = int(chunk["year"])
                    break
                except:
                    pass
        
        for chunk in chunks:
            text = chunk.get("text", "")
            # Detect section from context
            section = "unknown"
            text_lower = text.lower()
            for sec, hints in SECTION_HINTS.items():
                for hint in hints:
                    if hint in text_lower[:200]:
                        section = sec
                        break
                if section != "unknown":
                    break
            
            # Classify citation
            cat, conf = classify_citation(text, scholar)
            
            mentions.append(CitationRecord(
                paper_id=paper_id,
                section=section,
                cite_kind="in-text",
                context=text[:500],
                category=cat,
                confidence=conf,
                year=paper_year,
            ))
    
    # Deduplicate
    seen = set()
    uniq_mentions = []
    for m in mentions:
        key = (m.paper_id, m.context[:100])
        if key not in seen:
            seen.add(key)
            uniq_mentions.append(m)
    mentions = uniq_mentions
    
    # Aggregate stats
    cat_counter = Counter(m.category for m in mentions)
    section_counter = Counter(m.section for m in mentions)
    year_counter = Counter()
    for m in mentions:
        if m.year:
            year_counter[str(m.year)] += 1
    
    # Per-paper stats
    per_paper = defaultdict(lambda: {"count": 0, "categories": Counter(), "years": []})
    for m in mentions:
        per_paper[m.paper_id]["count"] += 1
        per_paper[m.paper_id]["categories"][m.category] += 1
        if m.year:
            per_paper[m.paper_id]["years"].append(m.year)
    
    return {
        "meta": {
            "scholar": scholar,
            "aliases": aliases,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_citations": len(mentions),
            "papers_with_citation": len(set(m.paper_id for m in mentions)),
        },
        "categories": {k: int(v) for k, v in sorted(cat_counter.items(), key=lambda x: -x[1])},
        "sections": {k: int(v) for k, v in sorted(section_counter.items(), key=lambda x: -x[1])},
        "time_trend": {k: int(v) for k, v in sorted(year_counter.items())},
        "per_paper": {
            pid: {
                "count": data["count"],
                "dominant_category": data["categories"].most_common(1)[0][0] if data["categories"] else "unknown",
                "years": data["years"],
            }
            for pid, data in sorted(per_paper.items(), key=lambda x: -x[1]["count"])
        },
        "citations": [
            {
                "paper_id": m.paper_id,
                "year": m.year,
                "section": m.section,
                "category": m.category,
                "confidence": m.confidence,
                "context": m.context[:300],
            }
            for m in sorted(mentions, key=lambda x: x.confidence, reverse=True)[:50]
        ],
    }


def generate_time_series_plot_data(analysis: Dict) -> Dict:
    """Generate data for time series visualization."""
    trend = analysis.get("time_trend", {})
    years = sorted(trend.keys())
    counts = [trend[y] for y in years]
    
    # Category breakdown per year (approximate from citation records)
    cat_by_year = defaultdict(lambda: Counter())
    for cite in analysis.get("citations", []):
        if cite.get("year"):
            cat_by_year[str(cite["year"])][cite["category"]] += 1
    
    # Build stacked data
    categories = list(analysis.get("categories", {}).keys())
    stacked_data = []
    for year in years:
        row = {"year": int(year), "total": trend.get(year, 0)}
        for cat in categories:
            row[cat] = cat_by_year[year].get(cat, 0)
        stacked_data.append(row)
    
    return {
        "years": [int(y) for y in years],
        "counts": counts,
        "categories": categories,
        "stacked_data": stacked_data,
    }


def run_scholar_analysis(scholar: str, qdrant_host: str = "host.docker.internal", qdrant_port: int = 6333, collection: str = "vf_profiles_slr") -> Dict:
    """Main entry point for scholar influence analysis."""
    LOG.info(f"Starting scholar analysis for: {scholar}")
    
    # Search Qdrant
    matches = search_qdrant_for_scholar(scholar, host=qdrant_host, port=qdrant_port, collection=collection)
    
    if not matches:
        return {
            "meta": {"scholar": scholar, "timestamp": datetime.utcnow().isoformat() + "Z"},
            "error": "No mentions found in corpus",
            "total_citations": 0,
        }
    
    # Analyze
    analysis = analyze_citations(matches, scholar)
    
    # Add plot data
    analysis["plot_data"] = generate_time_series_plot_data(analysis)
    
    return analysis
