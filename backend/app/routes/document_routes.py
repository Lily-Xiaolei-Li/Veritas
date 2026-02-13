"""Document Routes (B1.7 - Document Processing)

Provides:
- POST /documents/upload - Upload a document and convert into artifact(s)
- POST /documents/generate/docx - Generate a .docx artifact
- POST /documents/generate/xlsx - Generate a .xlsx artifact

Design notes (v1):
- No Docker dependency.
- Uses existing artifact pipeline (Run + Artifact rows).
- Conversion uses DocumentProcessingService / explorer conversion logic.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifact_service import create_artifact_internal
from app.config import get_settings
from app.database import get_session
from app.logging_config import get_logger
from app.models import Run, Session
from app.routes.auth_routes import require_auth
from app.routes.message_routes import get_or_create_session_queue
from app.services.document_processing_service import (
    convert_file_to_artifact_payloads,
    generate_docx_bytes,
    generate_xlsx_bytes,
)

router = APIRouter(prefix="/documents")
logger = get_logger("documents")
settings = get_settings()


class UploadDocumentResponse(BaseModel):
    success: bool
    run_id: Optional[str] = None
    artifacts: list[dict] = Field(default_factory=list)
    created_count: int = 0
    failed_count: int = 0
    source_file: Optional[str] = None
    errors: list[str] = Field(default_factory=list)


class GenerateDocxRequest(BaseModel):
    session_id: str
    filename: str = Field(default="generated.docx", min_length=1, max_length=255)
    content: str = Field(default="")
    artifact_meta: Optional[dict[str, Any]] = None


class GenerateXlsxRequest(BaseModel):
    session_id: str
    filename: str = Field(default="generated.xlsx", min_length=1, max_length=255)
    sheets: list[dict] = Field(default_factory=list)
    artifact_meta: Optional[dict[str, Any]] = None


async def _ensure_session(db: AsyncSession, session_id: str) -> Session:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    return session


def _emit_artifact_created(session_id: str, artifact) -> None:
    try:
        q = get_or_create_session_queue(session_id)
        q.put_nowait(
            (
                "artifact_created",
                {
                    "artifact": {
                        "id": artifact.id,
                        "run_id": artifact.run_id,
                        "session_id": artifact.session_id,
                        "display_name": artifact.display_name,
                        "storage_path": artifact.storage_path,
                        "extension": artifact.extension,
                        "size_bytes": artifact.size_bytes,
                        "content_hash": artifact.content_hash,
                        "mime_type": artifact.mime_type,
                        "artifact_type": artifact.artifact_type,
                        "created_at": artifact.created_at.isoformat()
                        if hasattr(artifact.created_at, "isoformat")
                        else str(artifact.created_at),
                        "artifact_meta": artifact.artifact_meta,
                        "is_deleted": artifact.is_deleted,
                        "can_preview": True,
                        "preview_kind": "markdown"
                        if artifact.extension == "md"
                        else "text",
                        "download_url": f"/api/v1/artifacts/{artifact.id}/content",
                    }
                },
                None,
            )
        )
    except Exception:
        # best-effort only
        pass


@router.post("/upload", response_model=UploadDocumentResponse)
async def upload_document(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """Upload a document and convert it into one or more artifacts."""

    await _ensure_session(db_session, session_id)

    source_file = file.filename or "uploaded"

    now = datetime.now(timezone.utc)
    run = Run(
        session_id=session_id,
        task=f"Upload document: {source_file}",
        status="running",
        started_at=now,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    created: list[dict] = []
    errors: list[str] = []

    try:
        # save upload to a temp file so conversion code can work with a path
        suffix = Path(source_file).suffix or ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)

        payloads = convert_file_to_artifact_payloads(tmp_path, imported_via="upload")
        if not payloads:
            raise ValueError("No artifacts produced")

        # Ensure artifacts are named after the original uploaded filename,
        # not the temporary file's random stem.
        original_stem = Path(source_file).stem or "uploaded"
        for p in payloads:
            try:
                ext = Path(p.get("filename") or "").suffix
                if ext:
                    p["filename"] = f"{original_stem}{ext}"
            except Exception:
                pass

            # Fix metadata to reference the original upload rather than temp path
            meta = p.get("artifact_meta") or {}
            meta.update(
                {
                    "source_file": source_file,
                    "source_path": f"upload:{source_file}",
                    "original_filename": source_file,
                }
            )
            p["artifact_meta"] = meta
            try:
                artifact = await create_artifact_internal(
                    db_session=db_session,
                    run_id=run.id,
                    session_id=session_id,
                    filename=p["filename"],
                    content=p["content"],
                    artifact_type="file",
                    artifact_meta=p.get("artifact_meta"),
                )
                created.append(
                    {
                        "artifact_id": artifact.id,
                        "run_id": str(run.id),
                        "name": artifact.display_name,
                        "extension": artifact.extension,
                        "download_url": f"/api/v1/artifacts/{artifact.id}/content",
                    }
                )
                _emit_artifact_created(session_id, artifact)
            except Exception as e:
                logger.exception("Failed creating artifact from uploaded payload")
                errors.append(
                    f"{p.get('filename','(unknown)')}: {type(e).__name__}: {str(e)}"
                )

        run.completed_at = datetime.now(timezone.utc)
        if errors:
            run.status = "failed"
            run.error = f"{len(errors)} artifact(s) failed during upload"
        else:
            run.status = "completed"
        db_session.add(run)
        await db_session.commit()

        return UploadDocumentResponse(
            success=(len(errors) == 0),
            run_id=str(run.id),
            artifacts=created,
            created_count=len(created),
            failed_count=len(errors),
            source_file=source_file,
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Document upload failed")
        run.status = "failed"
        run.error = f"{type(e).__name__}: {str(e)}"
        run.completed_at = datetime.now(timezone.utc)
        db_session.add(run)
        await db_session.commit()
        return UploadDocumentResponse(
            success=False,
            run_id=str(run.id),
            artifacts=created,
            created_count=len(created),
            failed_count=max(1, len(errors)),
            source_file=source_file,
            errors=errors if errors else [f"{type(e).__name__}: {str(e)}"],
        )
    finally:
        try:
            if "tmp_path" in locals() and tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass


@router.post("/generate/docx")
async def generate_docx(
    request: GenerateDocxRequest,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    await _ensure_session(db_session, request.session_id)

    filename = request.filename
    if not filename.lower().endswith(".docx"):
        filename = f"{filename}.docx"

    now = datetime.now(timezone.utc)
    run = Run(
        session_id=request.session_id,
        task=f"Generate DOCX: {filename}",
        status="completed",
        started_at=now,
        completed_at=now,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    content = generate_docx_bytes(request.content)
    meta = {"generated": True, "format": "docx"}
    if request.artifact_meta:
        meta.update(request.artifact_meta)

    artifact = await create_artifact_internal(
        db_session=db_session,
        run_id=run.id,
        session_id=request.session_id,
        filename=filename,
        content=content,
        artifact_type="file",
        artifact_meta=meta,
    )
    _emit_artifact_created(request.session_id, artifact)

    return {
        "success": True,
        "run_id": str(run.id),
        "artifact_id": artifact.id,
        "download_url": f"/api/v1/artifacts/{artifact.id}/content",
    }


@router.post("/generate/xlsx")
async def generate_xlsx(
    request: GenerateXlsxRequest,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    await _ensure_session(db_session, request.session_id)

    filename = request.filename
    if not filename.lower().endswith(".xlsx"):
        filename = f"{filename}.xlsx"

    now = datetime.now(timezone.utc)
    run = Run(
        session_id=request.session_id,
        task=f"Generate XLSX: {filename}",
        status="completed",
        started_at=now,
        completed_at=now,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    content = generate_xlsx_bytes(sheets=request.sheets)
    meta = {"generated": True, "format": "xlsx"}
    if request.artifact_meta:
        meta.update(request.artifact_meta)

    artifact = await create_artifact_internal(
        db_session=db_session,
        run_id=run.id,
        session_id=request.session_id,
        filename=filename,
        content=content,
        artifact_type="file",
        artifact_meta=meta,
    )
    _emit_artifact_created(request.session_id, artifact)

    return {
        "success": True,
        "run_id": str(run.id),
        "artifact_id": artifact.id,
        "download_url": f"/api/v1/artifacts/{artifact.id}/content",
    }
