"""
Artifact API routes (B1.3 - Artifact Handling).

Provides:
- GET /sessions/{session_id}/artifacts - List artifacts for session
- GET /runs/{run_id}/artifacts - List artifacts for run
- GET /artifacts/{artifact_id} - Get artifact metadata
- GET /artifacts/{artifact_id}/content - Download artifact (streaming)
- GET /artifacts/{artifact_id}/preview - Get preview content
- GET /runs/{run_id}/artifacts/zip - Download all as ZIP (streaming)
- DELETE /artifacts/{artifact_id} - Soft-delete artifact

Note: No POST endpoint. Artifacts created only via internal pipeline.
"""

from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifact_service import (
    can_preview,
    create_artifact_internal,
    create_zip_stream,
    get_artifact_content_stream,
    get_artifact_preview,
    get_preview_kind,
    soft_delete_artifact,
)
from app.config import get_settings
from app.database import get_session
from app.logging_config import get_logger
from app.models import Artifact, AuditLog, Run, Session
from app.routes.auth_routes import require_auth
from app.routes.message_routes import get_or_create_session_queue

router = APIRouter()
logger = get_logger("artifacts")


# =============================================================================
# Request/Response Models
# =============================================================================


class ArtifactResponse(BaseModel):
    """Response model for an artifact."""

    id: str
    run_id: str
    session_id: str
    display_name: str
    storage_path: str
    extension: Optional[str]
    size_bytes: int
    content_hash: Optional[str]
    mime_type: Optional[str]
    artifact_type: str
    created_at: datetime
    artifact_meta: Optional[dict]
    is_deleted: bool

    # Computed fields
    can_preview: bool = Field(default=False)
    preview_kind: str = Field(default="none")
    download_url: str = Field(default="")


class ArtifactListResponse(BaseModel):
    """Response model for paginated artifact list."""

    artifacts: List[ArtifactResponse]
    total: int
    has_more: bool
    limit: int
    offset: int


class ArtifactPreviewResponse(BaseModel):
    """Response model for artifact preview."""

    kind: Literal["text", "code", "markdown", "image", "none"]
    content_type: str
    truncated: bool
    text: Optional[str] = None


class ArtifactCreateRequest(BaseModel):
    """Create a new artifact from provided text content.

    Stage 8: used to save edited local artifacts back into the DB.
    We intentionally create a new artifact instead of overwriting.
    """

    filename: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., description="UTF-8 text content")
    artifact_type: str = Field(default="file")
    artifact_meta: Optional[dict] = None
    source_artifact_id: Optional[str] = None


class ArtifactUpdateContentRequest(BaseModel):
    """Update content of an existing artifact."""

    content: str = Field(..., description="New UTF-8 text content")


class ArtifactDraftResponse(BaseModel):
    """Draft state for an artifact (Phase 1)."""

    artifact_id: str
    session_id: str
    is_draft: bool
    draft_content: Optional[str] = None
    draft_updated_at: Optional[datetime] = None


class ArtifactDraftUpdateRequest(BaseModel):
    """Update draft content for an artifact."""

    draft_content: str = Field("", description="UTF-8 text draft")
    clear: bool = False
    is_auto_save: bool = True


class ArtifactRenameRequest(BaseModel):
    """Rename an artifact."""

    new_name: str = Field(..., min_length=1, max_length=255, description="New display name for the artifact")


# =============================================================================
# Helper Functions
# =============================================================================


def artifact_to_response(artifact: Artifact) -> ArtifactResponse:
    """Convert Artifact model to response with computed fields."""
    preview_kind = get_preview_kind(artifact.extension, artifact.mime_type)
    preview_possible = can_preview(
        artifact.size_bytes, artifact.extension, artifact.mime_type
    )

    return ArtifactResponse(
        id=artifact.id,
        run_id=artifact.run_id,
        session_id=artifact.session_id,
        display_name=artifact.display_name,
        storage_path=artifact.storage_path,
        extension=artifact.extension,
        size_bytes=artifact.size_bytes,
        content_hash=artifact.content_hash,
        mime_type=artifact.mime_type,
        artifact_type=artifact.artifact_type,
        created_at=artifact.created_at,
        artifact_meta=artifact.artifact_meta,
        is_deleted=artifact.is_deleted,
        can_preview=preview_possible,
        preview_kind=preview_kind,
        download_url=f"/api/v1/artifacts/{artifact.id}/content",
    )


# =============================================================================
# List Endpoints
# =============================================================================


