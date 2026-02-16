"""
Gnosiplexio Data Source Adapters.

Defines the DataSourceAdapter protocol and common data types.
Any structured knowledge database can plug into Gnosiplexio
by implementing this protocol.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
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


@runtime_checkable
class DataSourceAdapter(Protocol):
    """
    Protocol for Gnosiplexio data source adapters.

    Any data source (VF Store, Zotero, OpenAlex, custom DB)
    can plug into Gnosiplexio by implementing these 4 methods.
    """

    def list_works(self) -> List[WorkRecord]:
        """List all available works in the data source."""
        ...

    def get_profile(self, work_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the full profile/record for a work.

        Returns a dict with at least: title, authors, year, doi, abstract.
        May include additional fields like full_text, references, chunks, etc.
        """
        ...

    def get_citations(self, work_id: str) -> List[Citation]:
        """
        Get citation relationships for a work.

        Returns both outgoing (this work cites...) and incoming (cited by...)
        citations, if available.
        """
        ...

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        Search for works matching a query.

        Can be keyword-based or semantic search depending on the adapter.
        """
        ...
