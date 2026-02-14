"""
Paper Download Service for Agent-B Research.

Provides OA + EZProxy download pipeline for academic papers.
Strategy: Unpaywall → Semantic Scholar → DOI redirect → EZProxy (Playwright CDP).
"""

from __future__ import annotations

import asyncio
import base64
import csv
import io
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from app.logging_config import get_logger

logger = get_logger("paper_downloader")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNPAYWALL_API = "https://api.unpaywall.org/v2"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper"
CROSSREF_API = "https://api.crossref.org/works"
EZPROXY_TEMPLATE = "https://ezproxy.newcastle.edu.au/login?url=https://doi.org/{doi}"
DEFAULT_EMAIL = "lily.xiaolei.li@outlook.com"
USER_AGENT = "AgentB-Research/1.0 (mailto:{email})"
CDP_URL = "http://127.0.0.1:9222"

# Default PDF output directory
DEFAULT_PDF_DIR = Path(os.environ.get(
    "PAPER_PDF_DIR",
    str(Path.home() / "AgentB-Papers")
))


class DownloadStatus(str, Enum):
    SUCCESS = "success"
    PAYWALL = "paywall"
    NO_DOI = "no_doi_found"
    DOWNLOAD_FAILED = "download_failed"
    NOT_PDF = "not_pdf"
    NO_OA = "no_oa_source"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ERROR = "error"


@dataclass
class PaperResult:
    doi: str = ""
    title: str = ""
    author: str = ""
    year: str = ""
    status: DownloadStatus = DownloadStatus.PENDING
    source: str = ""
    file_path: str = ""
    file_size: int = 0
    error: str = ""
    pdf_url: str = ""

    def to_dict(self) -> dict:
        return {
            "doi": self.doi,
            "title": self.title,
            "author": self.author,
            "year": self.year,
            "status": self.status.value,
            "source": self.source,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "error": self.error,
        }


@dataclass
class BatchJob:
    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "pending"
    total: int = 0
    completed: int = 0
    success: int = 0
    failed: int = 0
    results: list[PaperResult] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "total": self.total,
            "completed": self.completed,
            "success": self.success,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# In-memory job store
_batch_jobs: dict[str, BatchJob] = {}

# SSL context for urllib
_ssl_ctx = ssl.create_default_context()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _api_get(url: str, headers: dict | None = None, timeout: int = 20) -> dict | None:
    """Synchronous JSON GET request."""
    try:
        req = urllib.request.Request(url, headers=headers or {
            "User-Agent": USER_AGENT.format(email=DEFAULT_EMAIL)
        })
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug(f"API GET failed for {url[:80]}: {e}")
        return None


