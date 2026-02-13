"""Workspace utility routes.

Stage: Workbench UX enhancements.

Provides:
- POST /api/v1/workspace/save
- GET  /api/v1/workspace/undo-stack
- POST /api/v1/workspace/undo

Note: Core workspace state persistence already happens automatically.
Save/Undo endpoints are primarily for UX and workflow support.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Session, AuditLog, Artifact, Message
from app.routes.auth_routes import require_auth

router = APIRouter(prefix="/workspace")


class WorkspaceSaveRequest(BaseModel):
    session_id: str = Field(..., description="Session id to mark as saved")


class WorkspaceSaveResponse(BaseModel):
    session_id: str
    saved_at: datetime
    workspace_state_version: int


class UndoStackItem(BaseModel):
    id: str
    action_type: str  # artifact_delete|session_delete
    target_id: str
    created_at: datetime


class UndoStackResponse(BaseModel):
    items: list[UndoStackItem]


class UndoRequest(BaseModel):
    session_id: str


class UndoResponse(BaseModel):
    ok: bool
    undone_action_id: str | None = None
    action_type: str | None = None
    target_id: str | None = None


class ResetWorkspaceResponse(BaseModel):
    ok: bool
    deleted_sessions: int
    deleted_artifacts: int
    deleted_messages: int


@router.post("/save", response_model=WorkspaceSaveResponse, status_code=status.HTTP_200_OK)
async def save_workspace(
    body: WorkspaceSaveRequest,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """Mark the workspace as explicitly saved."""

    result = await db_session.execute(select(Session).where(Session.id == body.session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    now = datetime.now(timezone.utc)

    state = session.workspace_state or {}
    if not isinstance(state, dict):
        state = {}

    state["last_manual_save_at"] = now.isoformat()
    session.workspace_state = state
    session.workspace_state_version = (session.workspace_state_version or 0) + 1

    await db_session.commit()
    await db_session.refresh(session)

    return WorkspaceSaveResponse(
        session_id=session.id,
        saved_at=now,
        workspace_state_version=session.workspace_state_version,
    )


@router.get("/undo-stack", response_model=UndoStackResponse)
async def get_undo_stack(
    session_id: str = Query(..., description="Session id"),
    limit: int = Query(default=50, ge=1, le=200),
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """Get undo stack for a session (MVP).

    Uses AuditLog entries with action prefix "undoable_".
    """

    q = (
        select(AuditLog)
        .where(AuditLog.session_id == session_id)
        .where(AuditLog.success == True)  # noqa: E712
        .where(AuditLog.action.in_(["undoable_artifact_delete", "undoable_session_delete"]))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    result = await db_session.execute(q)
    rows = list(result.scalars().all())

    items: list[UndoStackItem] = []
    for r in rows:
        details = r.details or {}
        if details.get("undone") is True:
            continue
        action_type = details.get("action_type")
        if action_type == "artifact_delete":
            target_id = details.get("artifact_id")
        elif action_type == "session_delete":
            target_id = details.get("session_id")
        else:
            continue

        if not target_id:
            continue

        items.append(
            UndoStackItem(
                id=r.id,
                action_type=str(action_type),
                target_id=str(target_id),
                created_at=r.created_at,
            )
        )

    return UndoStackResponse(items=items)


@router.post("/undo", response_model=UndoResponse)
async def undo_latest(
    body: UndoRequest,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """Undo the latest undoable action for a session (MVP)."""

    q = (
        select(AuditLog)
        .where(AuditLog.session_id == body.session_id)
        .where(AuditLog.success == True)  # noqa: E712
        .where(AuditLog.action.in_(["undoable_artifact_delete", "undoable_session_delete"]))
        .order_by(AuditLog.created_at.desc())
        .limit(50)
    )
    result = await db_session.execute(q)
    rows = list(result.scalars().all())

    target = None
    for r in rows:
        details = r.details or {}
        if details.get("undone") is True:
            continue
        target = r
        break

    if not target:
        return UndoResponse(ok=False)

    details = target.details or {}
    action_type = details.get("action_type")

    if action_type == "artifact_delete":
        artifact_id = details.get("artifact_id")
        if not artifact_id:
            return UndoResponse(ok=False)

        art_result = await db_session.execute(select(Artifact).where(Artifact.id == artifact_id))
        artifact = art_result.scalar_one_or_none()
        if not artifact:
            return UndoResponse(ok=False)

        artifact.is_deleted = False
        await db_session.commit()

        # Mark undone
        details["undone"] = True
        target.details = details
        await db_session.commit()

        return UndoResponse(ok=True, undone_action_id=target.id, action_type=action_type, target_id=artifact_id)

    if action_type == "session_delete":
        session_id = details.get("session_id")
        old_status = details.get("old_status") or "active"
        if not session_id:
            return UndoResponse(ok=False)

        s_result = await db_session.execute(select(Session).where(Session.id == session_id))
        session = s_result.scalar_one_or_none()
        if not session:
            return UndoResponse(ok=False)

        session.status = str(old_status)
        session.ended_at = None
        await db_session.commit()

        details["undone"] = True
        target.details = details
        await db_session.commit()

        return UndoResponse(ok=True, undone_action_id=target.id, action_type=action_type, target_id=session_id)

    return UndoResponse(ok=False)


@router.post("/reset", response_model=ResetWorkspaceResponse, status_code=status.HTTP_200_OK)
async def reset_workspace(
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """Reset entire workspace - delete all sessions, artifacts, and messages.
    
    This is a destructive operation. Frontend should confirm with user first.
    """
    from sqlalchemy import delete, func
    
    # Count before deleting
    sessions_count = (await db_session.execute(select(func.count(Session.id)))).scalar() or 0
    artifacts_count = (await db_session.execute(select(func.count(Artifact.id)))).scalar() or 0
    messages_count = (await db_session.execute(select(func.count(Message.id)))).scalar() or 0
    
    # Delete in order (respect foreign keys)
    # Messages reference sessions
    await db_session.execute(delete(Message))
    # Artifacts reference sessions
    await db_session.execute(delete(Artifact))
    # Audit logs reference sessions
    await db_session.execute(delete(AuditLog))
    # Finally delete sessions
    await db_session.execute(delete(Session))
    
    await db_session.commit()
    
    return ResetWorkspaceResponse(
        ok=True,
        deleted_sessions=sessions_count,
        deleted_artifacts=artifacts_count,
        deleted_messages=messages_count,
    )
