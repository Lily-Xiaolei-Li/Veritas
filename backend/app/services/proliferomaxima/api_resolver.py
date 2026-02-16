from __future__ import annotations

import re
from typing import Any, Dict, Optional

import httpx

CROSSREF_WORK = "https://api.crossref.org/works"
S2_WORK = "https://api.semanticscholar.org/graph/v1/paper"
TAG_RE = re.compile(r"<[^>]+>")


class ProliferomaximaAPIResolver:
    def __init__(self, mailto: str = "proliferomaxima@local", timeout: float = 30.0):
        self.mailto = mailto
        self.timeout = timeout

    async def resolve(self, ref: Dict[str, Any]) -> Dict[str, Any] | None:
        doi = (ref.get("doi") or "").strip().lower()

        if doi:
            result = await self._crossref_by_doi(doi)
            if result and result.get("abstract"):
                return result
            fallback = await self._semanticscholar_by_doi(doi)
            if fallback and fallback.get("abstract"):
                return fallback
            return result or fallback

        title = str(ref.get("title") or "").strip()
        if not title:
            return None
        return await self._crossref_by_title(title)

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
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(f"{S2_WORK}/DOI:{doi}", params={"fields": fields})
            if r.status_code != 200:
                return None
            data = r.json() or {}

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
