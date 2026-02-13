"""
Crash Reconciliation (B2.1).

On startup, marks stale "running" runs as "interrupted" so they can be resumed.

Problem: Server restart leaves runs stuck in "running" status.
Solution: Mark any run with status="running" and stale last_event_at as "interrupted".
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models import Event, Run

logger = get_logger("reconciliation")

# Default threshold for considering a run stale (no events for this long = interrupted)
DEFAULT_STALE_THRESHOLD_SECONDS = 60


async def reconcile_stale_runs(
    db_session: AsyncSession,
    stale_threshold_seconds: int = DEFAULT_STALE_THRESHOLD_SECONDS,
) -> int:
    """
    Mark stale running runs as interrupted.

    A run is considered stale if:
    - status = "running"
    - No events have been recorded for > stale_threshold_seconds

    This allows users to resume interrupted runs after a server crash.

    Args:
        db_session: Database session
        stale_threshold_seconds: How long without events before considering stale

    Returns:
        Number of runs marked as interrupted
    """
    threshold_time = datetime.now(timezone.utc) - timedelta(seconds=stale_threshold_seconds)

    logger.info(
        f"Reconciling stale runs (threshold: {stale_threshold_seconds}s, "
        f"cutoff: {threshold_time.isoformat()})"
    )

    try:
        # Find all running runs
        running_query = select(Run).where(Run.status == "running")
        result = await db_session.execute(running_query)
        running_runs = result.scalars().all()

        if not running_runs:
            logger.info("No running runs found, nothing to reconcile")
            return 0

        interrupted_count = 0

        for run in running_runs:
            # Get the most recent event for this run
            last_event_query = (
                select(Event.created_at)
                .where(Event.run_id == run.id)
                .order_by(Event.created_at.desc())
                .limit(1)
            )
            event_result = await db_session.execute(last_event_query)
            last_event_time = event_result.scalar_one_or_none()

            # Determine if run is stale
            is_stale = False

            if last_event_time is None:
                # No events at all - check started_at
                if run.started_at and run.started_at < threshold_time:
                    is_stale = True
                elif run.created_at < threshold_time:
                    is_stale = True
            else:
                # Have events - check last event time
                # Ensure timezone awareness
                if last_event_time.tzinfo is None:
                    last_event_time = last_event_time.replace(tzinfo=timezone.utc)
                if last_event_time < threshold_time:
                    is_stale = True

            if is_stale:
                run.status = "interrupted"
                interrupted_count += 1
                logger.info(
                    f"Marked run {run.id} as interrupted "
                    f"(session: {run.session_id}, last_event: {last_event_time})"
                )

        if interrupted_count > 0:
            await db_session.commit()
            logger.warning(
                f"Reconciliation complete: {interrupted_count} runs marked as interrupted"
            )
        else:
            logger.info("Reconciliation complete: no stale runs found")

        return interrupted_count

    except Exception as e:
        logger.error(f"Failed to reconcile stale runs: {e}", exc_info=True)
        await db_session.rollback()
        raise


async def get_stale_run_count(
    db_session: AsyncSession,
    stale_threshold_seconds: int = DEFAULT_STALE_THRESHOLD_SECONDS,
) -> int:
    """
    Count how many runs would be marked as interrupted.

    Useful for health checks and monitoring without actually modifying data.
    """
    threshold_time = datetime.now(timezone.utc) - timedelta(seconds=stale_threshold_seconds)

    try:
        # Count running runs that are stale
        query = (
            select(func.count(Run.id))
            .where(Run.status == "running")
            .where(Run.created_at < threshold_time)
        )
        result = await db_session.execute(query)
        return result.scalar_one() or 0

    except Exception as e:
        logger.error(f"Failed to count stale runs: {e}", exc_info=True)
        return 0
