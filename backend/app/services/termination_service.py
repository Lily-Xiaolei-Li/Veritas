"""
Termination Service (B1.4 - Kill Switch)

Handles reliable termination of active runs within ≤2 second SLA.

Responsibilities:
- Cancel mock agent tasks (cooperative cancellation)
- Terminate active local executions (best-effort terminate/kill)
- Cancel LLM calls (stub for Phase 2)
- Emit SSE event via in-memory queue
- Write audit log entry
- Clean up run registry
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.logging_config import get_logger
from app.schemas.sse_events import (
    RunTerminatedEvent,
    TerminationReason,
    CancelStatus,
)
from app.services.run_registry import (
    get_active_run,
    get_run_resources,
    mark_cancelled,
    clear_run,
    RunResources,
)

logger = get_logger("termination_service")

# Thread pool for blocking termination operations
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="termination")


@dataclass
class TerminationResult:
    """Result of a termination operation."""

    status: str  # "terminated" | "no_active_run" | "failed"
    run_id: Optional[str] = None
    session_id: Optional[str] = None
    reason: str = "user_cancel"
    cancel_status: str = "none"
    latency_ms: float = 0.0
    message: Optional[str] = None


async def terminate_session(
    session_id: str,
    reason: TerminationReason = TerminationReason.USER_CANCEL,
    db_session=None,
) -> TerminationResult:
    """
    Terminate the active run for a session.

    Algorithm (bounded time ~2s max):
    1. Get active run from registry
    2. Mark run as cancelled (cooperative cancellation flag)
    3. Cancel asyncio task if present
    4. Stop/kill local execution if present
    5. Cancel LLM handle (stub)
    6. Write SSE event to in-memory queue
    7. Write audit log entry (if db_session provided)
    8. Clear run from registry

    Args:
        session_id: Session to terminate active run for
        reason: Why the run is being terminated
        db_session: Optional database session for audit logging

    Returns:
        TerminationResult with status and details
    """
    start_time = time.monotonic()

    # 1. Get active run
    run_id = await get_active_run(session_id)
    if not run_id:
        logger.debug(f"No active run for session {session_id}")
        return TerminationResult(
            status="no_active_run",
            session_id=session_id,
            message="No active run to terminate",
        )

    logger.info(f"Terminating run {run_id} for session {session_id}")

    # Get run resources
    resources = await get_run_resources(run_id)
    if not resources:
        # Run was already cleared
        return TerminationResult(
            status="no_active_run",
            run_id=run_id,
            session_id=session_id,
            message="Run already terminated",
        )

    cancel_status = CancelStatus.NONE

    try:
        # 2. Mark run as cancelled (cooperative cancellation)
        await mark_cancelled(run_id)

        # 3. Cancel asyncio task if present
        if resources.task and not resources.task.done():
            resources.task.cancel()
            try:
                # Brief wait for task to respond to cancellation
                await asyncio.wait_for(
                    asyncio.shield(resources.task),
                    timeout=0.5,
                )
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            cancel_status = CancelStatus.TASK_CANCELLED
            logger.debug(f"Cancelled task for run {run_id}")

        # 4. Stop/kill local execution if present
        if resources.container_id:
            container_status = await _terminate_container(resources.container_id)
            if container_status:
                cancel_status = container_status
                logger.debug(f"Terminated execution {resources.container_id} for run {run_id}")

        # 5. Cancel LLM handle (stub for Phase 2)
        if resources.llm_handle:
            await _cancel_llm(run_id, resources.llm_handle)

        # Calculate latency
        latency_ms = (time.monotonic() - start_time) * 1000

        # 6. Write SSE event to in-memory queue
        await _emit_termination_event(
            session_id=session_id,
            run_id=run_id,
            reason=reason,
            cancel_status=cancel_status,
            latency_ms=latency_ms,
        )

        # 7. Write audit log entry
        if db_session:
            await _write_audit_log(
                db_session=db_session,
                session_id=session_id,
                run_id=run_id,
                reason=reason,
                cancel_status=cancel_status,
                resources=resources,
                latency_ms=latency_ms,
            )

        # 8. Clear run from registry
        await clear_run(run_id)

        logger.info(
            f"Run {run_id} terminated successfully in {latency_ms:.1f}ms",
            extra={
                "run_id": run_id,
                "session_id": session_id,
                "cancel_status": cancel_status.value,
                "latency_ms": latency_ms,
            },
        )

        return TerminationResult(
            status="terminated",
            run_id=run_id,
            session_id=session_id,
            reason=reason.value,
            cancel_status=cancel_status.value,
            latency_ms=latency_ms,
            message="Run terminated successfully",
        )

    except Exception as e:
        latency_ms = (time.monotonic() - start_time) * 1000
        logger.error(
            f"Failed to terminate run {run_id}: {e}",
            exc_info=True,
            extra={"run_id": run_id, "session_id": session_id},
        )

        # Still try to clear registry and emit event
        try:
            await clear_run(run_id)
            await _emit_termination_event(
                session_id=session_id,
                run_id=run_id,
                reason=TerminationReason.ERROR,
                cancel_status=CancelStatus.NONE,
                latency_ms=latency_ms,
                message=f"Termination error: {str(e)}",
            )
        except Exception:
            pass

        return TerminationResult(
            status="failed",
            run_id=run_id,
            session_id=session_id,
            reason=reason.value,
            cancel_status=cancel_status.value,
            latency_ms=latency_ms,
            message=f"Termination failed: {str(e)}",
        )


async def _terminate_container(container_id: str) -> Optional[CancelStatus]:
    """Terminate a local execution (best-effort).

    Note: `container_id` is legacy naming; it stores a local `execution_id`.
    """

    loop = asyncio.get_event_loop()

    def _stop() -> CancelStatus:
        try:
            from app.executor import cancel_execution

            ok = cancel_execution(container_id)
            return CancelStatus.CONTAINER_KILLED if ok else CancelStatus.ALREADY_STOPPED
        except Exception as e:
            logger.warning(f"Execution termination error: {e}")
            return CancelStatus.NONE

    try:
        return await asyncio.wait_for(loop.run_in_executor(_executor, _stop), timeout=2.0)
    except asyncio.TimeoutError:
        logger.warning(f"Execution termination timed out: {container_id}")
        return CancelStatus.NONE


async def _cancel_llm(run_id: str, handle) -> None:
    """
    Cancel LLM API call (stub for Phase 2).

    In Phase 2, this will:
    - Cancel streaming response if applicable
    - Abort pending API calls
    - Clean up any partial responses
    """
    logger.debug(f"LLM cancellation stub called for run {run_id}")
    # Phase 2: Implement actual LLM cancellation
    pass


async def _emit_termination_event(
    session_id: str,
    run_id: str,
    reason: TerminationReason,
    cancel_status: CancelStatus,
    latency_ms: float,
    message: Optional[str] = None,
) -> None:
    """
    Emit run_terminated event to SSE queue.

    Uses in-memory queue (consistent with current SSE architecture).
    """
    from app.routes.message_routes import get_session_event_queues

    event = RunTerminatedEvent(
        run_id=run_id,
        session_id=session_id,
        terminated_at=datetime.now(timezone.utc),
        reason=reason,
        cancel_status=cancel_status,
        latency_ms=latency_ms,
        message=message or f"Run terminated: {reason.value}",
    )

    queues = get_session_event_queues()
    queue = queues.get(session_id)

    if queue:
        await queue.put((
            "run_terminated",
            event.model_dump(mode="json"),
            f"{run_id}-terminated",
        ))
        logger.debug(f"Emitted run_terminated event for run {run_id}")
    else:
        logger.debug(f"No SSE queue for session {session_id}, event not emitted")


async def _write_audit_log(
    db_session,
    session_id: str,
    run_id: str,
    reason: TerminationReason,
    cancel_status: CancelStatus,
    resources: RunResources,
    latency_ms: float,
) -> None:
    """
    Write termination event to audit log.
    """
    from app.models import AuditLog

    audit_entry = AuditLog(
        id=str(uuid4()),
        actor="user",
        action="run_terminated",
        resource=f"run:{run_id}",
        session_id=session_id,
        message=f"Run terminated via kill switch: {reason.value}",
        details={
            "run_id": run_id,
            "session_id": session_id,
            "reason": reason.value,
            "cancel_status": cancel_status.value,
            "latency_ms": latency_ms,
            "had_task": resources.task is not None,
            "had_container": resources.container_id is not None,
            "execution_id": resources.container_id if resources.container_id else None,
            "started_at": resources.started_at.isoformat() if resources.started_at else None,
        },
        success=True,
    )

    db_session.add(audit_entry)
    await db_session.commit()
    logger.debug(f"Wrote audit log entry for run termination: {run_id}")
