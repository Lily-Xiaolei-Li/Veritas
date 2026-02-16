"""
Gnosiplexio Scheduler — Background task scheduling for automated graph maintenance.

Runs enrichment cycles and drift detection on configurable intervals
using asyncio background tasks.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.gnosiplexio.engine import GnosiplexioEngine

logger = logging.getLogger("gnosiplexio.scheduler")

# Default intervals in seconds
DEFAULT_ENRICHMENT_INTERVAL = 86400   # 24 hours
DEFAULT_DRIFT_INTERVAL = 604800       # 7 days


class GnosiplexioScheduler:
    """
    Background scheduler for Gnosiplexio automated tasks.

    Manages periodic enrichment cycles and drift detection using asyncio.
    """

    def __init__(
        self,
        engine: GnosiplexioEngine,
        enrichment_interval: int = DEFAULT_ENRICHMENT_INTERVAL,
        drift_interval: int = DEFAULT_DRIFT_INTERVAL,
    ):
        """
        Initialize the scheduler.

        Args:
            engine: The GnosiplexioEngine instance to operate on.
            enrichment_interval: Seconds between enrichment cycles.
            drift_interval: Seconds between drift detection runs.
        """
        self._engine = engine
        self._enrichment_interval = enrichment_interval
        self._drift_interval = drift_interval
        self._running = False
        self._enrichment_task: Optional[asyncio.Task] = None
        self._drift_task: Optional[asyncio.Task] = None
        self._last_enrichment: Optional[str] = None
        self._last_drift: Optional[str] = None
        self._enrichment_runs = 0
        self._drift_runs = 0

    @property
    def is_running(self) -> bool:
        """Whether the scheduler is currently active."""
        return self._running

    async def start(self) -> None:
        """Start background scheduling tasks."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._enrichment_task = asyncio.create_task(
            self._enrichment_loop(), name="gnosiplexio-enrichment"
        )
        self._drift_task = asyncio.create_task(
            self._drift_loop(), name="gnosiplexio-drift"
        )
        logger.info(
            "Scheduler started (enrichment=%ds, drift=%ds)",
            self._enrichment_interval, self._drift_interval
        )

    async def stop(self) -> None:
        """Stop all background tasks."""
        self._running = False
        for task in (self._enrichment_task, self._drift_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._enrichment_task = None
        self._drift_task = None
        logger.info("Scheduler stopped")

    async def _enrichment_loop(self) -> None:
        """Periodic enrichment cycle loop."""
        while self._running:
            try:
                await asyncio.sleep(self._enrichment_interval)
                if not self._running:
                    break
                await self._run_enrichment()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Enrichment cycle error: %s", e, exc_info=True)

    async def _drift_loop(self) -> None:
        """Periodic drift detection loop."""
        while self._running:
            try:
                await asyncio.sleep(self._drift_interval)
                if not self._running:
                    break
                await self._run_drift_detection()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Drift detection error: %s", e, exc_info=True)

    async def _run_enrichment(self) -> Dict[str, Any]:
        """Execute one enrichment cycle."""
        from app.services.gnosiplexio.self_growth import SelfGrowthEngine

        logger.info("Running scheduled enrichment cycle")
        growth_engine = SelfGrowthEngine(self._engine.graph)
        result = growth_engine.run_enrichment_cycle()
        self._last_enrichment = datetime.now(timezone.utc).isoformat()
        self._enrichment_runs += 1
        logger.info("Enrichment cycle #%d complete: %s stale nodes", self._enrichment_runs, result.get("stale_nodes_count", 0))
        return result

    async def _run_drift_detection(self) -> Dict[str, Any]:
        """Execute one drift detection run."""
        from app.services.gnosiplexio.concept_drift import ConceptDriftDetector

        logger.info("Running scheduled drift detection")
        detector = ConceptDriftDetector(self._engine.graph)
        result = detector.get_trend_report()
        self._last_drift = datetime.now(timezone.utc).isoformat()
        self._drift_runs += 1
        logger.info("Drift detection #%d complete: %d emerging, %d declining", self._drift_runs, result.get("emerging_count", 0), result.get("declining_count", 0))
        return result

    def get_status(self) -> Dict[str, Any]:
        """
        Get the scheduler's current status.

        Returns:
            Dict with running state, intervals, and last run times.
        """
        return {
            "running": self._running,
            "enrichment_interval_seconds": self._enrichment_interval,
            "drift_interval_seconds": self._drift_interval,
            "last_enrichment_run": self._last_enrichment,
            "last_drift_run": self._last_drift,
            "enrichment_runs_total": self._enrichment_runs,
            "drift_runs_total": self._drift_runs,
        }
