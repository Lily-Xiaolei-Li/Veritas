"""
Session Management API routes (B0.3).
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Session, Message, Artifact, AuditLog
from app.routes.auth_routes import require_auth
from app.logging_config import get_logger
from app.metrics import SESSIONS_CREATED_TOTAL

router = APIRouter()
logger = get_logger("sessions")


# Request/Response Models


class SessionCreate(BaseModel):
    """Request model for creating a session."""

    title: Optional[str] = Field(None, max_length=255, description="Session title")
    mode: str = Field(
        default="engineering",
        max_length=50,
        description="Session mode (e.g., engineering, creative, conservative)",
    )
    config: Optional[dict] = Field(None, description="Session configuration")


class SessionUpdate(BaseModel):
    """Request model for updating a session."""

    title: Optional[str] = Field(None, max_length=255, description="Session title")


class SessionResponse(BaseModel):
    """Response model for session."""

    id: str
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime]
    title: Optional[str]
    mode: str
    status: str
    config: Optional[dict]


class WorkspaceStateResponse(BaseModel):
    """Workspace state for a session (Phase 1 persistence)."""

    session_id: str
    workspace_state: dict
    workspace_state_version: int
    last_auto_save_at: Optional[datetime]


class WorkspaceStatePatch(BaseModel):
    """Patch workspace state. Provide partial updates."""

    patch: dict = Field(default_factory=dict)
    expected_version: Optional[int] = None
    is_auto_save: bool = True


# Conversation API (Console Conversation Tab)


class ConversationItem(BaseModel):
    id: str
    role: str  # user|assistant|system
    type: str  # message|artifact
    content: str
    timestamp: datetime


class ConversationResponse(BaseModel):
    messages: List[ConversationItem]


# Session Endpoints


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Create a new session.

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        # Create session
        session = Session(
            id=str(uuid4()),
            title=session_data.title,
            mode=session_data.mode,
            status="active",
            config=session_data.config,
        )

        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        # Increment metrics counter (B7.2)
        SESSIONS_CREATED_TOTAL.inc()

        logger.info(
            f"Session created: {session.id}",
            extra={"session_id": session.id, "user_id": current_user.get("user_id")},
        )

        return SessionResponse(
            id=session.id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            ended_at=session.ended_at,
            title=session.title,
            mode=session.mode,
            status=session.status,
            config=session.config,
        )

    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session",
        )


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
    status_filter: Optional[str] = None,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    """
    List sessions.

    Requires authentication if AUTH_ENABLED=true.
    By default, excludes deleted sessions unless include_deleted=true.
    """
    try:
        # Build query
        query = select(Session)

        if status_filter:
            query = query.where(Session.status == status_filter)
        elif not include_deleted:
            # By default, exclude deleted sessions
            query = query.where(Session.status != "deleted")

        query = query.order_by(Session.created_at.desc()).limit(limit).offset(offset)

        # Execute query
        result = await db_session.execute(query)
        sessions = result.scalars().all()

        return [
            SessionResponse(
                id=s.id,
                created_at=s.created_at,
                updated_at=s.updated_at,
                ended_at=s.ended_at,
                title=s.title,
                mode=s.mode,
                status=s.status,
                config=s.config,
            )
            for s in sessions
        ]

    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        logger.error(f"Failed to list sessions: {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {error_detail}",
        )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session_details(
    session_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Get session details.

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        # Find session
        result = await db_session.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        return SessionResponse(
            id=session.id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            ended_at=session.ended_at,
            title=session.title,
            mode=session.mode,
            status=session.status,
            config=session.config,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session",
        )


@router.get("/sessions/{session_id}/workspace", response_model=WorkspaceStateResponse)
async def get_workspace_state(
    session_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """Get persisted workspace state for a session."""
    result = await db_session.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return WorkspaceStateResponse(
        session_id=session.id,
        workspace_state=session.workspace_state or {},
        workspace_state_version=session.workspace_state_version,
        last_auto_save_at=session.last_auto_save_at,
    )


@router.patch("/sessions/{session_id}/workspace", response_model=WorkspaceStateResponse)
async def patch_workspace_state(
    session_id: str,
    body: WorkspaceStatePatch,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """Patch persisted workspace state. Uses optimistic locking when expected_version provided."""
    result = await db_session.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if body.expected_version is not None and session.workspace_state_version != body.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Workspace state version conflict",
                "expected": body.expected_version,
                "actual": session.workspace_state_version,
            },
        )

    # Apply patch (shallow merge)
    current = session.workspace_state or {}
    if not isinstance(current, dict):
        current = {}
    patch = body.patch or {}
    if not isinstance(patch, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="patch must be an object")

    current.update(patch)
    session.workspace_state = current
    session.workspace_state_version = (session.workspace_state_version or 0) + 1

    if body.is_auto_save:
        session.last_auto_save_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(session)

    return WorkspaceStateResponse(
        session_id=session.id,
        workspace_state=session.workspace_state or {},
        workspace_state_version=session.workspace_state_version,
        last_auto_save_at=session.last_auto_save_at,
    )


@router.get("/sessions/{session_id}/conversation", response_model=ConversationResponse)
async def get_session_conversation(
    session_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
    limit: int = 500,
):
    """Get unified conversation timeline for a session.

    Combines:
    - Message rows (user/assistant/system)
    - Artifact creations (assistant, type=artifact)

    Used by the Console "Conversation" tab.
    """
    # Verify session exists
    result = await db_session.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Fetch messages
    msg_result = await db_session.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    msgs = msg_result.scalars().all()

    # Fetch artifacts (non-deleted)
    art_result = await db_session.execute(
        select(Artifact)
        .where(Artifact.session_id == session_id)
        .where(Artifact.is_deleted == False)  # noqa: E712
        .order_by(Artifact.created_at.asc())
        .limit(limit)
    )
    arts = art_result.scalars().all()

    items: List[ConversationItem] = []

    for m in msgs:
        items.append(
            ConversationItem(
                id=m.id,
                role=m.role,
                type="message",
                content=m.content,
                timestamp=m.created_at,
            )
        )

    for a in arts:
        items.append(
            ConversationItem(
                id=a.id,
                role="assistant",
                type="artifact",
                content=a.display_name,
                timestamp=a.created_at,
            )
        )

    items.sort(key=lambda x: x.timestamp)

    return ConversationResponse(messages=items)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Delete a session.

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        # Find session
        result = await db_session.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        # Soft-delete session (Undo MVP)
        old_status = session.status
        session.status = "deleted"
        session.ended_at = datetime.now(timezone.utc)
        await db_session.commit()

        # Record undoable action
        try:
            audit = AuditLog(
                id=str(uuid4()),
                actor="user",
                actor_id=current_user.get("user_id"),
                action="undoable_session_delete",
                resource=f"session:{session_id}",
                session_id=session_id,
                message=f"Session soft-deleted: {session.title or session_id}",
                details={
                    "action_type": "session_delete",
                    "session_id": session_id,
                    "old_status": old_status,
                    "undone": False,
                },
                success=True,
            )
            db_session.add(audit)
            await db_session.commit()
        except Exception:
            pass

        logger.info(
            f"Session deleted (soft): {session_id}",
            extra={"session_id": session_id, "user_id": current_user.get("user_id")},
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session",
        )


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    update_data: SessionUpdate,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Update a session (currently only title).

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        # Find session
        result = await db_session.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        # Update fields if provided
        if update_data.title is not None:
            session.title = update_data.title

        await db_session.commit()
        await db_session.refresh(session)

        logger.info(
            f"Session updated: {session_id}",
            extra={"session_id": session_id, "user_id": current_user.get("user_id")},
        )

        return SessionResponse(
            id=session.id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            ended_at=session.ended_at,
            title=session.title,
            mode=session.mode,
            status=session.status,
            config=session.config,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session",
        )


# =============================================================================
# Kill Switch Endpoint (B1.4)
# =============================================================================


class TerminateResponse(BaseModel):
    """Response model for terminate endpoint."""

    status: str = Field(..., description="terminated | no_active_run | failed")
    run_id: Optional[str] = Field(None, description="ID of terminated run")
    reason: str = Field(..., description="Termination reason")
    cancel_status: str = Field(..., description="What was cancelled")
    latency_ms: float = Field(..., description="Termination latency in ms")
    message: Optional[str] = Field(None, description="Human-readable message")


@router.post(
    "/sessions/{session_id}/terminate",
    response_model=TerminateResponse,
    status_code=status.HTTP_200_OK,
)
async def terminate_session_run(
    session_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Terminate the active run for a session (Kill Switch).

    Stops the current agent execution within ~2 seconds:
    - Cancels mock agent task (cooperative cancellation)
    - Terminates active execution if running
    - Cancels LLM API calls (stub for Phase 2)
    - Emits run_terminated SSE event
    - Logs to audit trail

    Requires authentication if AUTH_ENABLED=true.

    Returns:
        TerminateResponse with status and termination details
    """
    from app.services.termination_service import terminate_session
    from app.schemas.sse_events import TerminationReason

    try:
        # Verify session exists
        result = await db_session.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )

        # Terminate the active run
        termination_result = await terminate_session(
            session_id=session_id,
            reason=TerminationReason.USER_CANCEL,
            db_session=db_session,
        )

        logger.info(
            f"Kill switch activated for session {session_id}",
            extra={
                "session_id": session_id,
                "user_id": current_user.get("user_id"),
                "run_id": termination_result.run_id,
                "status": termination_result.status,
                "latency_ms": termination_result.latency_ms,
            },
        )

        return TerminateResponse(
            status=termination_result.status,
            run_id=termination_result.run_id,
            reason=termination_result.reason,
            cancel_status=termination_result.cancel_status,
            latency_ms=termination_result.latency_ms,
            message=termination_result.message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to terminate session run: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to terminate: {str(e)}",
        )
