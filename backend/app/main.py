import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Windows compatibility: psycopg3 async does not support ProactorEventLoop.
# Force SelectorEventLoopPolicy early, before any async DB/checkpointer init.
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        # Best-effort; if policy cannot be set, checkpointer will fall back to disabled.
        pass

# NOTE: keep stdout clean for tests; use structured logger later in startup.

# Load .env file FIRST, before any other imports.
# IMPORTANT: do not override explicitly provided environment variables (even if empty).
from dotenv import dotenv_values

_env_path = Path(__file__).resolve().parent.parent / ".env"
for _k, _v in (dotenv_values(_env_path) or {}).items():
    if _v is None:
        continue
    if _k not in os.environ:
        os.environ[_k] = _v

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .agent.checkpointer import (
    initialize_checkpointer,
    is_checkpointer_ready,
    shutdown_checkpointer,
)
from .agent.reconciliation import reconcile_stale_runs
from .config import ConfigurationError, get_settings

# docker_check removed (repo enforces no-docker)
from .database import get_database
from .file_watcher import (
    FileWatcher,
    broadcast_file_event_to_all_sessions,
    set_session_event_queues,
)
from .logging_config import get_logger, setup_logging
from .metrics import APP_INFO
from .middleware import MetricsMiddleware, RequestIDMiddleware
from .migrations import run_migrations
from .routes import api_router
from .routes.log_routes import router as log_router
from .routes.log_routes import setup_websocket_log_handler
from .routes.message_routes import get_session_event_queues
from .routes.metrics_routes import router as metrics_router
from .routes.xiaolei_chat_routes import router as xiaolei_chat_router
from .routes.checker_routes import router as checker_router
from .routes.citalio_routes import router as citalio_router
from .services.llm_service import shutdown_llm_service

# Load and validate configuration at module level
try:
    settings = get_settings()
except ConfigurationError as e:
    print(f"FATAL: Configuration error:\n{e}", file=sys.stderr)
    sys.exit(1)

# Setup logging based on configuration
setup_logging(settings)
logger = get_logger("api")

# Setup WebSocket log streaming
setup_websocket_log_handler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown tasks:
    - Database initialization
    - Running migrations
    - File watcher initialization (B1.2)
    - Metrics initialization (B7.2)
    - Cleanup on shutdown
    """
    # Startup
    logger.info("Agent B starting up...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"Log format: {settings.log_format}")

    # Initialize metrics (B7.2)
    APP_INFO.info({
        "version": "0.0.4",
        "environment": settings.environment,
    })

    # Warn about multi-process limitations
    web_concurrency = int(os.environ.get("WEB_CONCURRENCY", "1"))
    if web_concurrency > 1:
        logger.warning(
            f"WEB_CONCURRENCY={web_concurrency}: Prometheus metrics are per-process. "
            "Multiprocess mode requires prometheus_client multiprocess collector (B7.3)."
        )

    # Initialize database if configured
    db = get_database()
    if db.is_configured:
        # Redact credentials from log output
        db_url_safe = settings.database_url.split('@')[0] + '@...' if settings.database_url else ''
        logger.info(f"Database configured: {db_url_safe}")

        try:
            await db.initialize()
            logger.info("Database initialized successfully")

            # Run migrations (B2.4 stability)
            logger.info("Running database migrations...")
            migration_result = run_migrations()

            if migration_result.get("ok"):
                logger.info(f"✓ {migration_result.get('detail')}")
            else:
                msg = f"Migrations failed: {migration_result.get('detail')}"

                if settings.environment == "production":
                    # Fail fast in production to avoid running with a broken schema.
                    logger.error(msg)
                    raise RuntimeError(msg)

                # In dev/test, warn and keep running so UI/dev tools can still load.
                logger.warning(msg)
                logger.warning("Application will continue, but database functionality may be limited")

            # Initialize LangGraph checkpointer (B2.1)
            try:
                await initialize_checkpointer(settings.database_url)
                if is_checkpointer_ready():
                    logger.info("LangGraph checkpointer initialized (persistence enabled)")
                else:
                    logger.warning("LangGraph checkpointer not available (persistence disabled)")
            except Exception as exc:
                logger.error(f"Checkpointer initialization failed: {exc}", exc_info=True)
                logger.warning("Application will continue without checkpoint persistence")

            # Reconcile stale runs on startup (B2.1)
            try:
                async with db.session() as reconcile_session:
                    interrupted_count = await reconcile_stale_runs(reconcile_session)
                    if interrupted_count > 0:
                        logger.info(f"Reconciled {interrupted_count} stale runs to 'interrupted' status")
            except Exception as exc:
                logger.error(f"Run reconciliation failed: {exc}", exc_info=True)
                logger.warning("Application will continue, but some runs may be stuck in 'running' status")

        except Exception as exc:
            logger.error(f"Database initialization failed: {exc}", exc_info=True)

            if settings.environment == "production":
                # Fail fast in production: DB init/migrations are required for correctness.
                raise

            logger.warning("Application will continue without database")
    else:
        logger.info("Database not configured (DATABASE_URL not set)")
        logger.info("Application will run without persistent storage")

    # Initialize file watcher (B1.2) - declare BEFORE conditional to fix scope bug
    file_watcher: FileWatcher | None = None

    try:
        # Start file watcher if enabled and database is configured
        if settings.file_watcher_enabled and db.is_configured:
            logger.info(f"File watcher enabled, watching: {settings.workspace_dir}")

            # Connect file watcher to SSE infrastructure
            set_session_event_queues(get_session_event_queues())

            file_watcher = FileWatcher(
                workspace_dir=settings.workspace_dir,
                database=db,
                broadcast_callback=broadcast_file_event_to_all_sessions,
            )

            try:
                await file_watcher.start()
                logger.info("File watcher started successfully")
            except Exception as exc:
                logger.error(f"File watcher failed to start: {exc}", exc_info=True)
                logger.warning("Application will continue without file watching")
                file_watcher = None
        elif settings.file_watcher_enabled and not db.is_configured:
            logger.info("File watcher disabled (requires database)")
        else:
            logger.info("File watcher disabled by configuration")

        logger.info("Agent B ready")
        logger.info(f"API server listening on {settings.api_host}:{settings.api_port}")

        yield

    finally:
        # Shutdown - always runs, even on crash
        logger.info("Agent B shutting down...")

        # Stop file watcher first
        if file_watcher is not None:
            try:
                await file_watcher.stop()
                logger.info("File watcher stopped")
            except Exception as exc:
                logger.error(f"Error stopping file watcher: {exc}", exc_info=True)

        # Shutdown LLM service (B2.0) - close provider connections
        try:
            await shutdown_llm_service()
            logger.info("LLM service shutdown complete")
        except Exception as exc:
            logger.error(f"Error shutting down LLM service: {exc}", exc_info=True)

        # Shutdown LangGraph checkpointer (B2.1)
        try:
            await shutdown_checkpointer()
            logger.info("LangGraph checkpointer shutdown complete")
        except Exception as exc:
            logger.error(f"Error shutting down checkpointer: {exc}", exc_info=True)

        # Close database connections
        if db.is_configured:
            await db.dispose()
            logger.info("Database connections closed")

        logger.info("Agent B shutdown complete")


app = FastAPI(
    title="Agent B - Local Cognitive Workbench",
    version="0.0.4",
    lifespan=lifespan
)

# Add CORS middleware (B0.0.4 - Architecture A: separate frontend)
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        # Allow any localhost/127.0.0.1 port in dev to avoid CORS issues when frontend binds to 3001/3002 etc.
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {settings.cors_origins}")

# Add custom middleware (order matters: first added = outermost)

class _ForceCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        resp: Response = await call_next(request)
        origin = request.headers.get("origin")
        if origin:
            resp.headers.setdefault("Access-Control-Allow-Origin", origin)
            resp.headers.setdefault("Vary", "Origin")
            if settings.cors_allow_credentials:
                resp.headers.setdefault("Access-Control-Allow-Credentials", "true")
        return resp

app.add_middleware(_ForceCORSMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(MetricsMiddleware)


# Global exception handler to ensure CORS headers on error responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled exceptions and return a proper JSON response.
    This ensures CORS headers are included even on 500 errors.
    """
    import traceback
    error_detail = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    logger.error(f"Unhandled exception: {error_detail}")
    
    # Get the origin from the request
    origin = request.headers.get("origin", "")
    
    # Build response with CORS headers - always include full error for debugging
    response = JSONResponse(
        status_code=500,
        content={"detail": error_detail}
    )
    
    # Add CORS headers if origin is in allowed list
    if origin and settings.cors_enabled:
        if origin in settings.cors_origins or "*" in settings.cors_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response

