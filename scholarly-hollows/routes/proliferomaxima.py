from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

try:
    # Try Veritas Core imports first (when loaded as plugin)
    from app.services.proliferomaxima.batch_engine import ProliferomaximaBatchEngine
    from app.services.proliferomaxima.paper_selector import PaperSelector, find_paper_md_files
    from app.services.proliferomaxima.ref_extractor import ReferenceExtractor
except ImportError:
    # Fallback to local imports (standalone mode)
    from ..services.proliferomaxima.batch_engine import ProliferomaximaBatchEngine
    from ..services.proliferomaxima.paper_selector import PaperSelector, find_paper_md_files
    from ..services.proliferomaxima.ref_extractor import ReferenceExtractor

router = APIRouter(prefix="/proliferomaxima", tags=["proliferomaxima"])

_runs: Dict[str, Dict[str, Any]] = {}


class ProliferomaximaFilters(BaseModel):
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    authors: Optional[List[str]] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    paper_type: Optional[str] = None
    primary_method: Optional[str] = None
    secondary_methods: Optional[List[str]] = None
    empirical_context: Optional[str] = None
    keywords: Optional[List[str]] = None
    in_library: Optional[bool] = None


class ProliferomaximaRunRequest(BaseModel):
    # Legacy fields (kept for compatibility)
    library_path: Optional[str] = None
    max_files: Optional[int] = Field(default=None, ge=1)
    max_items: Optional[int] = Field(default=None, ge=1)

    # New selection API
    paper_ids: Optional[List[str]] = None
    filters: Optional[ProliferomaximaFilters] = None

    # New pacing controls
    max_refs_per_paper: Optional[int] = Field(default=20, ge=1)
    max_total: Optional[int] = Field(default=100, ge=1)
    require_abstract: bool = True
    min_ref_year: Optional[int] = None

    # Reference type filtering (new)
    reference_types: Optional[List[str]] = Field(
        default=None,
        description="Types to include: journal_article, book, book_chapter, conference, thesis, report, webpage, other. Default: academic types only."
    )
    year_from: Optional[int] = Field(default=None, description="Minimum publication year for references")
    year_to: Optional[int] = Field(default=None, description="Maximum publication year for references")


class ProliferomaximaPreviewRequest(BaseModel):
    paper_ids: Optional[List[str]] = None
    filters: Optional[ProliferomaximaFilters] = None
    library_path: Optional[str] = None
    max_refs_per_paper: Optional[int] = Field(default=20, ge=1)


class ProliferomaximaRunResponse(BaseModel):
    run_id: str
    status: str


class ProliferomaximaStatusResponse(BaseModel):
    run_id: str
    status: str
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ProliferomaximaResultsResponse(BaseModel):
    run_id: str
    status: str
    results: Optional[Dict[str, Any]] = None


class PreviewPaperItem(BaseModel):
    paper_id: str
    title: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    ref_count: int = 0


class ProliferomaximaPreviewResponse(BaseModel):
    matched_papers: List[PreviewPaperItem]
    total_matched: int


class PaperSearchRequest(BaseModel):
    """Simple search for papers in library."""
    query: str = Field(..., min_length=1, description="Search query (searches title, authors, journal, keywords)")
    limit: int = Field(default=50, ge=1, le=200)


class PaperSearchItem(BaseModel):
    paper_id: str
    title: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    authors: List[str] = []


class PaperSearchResponse(BaseModel):
    papers: List[PaperSearchItem]
    total: int


