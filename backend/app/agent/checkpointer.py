"""
LangGraph PostgreSQL Checkpointer (B2.1).

Provides async checkpoint persistence using langgraph-checkpoint-postgres.
Uses psycopg_pool.AsyncConnectionPool for efficient connection management.

Usage:
    # In FastAPI lifespan
    await initialize_checkpointer(database_url)

    # In agent service
    checkpointer = get_checkpointer()

    # On shutdown
    await shutdown_checkpointer()
"""

from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection, InterfaceError

from app.logging_config import get_logger

logger = get_logger("checkpointer")

# Module-level singletons
_checkpointer: Optional[AsyncPostgresSaver] = None
_conn: Optional[AsyncConnection] = None


async def initialize_checkpointer(database_url: str) -> None:
    """Initialize the LangGraph checkpointer with a long-lived psycopg3 AsyncConnection.

    Notes:
        langgraph-checkpoint-postgres exposes `AsyncPostgresSaver.from_conn_string` as an
        **async context manager** (it yields a saver and then closes the connection on exit).
        For an app-lifetime singleton, we must manage the connection ourselves.

    Args:
        database_url: PostgreSQL connection string (asyncpg format).
                      Will be converted to psycopg format internally.
    """
    global _checkpointer, _conn

    if _checkpointer is not None:
        logger.warning("Checkpointer already initialized, skipping")
        return

    # Convert asyncpg URL to psycopg format for langgraph-checkpoint-postgres
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    logger.info("Initializing LangGraph checkpointer...")

    try:
        # Create a dedicated connection for checkpointing
        _conn = await AsyncConnection.connect(
            sync_url,
            autocommit=True,
            prepare_threshold=0,
        )

        _checkpointer = AsyncPostgresSaver(conn=_conn)

        # Setup creates the checkpoint tables if they don't exist
        await _checkpointer.setup()

        logger.info("LangGraph checkpointer initialized successfully")

    except InterfaceError as e:
        # Windows/uvicorn often runs with ProactorEventLoop; psycopg3 async doesn't support it.
        # In that case, gracefully disable checkpoint persistence instead of crashing startup.
        msg = str(e)
        if "ProactorEventLoop" in msg:
            logger.warning(
                "Psycopg async is incompatible with ProactorEventLoop on Windows; "
                "disabling checkpoint persistence (continuing without checkpointer)."
            )
            _checkpointer = None
            if _conn is not None:
                try:
                    await _conn.close()
                except Exception:
                    pass
            _conn = None
            return
        logger.error(f"Failed to initialize checkpointer: {e}", exc_info=True)
        _checkpointer = None
        if _conn is not None:
            try:
                await _conn.close()
            except Exception:
                pass
        _conn = None
        raise

    except Exception as e:
        logger.error(f"Failed to initialize checkpointer: {e}", exc_info=True)
        _checkpointer = None
        if _conn is not None:
            try:
                await _conn.close()
            except Exception:
                pass
        _conn = None
        raise


async def shutdown_checkpointer() -> None:
    """Shutdown the checkpointer and close the underlying connection."""
    global _checkpointer, _conn

    if _checkpointer is None and _conn is None:
        logger.debug("Checkpointer not initialized, nothing to shutdown")
        return

    logger.info("Shutting down LangGraph checkpointer...")

    try:
        _checkpointer = None
        if _conn is not None:
            await _conn.close()
        _conn = None
        logger.info("LangGraph checkpointer shutdown complete")

    except Exception as e:
        logger.error(f"Error during checkpointer shutdown: {e}", exc_info=True)
        _checkpointer = None
        _conn = None


def get_checkpointer() -> Optional[AsyncPostgresSaver]:
    """
    Get the global checkpointer instance.

    Returns:
        The AsyncPostgresSaver instance, or None if not initialized.
    """
    return _checkpointer


def is_checkpointer_ready() -> bool:
    """Check if the checkpointer is initialized and ready."""
    return _checkpointer is not None


async def has_checkpoint(run_id: str) -> bool:
    """
    Check if a checkpoint exists for the given run_id.

    Uses LangGraph's checkpoint tables to determine if state can be resumed.

    Args:
        run_id: The run ID (used as thread_id in LangGraph)

    Returns:
        True if at least one checkpoint exists for this run
    """
    if _checkpointer is None:
        return False

    try:
        # LangGraph stores checkpoints by thread_id
        # We use run_id as thread_id for consistent mapping
        config = {"configurable": {"thread_id": run_id}}

        # Try to get the latest checkpoint tuple
        checkpoint_tuple = await _checkpointer.aget_tuple(config)

        return checkpoint_tuple is not None

    except Exception as e:
        logger.warning(f"Error checking checkpoint for run {run_id}: {e}")
        return False