# Register API routes
app.include_router(api_router)

# Register XiaoLei chat proxy routes (Step 2 - Chat Integration)
app.include_router(xiaolei_chat_router)

# Register metrics endpoint at root level (B7.2)
app.include_router(metrics_router)

# Register log streaming endpoint
app.include_router(log_router)
app.include_router(checker_router, prefix="/api/v1")
app.include_router(citalio_router, prefix="/api/v1")


@app.get("/debug/headers")
async def debug_headers(request: Request):
    # DO NOT include auth headers; this endpoint is for local debugging only.
    items = []
    for k, v in request.headers.items():
        if k.lower() in {"authorization", "cookie"}:
            continue
        items.append([k, v])
    return {"headers": items}


@app.get("/health")
async def health(request: Request):
    """
    Health check endpoint (Agent-B-Academic simplified version).

    Returns system health status.
    Docker check removed - not needed for academic workbench.
    """
    logger.debug("Health check requested")

    # Simplified health check - no Docker needed for Agent-B-Academic
    payload = {
        "status": "healthy",
        "docker": {"ok": True, "checks": []},  # Skipped - not needed
        "resources": {"ok": True, "checks": []},
    }

    # Add database health check if configured
    db = get_database()
    logger.debug(f"[DEBUG HEALTH] db.is_configured={db.is_configured}, db.config.database_url={repr(db.config.database_url[:20] if db.config.database_url else 'None')}")
    if db.is_configured:
        db_health = await db.health_check()
        payload["database"] = {
            "ok": db_health["ok"],
            "checks": [db_health]
        }

        # Update overall status
        if not db_health["ok"]:
            payload["status"] = "degraded"
            logger.warning("Health check: database unhealthy")
    else:
        # Database not configured is not an error
        payload["database"] = {
            "ok": True,
            "checks": [{
                "name": "database",
                "ok": True,
                "detail": "Database not configured (optional)",
                "remediation": None,
            }]
        }

    logger.debug(f"Health check result: {payload['status']}")

    # Ensure CORS headers are present even if middleware behaves unexpectedly.
    origin = request.headers.get("origin")
    # Debug field to confirm what origin the server sees (safe; no secrets)
    payload["_origin"] = origin
    resp = JSONResponse(payload)
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        if settings.cors_allow_credentials:
            resp.headers["Access-Control-Allow-Credentials"] = "true"
    return resp

