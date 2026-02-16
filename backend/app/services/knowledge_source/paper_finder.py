from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

CROSSREF_API = "https://api.crossref.org/works"
SEMANTIC_SCHOLAR_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"


def _safe_get_json(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "AgentB-Knowledge/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


@dataclass
class PaperCandidate:
    title: str
    authors: list[str]
    year: int | None
    journal: str | None
    doi: str | None
    is_open_access: bool | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal,
            "doi": self.doi,
            "is_open_access": self.is_open_access,
        }


class PaperFinder:
    def search(self, query: str, rows: int = 5) -> list[dict[str, Any]]:
        results = self._search_crossref(query=query, rows=rows)
        if not results:
            results = self._search_semantic_scholar(query=query, rows=rows)
        return results

    def _search_crossref(self, query: str, rows: int = 5) -> list[dict[str, Any]]:
        url = f"{CROSSREF_API}?query={urllib.parse.quote(query)}&rows={rows}"
        data = _safe_get_json(url)
        if not data:
            return []

        items = data.get("message", {}).get("items", [])
        out: list[dict[str, Any]] = []
        for item in items:
            title = ""
            title_raw = item.get("title") or []
            if isinstance(title_raw, list) and title_raw:
                title = str(title_raw[0])

            authors = []
            for a in item.get("author", []) or []:
                given = a.get("given", "")
                family = a.get("family", "")
                full = f"{given} {family}".strip()
                if full:
                    authors.append(full)

            year = None
            date_parts = ((item.get("published-print") or {}).get("date-parts") or
                          (item.get("published-online") or {}).get("date-parts") or [])
            if date_parts and isinstance(date_parts[0], list) and date_parts[0]:
                try:
                    year = int(date_parts[0][0])
                except Exception:
                    year = None

            journal = None
            container = item.get("container-title") or []
            if container:
                journal = str(container[0])

            out.append(
                PaperCandidate(
                    title=title,
                    authors=authors,
                    year=year,
                    journal=journal,
                    doi=item.get("DOI"),
                    is_open_access=bool(item.get("is-oa")) if "is-oa" in item else None,
                ).to_dict()
            )

        return out

    def _search_semantic_scholar(self, query: str, rows: int = 5) -> list[dict[str, Any]]:
        fields = "title,authors,year,venue,externalIds,isOpenAccess"
        url = (
            f"{SEMANTIC_SCHOLAR_SEARCH}?query={urllib.parse.quote(query)}"
            f"&limit={rows}&fields={urllib.parse.quote(fields)}"
        )
        data = _safe_get_json(url)
        if not data:
            return []

        out: list[dict[str, Any]] = []
        for item in data.get("data", []) or []:
            out.append(
                PaperCandidate(
                    title=item.get("title", ""),
                    authors=[a.get("name", "") for a in item.get("authors", []) if a.get("name")],
                    year=item.get("year"),
                    journal=item.get("venue"),
                    doi=(item.get("externalIds") or {}).get("DOI"),
                    is_open_access=item.get("isOpenAccess"),
                ).to_dict()
            )
        return out
