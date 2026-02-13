"""Workspace Export/Import routes.

MVP implementation for workbench portability.

Endpoints:
- GET  /api/v1/workspace/export
- POST /api/v1/workspace/import

Security:
- Requires auth.
- Does NOT export secrets (API keys).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Artifact, Message, Run, Session
from app.routes.auth_routes import require_auth

router = APIRouter(prefix="/workspace")


class WorkspaceExport(BaseModel):
    version: str = "1.0"
    exported_at: str
    session: dict
    messages: list[dict]
    artifacts: list[dict]


@router.get("/export", response_model=WorkspaceExport)
async def export_workspace(
    session_id: str = Query(..., description="Session id to export"),
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    # session
    s_res = await db_session.execute(select(Session).where(Session.id == session_id))
    s = s_res.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    # messages
    m_res = await db_session.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
    )
    msgs = list(m_res.scalars().all())

    # artifacts (include deleted so import can restore if desired)
    a_res = await db_session.execute(
        select(Artifact).where(Artifact.session_id == session_id).order_by(Artifact.created_at.asc())
    )
    arts = list(a_res.scalars().all())

    exported_at = datetime.now(timezone.utc).isoformat()

    payload = WorkspaceExport(
        exported_at=exported_at,
        session={
            "id": s.id,
            "title": s.title,
            "mode": s.mode,
            "status": s.status,
            "config": s.config,
            "workspace_state": s.workspace_state,
            "workspace_state_version": s.workspace_state_version,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        },
        messages=[
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
        artifacts=[
            {
                "id": a.id,
                "run_id": a.run_id,
                "display_name": a.display_name,
                "storage_path": a.storage_path,
                "extension": a.extension,
                "size_bytes": a.size_bytes,
                "content_hash": a.content_hash,
                "mime_type": a.mime_type,
                "artifact_type": a.artifact_type,
                "artifact_meta": a.artifact_meta,
                "source": a.source,
                "is_draft": a.is_draft,
                "draft_content": a.draft_content,
                "is_deleted": a.is_deleted,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in arts
        ],
    ).model_dump()

    # Force download in browser
    filename = f"workspace_{session_id[:8]}.json"
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class WorkspaceImportRequest(BaseModel):
    data: dict = Field(..., description="Exported workspace JSON")
    mode: str = Field(default="merge", description="merge|replace")


class WorkspaceImportResponse(BaseModel):
    ok: bool
    imported_session_id: str | None = None
    imported_messages: int = 0
    imported_artifacts: int = 0


@router.post("/import", response_model=WorkspaceImportResponse)
async def import_workspace(
    body: WorkspaceImportRequest,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    data = body.data or {}
    mode = (body.mode or "merge").lower()
    if mode not in {"merge", "replace"}:
        raise HTTPException(status_code=422, detail="mode must be merge|replace")

    # Basic validation
    session_obj = (data.get("session") or {})
    src_session_id = session_obj.get("id")
    if not src_session_id:
        raise HTTPException(status_code=422, detail="export missing session.id")

    if mode == "replace":
        # DANGEROUS: remove all existing rows (MVP). Frontend must confirm.
        await db_session.execute(delete(Artifact))
        await db_session.execute(delete(Message))
        await db_session.execute(delete(Run))
        await db_session.execute(delete(Session))
        await db_session.commit()

    # Ensure session exists (merge: create if not)
    s_res = await db_session.execute(select(Session).where(Session.id == src_session_id))
    session = s_res.scalar_one_or_none()
    if not session:
        session = Session(
            id=src_session_id,
            title=session_obj.get("title"),
            mode=session_obj.get("mode") or "engineering",
            status=session_obj.get("status") or "active",
            config=session_obj.get("config"),
            workspace_state=session_obj.get("workspace_state") or {},
            workspace_state_version=int(session_obj.get("workspace_state_version") or 1),
        )
        db_session.add(session)
        await db_session.commit()
    else:
        # merge: update a few fields (non-destructive)
        session.title = session_obj.get("title") or session.title
        session.config = session_obj.get("config") or session.config
        # keep existing state if present, otherwise take imported
        if not session.workspace_state and session_obj.get("workspace_state"):
            session.workspace_state = session_obj.get("workspace_state")
        await db_session.commit()

    # Import messages (idempotent: skip if id exists)
    imported_messages = 0
    for m in (data.get("messages") or []):
        mid = m.get("id")
        if not mid:
            continue
        exists = await db_session.execute(select(Message).where(Message.id == mid))
        if exists.scalar_one_or_none():
            continue
        msg = Message(
            id=mid,
            session_id=src_session_id,
            role=m.get("role") or "user",
            content=m.get("content") or "",
        )
        db_session.add(msg)
        imported_messages += 1

    # Import artifacts (DB rows only; files may not exist on disk)
    imported_artifacts = 0
    for a in (data.get("artifacts") or []):
        aid = a.get("id")
        if not aid:
            continue
        exists = await db_session.execute(select(Artifact).where(Artifact.id == aid))
        if exists.scalar_one_or_none():
            continue

        # NOTE: run_id must exist; if missing, we create a stub run
        run_id = a.get("run_id")
        if not run_id:
            continue

        run_exists = await db_session.execute(select(Run).where(Run.id == run_id))
        if not run_exists.scalar_one_or_none():
            db_session.add(
                Run(
                    id=run_id,
                    session_id=src_session_id,
                    task="Imported artifact",
                    status="completed",
                )
            )

        art = Artifact(
            id=aid,
            run_id=run_id,
            session_id=src_session_id,
            display_name=a.get("display_name") or "artifact",
            storage_path=a.get("storage_path") or "",
            extension=a.get("extension"),
            size_bytes=int(a.get("size_bytes") or 0),
            content_hash=a.get("content_hash"),
            mime_type=a.get("mime_type"),
            artifact_type=a.get("artifact_type") or "file",
            artifact_meta=a.get("artifact_meta"),
            source=a.get("source") or "import",
            is_draft=bool(a.get("is_draft") or False),
            draft_content=a.get("draft_content"),
            is_deleted=bool(a.get("is_deleted") or False),
        )
        db_session.add(art)
        imported_artifacts += 1

    await db_session.commit()

    return WorkspaceImportResponse(
        ok=True,
        imported_session_id=src_session_id,
        imported_messages=imported_messages,
        imported_artifacts=imported_artifacts,
    )