def _title_similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity."""
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0
    return len(wa & wb) / max(len(wa), len(wb))


def sanitize_filename(author: str, year: str, title: str, max_words: int = 6) -> str:
    """Generate Author_Year_First_Words_Of_Title.pdf filename."""
    words = re.sub(r'[^\w\s]', '', title).split()[:max_words]
    title_part = '_'.join(words) if words else 'untitled'
    author = re.sub(r'[^\w]', '', author or 'Unknown')
    return f"{author}_{year or 'XXXX'}_{title_part}.pdf"


def is_valid_pdf(data: bytes) -> bool:
    """Check if data starts with %PDF magic bytes."""
    return data[:5].startswith(b'%PDF')


# ---------------------------------------------------------------------------
# DOI Resolution
# ---------------------------------------------------------------------------

def resolve_doi_crossref(title: str, email: str = DEFAULT_EMAIL) -> str | None:
    """Resolve DOI from title via CrossRef."""
    query = urllib.parse.quote(title[:200])
    url = f"{CROSSREF_API}?query={query}&rows=3&mailto={email}"
    data = _api_get(url, {"User-Agent": USER_AGENT.format(email=email)})
    if not data or "message" not in data:
        return None
    title_lower = title.lower().strip()
    for item in data["message"].get("items", []):
        item_title = " ".join(item.get("title", []))
        if item_title and _title_similarity(title_lower, item_title.lower()) > 0.7:
            return item.get("DOI")
    return None


def resolve_doi_semantic_scholar(title: str) -> str | None:
    """Resolve DOI from title via Semantic Scholar."""
    query = urllib.parse.quote(title[:200])
    url = f"{SEMANTIC_SCHOLAR_API}/search?query={query}&limit=3&fields=externalIds,title"
    data = _api_get(url)
    if not data:
        return None
    title_lower = title.lower().strip()
    for paper in data.get("data", []):
        paper_title = paper.get("title", "")
        if _title_similarity(title_lower, paper_title.lower()) > 0.7:
            ids = paper.get("externalIds", {})
            return ids.get("DOI")
    return None


def resolve_doi(title: str, email: str = DEFAULT_EMAIL) -> str | None:
    """Try CrossRef then Semantic Scholar to resolve DOI from title."""
    doi = resolve_doi_crossref(title, email)
    if doi:
        return doi
    time.sleep(0.5)
    return resolve_doi_semantic_scholar(title)


# ---------------------------------------------------------------------------
# OA PDF URL Finders
# ---------------------------------------------------------------------------

def find_oa_pdf_url(doi: str, email: str = DEFAULT_EMAIL) -> str | None:
    """Find open-access PDF URL for a DOI (Unpaywall → S2 → DOI redirect)."""
    # 1. Unpaywall
    url = f"{UNPAYWALL_API}/{urllib.parse.quote(doi, safe='')}?email={email}"
    data = _api_get(url)
    if data:
        oa = data.get("best_oa_location") or {}
        pdf_url = oa.get("url_for_pdf") or oa.get("url")
        if pdf_url:
            return pdf_url

    time.sleep(0.5)

    # 2. Semantic Scholar
    url = f"{SEMANTIC_SCHOLAR_API}/DOI:{urllib.parse.quote(doi, safe='')}?fields=openAccessPdf"
    data = _api_get(url)
    if data:
        oa_pdf = data.get("openAccessPdf") or {}
        if oa_pdf.get("url"):
            return oa_pdf["url"]

    return None


def _download_pdf_direct(url: str, filepath: str, email: str = DEFAULT_EMAIL) -> tuple[bool, str]:
    """Download PDF from URL directly, verify it's actually a PDF."""
    headers = {
        "User-Agent": USER_AGENT.format(email=email),
        "Accept": "application/pdf,*/*"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60, context=_ssl_ctx) as resp:
            content = resp.read()
            if not is_valid_pdf(content):
                return False, "not_pdf"
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(content)
            return True, str(len(content))
    except Exception as e:
        return False, str(e)[:200]


# ---------------------------------------------------------------------------
# Publisher-specific PDF URL patterns (for EZProxy)
# ---------------------------------------------------------------------------

def _find_publisher_pdf_url(doi: str, page_url: str) -> str | None:
    """Determine publisher-specific PDF URL from the landing page URL."""
    # Emerald
    if "emerald.com" in page_url:
        pdf_url = page_url.replace("/doi/full/", "/doi/pdfplus/").replace("/doi/abs/", "/doi/pdfplus/")
        if "/doi/pdfplus/" in pdf_url:
            return pdf_url

    # Wiley
    if "wiley.com" in page_url:
        m = re.search(r"/doi/(10\.\d+/[^?#\s]+)", page_url)
        if m:
            base = page_url.split("/doi/")[0]
            return f"{base}/doi/pdfdirect/{m.group(1)}?download=true"

    # Taylor & Francis
    if "tandfonline.com" in page_url:
        m = re.search(r"/doi/(?:full|abs)/(10\.\d+/[^?#\s]+)", page_url)
        if m:
            base = page_url.split("/doi/")[0]
            return f"{base}/doi/pdf/{m.group(1)}?needAccess=true"

    # Springer / Nature
    if "springer.com" in page_url or "nature.com" in page_url:
        m = re.search(r"(10\.\d+/[^?#\s]+)", page_url)
        if m:
            return f"https://link.springer.com/content/pdf/{m.group(1)}.pdf"

    # Sage
    if "sagepub.com" in page_url:
        m = re.search(r"/doi/(10\.\d+/[^?#\s]+)", page_url)
        if m:
            return f"https://journals.sagepub.com/doi/pdf/{m.group(1)}"

    # Elsevier / ScienceDirect
    if "sciencedirect.com" in page_url:
        # ScienceDirect PDF URLs are complex; try the pii-based pattern
        m = re.search(r"/pii/(S\w+)", page_url)
        if m:
            return f"https://www.sciencedirect.com/science/article/pii/{m.group(1)}/pdfft"

    return None


# ---------------------------------------------------------------------------
# EZProxy download via Playwright CDP
# ---------------------------------------------------------------------------

