"""
Run Registry (B1.4 - Kill Switch)

Central in-memory registry for tracking active runs and their resources.
Enables reliable termination of runs within the ≤2 second SLA.

IMPORTANT: This registry is in-memory only. Single uvicorn worker required.
On restart, registry is lost - containers may be orphaned (documented limitation).

Thread-safety: Uses asyncio.Lock for concurrent access protection.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.logging_config import get_logger

logger = get_logger("run_registry")


@dataclass
class RunResources:
    """Resources associated with an active run."""

    run_id: str
    session_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Mock agent task (asyncio.Task)
    task: Optional[asyncio.Task] = None

    # Docker container ID (if execution started)
    container_id: Optional[str] = None

    # LLM cancellation handle (stub for Phase 2)
    llm_handle: Optional[Any] = None

    # Cancellation flag for cooperative cancellation
    cancelled: bool = False


class RunRegistry:
    """
    Central registry for tracking active runs and their resources.

    Provides:
    - One active run per session tracking
    - Task/container/LLM handle registration
    - Cooperative cancellation via cancelled flag
    - Thread-safe operations via asyncio.Lock
    - Reverse lookup from run_id to session_id
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        # session_id -> run_id (only one active run per session)
        self._active_by_session: Dict[str, str] = {}
        # run_id -> RunResources
        self._runs: Dict[str, RunResources] = {}
        # run_id -> session_id (reverse lookup for clearing by run_id)
        self._session_by_run: Dict[str, str] = {}

    async def set_active_run(self, session_id: str, run_id: str) -> None:
        """
        Register a new active run for a session.

        If there's an existing active run for this session, it will be
        replaced (the old run should have been terminated first).
        """
        async with self._lock:
            # Check for existing active run
            existing_run_id = self._active_by_session.get(session_id)
            if existing_run_id and existing_run_id != run_id:
                logger.warning(
                    f"Replacing active run {existing_run_id} with {run_id} for session {session_id}"
                )
                # Mark old run as cancelled but don't clean up (let termination handle it)
                if existing_run_id in self._runs:
                    self._runs[existing_run_id].cancelled = True
                # Clean up reverse lookup for old run
                if existing_run_id in self._session_by_run:
                    del self._session_by_run[existing_run_id]

            # Set new active run
            self._active_by_session[session_id] = run_id
            self._runs[run_id] = RunResources(run_id=run_id, session_id=session_id)
            self._session_by_run[run_id] = session_id

            logger.debug(f"Registered active run {run_id} for session {session_id}")

    async def get_active_run(self, session_id: str) -> Optional[str]:
        """Get the active run_id for a session, if any."""
        async with self._lock:
            return self._active_by_session.get(session_id)

    async def get_run_resources(self, run_id: str) -> Optional[RunResources]:
        """Get resources for a specific run."""
        async with self._lock:
            return self._runs.get(run_id)

    async def register_task(self, run_id: str, task: asyncio.Task) -> bool:
        """
        Register an asyncio task for a run.

        Returns True if successful, False if run not found.
        """
        async with self._lock:
            if run_id not in self._runs:
                logger.warning(f"Cannot register task: run {run_id} not found")
                return False

            self._runs[run_id].task = task
            logger.debug(f"Registered task for run {run_id}")
            return True

    async def register_container(self, run_id: str, container_id: str) -> bool:
        """
        Register a Docker container ID for a run.

        Returns True if successful, False if run not found.
        """
        async with self._lock:
            if run_id not in self._runs:
                logger.warning(f"Cannot register container: run {run_id} not found")
                return False

            self._runs[run_id].container_id = container_id
            logger.debug(f"Registered container {container_id} for run {run_id}")
            return True

    async def register_llm_handle(self, run_id: str, handle: Any) -> bool:
        """
        Register an LLM cancellation handle for a run.

        Stub for Phase 2 - real LLM integration.

        Returns True if successful, False if run not found.
        """
        async with self._lock:
            if run_id not in self._runs:
                logger.warning(f"Cannot register LLM handle: run {run_id} not found")
                return False

            self._runs[run_id].llm_handle = handle
            logger.debug(f"Registered LLM handle for run {run_id}")
            return True

    async def is_cancelled(self, run_id: str) -> bool:
        """
        Check if a run has been marked for cancellation.

        Used for cooperative cancellation - tasks should check this periodically.
        """
        async with self._lock:
            run = self._runs.get(run_id)
            return run.cancelled if run else True  # Unknown runs are considered cancelled

    async def mark_cancelled(self, run_id: str) -> bool:
        """
        Mark a run as cancelled (cooperative cancellation).

        Returns True if successful, False if run not found.
        """
        async with self._lock:
            if run_id not in self._runs:
                return False

            self._runs[run_id].cancelled = True
            logger.debug(f"Marked run {run_id} as cancelled")
            return True

    async def clear_run(self, run_id: str) -> Optional[RunResources]:
        """
        Remove a run from the registry (idempotent).

        Returns the RunResources if found, None otherwise.
        Also removes the session->run mapping if this was the active run.
        """
        async with self._lock:
            run = self._runs.pop(run_id, None)
            session_id = self._session_by_run.pop(run_id, None)

            if run:
                # Remove from active session mapping if this was the active run
                if self._active_by_session.get(run.session_id) == run_id:
                    del self._active_by_session[run.session_id]

                logger.debug(f"Cleared run {run_id} from registry")
            elif session_id:
                # Even if run not found, clear session mapping if we have reverse lookup
                if self._active_by_session.get(session_id) == run_id:
                    del self._active_by_session[session_id]
                logger.debug(f"Cleared run {run_id} from session mapping (run already gone)")

            return run

    async def has_active_run(self, session_id: str) -> bool:
        """Check if a session has an active (non-cancelled) run."""
        async with self._lock:
            run_id = self._active_by_session.get(session_id)
            if not run_id:
                return False
            run = self._runs.get(run_id)
            return run is not None and not run.cancelled

    async def get_stats(self) -> Dict[str, int]:
        """Get registry statistics for monitoring."""
        async with self._lock:
            return {
                "active_sessions": len(self._active_by_session),
                "total_runs": len(self._runs),
                "runs_with_tasks": sum(1 for r in self._runs.values() if r.task),
                "runs_with_containers": sum(1 for r in self._runs.values() if r.container_id),
                "cancelled_runs": sum(1 for r in self._runs.values() if r.cancelled),
            }


