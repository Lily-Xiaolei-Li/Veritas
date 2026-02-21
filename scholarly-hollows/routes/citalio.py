from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

try:
    # Try Veritas Core imports first (when loaded as plugin)
    from app.logging_config import get_logger
    from app.services.citalio.engine import run_citalio
    from app.services.citalio.manual_search import CitalioManualSearcher
except ImportError:
    # Fallback to local imports (standalone mode)
    from ..logging_config import get_logger
    from ..services.citalio.engine import run_citalio
    from ..services.citalio.manual_search import CitalioManualSearcher

logger = get_logger("citalio.routes")

router = APIRouter(prefix="/citalio", tags=["citalio"])

_runs: Dict[str, Dict[str, Any]] = {}


class CitalioRunRequest(BaseModel):
    text: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class CitalioRunResponse(BaseModel):
    run_id: str
    status: str
    estimated_time: str = "1-3 min"


class CitalioStatusResponse(BaseModel):
    run_id: str
    status: str
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CitalioResultsResponse(BaseModel):
    run_id: str
    status: str
    results: Optional[Dict[str, Any]] = None


async def _run_citalio_bg(run_id: str, text: str, session_id: Optional[str], options: Dict[str, Any]):
    _runs[run_id]["status"] = "running"

    async def _progress(current: int = 0, total: int = 0, step: str = ""):
        _runs[run_id]["progress"] = {"current": current, "total": total, "step": step}

    try:
        result = await run_citalio(text=text, session_id=session_id, options=options, progress_callback=_progress)
        _runs[run_id]["status"] = "completed"
        _runs[run_id]["results"] = result
        _runs[run_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        logger.error(f"Citalio run {run_id} failed: {e}", exc_info=True)
        _runs[run_id]["status"] = "failed"
        _runs[run_id]["error"] = str(e)


@router.post("/run", response_model=CitalioRunResponse)
async def start_citalio_run(request: CitalioRunRequest, background_tasks: BackgroundTasks):
    run_id = f"citalio-{uuid4().hex[:8]}"
    _runs[run_id] = {
        "run_id": run_id,
        "status": "queued",
        "session_id": request.session_id,
        "progress": None,
        "results": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    background_tasks.add_task(_run_citalio_bg, run_id, request.text, request.session_id, request.options)
    return CitalioRunResponse(run_id=run_id, status="queued")


@router.get("/status/{run_id}", response_model=CitalioStatusResponse)
async def get_citalio_status(run_id: str):
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return CitalioStatusResponse(run_id=run_id, status=run["status"], progress=run.get("progress"), error=run.get("error"))


@router.get("/results/{run_id}", response_model=CitalioResultsResponse)
async def get_citalio_results(run_id: str):
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    if run["status"] not in ("completed", "failed"):
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail=f"Run still in progress: {run['status']}")
    return CitalioResultsResponse(run_id=run_id, status=run["status"], results=run.get("results"))


# ============================================================================
# MANUAL MODE - Citalio 手动模式
# ============================================================================


class CitalioManualFilters(BaseModel):
    """Filters for manual Citalio search."""
    year_min: Optional[int] = Field(None, description="Minimum year (inclusive)")
    year_max: Optional[int] = Field(None, description="Maximum year (inclusive)")
    paper_type: Optional[str] = Field(None, description="Paper type: empirical, theoretical, review, conceptual")
    primary_method: Optional[str] = Field(None, description="Primary method: qualitative, quantitative, case study, mixed")
    keywords: Optional[List[str]] = Field(None, description="Keywords to filter by (author or inferred)")
    journal: Optional[str] = Field(None, description="Journal name (partial match)")
    authors: Optional[List[str]] = Field(None, description="Author names to filter by (partial match)")
    in_library: Optional[bool] = Field(None, description="Filter by in_library status")
    empirical_context: Optional[str] = Field(None, description="Empirical context (partial match)")


class CitalioManualSearchRequest(BaseModel):
    """Request for manual Citalio search."""
    query: str = Field(..., min_length=1, description="The selected sentence or text to find citations for")
    chunk_types: List[str] = Field(
        default=["cited_for", "theory", "contributions"],
        description="Which chunk types to search: cited_for, theory, contributions, literature, abstract, key_concepts, research_questions"
    )
    limit: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    filters: Optional[CitalioManualFilters] = Field(default=None, description="Optional filters")


class CitalioManualResult(BaseModel):
    """A single result from manual Citalio search."""
    paper_id: str
    authors: List[str]
    year: Optional[int]
    title: str
    journal: Optional[str]
    matched_chunk_type: str
    matched_text: str  # Full paragraph, not just keywords
    relevance_score: float
    cite_intext: str  # e.g., "(Power, 2003)"
    cite_full: str  # Full Harvard reference
    meta: Dict[str, Any]  # All metadata for additional info


class CitalioManualSearchResponse(BaseModel):
    """Response from manual Citalio search."""
    query: str
    results: List[CitalioManualResult]
    total_found: int
    filters_applied: Dict[str, Any]


@router.post("/manual/search", response_model=CitalioManualSearchResponse)
async def citalio_manual_search(request: CitalioManualSearchRequest):
    """
    Manual Citalio search - search VF Store with custom filters.
    
    Returns citation candidates with full matched paragraphs and cite_how fields
    for easy insertion into text.
    """
    searcher = CitalioManualSearcher()
    
    filters_dict = request.filters.model_dump() if request.filters else {}
    
    results = searcher.search(
        query=request.query,
        chunk_types=request.chunk_types,
        limit=request.limit,
        filters=filters_dict,
    )
    
    return CitalioManualSearchResponse(
        query=request.query,
        results=results,
        total_found=len(results),
        filters_applied=filters_dict,
    )


@router.get("/manual/filter-options")
async def get_filter_options():
    """
    Get available filter options from VF Store for the UI dropdowns.
    """
    searcher = CitalioManualSearcher()
    return searcher.get_filter_options()
