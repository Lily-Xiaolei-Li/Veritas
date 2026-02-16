from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

UNPAYWALL_API = "https://api.unpaywall.org/v2"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper"
CROSSREF_API = "https://api.crossref.org/works"
DOI_RESOLVER = "https://doi.org"
EZPROXY_TEMPLATE = "https://ezproxy.newcastle.edu.au/login?url=https://doi.org/{doi}"
UNPAYWALL_EMAIL = "lily.xiaolei.li@outlook.com"
USER_AGENT_API = f"AgentB-Knowledge/2.0 (mailto:{UNPAYWALL_EMAIL})"
USER_AGENT_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
MIN_PDF_BYTES = 10 * 1024


class PaperDownloader:
    def __init__(self) -> None:
        self.output_dir = Path("data/downloads/knowledge")
        self.proxy_queue_path = Path("data/downloads/knowledge/proxy_queue.json")
        self._last_call: dict[str, float] = {}

    async def download(self, doi: str | None = None, title: str | None = None, url: str | None = None) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if url:
            direct = await self._download_and_save(url=url, source="direct_url")
            if direct:
                return direct
            return {
                "status": "error",
                "error": "Direct URL download failed or not a valid PDF",
                "source": "direct_url",
            }

        resolved_doi = doi
        metadata: dict[str, Any] = {"title": title or "", "author": "Unknown", "year": "XXXX"}

        if not resolved_doi and title:
            resolved_doi = await self._resolve_doi_from_title(title)
            if not resolved_doi:
                return {"status": "error", "error": "Could not resolve DOI from title", "title": title}

        if resolved_doi:
            unpaywall = await self._try_unpaywall(resolved_doi)
            if unpaywall:
                return unpaywall

            semantic = await self._try_semantic_scholar(resolved_doi)
            if semantic:
                return semantic

            doi_redirect = await self._try_doi_redirect(resolved_doi, metadata)
            if doi_redirect:
                return doi_redirect

            proxy = await self._try_ezproxy(resolved_doi, metadata)
            if proxy:
                return proxy

            return {
                "status": "error",
                "error": "No OA source succeeded; queued for EZProxy/manual download",
                "doi": resolved_doi,
                "paywall_doi": resolved_doi,
                "needs_proxy": True,
                "proxy_url": EZPROXY_TEMPLATE.format(doi=urllib.parse.quote(resolved_doi, safe="")),
            }

        return {"status": "error", "error": "one of doi/title/url is required"}

    async def _try_unpaywall(self, doi: str) -> dict[str, Any] | None:
        await self._rate_limit("unpaywall", 0.12)
        safe = urllib.parse.quote(doi, safe="")
        api_url = f"{UNPAYWALL_API}/{safe}?email={urllib.parse.quote(UNPAYWALL_EMAIL)}"
        data = await asyncio.to_thread(self._json_get, api_url)
        if not data:
            return None

        best = data.get("best_oa_location") or {}
        pdf_url = best.get("url_for_pdf") or best.get("url")
        if not pdf_url:
            return None

        metadata = self._metadata_from_unpaywall(data, doi)
        return await self._download_and_save(pdf_url, source="unpaywall", doi=doi, metadata=metadata)

    async def _try_semantic_scholar(self, doi: str) -> dict[str, Any] | None:
        await self._rate_limit("semantic", 0.35)
        fields = urllib.parse.quote("openAccessPdf,title,authors,year")
        safe_doi = urllib.parse.quote(doi, safe="")
        api_url = f"{SEMANTIC_SCHOLAR_API}/DOI:{safe_doi}?fields={fields}"
        data = await asyncio.to_thread(self._json_get, api_url)
        if not data:
            return None

        oa = data.get("openAccessPdf") or {}
        pdf_url = oa.get("url")
        if not pdf_url:
            return None

        metadata = self._metadata_from_semantic(data, doi)
        return await self._download_and_save(pdf_url, source="semantic_scholar", doi=doi, metadata=metadata)

    async def _try_doi_redirect(self, doi: str, fallback_metadata: dict[str, Any] | None = None) -> dict[str, Any] | None:
        safe_doi = urllib.parse.quote(doi, safe="")
        doi_url = f"{DOI_RESOLVER}/{safe_doi}"

        resp = await asyncio.to_thread(self._binary_get, doi_url)
        if not resp:
            return None

        content_type = (resp.get("content_type") or "").lower()
        final_url = resp.get("final_url") or doi_url
        content = resp.get("content") or b""

        # direct PDF via DOI redirect
        if ("application/pdf" in content_type or final_url.lower().endswith(".pdf")) and self._is_valid_pdf(content):
            metadata = fallback_metadata or {"title": doi, "author": "Unknown", "year": "XXXX"}
            return self._save_result(content=content, metadata=metadata, source="doi_redirect", doi=doi, pdf_url=final_url)

        # publisher heuristic URLs
        candidates = self._publisher_pdf_candidates(final_url, doi)
        for candidate in candidates:
            cand_resp = await asyncio.to_thread(self._binary_get, candidate)
            if not cand_resp:
                continue
            cand_content = cand_resp.get("content") or b""
            if self._is_valid_pdf(cand_content):
                metadata = fallback_metadata or {"title": doi, "author": "Unknown", "year": "XXXX"}
                return self._save_result(content=cand_content, metadata=metadata, source="doi_redirect_pattern", doi=doi, pdf_url=candidate)

        return None

    async def _try_ezproxy(self, doi: str, metadata: dict[str, Any] | None = None) -> dict[str, Any] | None:
        await self._rate_limit("ezproxy", 6.0)
        proxy_url = EZPROXY_TEMPLATE.format(doi=urllib.parse.quote(doi, safe=""))

        queued = {
            "doi": doi,
            "proxy_url": proxy_url,
            "status": "needs_proxy",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "publisher_selectors": {
                "elsevier": ["a[href*='pdfft']", "a[href*='/full/pdf']"],
                "emerald": ["a[href*='/insight/content/doi/'][href*='/full/pdf']"],
                "wiley": ["a[href*='/pdfdirect/']"],
                "tandf": ["a[href*='/doi/pdf/']"],
                "generic": ["a[href$='.pdf']", "meta[name='citation_pdf_url']"],
            },
            "note": "Use OpenClaw browser profile=chrome and fetch PDF inside browser session (base64 export).",
            "metadata": metadata or {},
        }

        queue = []
        if self.proxy_queue_path.exists():
            try:
                queue = json.loads(self.proxy_queue_path.read_text(encoding="utf-8"))
            except Exception:
                queue = []
        if not any((item.get("doi") == doi) for item in queue if isinstance(item, dict)):
            queue.append(queued)
            self.proxy_queue_path.parent.mkdir(parents=True, exist_ok=True)
            self.proxy_queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "status": "error",
            "error": "Paywalled paper requires EZProxy browser workflow",
            "doi": doi,
            "paywall_doi": doi,
            "needs_proxy": True,
            "proxy_url": proxy_url,
            "proxy_queue_path": str(self.proxy_queue_path),
        }

    async def _download_and_save(
        self,
        url: str,
        source: str,
        doi: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        resp = await asyncio.to_thread(self._binary_get, url)
        if not resp:
            return None

        content = resp.get("content") or b""
        content_type = (resp.get("content_type") or "").lower()
        final_url = resp.get("final_url") or url

        if "pdf" not in content_type and not final_url.lower().endswith(".pdf"):
            if not self._is_valid_pdf(content):
                return None

        if not self._is_valid_pdf(content):
            return None

        meta = metadata or {"title": doi or "paper", "author": "Unknown", "year": "XXXX"}
        return self._save_result(content=content, metadata=meta, source=source, doi=doi, pdf_url=final_url)

    def _save_result(
        self,
        content: bytes,
        metadata: dict[str, Any],
        source: str,
        doi: str | None,
        pdf_url: str,
    ) -> dict[str, Any]:
        filename = self._safe_name(metadata.get("author"), metadata.get("year"), metadata.get("title") or doi or "paper")
        path = self.output_dir / filename
        path.write_bytes(content)

        return {
            "status": "success",
            "source": source,
            "doi": doi,
            "title": metadata.get("title") or "",
            "author": metadata.get("author") or "Unknown",
            "year": metadata.get("year") or "XXXX",
            "file_path": str(path),
            "file_size": len(content),
            "pdf_url": pdf_url,
        }

    async def _resolve_doi_from_title(self, title: str) -> str | None:
        # CrossRef first (~1 req/s)
        await self._rate_limit("crossref", 1.0)
        crossref_url = f"{CROSSREF_API}?query={urllib.parse.quote(title[:200])}&rows=3&mailto={urllib.parse.quote(UNPAYWALL_EMAIL)}"
        cross = await asyncio.to_thread(self._json_get, crossref_url)
        if cross:
            for item in (cross.get("message", {}).get("items", []) or []):
                item_title = " ".join(item.get("title") or [])
                if item_title and self._title_similarity(title, item_title) > 0.7:
                    doi = item.get("DOI")
                    if doi:
                        return str(doi)

        # Semantic Scholar fallback
        await self._rate_limit("semantic", 0.35)
        s2_url = (
            f"{SEMANTIC_SCHOLAR_API}/search?query={urllib.parse.quote(title[:200])}"
            "&limit=3&fields=externalIds,title"
        )
        s2 = await asyncio.to_thread(self._json_get, s2_url)
        if s2:
            for paper in (s2.get("data") or []):
                p_title = str(paper.get("title") or "")
                if p_title and self._title_similarity(title, p_title) > 0.7:
                    doi = ((paper.get("externalIds") or {}).get("DOI"))
                    if doi:
                        return str(doi)
        return None

    def _metadata_from_unpaywall(self, data: dict[str, Any], doi: str) -> dict[str, Any]:
        z_authors = data.get("z_authors") or []
        author = "Unknown"
        if z_authors:
            first = z_authors[0] or {}
            family = str(first.get("family") or "").strip()
            given = str(first.get("given") or "").strip()
            author = family or given or "Unknown"
        year = data.get("year") or "XXXX"
        title = data.get("title") or doi
        return {"author": author, "year": year, "title": title}

    def _metadata_from_semantic(self, data: dict[str, Any], doi: str) -> dict[str, Any]:
        author = "Unknown"
        authors = data.get("authors") or []
        if authors:
            first = authors[0] or {}
            name = str(first.get("name") or "").strip()
            if name:
                author = name.split()[-1]
        year = data.get("year") or "XXXX"
        title = data.get("title") or doi
        return {"author": author, "year": year, "title": title}

    def _publisher_pdf_candidates(self, final_url: str, doi: str) -> list[str]:
        candidates: list[str] = []
        parsed = urllib.parse.urlparse(final_url)
        lower = final_url.lower()

        # meta-like common patterns based on landing page
        if "mdpi.com" in lower and not lower.endswith(".pdf"):
            candidates.append(final_url.rstrip("/") + "/pdf")
        if "hindawi.com" in lower and "/journals/" in lower:
            candidates.append(final_url.rstrip("/") + ".pdf")
        if "scielo" in lower and "/pdf/" not in lower:
            candidates.append(final_url.rstrip("/") + "/pdf")
        if "sciencedirect.com" in lower and "/science/article/pii/" in lower:
            candidates.append(final_url.rstrip("/") + "/pdfft")
        if "emerald.com" in lower and "/doi/" in lower and "/full/" in lower:
            candidates.append(final_url.replace("/doi/full/", "/insight/content/doi/").rstrip("/") + "/full/pdf")
        if "wiley.com" in lower and "/doi/" in lower:
            safe_doi = urllib.parse.quote(doi, safe="/")
            candidates.append(f"{parsed.scheme}://{parsed.netloc}/doi/pdfdirect/{safe_doi}")
        if "tandfonline.com" in lower and "/doi/" in lower:
            safe_doi = urllib.parse.quote(doi, safe="/")
            candidates.append(f"{parsed.scheme}://{parsed.netloc}/doi/pdf/{safe_doi}?needAccess=true")

        # generic
        candidates.append(final_url.rstrip("/") + ".pdf")
        # de-dup order-preserving
        seen: set[str] = set()
        out: list[str] = []
        for c in candidates:
            if c not in seen:
                out.append(c)
                seen.add(c)
        return out

    def _json_get(self, url: str, timeout: int = 30) -> dict[str, Any] | None:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT_API, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", errors="ignore"))
        except Exception as e:
            logger.debug("json_get failed for %s: %s", url, e)
            return None

    def _binary_get(self, url: str, timeout: int = 60) -> dict[str, Any] | None:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/pdf,text/html,*/*;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                headers = resp.headers
                content_type = headers.get("Content-Type", "")
                final_url = resp.geturl()
                content = resp.read()
                return {
                    "content": content,
                    "content_type": content_type,
                    "final_url": final_url,
                    "status": getattr(resp, "status", 200),
                }
        except Exception as e:
            logger.debug("binary_get failed for %s: %s", url, e)
            return None

    def _is_valid_pdf(self, content: bytes) -> bool:
        return bool(content and content.startswith(b"%PDF") and len(content) > MIN_PDF_BYTES)

    async def _rate_limit(self, key: str, min_interval_s: float) -> None:
        now = time.monotonic()
        last = self._last_call.get(key, 0.0)
        wait = min_interval_s - (now - last)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_call[key] = time.monotonic()

    def _slug_words(self, text: str, max_words: int = 6) -> str:
        words = re.sub(r"[^\w\s]", "", text or "").split()
        return "_".join(words[:max_words]) or "untitled"

    def _safe_name(self, author: str | None, year: int | str | None, title: str) -> str:
        author_part = re.sub(r"[^\w]", "", author or "Unknown") or "Unknown"
        year_part = str(year or "XXXX")
        return f"{author_part}_{year_part}_{self._slug_words(title)}.pdf"

    def _title_similarity(self, a: str, b: str) -> float:
        wa = set(re.sub(r"[^\w\s]", " ", (a or "").lower()).split())
        wb = set(re.sub(r"[^\w\s]", " ", (b or "").lower()).split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / max(len(wa), len(wb))
