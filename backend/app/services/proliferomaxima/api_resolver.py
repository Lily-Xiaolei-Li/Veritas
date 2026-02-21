from __future__ import annotations

import re
from typing import Any, Dict, Optional

import httpx

CROSSREF_WORK = "https://api.crossref.org/works"
S2_WORK = "https://api.semanticscholar.org/graph/v1/paper"
OPENALEX_WORK = "https://api.openalex.org/works"
TAG_RE = re.compile(r"<[^>]+>")


class ProliferomaximaAPIResolver:
    def __init__(self, mailto: str = "proliferomaxima@local", timeout: float = 30.0):
        self.mailto = mailto
        self.timeout = timeout

    async def resolve(self, ref: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        Resolve reference metadata from multiple sources.
        Priority: CrossRef → Semantic Scholar → OpenAlex
        Returns first result with abstract, or best available metadata.
        """
        doi = (ref.get("doi") or "").strip().lower()
        best_result = None

        if doi:
            # Try all sources with DOI
            for fetch_fn in [self._crossref_by_doi, self._semanticscholar_by_doi, self._openalex_by_doi]:
                result = await fetch_fn(doi)
                if result:
                    if not best_result:
                        best_result = result
                    if result.get("abstract"):
                        return result  # Found abstract, done!
            return best_result

        # No DOI - try title search
        title = str(ref.get("title") or "").strip()
        if not title:
            return None

        # CrossRef title search
        result = await self._crossref_by_title(title)
        if result:
            if result.get("abstract"):
                return result
            best_result = result
            # Got DOI from title search? Try other sources for abstract
            found_doi = (result.get("doi") or "").strip().lower()
            if found_doi:
                for fetch_fn in [self._semanticscholar_by_doi, self._openalex_by_doi]:
                    fallback = await fetch_fn(found_doi)
                    if fallback and fallback.get("abstract"):
                        # Merge: keep CrossRef metadata, use fallback abstract
                        result["abstract"] = fallback["abstract"]
                        result["source"] = f"crossref+{fallback.get('source', 'other')}"
                        return result

        return best_result

    async def _crossref_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        headers = {"User-Agent": f"Proliferomaxima/1.0 (mailto:{self.mailto})"}
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            r = await client.get(f"{CROSSREF_WORK}/{doi}")
            if r.status_code != 200:
                return None
            msg = (r.json() or {}).get("message") or {}
        return self._crossref_to_record(msg)

    async def _crossref_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        headers = {"User-Agent": f"Proliferomaxima/1.0 (mailto:{self.mailto})"}
        params = {"query.bibliographic": title, "rows": 1}
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
            r = await client.get(CROSSREF_WORK, params=params)
            if r.status_code != 200:
                return None
            items = (((r.json() or {}).get("message") or {}).get("items") or [])
            if not items:
                return None
        return self._crossref_to_record(items[0])

    async def _semanticscholar_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        fields = "title,year,abstract,authors,externalIds,venue"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(f"{S2_WORK}/DOI:{doi}", params={"fields": fields})
                if r.status_code != 200:
                    return None
                data = r.json() or {}
        except Exception:
            return None

        abstract = (data.get("abstract") or "").strip()
        return {
            "title": data.get("title") or "",
            "authors": [a.get("name") for a in (data.get("authors") or []) if a.get("name")],
            "year": data.get("year"),
            "doi": ((data.get("externalIds") or {}).get("DOI") or doi).lower(),
            "journal": data.get("venue"),
            "abstract": abstract,
            "source": "semanticscholar",
        }

    async def _openalex_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Fetch from OpenAlex. Abstract is stored as inverted index, needs reconstruction."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.get(f"{OPENALEX_WORK}/doi:{doi}")
                if r.status_code != 200:
                    return None
                data = r.json() or {}
        except Exception:
            return None

        # Reconstruct abstract from inverted index
        abstract = self._reconstruct_abstract(data.get("abstract_inverted_index"))

        # Extract authors
        authors = []
        for authorship in data.get("authorships") or []:
            author = authorship.get("author") or {}
            name = author.get("display_name")
            if name:
                authors.append(name)

        # Extract year from publication_date
        year = None
        pub_date = data.get("publication_date") or ""
        if pub_date and len(pub_date) >= 4:
            try:
                year = int(pub_date[:4])
            except ValueError:
                pass

        return {
            "title": data.get("title") or "",
            "authors": authors,
            "year": year,
            "doi": (data.get("doi") or "").replace("https://doi.org/", "").lower() or doi.lower(),
            "journal": ((data.get("primary_location") or {}).get("source") or {}).get("display_name"),
            "abstract": abstract,
            "source": "openalex",
        }

    def _reconstruct_abstract(self, inverted_index: Optional[Dict[str, list]]) -> str:
        """Reconstruct abstract text from OpenAlex inverted index format."""
        if not inverted_index or not isinstance(inverted_index, dict):
            return ""
        # inverted_index: {"word": [position1, position2, ...], ...}
        # Rebuild by placing each word at its positions
        words: Dict[int, str] = {}
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
        if not words:
            return ""
        max_pos = max(words.keys())
        result = [words.get(i, "") for i in range(max_pos + 1)]
        return " ".join(result).strip()

    def _crossref_to_record(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        title = (msg.get("title") or [""])[0] if isinstance(msg.get("title"), list) else (msg.get("title") or "")
        authors = []
        for a in msg.get("author") or []:
            name = " ".join([str(a.get("given") or "").strip(), str(a.get("family") or "").strip()]).strip()
            if name:
                authors.append(name)
        year = None
        parts = ((msg.get("issued") or {}).get("date-parts") or [])
        if parts and isinstance(parts[0], list) and parts[0]:
            year = parts[0][0]

        abstract = TAG_RE.sub(" ", msg.get("abstract") or "").strip()
        abstract = " ".join(abstract.split())

        return {
            "title": title,
            "authors": authors,
            "year": year,
            "doi": (msg.get("DOI") or "").lower() or None,
            "journal": ((msg.get("container-title") or [""])[0] if isinstance(msg.get("container-title"), list) else msg.get("container-title")),
            "abstract": abstract,
            "source": "crossref",
        }
