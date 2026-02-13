"""
Explorer Routes - File browsing and import API for Agent B.

Endpoints:
- GET /explorer/browse - Browse a directory
- GET /explorer/file - Get file info
- POST /explorer/import - Import file as artifact
- GET /explorer/roots - Get common root directories
"""

import os
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from datetime import datetime, timezone

from ..services.explorer_service import (
    list_directory,
    get_file_info,
    convert_file_to_artifact_payloads,
)
from ..services.capabilities_service import get_explorer_capabilities
from ..services.bulk_import_service import list_importable_files
from ..config import get_settings
from ..database import get_session
from ..models import Run, Session
from ..artifact_service import create_artifact_internal
from ..routes.message_routes import get_or_create_session_queue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/explorer")

settings = get_settings()


class ImportRequest(BaseModel):
    """Request to import a file as artifact."""
    file_path: str
    session_id: str


class ImportResponse(BaseModel):
    """Response from import operation."""

    success: bool

    # The run created for this import (so UI can link artifacts to a run)
    run_id: Optional[str] = None

    # Artifacts created (best-effort; may be partial if some payloads fail)
    artifacts: list = []

    # Basic summary
    created_count: int = 0
    failed_count: int = 0

    # Source filename (basename)
    source_file: Optional[str] = None

    # Legacy single error message (kept for backward compatibility)
    error: Optional[str] = None

    # Detailed errors (if any)
    errors: list[str] = []


@router.get("/roots")
async def get_root_directories():
    """
    Get common root directories for browsing.
    Returns user's home, desktop, documents, and drives.
    """
    roots = []
    
    # User directories
    home = Path.home()
    roots.append({
        "name": "Home",
        "path": str(home),
        "icon": "home",
    })
    
    # Desktop
    desktop = home / "Desktop"
    if desktop.exists():
        roots.append({
            "name": "Desktop",
            "path": str(desktop),
            "icon": "desktop",
        })
    
    # OneDrive Desktop (common on Windows)
    onedrive_desktop = home / "OneDrive - The University Of Newcastle" / "Desktop"
    if onedrive_desktop.exists():
        roots.append({
            "name": "OneDrive Desktop",
            "path": str(onedrive_desktop),
            "icon": "cloud",
        })
    
    # Documents
    documents = home / "Documents"
    if documents.exists():
        roots.append({
            "name": "Documents",
            "path": str(documents),
            "icon": "folder",
        })
    
    # Downloads
    downloads = home / "Downloads"
    if downloads.exists():
        roots.append({
            "name": "Downloads",
            "path": str(downloads),
            "icon": "download",
        })
    
    # Windows drives
    if os.name == 'nt':
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                roots.append({
                    "name": f"Drive {letter}:",
                    "path": drive,
                    "icon": "hard-drive",
                })
    
    return {"roots": roots}


@router.get("/browse")
async def browse_directory(
    path: str = Query(..., description="Directory path to browse"),
):
    """
    Browse contents of a directory.
    Returns folders first, then files, sorted alphabetically.
    """
    result = list_directory(path)
    if "error" in result and result.get("error"):
        # Still return 200 with error in body for better UX
        pass
    return result


@router.get("/file")
async def get_file_details(
    path: str = Query(..., description="File path"),
):
    """Get detailed information about a file."""
    result = get_file_info(path)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/import", response_model=ImportResponse)
