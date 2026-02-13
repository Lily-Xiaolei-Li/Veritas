"""
Prometheus metrics endpoint (B7.2).

Security:
- METRICS_ENABLED must be true
- METRICS_TOKEN required in production (or behind proxy)
"""

from fastapi import APIRouter, Response, HTTPException, Header
from typing import Optional

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.config import get_settings

router = APIRouter()


@router.get("/metrics")
async def metrics(authorization: Optional[str] = Header(default=None)):
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.

    Security:
    - Returns 404 if metrics are disabled
    - Requires Bearer token authentication in production
    - In development, allows unauthenticated access if no token configured
    """
    settings = get_settings()

    # Check if metrics enabled
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics not enabled")

    # Check token if configured
    if settings.metrics_token:
        expected = f"Bearer {settings.metrics_token}"
        if authorization != expected:
            raise HTTPException(status_code=403, detail="Invalid metrics token")
    elif settings.environment == "production":
        # No token in prod = reject (must be behind proxy)
        raise HTTPException(
            status_code=403,
            detail="Metrics require token in production"
        )

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
