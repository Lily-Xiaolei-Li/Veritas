"""
Generic Data Source Adapter for Gnosiplexio.

Reads papers from JSON or CSV files. Works without any external
dependencies (no Qdrant, no VF Store needed).

JSON format:
[
  {
    "id": "power_1997",
    "title": "The Audit Society",
    "authors": ["Michael Power"],
    "year": 1997,
    "doi": "10.1093/...",
    "abstract": "...",
    "references": [
      {"id": "meyer_1977", "context": "...", "cited_for": "institutional theory"}
    ]
  }
]

CSV format:
id,title,authors,year,doi,abstract
power_1997,"The Audit Society","Michael Power",1997,"10.1093/...","..."
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .types import Citation, SearchResult, WorkRecord

logger = logging.getLogger("gnosiplexio.adapters.generic")


class GenericAdapter:
    """
    Generic adapter that reads from JSON or CSV files.

    This is the simplest way to get data into Gnosiplexio — just
    provide a JSON file with your papers.
    """

    def __init__(
        self,
        file: Optional[Union[str, Path]] = None,
        data: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize with a file path or in-memory data.

        Args:
            file: Path to a JSON or CSV file.
            data: In-memory list of work dicts.
        """
        self._works: Dict[str, Dict[str, Any]] = {}

        if data:
            self._load_from_list(data)
        elif file:
            self._load_from_file(Path(file))

    def _load_from_file(self, path: Path) -> None:
        """Load works from a JSON or CSV file."""
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".json":
            self._load_json(path)
        elif suffix == ".csv":
            self._load_csv(path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Use .json or .csv")

    def _load_json(self, path: Path) -> None:
        """Load from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            self._load_from_list(data)
        elif isinstance(data, dict) and "works" in data:
            self._load_from_list(data["works"])
        else:
            raise ValueError("JSON must be a list of works or a dict with 'works' key")

        logger.info("Loaded %d works from %s", len(self._works), path)

    def _load_csv(self, path: Path) -> None:
        """Load from a CSV file."""
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                work_id = row.get("id", "")
                if not work_id:
                    continue

                # Parse authors (comma or semicolon separated)
                authors_str = row.get("authors", "")
                authors = [a.strip() for a in authors_str.replace(";", ",").split(",") if a.strip()]

                # Parse year
                year_str = row.get("year", "")
                year = int(year_str) if year_str.isdigit() else None

                self._works[work_id] = {
                    "id": work_id,
                    "title": row.get("title", ""),
                    "authors": authors,
                    "year": year,
                    "doi": row.get("doi", ""),
                    "abstract": row.get("abstract", ""),
                    "type": row.get("type", "paper"),
                    "references": [],
                }

        logger.info("Loaded %d works from CSV %s", len(self._works), path)

    def _load_from_list(self, data: List[Dict[str, Any]]) -> None:
        """Load from an in-memory list of work dicts."""
        for item in data:
            work_id = item.get("id", "")
            if work_id:
                self._works[work_id] = item

    # -- DataSourceAdapter Protocol ------------------------------------------

    def list_works(self) -> List[WorkRecord]:
        """List all works in the data source."""
        results = []
        for work_id, work in self._works.items():
            results.append(WorkRecord(
                id=work_id,
                title=work.get("title", ""),
                authors=work.get("authors", []),
                year=work.get("year"),
                doi=work.get("doi"),
                type=work.get("type", "paper"),
            ))
        return results

    def get_profile(self, work_id: str) -> Optional[Dict[str, Any]]:
        """Get the full profile for a work."""
        return self._works.get(work_id)

    def get_citations(self, work_id: str) -> List[Citation]:
        """Get citations from this work's references."""
        work = self._works.get(work_id)
        if not work:
            return []

        citations = []
        for ref in work.get("references", []):
            citation = Citation(
                citing_id=work_id,
                cited_id=ref.get("id", ref.get("cited_id", "")),
                context=ref.get("context", ""),
                cited_for=ref.get("cited_for", ""),
                sentiment=ref.get("sentiment", "supportive"),
                source_type=ref.get("source_type", "direct"),
            )
            citations.append(citation)

        return citations

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Simple keyword search across titles and abstracts."""
        query_lower = query.lower()
        results = []

        for work_id, work in self._works.items():
            searchable = f"{work.get('title', '')} {work.get('abstract', '')}".lower()
            if query_lower in searchable:
                # Simple relevance: prefer title matches
                score = 1.0 if query_lower in work.get("title", "").lower() else 0.5
                results.append(SearchResult(
                    work_id=work_id,
                    title=work.get("title", ""),
                    score=score,
                    snippet=work.get("abstract", "")[:200],
                ))

        # Sort by score descending
        results.sort(key=lambda r: r.get("score", 0), reverse=True)
        return results[:top_k]

    def __repr__(self) -> str:
        return f"GenericAdapter(works={len(self._works)})"