@router.get("/sessions/{session_id}/artifacts", response_model=ArtifactListResponse)
async def list_session_artifacts(
    session_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
    limit: int = Query(default=100, ge=1, le=500, description="Max artifacts to return"),
    offset: int = Query(default=0, ge=0, description="Number of artifacts to skip"),
    sort: Literal["created_desc", "name_asc", "size_desc"] = Query(
        default="created_desc", description="Sort order"
    ),
    artifact_type: Optional[str] = Query(
        default=None, description="Filter by artifact type (file, stdout, stderr, log)"
    ),
    extension: Optional[str] = Query(
        default=None, description="Filter by file extension (e.g., 'py')"
    ),
    include_deleted: bool = Query(
        default=False, description="Include soft-deleted artifacts"
    ),
):
    """
    List artifacts for a session with pagination and filtering.

    Requires authentication if AUTH_ENABLED=true.
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

        # Build query
        query = select(Artifact).where(Artifact.session_id == session_id)

        # Filter by deletion status
        if not include_deleted:
            query = query.where(Artifact.is_deleted == False)

        # Filter by artifact type
        if artifact_type:
            query = query.where(Artifact.artifact_type == artifact_type)

        # Filter by extension
        if extension:
            ext = extension.lstrip(".")
            query = query.where(Artifact.extension == ext)

        # Get total count before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db_session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        if sort == "created_desc":
            query = query.order_by(Artifact.created_at.desc())
        elif sort == "name_asc":
            query = query.order_by(Artifact.display_name.asc())
        elif sort == "size_desc":
            query = query.order_by(Artifact.size_bytes.desc())

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Execute query
        result = await db_session.execute(query)
        artifacts = result.scalars().all()

        return ArtifactListResponse(
            artifacts=[artifact_to_response(a) for a in artifacts],
            total=total,
            has_more=offset + len(artifacts) < total,
            limit=limit,
            offset=offset,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list session artifacts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list artifacts: {str(e)}",
        )


@router.post("/sessions/{session_id}/artifacts", response_model=ArtifactResponse)
async def create_session_artifact(
    session_id: str,
    request: ArtifactCreateRequest,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """Create a new artifact from provided content.

    Stage 8: Save edited artifacts back into the workbench.

    Behavior:
    - Always creates a new Run (task: "Save artifact: <filename>")
    - Always creates a new Artifact row (no overwrite)
    """

    # Verify session exists
    session_result = await db_session.execute(select(Session).where(Session.id == session_id))
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    now = datetime.now(timezone.utc)
    run = Run(
        session_id=session_id,
        task=f"Save artifact: {request.filename}",
        status="completed",
        started_at=now,
        completed_at=now,
        error=None,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    meta = request.artifact_meta or {}
    if request.source_artifact_id:
        meta = {**meta, "source_artifact_id": request.source_artifact_id}

    artifact = await create_artifact_internal(
        db_session=db_session,
        run_id=run.id,
        session_id=session_id,
        filename=request.filename,
        content=request.content.encode("utf-8"),
        artifact_type=request.artifact_type,
        artifact_meta=meta,
    )

    resp = artifact_to_response(artifact)

    # Stage 10: emit SSE artifact_created
    try:
        q = get_or_create_session_queue(session_id)
        q.put_nowait(("artifact_created", {"artifact": resp.model_dump()}, None))
    except Exception:
        pass

    return resp


@router.get("/runs/{run_id}/artifacts", response_model=ArtifactListResponse)
async def list_run_artifacts(
    run_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
    limit: int = Query(default=100, ge=1, le=500, description="Max artifacts to return"),
    offset: int = Query(default=0, ge=0, description="Number of artifacts to skip"),
    sort: Literal["created_desc", "name_asc", "size_desc"] = Query(
        default="created_desc", description="Sort order"
    ),
    artifact_type: Optional[str] = Query(
        default=None, description="Filter by artifact type"
    ),
    include_deleted: bool = Query(
        default=False, description="Include soft-deleted artifacts"
    ),
):
    """
    List artifacts for a specific run with pagination and filtering.

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        # Verify run exists
        run_result = await db_session.execute(
            select(Run).where(Run.id == run_id)
        )
        run = run_result.scalar_one_or_none()

        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run not found: {run_id}",
            )

        # Build query
        query = select(Artifact).where(Artifact.run_id == run_id)

        # Filter by deletion status
        if not include_deleted:
            query = query.where(Artifact.is_deleted == False)

        # Filter by artifact type
        if artifact_type:
            query = query.where(Artifact.artifact_type == artifact_type)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db_session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        if sort == "created_desc":
            query = query.order_by(Artifact.created_at.desc())
        elif sort == "name_asc":
            query = query.order_by(Artifact.display_name.asc())
        elif sort == "size_desc":
            query = query.order_by(Artifact.size_bytes.desc())

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Execute query
        result = await db_session.execute(query)
        artifacts = result.scalars().all()

        return ArtifactListResponse(
            artifacts=[artifact_to_response(a) for a in artifacts],
            total=total,
            has_more=offset + len(artifacts) < total,
            limit=limit,
            offset=offset,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list run artifacts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list artifacts: {str(e)}",
        )


