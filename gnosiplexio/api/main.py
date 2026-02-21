"""
Gnosiplexio API — Knowledge Graph Engine entry point.

FastAPI application for the Gnosiplexio knowledge graph service.
Connects to Veritas or generic data sources via configurable adapters.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as gnosiplexio_router
from config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("gnosiplexio")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — startup and shutdown."""
    settings = get_settings()
    logger.info("Gnosiplexio starting...")
    logger.info("  Data source: %s", settings.DATA_SOURCE)
    if settings.DATA_SOURCE == "veritas":
        logger.info("  Veritas API: %s", settings.VERITAS_API_URL)
    logger.info("  Data directory: %s", settings.DATA_DIR)
    yield
    logger.info("Gnosiplexio shutting down...")


# Create the FastAPI application
app = FastAPI(
    title="Gnosiplexio - Knowledge Graph Engine",
    description=(
        "Knowledge graph engine that transforms research papers into a rich, "
        "interconnected network of knowledge. Integrates with Veritas for paper "
        "metadata or operates standalone with generic data sources."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
def health_check():
    """
    Health check endpoint.
    
    Returns service status and configuration summary.
    """
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "gnosiplexio",
        "version": "0.1.0",
        "config": {
            "data_source": settings.DATA_SOURCE,
            "veritas_api_url": settings.VERITAS_API_URL if settings.DATA_SOURCE == "veritas" else None,
            "auto_save": settings.AUTO_SAVE,
        },
    }


@app.get("/", tags=["system"])
def root():
    """Root endpoint with service info."""
    return {
        "service": "Gnosiplexio - Knowledge Graph Engine",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1/gnosiplexio",
    }


# ---------------------------------------------------------------------------
# Include API routes
# ---------------------------------------------------------------------------

app.include_router(gnosiplexio_router, prefix=settings.API_PREFIX)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.DEBUG,
    )
