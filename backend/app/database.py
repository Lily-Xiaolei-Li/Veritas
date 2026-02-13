"""
Database configuration and session management for Agent B.

Handles PostgreSQL connections using SQLAlchemy async engine.
"""

import os
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

# Load .env file from backend directory
_backend_dir = Path(__file__).resolve().parent.parent
_env_file = _backend_dir / ".env"

# IMPORTANT: do not override an explicitly provided DATABASE_URL (even if empty)
if "DATABASE_URL" not in os.environ:
    load_dotenv(_env_file)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class DatabaseConfig:
    """Database configuration from environment variables."""

    # Default DATABASE_URL for local development
    _DEFAULT_DB_URL = "postgresql+asyncpg://agentb:AgentB#Lily2026!@localhost:5433/agent_b"

    def __init__(self):
        # Try loading from .env file.
        # Do NOT override existing process env vars; explicit env should win over .env.
        # If DATABASE_URL is explicitly set (even empty), do not read it from .env.
        if "DATABASE_URL" not in os.environ:
            load_dotenv(_env_file, override=False)

        # IMPORTANT: Distinguish between "unset" and "set to empty".
        # - If DATABASE_URL is unset, we fall back to a local dev default.
        # - If DATABASE_URL is explicitly set to an empty string (e.g., CI), treat as NOT configured.
        env_db_url = os.environ.get("DATABASE_URL")
        if env_db_url is None:
            self.database_url = self._DEFAULT_DB_URL
        else:
            self.database_url = env_db_url
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
        self.pool_pre_ping = True  # Enable connection health checks
        self.echo = os.getenv("DB_ECHO", "false").lower() == "true"

    @property
    def is_configured(self) -> bool:
        """Check if database is configured."""
        return bool(self.database_url)

    def get_engine_kwargs(self) -> dict:
        """Get SQLAlchemy engine configuration."""
        return {
            "echo": self.echo,
            "pool_pre_ping": self.pool_pre_ping,
            "poolclass": AsyncAdaptedQueuePool,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
        }


class Database:
    """Database connection manager."""

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    @property
    def is_configured(self) -> bool:
        """Check if database is configured."""
        return self.config.is_configured

    async def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if not self.config.is_configured:
            raise ValueError(
                "Database not configured. Set DATABASE_URL environment variable."
            )

        self._engine = create_async_engine(
            self.config.database_url, **self.config.get_engine_kwargs()
        )

        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def dispose(self) -> None:
        """Close all database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional scope for database operations."""
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def get_pool_stats(self) -> dict:
        """
        Get pool stats (best-effort, may return -1 for unavailable).

        SQLAlchemy async pool introspection is limited. This method
        attempts to read available stats but returns -1 for metrics
        that cannot be determined.

        Returns:
            dict with keys: size (int), in_use (int)
        """
        if not self._engine:
            return {"size": -1, "in_use": -1}

        try:
            pool = self._engine.pool
            return {
                "size": pool.size() if hasattr(pool, 'size') else -1,
                "in_use": pool.checkedout() if hasattr(pool, 'checkedout') else -1,
            }
        except Exception:
            return {"size": -1, "in_use": -1}

    async def health_check(self) -> dict:
        """
        Check database connectivity.

        Returns:
            dict with keys: ok (bool), detail (str), error (Optional[str])
        """
        if not self.is_configured:
            return {
                "ok": False,
                "detail": "Database not configured",
                "remediation": "Set DATABASE_URL environment variable to enable database functionality",
            }

        if not self._engine:
            return {
                "ok": False,
                "detail": "Database not initialized",
                "remediation": "Database engine not initialized. This is an internal error.",
            }

        try:
            async with self._engine.connect() as conn:
                # Simple query to test connectivity
                await conn.execute(text("SELECT 1"))
            return {
                "ok": True,
                "detail": "Database connection healthy",
                "remediation": None,
            }
        except Exception as exc:
            return {
                "ok": False,
                "detail": f"Database connection failed: {type(exc).__name__}: {str(exc)}",
                "remediation": """Database connection failed.

Steps to resolve:
1. Verify PostgreSQL is running
2. Check DATABASE_URL format: postgresql+asyncpg://user:password@host:port/database
3. Verify database credentials
4. Ensure database exists (create with: CREATE DATABASE agentb)
5. Check network connectivity to database host
6. Review PostgreSQL logs for connection errors""",
            }


# Global database instance
_db: Optional[Database] = None


def get_database() -> Database:
    """Get the global database instance.

    IMPORTANT: do not let .env override an explicitly provided DATABASE_URL
    (including an explicit empty string used to disable DB in CI/tests).
    """
    global _db
    if _db is None:
        if "DATABASE_URL" not in os.environ:
            load_dotenv(_env_file, override=False)
        _db = Database()
    return _db


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to provide database sessions.

    Usage:
        @app.get("/endpoint")
        async def endpoint(session: AsyncSession = Depends(get_session)):
            # use session
    """
    db = get_database()
    
    print(f"[DEBUG get_session] db.is_configured={db.is_configured}, db._engine={db._engine}, db.config.database_url={repr(db.config.database_url[:30] if db.config.database_url else None)}")
    
    # Ensure database is initialized
    if not db._engine:
        if not db.is_configured:
            raise RuntimeError(f"Database not configured. Set DATABASE_URL environment variable. (db.config.database_url={repr(db.config.database_url)})")
        await db.initialize()
    
    async with db.session() as session:
        yield session
