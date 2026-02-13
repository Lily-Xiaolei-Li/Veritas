"""RAG Source registry routes (Managed RAG) — M1.

Endpoints:
- GET  /rag/sources
- POST /rag/sources
- GET  /rag/sources/{source_id}

Notes:
- Requires DB. If DB is not configured, returns 503 with remediation.
- Follows global auth rules via require_auth.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.database import get_database
from app.logging_config import get_logger
from app.models import RagSource
from app.routes.auth_routes import require_auth

router = APIRouter(prefix="/rag", tags=["rag"])
logger = get_logger("rag")


# =============================================================================
# Schemas
# =============================================================================


class RagSourceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    preset: str
    status: str
    source_metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class RagSourceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    preset: str = Field(default="generic", description="papers|interviews|books|generic")
    source_metadata: Optional[dict] = None


class RagSourceListResponse(BaseModel):
    sources: list[RagSourceResponse]


def _db_required_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Database not configured. Set DATABASE_URL to enable managed RAG sources. "
            "(In no-DB mode, only /health and limited features are available.)"
        ),
    )


# =============================================================================
# Routes
# =============================================================================


@router.get("/sources", response_model=RagSourceListResponse)
async def list_sources(current_user: dict = Depends(require_auth)):
    db = get_database()
    if not db.is_configured:
        raise _db_required_error()

    if not db._engine:
        await db.initialize()

    async with db.session() as s:
        result = await s.execute(select(RagSource).order_by(RagSource.created_at.desc()))
        rows = result.scalars().all()

    return RagSourceListResponse(
        sources=[
            RagSourceResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                preset=r.preset,
                status=r.status,
                source_metadata=r.source_metadata,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]
    )


@router.post("/sources", response_model=RagSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    req: RagSourceCreateRequest,
    current_user: dict = Depends(require_auth),
):
    db = get_database()
    if not db.is_configured:
        raise _db_required_error()

    if not db._engine:
        await db.initialize()

    async with db.session() as s:
        # uniqueness check
        existing = await s.execute(select(RagSource).where(RagSource.name == req.name))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"RAG source already exists: {req.name}",
            )

        src = RagSource(
            id=str(uuid4()),
            name=req.name,
            description=req.description,
            preset=req.preset,
            status="creating",
            source_metadata=req.source_metadata,
        )
        s.add(src)

    # Re-open to read back (updated timestamps)
    async with db.session() as s:
        result = await s.execute(select(RagSource).where(RagSource.id == src.id))
        created = result.scalar_one()

    # mark ready (M1 doesn't ingest yet)
    async with db.session() as s:
        await s.execute(
            RagSource.__table__.update()
            .where(RagSource.id == src.id)
            .values(status="ready")
        )

    async with db.session() as s:
        result = await s.execute(select(RagSource).where(RagSource.id == src.id))
        created = result.scalar_one()

    logger.info(
        f"RAG source created: {created.name}",
        extra={"extra_fields": {"source_id": created.id, "preset": created.preset}},
    )

    return RagSourceResponse(
        id=created.id,
        name=created.name,
        description=created.description,
        preset=created.preset,
        status=created.status,
        source_metadata=created.source_metadata,
        created_at=created.created_at,
        updated_at=created.updated_at,
    )


@router.get("/sources/{source_id}", response_model=RagSourceResponse)
async def get_source(source_id: str, current_user: dict = Depends(require_auth)):
    db = get_database()
    if not db.is_configured:
        raise _db_required_error()

    if not db._engine:
        await db.initialize()

    async with db.session() as s:
        result = await s.execute(select(RagSource).where(RagSource.id == source_id))
        src = result.scalar_one_or_none()
        if not src:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source not found: {source_id}")

    return RagSourceResponse(
        id=src.id,
        name=src.name,
        description=src.description,
        preset=src.preset,
        status=src.status,
        source_metadata=src.source_metadata,
        created_at=src.created_at,
        updated_at=src.updated_at,
    )
