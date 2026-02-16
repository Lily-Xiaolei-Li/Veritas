"""Sentence Checker API routes.

Endpoints:
- POST /checker/run — Start a new checker run
- GET  /checker/status/{run_id} — Get run status
- GET  /checker/results/{artifact_id} — Get results for an artifact
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from app.logging_config import get_logger
from app.services.checker.engine import run_checker

logger = get_logger("checker.routes")

router = APIRouter(prefix="/checker", tags=["checker"])

# In-memory run store (TODO: move to database with checker_runs table)
_runs: Dict[str, Dict[str, Any]] = {}


class CheckerRunRequest(BaseModel):
    """Request to start a checker run."""
    text: str = Field(..., min_length=1, description="Academic text to check")
    artifact_id: Optional[str] = Field(default=None, description="Source artifact ID")
    options: Optional[Dict[str, bool]] = Field(
        default=None,
        description="Options: check_citations, check_ai, check_flow",
    )


class CheckerRunResponse(BaseModel):
    """Response after starting a checker run."""
    run_id: str
    status: str
    estimated_time: str = "2-5 min"


class CheckerStatusResponse(BaseModel):
    """Status of a checker run."""
    run_id: str
    status: str  # queued, running, completed, failed
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CheckerResultsResponse(BaseModel):
    """Full checker results."""
    run_id: str
    status: str
    results: Optional[Dict[str, Any]] = None


async def _run_checker_background(run_id: str, text: str, artifact_id: Optional[str], options: Optional[Dict]):
    """Run checker in background and store results."""
    _runs[run_id]["status"] = "running"

    async def progress_cb(current: int = 0, total: int = 0, step: str = ""):
        _runs[run_id]["progress"] = {"current": current, "total": total, "step": step}

    try:
        result = await run_checker(
            text=text,
            artifact_id=artifact_id,
            options=options,
            progress_callback=progress_cb,
        )
        _runs[run_id]["status"] = "completed"
        _runs[run_id]["results"] = result
        _runs[run_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        logger.error(f"Checker run {run_id} failed: {e}", exc_info=True)
        _runs[run_id]["status"] = "failed"
        _runs[run_id]["error"] = str(e)


@router.post("/run", response_model=CheckerRunResponse)
async def start_checker_run(request: CheckerRunRequest, background_tasks: BackgroundTasks):
    """Start a new sentence checker run.
    
    The checker processes text asynchronously. Use /status/{run_id} to poll progress.
    """
    run_id = f"checker-{uuid4().hex[:8]}"

    _runs[run_id] = {
        "run_id": run_id,
        "status": "queued",
        "artifact_id": request.artifact_id,
        "progress": None,
        "results": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    background_tasks.add_task(
        _run_checker_background,
        run_id,
        request.text,
        request.artifact_id,
        request.options,
    )

    return CheckerRunResponse(run_id=run_id, status="queued")


@router.get("/status/{run_id}", response_model=CheckerStatusResponse)
async def get_checker_status(run_id: str):
    """Get the status and progress of a checker run."""
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    return CheckerStatusResponse(
        run_id=run_id,
        status=run["status"],
        progress=run.get("progress"),
        error=run.get("error"),
    )


@router.get("/results/{run_id}", response_model=CheckerResultsResponse)
async def get_checker_results(run_id: str):
    """Get the full results of a completed checker run."""
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    if run["status"] not in ("completed", "failed"):
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail=f"Run still in progress: {run['status']}",
        )

    return CheckerResultsResponse(
        run_id=run_id,
        status=run["status"],
        results=run.get("results"),
    )
