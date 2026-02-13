"""
Database migration utilities for Agent B.

Handles automatic migration on startup and migration status queries.
"""

import os
from pathlib import Path
from typing import Optional

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from alembic import command


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    # Get the backend directory (where alembic.ini is located)
    backend_dir = Path(__file__).parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"

    if not alembic_ini_path.exists():
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini_path}")

    config = Config(str(alembic_ini_path))

    # IMPORTANT: prevent Alembic from reconfiguring global logging.
    # Alembic's default fileConfig() can clobber pytest log capture and app loggers.
    config.attributes["configure_logger"] = False

    # Set absolute path for script location (alembic directory)
    alembic_dir = backend_dir / "alembic"
    config.set_main_option("script_location", str(alembic_dir))

    # Set database URL from environment if available
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Convert async URL to sync for Alembic (using psycopg v3)
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
        config.set_main_option("sqlalchemy.url", sync_url)

    return config


def get_current_revision(database_url: str) -> Optional[str]:
    """
    Get the current database schema revision.

    Args:
        database_url: Database connection string (can be async or sync)

    Returns:
        Current revision ID or None if not initialized
    """
    # Convert async URL to sync for this operation (using psycopg v3)
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

    try:
        engine = create_engine(sync_url)
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
        engine.dispose()
        return current_rev
    except Exception as exc:
        # Database might not exist or alembic_version table might not exist
        print(f"Warning: Could not determine current revision: {exc}")
        return None


def get_head_revision() -> str:
    """
    Get the latest (head) revision from migration scripts.

    Returns:
        Head revision ID
    """
    config = get_alembic_config()
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    return head


def run_migrations() -> dict:
    """
    Run pending database migrations.

    Returns:
        dict with keys:
            - ok (bool): Whether migrations succeeded
            - current_revision (str): Revision after migration
            - detail (str): Success/error message
            - error (Optional[str]): Error details if failed
    """
    try:
        config = get_alembic_config()

        # Get database URL
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return {
                "ok": False,
                "current_revision": None,
                "detail": "DATABASE_URL not configured",
                "error": "Cannot run migrations without DATABASE_URL",
            }

        # Get current and head revisions
        current = get_current_revision(database_url)
        head = get_head_revision()

        # Run migrations
        command.upgrade(config, "head")

        # Verify migration succeeded
        new_current = get_current_revision(database_url)

        if new_current == head:
            if current == head:
                detail = f"Database schema up to date (revision: {head})"
            else:
                detail = f"Migrations applied successfully (revision: {current} → {head})"

            return {
                "ok": True,
                "current_revision": new_current,
                "detail": detail,
                "error": None,
            }
        else:
            return {
                "ok": False,
                "current_revision": new_current,
                "detail": f"Migration incomplete (current: {new_current}, expected: {head})",
                "error": "Migration did not reach head revision",
            }

    except Exception as exc:
        return {
            "ok": False,
            "current_revision": None,
            "detail": f"Migration failed: {type(exc).__name__}: {str(exc)}",
            "error": str(exc),
        }


def check_migration_status() -> dict:
    """
    Check if migrations are pending.

    Returns:
        dict with keys:
            - ok (bool): True if no pending migrations
            - current_revision (Optional[str]): Current database revision
            - head_revision (str): Latest available revision
            - pending (bool): Whether migrations are pending
            - detail (str): Status description
    """
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return {
                "ok": False,
                "current_revision": None,
                "head_revision": None,
                "pending": False,
                "detail": "DATABASE_URL not configured",
            }

        current = get_current_revision(database_url)
        head = get_head_revision()

        if current is None:
            return {
                "ok": False,
                "current_revision": None,
                "head_revision": head,
                "pending": True,
                "detail": "Database not initialized (no alembic_version table)",
            }

        if current == head:
            return {
                "ok": True,
                "current_revision": current,
                "head_revision": head,
                "pending": False,
                "detail": f"Database schema up to date (revision: {head})",
            }
        else:
            return {
                "ok": False,
                "current_revision": current,
                "head_revision": head,
                "pending": True,
                "detail": f"Pending migrations (current: {current}, head: {head})",
            }

    except Exception as exc:
        return {
            "ok": False,
            "current_revision": None,
            "head_revision": None,
            "pending": False,
            "detail": f"Migration status check failed: {type(exc).__name__}: {str(exc)}",
        }