# =============================================================================
# Single Artifact Endpoints
# =============================================================================


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Get metadata for a single artifact.

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        result = await db_session.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: {artifact_id}",
            )

        return artifact_to_response(artifact)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get artifact {artifact_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get artifact: {str(e)}",
        )


@router.get("/artifacts/{artifact_id}/draft", response_model=ArtifactDraftResponse)
async def get_artifact_draft(
    artifact_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """Get draft content for an artifact."""
    result = await db_session.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {artifact_id}",
        )

    return ArtifactDraftResponse(
        artifact_id=artifact.id,
        session_id=artifact.session_id,
        is_draft=bool(getattr(artifact, "is_draft", False)),
        draft_content=getattr(artifact, "draft_content", None),
        draft_updated_at=getattr(artifact, "draft_updated_at", None),
    )


@router.put("/artifacts/{artifact_id}/draft", response_model=ArtifactDraftResponse)
async def update_artifact_draft(
    artifact_id: str,
    body: ArtifactDraftUpdateRequest,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """Update draft content for an artifact (auto-save)."""
    result = await db_session.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {artifact_id}",
        )

    if body.clear:
        artifact.draft_content = None
        artifact.is_draft = False
        artifact.draft_updated_at = datetime.now(timezone.utc)
    else:
        artifact.draft_content = body.draft_content
        artifact.is_draft = True
        artifact.draft_updated_at = datetime.now(timezone.utc)

    await db_session.commit()
    await db_session.refresh(artifact)

    return ArtifactDraftResponse(
        artifact_id=artifact.id,
        session_id=artifact.session_id,
        is_draft=artifact.is_draft,
        draft_content=artifact.draft_content,
        draft_updated_at=artifact.draft_updated_at,
    )


