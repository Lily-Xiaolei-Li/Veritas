from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PaperRecord:
    """Normalized paper payload used by API/UI responses."""

    paper_id: str
    title: str
    authors: str = ""
    year: str | None = None
    abstract: str | None = None
    keywords: str | None = None
    source: str | None = None
    doi: str | None = None
    relevance: float | None = None
    pdf_path: str | None = None
    raw_payload: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "source": self.source,
            "doi": self.doi,
            "relevance": self.relevance,
            "pdf_path": self.pdf_path,
            "payload": self.raw_payload or {},
        }