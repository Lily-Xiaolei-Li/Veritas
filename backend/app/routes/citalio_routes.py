from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from app.logging_config import get_logger
from app.services.citalio.engine import run_citalio

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