@router.get("/artifacts/{artifact_id}/content")
async def download_artifact_content(
    artifact_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Download artifact content as a streaming response.

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        result = await db_session.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: {artifact_id}",
            )

        # Get content stream
        try:
            content_stream = get_artifact_content_stream(artifact)
        except FileNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

        # Determine content type
        content_type = artifact.mime_type or "application/octet-stream"

        # Set filename for download
        filename = artifact.display_name

        return StreamingResponse(
            content_stream,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(artifact.size_bytes),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download artifact {artifact_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download artifact: {str(e)}",
        )


@router.get("/artifacts/{artifact_id}/preview", response_model=ArtifactPreviewResponse)
async def get_artifact_preview_endpoint(
    artifact_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Get preview content for an artifact.

    For text/code/markdown: Returns truncated text content.
    For images: Returns kind="image" (use content endpoint for actual image).
    For binary/unknown: Returns kind="none".

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        result = await db_session.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: {artifact_id}",
            )

        # Get preview
        preview = get_artifact_preview(artifact)

        return ArtifactPreviewResponse(
            kind=preview["kind"],
            content_type=preview["content_type"],
            truncated=preview["truncated"],
            text=preview["text"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get artifact preview {artifact_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get preview: {str(e)}",
        )


@router.put("/artifacts/{artifact_id}/content", response_model=ArtifactResponse)
async def update_artifact_content(
    artifact_id: str,
    request: ArtifactUpdateContentRequest,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Update content of an existing artifact in-place.

    - Writes new content to disk (overwrites existing file)
    - Updates size_bytes and content_hash in database
    - Preserves artifact metadata and relationships

    Requires authentication if AUTH_ENABLED=true.
    """
    import hashlib
    from pathlib import Path

    try:
        result = await db_session.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: {artifact_id}",
            )

        if artifact.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update deleted artifact: {artifact_id}",
            )

        # Get storage path
        settings = get_settings()
        storage_path = Path(settings.artifacts_dir) / artifact.storage_path

        # Ensure parent directory exists
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Write new content
        content_bytes = request.content.encode("utf-8")
        storage_path.write_bytes(content_bytes)

        # Update artifact metadata
        artifact.size_bytes = len(content_bytes)
        artifact.content_hash = hashlib.sha256(content_bytes).hexdigest()

        await db_session.commit()
        await db_session.refresh(artifact)

        logger.info(
            f"Artifact content updated: {artifact_id}",
            extra={
                "extra_fields": {
                    "artifact_id": artifact_id,
                    "new_size": len(content_bytes),
                    "user_id": current_user.get("user_id"),
                }
            },
        )

        return artifact_to_response(artifact)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update artifact {artifact_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update artifact: {str(e)}",
        )


# =============================================================================
# Rename Endpoint
# =============================================================================


@router.patch("/artifacts/{artifact_id}/rename", response_model=ArtifactResponse)
async def rename_artifact(
    artifact_id: str,
    request: ArtifactRenameRequest,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Rename an artifact.
    
    Updates the display_name of the artifact.
    For Excel imports (which create both .md and .json), this will also rename
    the sibling artifact if it exists.
    """
    try:
        # Find the artifact
        result = await db_session.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: {artifact_id}",
            )

        if artifact.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot rename deleted artifact: {artifact_id}",
            )

        old_name = artifact.display_name
        new_name = request.new_name.strip()

        # Update the artifact's display_name
        artifact.display_name = new_name
        
        # Check if this is part of an Excel import pair (.md/.json)
        # Excel imports create two artifacts with same base name but different extensions
        renamed_siblings = []
        if artifact.artifact_meta:
            source_path = artifact.artifact_meta.get("source_path", "")
            if source_path and (source_path.endswith(".xlsx") or source_path.endswith(".xls")):
                # This might be an Excel import - look for sibling
                old_base = old_name.rsplit(".", 1)[0] if "." in old_name else old_name
                new_base = new_name.rsplit(".", 1)[0] if "." in new_name else new_name
                
                # Find sibling artifacts in same session with matching base name
                siblings_result = await db_session.execute(
                    select(Artifact).where(
                        Artifact.session_id == artifact.session_id,
                        Artifact.id != artifact_id,
                        Artifact.is_deleted == False,
                    )
                )
                siblings = siblings_result.scalars().all()
                
                for sibling in siblings:
                    sibling_base = sibling.display_name.rsplit(".", 1)[0] if "." in sibling.display_name else sibling.display_name
                    sibling_ext = sibling.display_name.rsplit(".", 1)[1] if "." in sibling.display_name else ""
                    
                    if sibling_base == old_base:
                        # This is a sibling - rename it too
                        sibling.display_name = f"{new_base}.{sibling_ext}" if sibling_ext else new_base
                        renamed_siblings.append(sibling.id)

        await db_session.commit()
        await db_session.refresh(artifact)

        logger.info(
            f"Artifact renamed: {artifact_id} ({old_name} -> {new_name})",
            extra={
                "extra_fields": {
                    "artifact_id": artifact_id,
                    "old_name": old_name,
                    "new_name": new_name,
                    "renamed_siblings": renamed_siblings,
                    "user_id": current_user.get("user_id"),
                }
            },
        )

        return artifact_to_response(artifact)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rename artifact {artifact_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rename artifact: {str(e)}",
        )


# =============================================================================
# Copy Endpoint
# =============================================================================


def _get_copy_name(original_name: str, existing_names: list[str]) -> str:
    """Generate a copy name like 'name (1).ext' or 'name (2).ext'."""
    # Split name and extension
    if "." in original_name:
        base, ext = original_name.rsplit(".", 1)
        ext = f".{ext}"
    else:
        base, ext = original_name, ""
    
    # Try (1), (2), etc. until we find an unused name
    for i in range(1, 100):
        candidate = f"{base} ({i}){ext}"
        if candidate not in existing_names:
            return candidate
    
    # Fallback with UUID
    return f"{base} (copy){ext}"


@router.post("/artifacts/{artifact_id}/copy", response_model=ArtifactResponse)
async def copy_artifact(
    artifact_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Copy an artifact within the same session.
    
    Creates a new artifact record pointing to the same file, with a new name like "name (1).ext".
    Does NOT copy the physical file - just creates a new DB reference.
    """
    try:
        # Find the source artifact
        result = await db_session.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        source = result.scalar_one_or_none()

        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: {artifact_id}",
            )

        if source.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot copy deleted artifact: {artifact_id}",
            )

        # Get existing artifact names in session to avoid collisions
        existing_result = await db_session.execute(
            select(Artifact.display_name).where(
                Artifact.session_id == source.session_id,
                Artifact.is_deleted == False,
            )
        )
        existing_names = [r[0] for r in existing_result.fetchall()]
        
        # Generate new name
        new_name = _get_copy_name(source.display_name, existing_names)
        new_id = str(uuid4())
        
        # Create new artifact record pointing to SAME file
        new_artifact = Artifact(
            id=new_id,
            run_id=source.run_id,
            session_id=source.session_id,
            display_name=new_name,
            storage_path=source.storage_path,  # Same file!
            extension=source.extension,
            size_bytes=source.size_bytes,
            content_hash=source.content_hash,
            mime_type=source.mime_type,
            artifact_type=source.artifact_type,
            artifact_meta=source.artifact_meta.copy() if source.artifact_meta else None,
            is_deleted=False,
        )
        
        db_session.add(new_artifact)
        await db_session.commit()
        await db_session.refresh(new_artifact)

        logger.info(
            f"Artifact copied: {artifact_id} -> {new_id} ({new_name})",
            extra={
                "extra_fields": {
                    "source_id": artifact_id,
                    "new_id": new_id,
                    "new_name": new_name,
                    "user_id": current_user.get("user_id"),
                }
            },
        )

        return artifact_to_response(new_artifact)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to copy artifact {artifact_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to copy artifact: {str(e)}",
        )


# =============================================================================
# Batch Download Endpoint
# =============================================================================


@router.get("/runs/{run_id}/artifacts/zip")
async def download_run_artifacts_zip(
    run_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
    include_deleted: bool = Query(
        default=False, description="Include soft-deleted artifacts"
    ),
):
    """
    Download all artifacts for a run as a ZIP file (streaming).

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        # Verify run exists
        run_result = await db_session.execute(
            select(Run).where(Run.id == run_id)
        )
        run = run_result.scalar_one_or_none()

        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run not found: {run_id}",
            )

        # Get artifacts
        query = select(Artifact).where(Artifact.run_id == run_id)
        if not include_deleted:
            query = query.where(Artifact.is_deleted == False)

        result = await db_session.execute(query)
        artifacts = result.scalars().all()

        if not artifacts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No artifacts found for run: {run_id}",
            )

        # Create ZIP stream
        zip_stream = create_zip_stream(list(artifacts))

        # Generate filename
        filename = f"artifacts_{run_id[:8]}.zip"

        return StreamingResponse(
            zip_stream,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create ZIP for run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ZIP: {str(e)}",
        )


# =============================================================================
# Delete Endpoint
# =============================================================================


@router.delete("/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Soft-delete an artifact.

    The artifact remains in the database with is_deleted=True.
    The file on disk is NOT deleted (for audit purposes).

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        result = await db_session.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )
        artifact = result.scalar_one_or_none()

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact not found: {artifact_id}",
            )

        if artifact.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Artifact already deleted: {artifact_id}",
            )

        await soft_delete_artifact(db_session, artifact)

        # Record undoable action (Undo stack MVP)
        try:
            audit = AuditLog(
                id=str(uuid4()),
                actor="user",
                actor_id=current_user.get("user_id"),
                action="undoable_artifact_delete",
                resource=f"artifact:{artifact_id}",
                session_id=artifact.session_id,
                message=f"Artifact soft-deleted: {artifact.display_name}",
                details={
                    "action_type": "artifact_delete",
                    "artifact_id": artifact_id,
                    "undone": False,
                },
                success=True,
            )
            db_session.add(audit)
            await db_session.commit()
        except Exception:
            # Never fail delete due to audit log
            pass

        # Stage 10: emit SSE artifact_deleted
        try:
            q = get_or_create_session_queue(artifact.session_id)
            q.put_nowait(
                (
                    "artifact_deleted",
                    {
                        "artifact_id": artifact_id,
                        "session_id": artifact.session_id,
                        "run_id": artifact.run_id,
                    },
                    None,
                )
            )
        except Exception:
            pass

        logger.info(
            f"Artifact deleted: {artifact_id}",
            extra={
                "extra_fields": {
                    "artifact_id": artifact_id,
                    "user_id": current_user.get("user_id"),
                }
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete artifact {artifact_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete artifact: {str(e)}",
        )
