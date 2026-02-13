"""
Run History API Routes (B2.1 - LangGraph Runtime Integration).

Provides:
- GET /sessions/{id}/runs - List runs for a session (paginated)
- GET /runs/{run_id} - Get run details
- POST /runs/{run_id}/resume - Resume an interrupted/failed/terminated run
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Run, Session, AuditLog
from app.routes.auth_routes import require_auth
from app.logging_config import get_logger
from app.agent.checkpointer import has_checkpoint
from app.services.run_registry import has_active_run, set_active_run
from app.services.agent_service import (
    start_agent_run,
    can_resume_run,
    RESUMABLE_STATUSES,
)
from app.routes.message_routes import get_or_create_session_queue

router = APIRouter()
logger = get_logger("runs")


# =============================================================================
# Response Models
# =============================================================================


class RunResponse(BaseModel):
    """Response model for a run."""

    id: str
    session_id: str
    task: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None
    brain_used: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    has_checkpoints: bool = False


class RunListResponse(BaseModel):
    """Response model for paginated run list."""

    runs: List[RunResponse]
    total: int
    limit: int
    offset: int


class ResumeResponse(BaseModel):
    """Response model for resume operation."""

    run_id: str
    status: str
    message: str


# =============================================================================
# Run Endpoints
# =============================================================================


@router.get(
    "/sessions/{session_id}/runs",
    response_model=RunListResponse,
)
async def list_session_runs(
    session_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    List runs for a session with pagination.

    Returns runs ordered by creation time (newest first).
    Includes has_checkpoints flag for resume eligibility.
    """
    try:
        # Verify session exists
        session_result = await db_session.execute(
            select(Session).where(Session.id == session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )

        # Count total runs
        count_query = (
            select(func.count(Run.id))
            .where(Run.session_id == session_id)
        )
        count_result = await db_session.execute(count_query)
        total = count_result.scalar_one() or 0

        # Get paginated runs
        runs_query = (
            select(Run)
            .where(Run.session_id == session_id)
            .order_by(desc(Run.created_at))
            .limit(limit)
            .offset(offset)
        )
        runs_result = await db_session.execute(runs_query)
        runs = runs_result.scalars().all()

        # Build response with checkpoint info
        run_responses = []
        for run in runs:
            has_cp = await has_checkpoint(run.id)
            run_responses.append(RunResponse(
                id=run.id,
                session_id=run.session_id,
                task=run.task,
                status=run.status,
                result=run.result,
                error=run.error,
                escalated=run.escalated,
                escalation_reason=run.escalation_reason,
                brain_used=run.brain_used,
                created_at=run.created_at,
                started_at=run.started_at,
                completed_at=run.completed_at,
                has_checkpoints=has_cp,
            ))

        return RunListResponse(
            runs=run_responses,
            total=total,
            limit=limit,
            offset=offset,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list runs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list runs: {str(e)}",
        )


@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
)
async def get_run(
    run_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Get details for a specific run.

    Includes has_checkpoints flag for resume eligibility.
    """
    try:
        result = await db_session.execute(
            select(Run).where(Run.id == run_id)
        )
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run not found: {run_id}",
            )

        has_cp = await has_checkpoint(run_id)

        return RunResponse(
            id=run.id,
            session_id=run.session_id,
            task=run.task,
            status=run.status,
            result=run.result,
            error=run.error,
            escalated=run.escalated,
            escalation_reason=run.escalation_reason,
            brain_used=run.brain_used,
            created_at=run.created_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
            has_checkpoints=has_cp,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get run: {str(e)}",
        )


@router.post(
    "/runs/{run_id}/resume",
    response_model=ResumeResponse,
)
async def resume_run(
    run_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Resume an interrupted, failed, or terminated run.

    Requirements:
    - Run must have status: terminated, failed, or interrupted
    - Run must have at least one checkpoint
    - Session must not have an active run

    Returns 409 Conflict if another run is active.
    Returns 400 Bad Request if run cannot be resumed.
    """
    try:
        # Get run
        result = await db_session.execute(
            select(Run).where(Run.id == run_id)
        )
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run not found: {run_id}",
            )

        # Check if run can be resumed
        can_resume, reason = await can_resume_run(db_session, run_id)
        if not can_resume:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume run: {reason}",
            )

        # Check for active run in session
        if await has_active_run(run.session_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A run is already active for this session. Wait for it to complete or terminate it first.",
            )

        # Set active run BEFORE starting task
        await set_active_run(run.session_id, run_id)

        # Get session queue
        event_queue = get_or_create_session_queue(run.session_id)

        # Create audit log
        audit = AuditLog(
            id=str(uuid4()),
            actor="user",
            actor_id=current_user.get("user_id"),
            action="run_resumed",
            resource=run_id,
            session_id=run.session_id,
            message=f"Run {run_id} resumed by user",
            details={"previous_status": run.status},
            success=True,
        )
        db_session.add(audit)
        await db_session.commit()

        # Start agent with resume flag
        await start_agent_run(
            run_id=run_id,
            session_id=run.session_id,
            user_message="",  # Not used for resume
            event_queue=event_queue,
            is_resume=True,
        )

        logger.info(
            f"Run {run_id} resumed by user {current_user.get('user_id')}",
            extra={
                "run_id": run_id,
                "session_id": run.session_id,
                "previous_status": run.status,
            },
        )

        return ResumeResponse(
            run_id=run_id,
            status="running",
            message="Run resumed successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume run: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume run: {str(e)}",
        )
