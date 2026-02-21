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

# Main router for the plugin - exported for Veritas Core plugin loader
router = APIRouter()


# Placeholder routes - will be populated as spell modules are implemented
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
