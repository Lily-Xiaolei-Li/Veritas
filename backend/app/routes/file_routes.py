"""
File Browser API routes (B1.2 - File Browser & Workspace).

Provides:
- GET /files - List indexed files with pagination and filtering
- GET /files/{file_id} - Get single file details
- POST /sessions/{id}/files - Attach files to session
- GET /sessions/{id}/files - List attached files
- DELETE /sessions/{id}/files/{file_id} - Detach file from session
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.logging_config import get_logger
from app.models import FileIndex, Session, SessionFileAttachment
from app.routes.auth_routes import require_auth

router = APIRouter()
logger = get_logger("files")


# =============================================================================
# Request/Response Models
# =============================================================================


class FileIndexResponse(BaseModel):
    """Response model for a file index entry."""

    id: str
    path: str
    filename: str
    extension: Optional[str]
    parent_dir: str
    size_bytes: int
    content_hash: Optional[str]
    mime_type: Optional[str]
    modified_at: datetime
    indexed_at: datetime
    is_deleted: bool


class FileListResponse(BaseModel):
    """Response model for paginated file list."""

    files: List[FileIndexResponse]
    total: int
    has_more: bool
    limit: int
    offset: int


class AttachFilesRequest(BaseModel):
    """Request model for attaching files to session."""

    file_ids: List[str] = Field(
        ..., min_length=1, max_length=100, description="File IDs to attach"
    )


class FileAttachmentResponse(BaseModel):
    """Response model for a file attachment."""

    id: str
    session_id: str
    file_id: str
    attached_at: datetime
    file: FileIndexResponse


class AttachFilesResponse(BaseModel):
    """Response model for attach files operation."""

    attached: int
    already_attached: int
    not_found: int


# =============================================================================
# File Listing Endpoints
# =============================================================================


@router.get("/files", response_model=FileListResponse)
async def list_files(
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
    limit: int = Query(default=100, ge=1, le=500, description="Max files to return"),
    offset: int = Query(default=0, ge=0, description="Number of files to skip"),
    sort: Literal["mtime_desc", "name_asc", "size_desc"] = Query(
        default="mtime_desc", description="Sort order"
    ),
    prefix: Optional[str] = Query(
        default=None, description="Filter by parent_dir prefix (e.g., 'src/')"
    ),
    extension: Optional[str] = Query(
        default=None, description="Filter by file extension (e.g., 'py')"
    ),
    search: Optional[str] = Query(
        default=None, description="Filter filename contains (case-insensitive)"
    ),
    include_deleted: bool = Query(
        default=False, description="Include soft-deleted files"
    ),
):
    """
    List indexed files with pagination and filtering.

    Files are from the workspace directory and are indexed automatically
    by the file watcher service.

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        # Build base query
        query = select(FileIndex)

        # Filter by deletion status (default: hide deleted)
        if not include_deleted:
            query = query.where(FileIndex.is_deleted == False)

        # Filter by parent_dir prefix
        if prefix:
            query = query.where(FileIndex.parent_dir.startswith(prefix))

        # Filter by extension
        if extension:
            # Normalize: remove leading dot if provided
            ext = extension.lstrip(".")
            query = query.where(FileIndex.extension == ext)

        # Filter by filename search
        if search:
            query = query.where(FileIndex.filename.ilike(f"%{search}%"))

        # Get total count before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db_session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        if sort == "mtime_desc":
            query = query.order_by(FileIndex.modified_at.desc())
        elif sort == "name_asc":
            query = query.order_by(FileIndex.filename.asc())
        elif sort == "size_desc":
            query = query.order_by(FileIndex.size_bytes.desc())

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Execute query
        result = await db_session.execute(query)
        files = result.scalars().all()

        return FileListResponse(
            files=[
                FileIndexResponse(
                    id=f.id,
                    path=f.path,
                    filename=f.filename,
                    extension=f.extension,
                    parent_dir=f.parent_dir,
                    size_bytes=f.size_bytes,
                    content_hash=f.content_hash,
                    mime_type=f.mime_type,
                    modified_at=f.modified_at,
                    indexed_at=f.indexed_at,
                    is_deleted=f.is_deleted,
                )
                for f in files
            ],
            total=total,
            has_more=offset + len(files) < total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Failed to list files: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}",
        )


