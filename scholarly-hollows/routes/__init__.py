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

import logging
from fastapi import APIRouter

logger = logging.getLogger("scholarly-hollows.routes")

# Main router for the plugin - exported for Veritas Core plugin loader
router = APIRouter()

# Track which spells loaded successfully
_loaded_spells = []
_failed_spells = []


# Try to import each spell router, gracefully degrade if dependencies missing
try:
    from .veritafactum import router as veritafactum_router
    router.include_router(veritafactum_router)
    _loaded_spells.append("veritafactum")
except ImportError as e:
    logger.warning(f"Failed to load veritafactum spell: {e}")
    _failed_spells.append(("veritafactum", str(e)))

try:
    from .citalio import router as citalio_router
    router.include_router(citalio_router)
    _loaded_spells.append("citalio")
except ImportError as e:
    logger.warning(f"Failed to load citalio spell: {e}")
    _failed_spells.append(("citalio", str(e)))

try:
    from .proliferomaxima import router as proliferomaxima_router
    router.include_router(proliferomaxima_router)
    _loaded_spells.append("proliferomaxima")
except ImportError as e:
    logger.warning(f"Failed to load proliferomaxima spell: {e}")
    _failed_spells.append(("proliferomaxima", str(e)))

try:
    from .exportario import router as exportario_router
    router.include_router(exportario_router)
    _loaded_spells.append("exportario")
except ImportError as e:
    logger.warning(f"Failed to load exportario spell: {e}")
    _failed_spells.append(("exportario", str(e)))


@router.get("/health")
async def health_check():
    """Health check endpoint for Scholarly Hollows plugin."""
    return {
        "status": "ok" if len(_loaded_spells) > 0 else "degraded",
        "plugin": "scholarly-hollows",
        "spells": _loaded_spells,
        "failed": [{"spell": name, "error": err} for name, err in _failed_spells] if _failed_spells else None,
    }


@router.get("/spells")
async def list_spells():
    """List all available spells and their status."""
    all_spells = [
        {"id": "veritafactum", "name": "真知照见", "loaded": "veritafactum" in _loaded_spells},
        {"id": "citalio", "name": "引经据典", "loaded": "citalio" in _loaded_spells},
        {"id": "proliferomaxima", "name": "寻书万卷", "loaded": "proliferomaxima" in _loaded_spells},
        {"id": "exportario", "name": "破壁取珠", "loaded": "exportario" in _loaded_spells},
    ]
    return {"spells": all_spells, "total": len(all_spells), "loaded": len(_loaded_spells)}
