"""Paper Download API routes.

Endpoints:
- POST /papers/download        — single paper download
- POST /papers/batch-download  — batch download (async)
- GET  /papers/batch-download/{job_id} — batch progress
- POST /papers/import-csv      — import Google Scholar CSV
- GET  /papers/downloads       — list downloaded PDFs
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.logging_config import get_logger
from app.services.paper_downloader import (
    DEFAULT_PDF_DIR,
    BatchJob,
    batch_download,
    download_paper,
    get_batch_job,
    parse_bibtex,
    parse_google_scholar_csv,
)

router = APIRouter(prefix="/papers", tags=["papers"])
logger = get_logger("paper_routes")


# =============================================================================
# Schemas
# =============================================================================


class SingleDownloadRequest(BaseModel):
    doi: Optional[str] = Field(None, description="DOI of the paper")
    title: Optional[str] = Field(None, description="Title (used for DOI resolution if no DOI)")
    use_ezproxy: bool = Field(True, description="Fall back to EZProxy if OA fails")


class SingleDownloadResponse(BaseModel):
    doi: str
    title: str
    status: str
    source: str
    file_path: str
    file_size: int
    error: str


class BatchDownloadRequest(BaseModel):
    dois: list[str] = Field(..., description="List of DOIs to download")
    use_ezproxy: bool = Field(True, description="Fall back to EZProxy if OA fails")


class BatchDownloadResponse(BaseModel):
    job_id: str
    status: str
    total: int
    message: str


class BatchStatusResponse(BaseModel):
    job_id: str
    status: str
    total: int
    completed: int
    success: int
    failed: int
    results: list[dict]


class DownloadedFileInfo(BaseModel):
    filename: str
    size: int
    path: str


# =============================================================================
# Routes
# =============================================================================


@router.post("/download", response_model=SingleDownloadResponse)
async def download_single_paper(req: SingleDownloadRequest):
    """Download a single paper by DOI or title.

    Strategy: OA sources first (Unpaywall → Semantic Scholar),
    then EZProxy if enabled.
    """
    if not req.doi and not req.title:
        raise HTTPException(status_code=400, detail="Provide either doi or title")

    result = await download_paper(
        doi=req.doi,
        title=req.title,
        use_ezproxy=req.use_ezproxy,
    )
    return SingleDownloadResponse(
        doi=result.doi,
        title=result.title,
        status=result.status.value,
        source=result.source,
        file_path=result.file_path,
        file_size=result.file_size,
        error=result.error,
    )


@router.post("/batch-download", response_model=BatchDownloadResponse)
async def start_batch_download(req: BatchDownloadRequest):
    """Start a batch download job. Returns job_id for progress tracking."""
    if not req.dois:
        raise HTTPException(status_code=400, detail="dois list cannot be empty")
    if len(req.dois) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 DOIs per batch")

    job = await batch_download(
        dois=req.dois,
        use_ezproxy=req.use_ezproxy,
    )
    return BatchDownloadResponse(
        job_id=job.job_id,
        status=job.status,
        total=job.total,
        message=f"Batch job started with {job.total} papers",
    )


@router.get("/batch-download/{job_id}", response_model=BatchStatusResponse)
async def get_batch_status(job_id: str):
    """Get batch download job progress."""
    job = get_batch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return BatchStatusResponse(
        job_id=job.job_id,
        status=job.status,
        total=job.total,
        completed=job.completed,
        success=job.success,
        failed=job.failed,
        results=[r.to_dict() for r in job.results],
    )


@router.post("/import-csv", response_model=BatchDownloadResponse)
async def import_csv(file: UploadFile = File(...)):
    """Import a Google Scholar CSV or BibTeX file and start batch download.

    Parses the file, resolves DOIs where missing, and kicks off downloading.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = (await file.read()).decode("utf-8-sig")
    ext = Path(file.filename).suffix.lower()

    if ext in (".bib", ".bibtex"):
        papers = parse_bibtex(content)
    else:
        papers = parse_google_scholar_csv(content)

    if not papers:
        raise HTTPException(status_code=400, detail="No papers found in file")

    # Collect DOIs (resolve from title if needed)
    from app.services.paper_downloader import resolve_doi

    dois = []
    for p in papers:
        doi = p.get("doi", "")
        if not doi and p.get("title"):
            doi = resolve_doi(p["title"]) or ""
        if doi:
            dois.append(doi)

    if not dois:
        raise HTTPException(
            status_code=400,
            detail=f"Could not resolve any DOIs from {len(papers)} papers"
        )

    job = await batch_download(dois=dois)
    return BatchDownloadResponse(
        job_id=job.job_id,
        status=job.status,
        total=job.total,
        message=f"Imported {len(papers)} papers, resolved {len(dois)} DOIs, starting download",
    )


@router.get("/downloads", response_model=list[DownloadedFileInfo])
async def list_downloads():
    """List all downloaded PDF files."""
    pdf_dir = DEFAULT_PDF_DIR
    if not pdf_dir.exists():
        return []

    files = []
    for f in sorted(pdf_dir.glob("*.pdf")):
        files.append(DownloadedFileInfo(
            filename=f.name,
            size=f.stat().st_size,
            path=str(f),
        ))
    return files