async def _download_via_ezproxy(doi: str, output_dir: Path, email: str = DEFAULT_EMAIL) -> PaperResult:
    """Download a paper through university EZProxy using Playwright CDP."""
    result = PaperResult(doi=doi, source="ezproxy")
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        result.status = DownloadStatus.ERROR
        result.error = "playwright not installed"
        return result

    ezproxy_url = EZPROXY_TEMPLATE.format(doi=doi)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(ezproxy_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)

                current_url = page.url

                # Check if login is required
                if "login" in current_url.lower() and "ezproxy" in current_url.lower():
                    login_form = await page.query_selector('input[type="password"]')
                    if login_form:
                        result.status = DownloadStatus.ERROR
                        result.error = "EZProxy login required - please authenticate in Chrome first"
                        await page.close()
                        return result

                # Find PDF URL via publisher patterns
                pdf_url = _find_publisher_pdf_url(doi, current_url)

                # Fallback: try meta tag
                if not pdf_url:
                    pdf_url = await page.evaluate("""() => {
                        const meta = document.querySelector('meta[name="citation_pdf_url"]');
                        return meta ? meta.content : null;
                    }""")

                # Fallback: look for PDF links on page
                if not pdf_url:
                    pdf_links = await page.evaluate("""() => {
                        const links = Array.from(document.querySelectorAll('a[href]'));
                        return links.filter(a => {
                            const href = a.href.toLowerCase();
                            return (href.includes('.pdf') || href.includes('/pdf/') || href.includes('/pdfdirect/'));
                        }).map(a => a.href).slice(0, 3);
                    }""")
                    if pdf_links:
                        pdf_url = pdf_links[0]

                if not pdf_url:
                    result.status = DownloadStatus.DOWNLOAD_FAILED
                    result.error = "No PDF link found on page"
                    await page.close()
                    return result

                result.pdf_url = pdf_url

                # Download via browser fetch (preserves session/cookies)
                fetch_result = await page.evaluate("""async (url) => {
                    try {
                        const response = await fetch(url, {credentials: 'include', redirect: 'follow'});
                        if (!response.ok) return {error: `HTTP ${response.status}`};
                        const buffer = await response.arrayBuffer();
                        const bytes = new Uint8Array(buffer);
                        let binary = '';
                        const chunkSize = 8192;
                        for (let i = 0; i < bytes.length; i += chunkSize) {
                            const chunk = bytes.subarray(i, Math.min(i + chunkSize, bytes.length));
                            binary += String.fromCharCode.apply(null, chunk);
                        }
                        return {data: btoa(binary), size: bytes.length};
                    } catch(e) {
                        return {error: e.message};
                    }
                }""", pdf_url)

                if fetch_result.get("error"):
                    result.status = DownloadStatus.DOWNLOAD_FAILED
                    result.error = fetch_result["error"]
                    await page.close()
                    return result

                pdf_data = base64.b64decode(fetch_result["data"])

                if not is_valid_pdf(pdf_data):
                    result.status = DownloadStatus.NOT_PDF
                    result.error = "Downloaded content is not a valid PDF"
                    await page.close()
                    return result

                # Save file
                clean_doi = re.sub(r'[^\w\-.]', '_', doi)
                filepath = output_dir / f"ezproxy_{clean_doi}.pdf"
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, "wb") as f:
                    f.write(pdf_data)

                result.status = DownloadStatus.SUCCESS
                result.file_path = str(filepath)
                result.file_size = len(pdf_data)

            finally:
                await page.close()

    except Exception as e:
        result.status = DownloadStatus.ERROR
        result.error = str(e)[:200]

    return result


# ---------------------------------------------------------------------------
# Main download function
# ---------------------------------------------------------------------------

