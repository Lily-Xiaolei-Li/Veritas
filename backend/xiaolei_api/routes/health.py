from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="xiaolei_api",
        time=datetime.now(timezone.utc).isoformat(),
    )