async def import_file(
    request: ImportRequest,
    db_session=Depends(get_session),
):
    """Import a file as artifact(s) and register them in the artifacts DB.

    This endpoint is what powers the Explorer "Import as Artifact" button.

    Conversions:
    - .docx → .md
    - .xlsx/.csv → .md + .json (dual format)
    - .pdf → .md
    - .txt → .md
    - .md/.json → copy directly

    Note:
        Artifacts in the UI are backed by the `artifacts` table. Simply writing
        files to disk is not enough — we must create `Artifact` DB rows.
    """
    # Validate session exists
    from sqlalchemy import select

    session_result = await db_session.execute(
        select(Session).where(Session.id == request.session_id)
    )
    if session_result.scalar_one_or_none() is None:
        return ImportResponse(success=False, error=f"Session not found: {request.session_id}")

    source_file = os.path.basename(request.file_path)

    # Create an import run first, so failures still have a run record
    now = datetime.now(timezone.utc)
    run = Run(
        session_id=request.session_id,
        task=f"Import artifacts from file: {source_file}",
        status="running",
        started_at=now,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)

    created: list[dict] = []
    errors: list[str] = []

    try:
        payloads = convert_file_to_artifact_payloads(request.file_path)
        if not payloads:
            raise ValueError("No artifacts produced")

        for p in payloads:
            try:
                artifact = await create_artifact_internal(
                    db_session=db_session,
                    run_id=run.id,
                    session_id=request.session_id,
                    filename=p["filename"],
                    content=p["content"],
                    artifact_type="file",
                    artifact_meta=p.get("artifact_meta"),
                )
                created_item = {
                    "name": artifact.display_name,
                    "path": artifact.storage_path,
                    "type": "markdown"
                    if artifact.extension == "md"
                    else (artifact.extension or "file"),
                    "source": source_file,
                    "artifact_id": artifact.id,
                    "run_id": str(run.id),
                }
                created.append(created_item)

                # Stage 10: emit SSE artifact_created (lightweight)
                try:
                    q = get_or_create_session_queue(request.session_id)
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
                                    "created_at": artifact.created_at.isoformat() if hasattr(artifact.created_at,'isoformat') else str(artifact.created_at),
                                    "artifact_meta": artifact.artifact_meta,
                                    "is_deleted": artifact.is_deleted,
                                    "can_preview": True,
                                    "preview_kind": "markdown" if artifact.extension == "md" else "text",
                                    "download_url": f"/api/v1/artifacts/{artifact.id}/content",
                                }
                            },
                            None,
                        )
                    )
                except Exception:
                    pass

            except Exception as e:
                logger.exception("Failed creating artifact for payload")
                errors.append(f"{p.get('filename','(unknown)')}: {type(e).__name__}: {str(e)}")

        # Finalize run
        run.completed_at = datetime.now(timezone.utc)
        if errors:
            run.status = "failed"
            run.error = f"{len(errors)} artifact(s) failed during import"
        else:
            run.status = "completed"
        db_session.add(run)
        await db_session.commit()

        return ImportResponse(
            success=(len(errors) == 0),
            run_id=str(run.id),
            artifacts=created,
            created_count=len(created),
            failed_count=len(errors),
            source_file=source_file,
            error=(errors[0] if errors else None),
            errors=errors,
        )

    except Exception as e:
        logger.exception("Explorer import failed")
        # Mark run failed
        run.status = "failed"
        run.error = f"{type(e).__name__}: {str(e)}"
        run.completed_at = datetime.now(timezone.utc)
        db_session.add(run)
        await db_session.commit()

        return ImportResponse(
            success=False,
            run_id=str(run.id),
            artifacts=created,
            created_count=len(created),
            failed_count=max(1, len(errors)),
            source_file=source_file,
            error=str(e),
            errors=(errors if errors else [f"{type(e).__name__}: {str(e)}"]),
        )


@router.get("/importables")
async def list_importables(path: str = Query(..., description="Folder path"), recursive: bool = Query(default=False)):
    """List importable files under a folder.

    Stage 9: supports batch import from a folder.
    """

    try:
        files = list_importable_files(path, recursive=recursive)
        return {"path": path, "recursive": recursive, "count": len(files), "files": files}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/supported-types")
async def get_supported_types():
    """Get list of supported file types for import."""
    return {
        "types": [
            {
                "extension": ".docx",
                "description": "Microsoft Word",
                "converts_to": [".md"],
            },
            {
                "extension": ".xlsx",
                "description": "Microsoft Excel",
                "converts_to": [".md", ".json"],
            },
            {
                "extension": ".xls",
                "description": "Microsoft Excel (Legacy)",
                "converts_to": [".md", ".json"],
            },
            {
                "extension": ".csv",
                "description": "CSV File",
                "converts_to": [".md", ".json"],
            },
            {
                "extension": ".pdf",
                "description": "PDF Document",
                "converts_to": [".md"],
            },
            {
                "extension": ".txt",
                "description": "Text File",
                "converts_to": [".md"],
            },
            {
                "extension": ".md",
                "description": "Markdown",
                "converts_to": [".md"],
            },
            {
                "extension": ".json",
                "description": "JSON",
                "converts_to": [".json"],
            },
        ]
    }


@router.get("/capabilities")
async def get_capabilities():
    """Report backend capabilities for Explorer import conversions."""
    return get_explorer_capabilities()
