from fastapi import FastAPI

from .routes import router as api_router


def create_app() -> FastAPI:
    """Create FastAPI app used by docker API service."""
    app = FastAPI(title="GP Viz API", version="0.1.0")
    app.include_router(api_router)
    return app