@router.get("/files/{file_id}", response_model=FileIndexResponse)
async def get_file(
    file_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Get details for a single indexed file.

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        result = await db_session.execute(
            select(FileIndex).where(FileIndex.id == file_id)
        )
        file = result.scalar_one_or_none()

        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}",
            )

        return FileIndexResponse(
            id=file.id,
            path=file.path,
            filename=file.filename,
            extension=file.extension,
            parent_dir=file.parent_dir,
            size_bytes=file.size_bytes,
            content_hash=file.content_hash,
            mime_type=file.mime_type,
            modified_at=file.modified_at,
            indexed_at=file.indexed_at,
            is_deleted=file.is_deleted,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file {file_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file: {str(e)}",
        )


# =============================================================================
# Session File Attachment Endpoints
# =============================================================================


@router.post(
    "/sessions/{session_id}/files",
    response_model=AttachFilesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_files_to_session(
    session_id: str,
    request: AttachFilesRequest,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Attach files to a session.

    Files can be attached to provide context for the agent conversation.
    Duplicate attachments are silently ignored.

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

        attached = 0
        already_attached = 0
        not_found = 0

        for file_id in request.file_ids:
            # Check if file exists
            file_result = await db_session.execute(
                select(FileIndex).where(FileIndex.id == file_id)
            )
            file = file_result.scalar_one_or_none()

            if not file:
                not_found += 1
                continue

            # Check if already attached
            existing = await db_session.execute(
                select(SessionFileAttachment).where(
                    SessionFileAttachment.session_id == session_id,
                    SessionFileAttachment.file_id == file_id,
                )
            )
            if existing.scalar_one_or_none():
                already_attached += 1
                continue

            # Create attachment
            attachment = SessionFileAttachment(
                id=str(uuid4()),
                session_id=session_id,
                file_id=file_id,
            )
            db_session.add(attachment)
            attached += 1

        await db_session.commit()

        logger.info(
            f"Attached {attached} files to session {session_id}",
            extra={
                "extra_fields": {
                    "session_id": session_id,
                    "attached": attached,
                    "already_attached": already_attached,
                    "not_found": not_found,
                }
            },
        )

        return AttachFilesResponse(
            attached=attached,
            already_attached=already_attached,
            not_found=not_found,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to attach files to session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to attach files: {str(e)}",
        )


@router.get("/sessions/{session_id}/files", response_model=List[FileAttachmentResponse])
async def list_session_files(
    session_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    List files attached to a session.

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

        # Get attachments with file details
        result = await db_session.execute(
            select(SessionFileAttachment)
            .where(SessionFileAttachment.session_id == session_id)
            .order_by(SessionFileAttachment.attached_at.desc())
        )
        attachments = result.scalars().all()

        # Get file details for each attachment
        response = []
        for attachment in attachments:
            file_result = await db_session.execute(
                select(FileIndex).where(FileIndex.id == attachment.file_id)
            )
            file = file_result.scalar_one_or_none()

            if file:
                response.append(
                    FileAttachmentResponse(
                        id=attachment.id,
                        session_id=attachment.session_id,
                        file_id=attachment.file_id,
                        attached_at=attachment.attached_at,
                        file=FileIndexResponse(
                            id=file.id,
                            path=file.path,
                            filename=file.filename,
                            extension=file.extension,
                            parent_dir=file.parent_dir,
                            size_bytes=file.size_bytes,
                            content_hash=file.content_hash,
                            mime_type=file.mime_type,
                            modified_at=file.modified_at,
                            indexed_at=file.indexed_at,
                            is_deleted=file.is_deleted,
                        ),
                    )
                )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list session files for {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list session files: {str(e)}",
        )


@router.delete(
    "/sessions/{session_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def detach_file_from_session(
    session_id: str,
    file_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Detach a file from a session.

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

        # Find and delete attachment
        result = await db_session.execute(
            select(SessionFileAttachment).where(
                SessionFileAttachment.session_id == session_id,
                SessionFileAttachment.file_id == file_id,
            )
        )
        attachment = result.scalar_one_or_none()

        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File attachment not found: {file_id} in session {session_id}",
            )

        await db_session.delete(attachment)
        await db_session.commit()

        logger.info(
            f"Detached file {file_id} from session {session_id}",
            extra={
                "extra_fields": {
                    "session_id": session_id,
                    "file_id": file_id,
                }
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to detach file {file_id} from session {session_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detach file: {str(e)}",
        )