async def download_paper(
    doi: str | None = None,
    title: str | None = None,
    output_dir: Path | None = None,
    email: str = DEFAULT_EMAIL,
    use_ezproxy: bool = True,
) -> PaperResult:
    """
    Download a single paper. Strategy:
    1. Resolve DOI if only title provided
    2. Try OA sources (Unpaywall → S2)
    3. If OA fails and use_ezproxy=True, try EZProxy
    """
    output_dir = output_dir or DEFAULT_PDF_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    result = PaperResult(doi=doi or "", title=title or "")

    # Step 1: Resolve DOI if needed
    if not doi and title:
        logger.info(f"Resolving DOI for: {title[:60]}...")
        doi = resolve_doi(title, email)
        if not doi:
            result.status = DownloadStatus.NO_DOI
            result.error = "Could not resolve DOI from title"
            return result
        result.doi = doi
        await asyncio.sleep(0.5)

    if not doi:
        result.status = DownloadStatus.NO_DOI
        result.error = "No DOI or title provided"
        return result

    # Step 2: Try OA sources
    logger.info(f"Looking for OA PDF: {doi}")
    pdf_url = find_oa_pdf_url(doi, email)

    if pdf_url:
        filename = sanitize_filename(result.author, result.year, result.title or doi)
        filepath = str(output_dir / filename)
        ok, info = _download_pdf_direct(pdf_url, filepath, email)
        if ok:
            result.status = DownloadStatus.SUCCESS
            result.source = "oa"
            result.file_path = filepath
            result.file_size = int(info)
            result.pdf_url = pdf_url
            logger.info(f"✅ OA download success: {doi} ({info} bytes)")
            return result
        else:
            logger.info(f"OA download failed for {doi}: {info}")

    # Step 3: Try EZProxy
    if use_ezproxy:
        logger.info(f"Trying EZProxy for: {doi}")
        ezproxy_result = await _download_via_ezproxy(doi, output_dir, email)
        if ezproxy_result.status == DownloadStatus.SUCCESS:
            logger.info(f"✅ EZProxy download success: {doi}")
            return ezproxy_result
        else:
            result.status = ezproxy_result.status
            result.error = ezproxy_result.error
            result.source = "ezproxy_failed"
    else:
        result.status = DownloadStatus.PAYWALL
        result.error = "No OA source found, EZProxy disabled"

    return result


# ---------------------------------------------------------------------------
# Batch download
# ---------------------------------------------------------------------------

async def batch_download(
    dois: list[str],
    output_dir: Path | None = None,
    email: str = DEFAULT_EMAIL,
    use_ezproxy: bool = True,
) -> BatchJob:
    """Start a batch download job (runs in background)."""
    job = BatchJob(total=len(dois))
    _batch_jobs[job.job_id] = job

    # Launch background task
    asyncio.create_task(_run_batch(job, dois, output_dir, email, use_ezproxy))
    return job


async def _run_batch(
    job: BatchJob,
    dois: list[str],
    output_dir: Path | None,
    email: str,
    use_ezproxy: bool,
):
    """Background batch download worker."""
    job.status = "running"
    output_dir = output_dir or DEFAULT_PDF_DIR

    for doi in dois:
        try:
            result = await download_paper(
                doi=doi, output_dir=output_dir, email=email, use_ezproxy=use_ezproxy
            )
            job.results.append(result)
            job.completed += 1
            if result.status == DownloadStatus.SUCCESS:
                job.success += 1
            else:
                job.failed += 1
            job.updated_at = datetime.now().isoformat()
        except Exception as e:
            r = PaperResult(doi=doi, status=DownloadStatus.ERROR, error=str(e)[:200])
            job.results.append(r)
            job.completed += 1
            job.failed += 1

        await asyncio.sleep(1.5)  # Rate limit

    job.status = "completed"
    job.updated_at = datetime.now().isoformat()
    logger.info(f"Batch {job.job_id} complete: {job.success}/{job.total} success")


def get_batch_job(job_id: str) -> BatchJob | None:
    """Get batch job by ID."""
    return _batch_jobs.get(job_id)


# ---------------------------------------------------------------------------
# CSV Parsing
# ---------------------------------------------------------------------------

def parse_google_scholar_csv(content: str) -> list[dict]:
    """Parse Google Scholar CSV export. Returns list of {title, author, year, doi}."""
    papers = []
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        norm = {k.lower().strip(): v.strip() for k, v in row.items() if v}
        title = norm.get("title", "")
        author = norm.get("author", norm.get("authors", ""))
        if author:
            author = author.split(",")[0].split(" and ")[0].strip()
        papers.append({
            "title": title,
            "author": author,
            "year": norm.get("year", norm.get("date", ""))[:4],
            "doi": norm.get("doi", ""),
        })
    return papers


def parse_bibtex(content: str) -> list[dict]:
    """Simple BibTeX parser extracting title, author, year, doi."""
    papers = []
    entries = re.split(r'@\w+\{', content)[1:]  # skip preamble
    for entry in entries:
        fields = {}
        for m in re.finditer(r'(\w+)\s*=\s*\{([^}]*)\}', entry):
            fields[m.group(1).lower()] = m.group(2).strip()
        if fields.get("title") or fields.get("doi"):
            author = fields.get("author", "")
            if author:
                author = author.split(" and ")[0].split(",")[0].strip()
            papers.append({
                "title": fields.get("title", ""),
                "author": author,
                "year": fields.get("year", ""),
                "doi": fields.get("doi", ""),
            })
    return papers
