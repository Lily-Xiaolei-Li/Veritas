"""
Scholarly Hollows (SH) API Routes

This module exports the combined router for all Scholarly Hollows magic spells.

Spells:
    - Veritafactum (真知照见): Citation verification
    - Citalio (引经据典): Citation recommendation
    - Proliferomaxima (寻书万卷): Citation network expansion
    - Ex-portario (破壁取珠): Paywall bypass for full-text download

All routes are prefixed with /api/v1/sh/ when loaded by Veritas Core.
"""

from fastapi import APIRouter

from .veritafactum import router as veritafactum_router
from .citalio import router as citalio_router
from .proliferomaxima import router as proliferomaxima_router
from .exportario import router as exportario_router

# Main router for the plugin - exported for Veritas Core plugin loader
router = APIRouter()

# Include all spell routers
router.include_router(veritafactum_router)
router.include_router(citalio_router)
router.include_router(proliferomaxima_router)
router.include_router(exportario_router)


@router.get("/health")
async def health_check():
    """Health check endpoint for Scholarly Hollows plugin."""
    return {
        "status": "ok",
        "plugin": "scholarly-hollows",
        "spells": [
            "veritafactum",
            "citalio",
            "proliferomaxima",
            "exportario"
        ]
    }
