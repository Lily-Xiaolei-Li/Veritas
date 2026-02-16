from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from app.services.proliferomaxima.batch_engine import ProliferomaximaBatchEngine

router = APIRouter(prefix="/proliferomaxima", tags=["proliferomaxima"])

_runs: Dict[str, Dict[str, Any]] = {}


class ProliferomaximaRunRequest(BaseModel):
    library_path: Optional[str] = None
    max_files: Optional[int] = Field(default=None, ge=1)
    max_items: Optional[int] = Field(default=None, ge=1)


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


async def _run_bg(run_id: str, request: ProliferomaximaRunRequest):
    _runs[run_id]["status"] = "running"

    async def _progress(current: int = 0, total: int = 0, step: str = ""):
        _runs[run_id]["progress"] = {"current": current, "total": total, "step": step}

    try:
        engine = ProliferomaximaBatchEngine(library_path=request.library_path) if request.library_path else ProliferomaximaBatchEngine()
        result = await engine.run(max_files=request.max_files, max_items=request.max_items, progress_callback=_progress)
        _runs[run_id]["status"] = "completed"
        _runs[run_id]["results"] = result
        _runs[run_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        _runs[run_id]["status"] = "failed"
        _runs[run_id]["error"] = str(exc)


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