# Global singleton instance
_registry: Optional[RunRegistry] = None


def get_run_registry() -> RunRegistry:
    """Get the global run registry instance."""
    global _registry
    if _registry is None:
        _registry = RunRegistry()
    return _registry


# Convenience functions for direct access
async def set_active_run(session_id: str, run_id: str) -> None:
    """Register a new active run for a session."""
    await get_run_registry().set_active_run(session_id, run_id)


async def get_active_run(session_id: str) -> Optional[str]:
    """Get the active run_id for a session."""
    return await get_run_registry().get_active_run(session_id)


async def get_run_resources(run_id: str) -> Optional[RunResources]:
    """Get resources for a specific run."""
    return await get_run_registry().get_run_resources(run_id)


async def register_task(run_id: str, task: asyncio.Task) -> bool:
    """Register an asyncio task for a run."""
    return await get_run_registry().register_task(run_id, task)


async def register_container(run_id: str, container_id: str) -> bool:
    """Register a Docker container ID for a run."""
    return await get_run_registry().register_container(run_id, container_id)


async def is_cancelled(run_id: str) -> bool:
    """Check if a run has been marked for cancellation."""
    return await get_run_registry().is_cancelled(run_id)


async def mark_cancelled(run_id: str) -> bool:
    """Mark a run as cancelled."""
    return await get_run_registry().mark_cancelled(run_id)


async def clear_run(run_id: str) -> Optional[RunResources]:
    """Remove a run from the registry."""
    return await get_run_registry().clear_run(run_id)


async def has_active_run(session_id: str) -> bool:
    """Check if a session has an active (non-cancelled) run."""
    return await get_run_registry().has_active_run(session_id)