async def _run_bg(run_id: str, request: ProliferomaximaRunRequest):
    _runs[run_id]["status"] = "running"

    async def _progress(current: int = 0, total: int = 0, step: str = ""):
        _runs[run_id]["progress"] = {"current": current, "total": total, "step": step}

    try:
        engine = ProliferomaximaBatchEngine(library_path=request.library_path) if request.library_path else ProliferomaximaBatchEngine()

        # New flow: select by paper_ids + filters first.
        if request.paper_ids or request.filters:
            selector = PaperSelector()
            selected = selector.select(
                paper_ids=request.paper_ids,
                filters=(request.filters.model_dump(exclude_none=True) if request.filters else {}),
            )
            selected_ids = [x["paper_id"] for x in selected]
            # Build metadata dict for fuzzy file matching
            paper_metadata = {
                x["paper_id"]: {
                    "title": x.get("title"),
                    "authors": x.get("authors"),
                    "year": x.get("year"),
                    "journal": x.get("journal"),
                }
                for x in selected
            }
            result = await engine.run_by_papers(
                paper_ids=selected_ids,
                paper_metadata=paper_metadata,
                max_refs_per_paper=request.max_refs_per_paper,
                max_total=request.max_total,
                require_abstract=request.require_abstract,
                min_ref_year=request.min_ref_year,
                progress_callback=_progress,
            )
            result["selected_papers"] = selected
        else:
            result = await engine.run(
                max_files=request.max_files,
                max_items=request.max_items,
                reference_types=request.reference_types,
                year_from=request.year_from,
                year_to=request.year_to,
                progress_callback=_progress,
            )

        _runs[run_id]["status"] = "completed"
        _runs[run_id]["results"] = result
        _runs[run_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        _runs[run_id]["status"] = "failed"
        _runs[run_id]["error"] = str(exc)


@router.post("/search-papers", response_model=PaperSearchResponse)
async def search_papers(request: PaperSearchRequest):
    """Search papers in VF profiles by query string (title, authors, journal, keywords)."""
    selector = PaperSelector()
    # Get all meta points and filter by query
    all_papers = selector.select(paper_ids=None, filters={})
    
    query = request.query.lower().strip()
    matched: List[PaperSearchItem] = []
    
    for paper in all_papers:
        # Build searchable text
        title = str(paper.get("title") or "").lower()
        journal = str(paper.get("journal") or "").lower()
        authors = paper.get("authors") or []
        authors_text = " ".join(str(a).lower() for a in authors)
        
        # Check if query matches any field
        searchable = f"{title} {journal} {authors_text}"
        if query in searchable:
            matched.append(PaperSearchItem(
                paper_id=paper["paper_id"],
                title=paper.get("title"),
                year=paper.get("year"),
                journal=paper.get("journal"),
                authors=authors[:3],  # Limit to first 3 authors
            ))
            
            if len(matched) >= request.limit:
                break
    
    return PaperSearchResponse(papers=matched, total=len(matched))


@router.post("/preview", response_model=ProliferomaximaPreviewResponse)
async def preview_sources(request: ProliferomaximaPreviewRequest):
    selector = PaperSelector()
    selected = selector.select(
        paper_ids=request.paper_ids,
        filters=(request.filters.model_dump(exclude_none=True) if request.filters else {}),
    )

    library_path = Path(request.library_path) if request.library_path else ProliferomaximaBatchEngine().library_path
    file_map = find_paper_md_files(library_path, [x["paper_id"] for x in selected])
    extractor = ReferenceExtractor(library_path)

    out: List[PreviewPaperItem] = []
    per_cap = request.max_refs_per_paper

    for item in selected:
        pid = item["paper_id"]
        ref_count = 0
        f = file_map.get(pid)
        if f and f.exists():
            refs = extractor.extract_from_files([f], max_refs_per_paper=per_cap)
            ref_count = len(refs)

        out.append(
            PreviewPaperItem(
                paper_id=pid,
                title=item.get("title"),
                year=item.get("year"),
                journal=item.get("journal"),
                ref_count=ref_count,
            )
        )

    return ProliferomaximaPreviewResponse(matched_papers=out, total_matched=len(out))


@router.post("/run", response_model=ProliferomaximaRunResponse)
async def start_run(request: ProliferomaximaRunRequest, background_tasks: BackgroundTasks):
    run_id = f"proliferomaxima-{uuid4().hex[:8]}"
    _runs[run_id] = {
        "run_id": run_id,
        "status": "queued",
        "progress": None,
        "results": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    background_tasks.add_task(_run_bg, run_id, request)
    return ProliferomaximaRunResponse(run_id=run_id, status="queued")


@router.get("/status/{run_id}", response_model=ProliferomaximaStatusResponse)
async def get_status(run_id: str):
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return ProliferomaximaStatusResponse(run_id=run_id, status=run["status"], progress=run.get("progress"), error=run.get("error"))


@router.get("/results/{run_id}", response_model=ProliferomaximaResultsResponse)
async def get_results(run_id: str):
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    if run["status"] not in ("completed", "failed"):
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail=f"Run still in progress: {run['status']}")
    return ProliferomaximaResultsResponse(run_id=run_id, status=run["status"], results=run.get("results"))


@router.get("/progress")
async def get_progress():
    """Get current progress from progress.json (for CLI runs or any batch job)."""
    import json
    progress_file = Path(__file__).resolve().parents[2] / "data" / "progress.json"
    if not progress_file.exists():
        return {"status": "idle", "message": "No active job"}
    try:
        data = json.loads(progress_file.read_text(encoding="utf-8"))
        return data
    except Exception as e:
        return {"status": "error", "message": str(e)}
