"""
Gnosiplexio Growth API Routes — Self-growth and intelligence endpoints.

All routes prefix: /api/v1/gnosiplexio/growth
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.logging_config import get_logger

logger = get_logger("gnosiplexio.growth_routes")

router = APIRouter(prefix="/gnosiplexio/growth", tags=["gnosiplexio-growth"])


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class GapReport(BaseModel):
    isolated_nodes: List[str] = []
    isolated_count: int = 0
    small_components: List[List[str]] = []
    small_component_count: int = 0
    works_without_outgoing_citations: List[str] = []
    works_without_incoming_citations: List[str] = []
    orphaned_concepts: List[str] = []
    gap_score: float = 0.0
    total_components: int = 0


class PaperSuggestion(BaseModel):
    concept_area: str
    concept_id: str
    reason: str
    connected_works: int = 0
    priority: str = "medium"


class SuggestionsResponse(BaseModel):
    suggestions: List[PaperSuggestion]
    total: int


class GrowthReport(BaseModel):
    current_nodes: int
    current_edges: int
    node_type_distribution: Dict[str, int] = {}
    growth_rate_nodes: float = 0.0
    growth_rate_edges: float = 0.0
    history: List[Dict[str, Any]] = []
    snapshots_recorded: int = 0


class MergeResult(BaseModel):
    duplicates_found: int = 0
    merges_performed: int = 0
    merges: List[Dict[str, Any]] = []
    dry_run: bool = False


class ConceptDriftResponse(BaseModel):
    concept_id: str
    concept_name: str = ""
    total_connections: int = 0
    connections_over_time: Dict[str, int] = {}
    edge_type_evolution: Dict[str, Dict[str, int]] = {}
    undated_connections: int = 0
    growth_trend: str = "insufficient_data"
    error: Optional[str] = None


class EmergingConcept(BaseModel):
    concept_id: str
    name: str
    recent_edges: int
    total_edges: int
    growth_ratio: float


class EmergingResponse(BaseModel):
    emerging: List[EmergingConcept]
    total: int


class TrendReport(BaseModel):
    timestamp: str
    total_concepts: int = 0
    emerging_concepts: List[Dict[str, Any]] = []
    emerging_count: int = 0
    declining_concepts: List[Dict[str, Any]] = []
    declining_count: int = 0
    outdated_concepts: List[str] = []
    outdated_count: int = 0
    paradigm_shifts: List[Dict[str, Any]] = []
    paradigm_shift_count: int = 0
    health_score: float = 0.5


class EnrichmentCycleResult(BaseModel):
    timestamp: str
    total_nodes: int = 0
    stale_nodes_count: int = 0
    stale_node_ids: List[str] = []
    stale_threshold_days: int = 7


class SchedulerStatus(BaseModel):
    running: bool = False
    enrichment_interval_seconds: int = 0
    drift_interval_seconds: int = 0
    last_enrichment_run: Optional[str] = None
    last_drift_run: Optional[str] = None
    enrichment_runs_total: int = 0
    drift_runs_total: int = 0


# ---------------------------------------------------------------------------
# Engine + helpers singleton
# ---------------------------------------------------------------------------

_growth_engine = None
_drift_detector = None
_scheduler = None


def _get_graph_store():
    """Get the GraphStore from the existing engine singleton."""
    from app.routes.gnosiplexio_routes import _get_engine
    return _get_engine().graph


def _get_growth_engine():
    """Get or create the SelfGrowthEngine singleton."""
    global _growth_engine
    if _growth_engine is None:
        from app.services.gnosiplexio.self_growth import SelfGrowthEngine
        _growth_engine = SelfGrowthEngine(_get_graph_store())
    return _growth_engine


def _get_drift_detector():
    """Get or create the ConceptDriftDetector singleton."""
    global _drift_detector
    if _drift_detector is None:
        from app.services.gnosiplexio.concept_drift import ConceptDriftDetector
        _drift_detector = ConceptDriftDetector(_get_graph_store())
    return _drift_detector


def _get_scheduler():
    """Get or create the GnosiplexioScheduler singleton."""
    global _scheduler
    if _scheduler is None:
        from app.services.gnosiplexio.scheduler import GnosiplexioScheduler
        from app.routes.gnosiplexio_routes import _get_engine
        _scheduler = GnosiplexioScheduler(_get_engine())
    return _scheduler


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/gaps", response_model=GapReport)
def get_knowledge_gaps():
    """Detect knowledge gaps in the graph."""
    try:
        engine = _get_growth_engine()
        result = engine.detect_knowledge_gaps()
        return GapReport(**result)
    except Exception as e:
        logger.error("Gap detection failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/suggestions", response_model=SuggestionsResponse)
def get_paper_suggestions(max_results: int = Query(10, ge=1, le=50)):
    """Get suggestions for papers to add based on graph structure."""
    try:
        engine = _get_growth_engine()
        suggestions = engine.suggest_papers_to_add(max_suggestions=max_results)
        return SuggestionsResponse(suggestions=suggestions, total=len(suggestions))
    except Exception as e:
        logger.error("Suggestion generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/growth-report", response_model=GrowthReport)
def get_growth_report():
    """Get growth metrics and history for the knowledge graph."""
    try:
        engine = _get_growth_engine()
        result = engine.get_growth_report()
        return GrowthReport(**result)
    except Exception as e:
        logger.error("Growth report failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/merge-duplicates", response_model=MergeResult)
def merge_duplicates(dry_run: bool = Query(False)):
    """Detect and merge duplicate nodes with similar titles."""
    try:
        engine = _get_growth_engine()
        result = engine.merge_duplicate_nodes(dry_run=dry_run)
        return MergeResult(**result)
    except Exception as e:
        logger.error("Merge duplicates failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/drift/{concept_id}", response_model=ConceptDriftResponse)
def get_concept_drift(concept_id: str):
    """Analyze concept drift for a specific concept."""
    try:
        detector = _get_drift_detector()
        result = detector.analyze_concept_drift(concept_id)
        if "error" in result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
        return ConceptDriftResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Concept drift analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/emerging", response_model=EmergingResponse)
def get_emerging_concepts(window_days: int = Query(90, ge=1, le=365)):
    """Find emerging concepts with rapidly growing connections."""
    try:
        detector = _get_drift_detector()
        emerging = detector.detect_emerging_concepts(window_days=window_days)
        return EmergingResponse(emerging=emerging, total=len(emerging))
    except Exception as e:
        logger.error("Emerging concepts detection failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/trends", response_model=TrendReport)
def get_trend_report():
    """Get comprehensive trend analysis across all concepts."""
    try:
        detector = _get_drift_detector()
        result = detector.get_trend_report()
        return TrendReport(**result)
    except Exception as e:
        logger.error("Trend report failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/enrichment-cycle", response_model=EnrichmentCycleResult)
def trigger_enrichment_cycle(stale_days: int = Query(7, ge=1, le=90)):
    """Manually trigger an enrichment cycle for stale nodes."""
    try:
        engine = _get_growth_engine()
        result = engine.run_enrichment_cycle(stale_days=stale_days)
        return EnrichmentCycleResult(**result)
    except Exception as e:
        logger.error("Enrichment cycle failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/scheduler/status", response_model=SchedulerStatus)
def get_scheduler_status():
    """Get the background scheduler status."""
    try:
        scheduler = _get_scheduler()
        result = scheduler.get_status()
        return SchedulerStatus(**result)
    except Exception as e:
        logger.error("Scheduler status failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/scheduler/start", response_model=SchedulerStatus)
async def start_scheduler():
    """Start periodic enrichment + drift detection background tasks."""
    try:
        scheduler = _get_scheduler()
        await scheduler.start()
        return SchedulerStatus(**scheduler.get_status())
    except Exception as e:
        logger.error("Scheduler start failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/scheduler/stop", response_model=SchedulerStatus)
async def stop_scheduler():
    """Stop periodic background tasks."""
    try:
        scheduler = _get_scheduler()
        await scheduler.stop()
        return SchedulerStatus(**scheduler.get_status())
    except Exception as e:
        logger.error("Scheduler stop failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
