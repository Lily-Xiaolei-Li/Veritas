"""
Common data types for Gnosiplexio adapters.
"""
from __future__ import annotations

from typing import List, Optional
from typing_extensions import TypedDict


class WorkRecord(TypedDict, total=False):
    """Minimal work record returned by list_works."""
    id: str
    title: str
    authors: List[str]
    year: Optional[int]
    doi: Optional[str]
    type: str  # paper, book, chapter, report


class Citation(TypedDict, total=False):
    """Citation relationship between two works."""
    citing_id: str
    cited_id: str
    context: str          # The sentence/paragraph where the citation appears
    cited_for: str        # Why the work is cited (semantic summary)
    sentiment: str        # supportive, critical, neutral, extends
    source_type: str      # direct (from full text) or inferred (from abstract)


class SearchResult(TypedDict, total=False):
    """Search result from the adapter."""
    work_id: str
    title: str
    score: float
    snippet: str
