"""
Gnosiplexio API Routes — Knowledge graph endpoints.

All routes prefix: /api/v1/gnosiplexio
"""
from __future__ import annotations

import json
import threading
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.logging_config import get_logger

logger = get_logger("gnosiplexio.routes")

router = APIRouter(prefix="/gnosiplexio", tags=["gnosiplexio"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    """Ingest a paper by work_id (from adapter) or inline data."""
    work_id: Optional[str] = Field(None, description="Work ID in the configured adapter")
    source: Optional[str] = Field(None, description="Source type: json, csv (for inline data)")
    data: Optional[str] = Field(None, description="Inline JSON/CSV data for generic adapter")
    options: Dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    node_id: str
    ingested_count: int = 0
    nodes_created: int = 0
    edges_created: int = 0
    enriched_nodes: int = 0
    errors: List[str] = []
    duration_ms: float = 0.0


class NodeResponse(BaseModel):
    id: str
    type: str
    properties: dict
    network_citations: list = []
    network_credibility: Optional[dict] = None
    relative_position: Optional[dict] = None
    cross_perspectives: list = []


class GraphExportResponse(BaseModel):
    format: str
    nodes: list
    edges: list
    stats: dict


class CredibilityResponse(BaseModel):
    work_id: str
    total_citations_in_network: int
    unique_citing_journals: int
    credibility_score: float
    top_cited_for: list = []
    known_limitations: list = []
    sentiment_distribution: dict = {}
    last_updated: str


class SearchResult(BaseModel):
    id: str
    type: str
    label: str
    score: float
    snippet: Optional[str] = None
    source: str = "graph"


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResult]
    source: str = "graph"


class StatsResponse(BaseModel):
    total_nodes: int
    total_edges: int
    node_types: Dict[str, int]
    edge_types: Dict[str, int]
    connected_components: int = 0
    largest_component_size: int = 0
    density: float
    avg_degree: Optional[float] = None
    total_network_citations: int = 0
    nodes_with_credibility: int = 0


class CompareRequest(BaseModel):
    node_id_1: str
    node_id_2: str


class CompareResponse(BaseModel):
    node_id_1: str
    node_id_2: str
    shared_citations: list = []
    shared_concepts: list = []
    divergent_edges_a: list = []
    divergent_edges_b: list = []
    shortest_path: Optional[list] = None
    similarity_score: float = 0.0


class IngestAllResponse(BaseModel):
    ingested_count: int = 0
    new_nodes: int = 0
    new_edges: int = 0
    enriched_nodes: int = 0
    errors: List[str] = []
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Engine singleton
# ---------------------------------------------------------------------------

_engine_instance = None
_engine_lock = threading.Lock()


def _get_engine():
    """Get or create the singleton GnosiplexioEngine."""
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:
                from app.services.gnosiplexio.engine import GnosiplexioEngine
                from pathlib import Path
                import os

                # Default graph path
                data_dir = Path(os.getenv("GNOSIPLEXIO_DATA_DIR", "data/gnosiplexio"))
                graph_path = data_dir / "graph.json"

                # Try to set up VF adapter if available
                adapter = None
                try:
                    from app.services.gnosiplexio.adapters.vf_adapter import VFAdapter
                    adapter = VFAdapter()
                    logger.info("VF adapter initialized")
                except Exception as e:
                    logger.warning("VF adapter not available, starting without adapter: %s", e)

                _engine_instance = GnosiplexioEngine(
                    adapter=adapter,
                    graph_path=graph_path,
                    auto_save=True,
                )
                logger.info("GnosiplexioEngine singleton created")

    return _engine_instance


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_paper(request: IngestRequest):
    """Ingest a paper and trigger network enrichment."""
    try:
        engine = _get_engine()

        if request.work_id:
            # Ingest from configured adapter by work_id
            result = engine.ingest(request.work_id)
            return IngestResponse(
                node_id=request.work_id,
                ingested_count=result.ingested_count,
                nodes_created=result.new_nodes,
                edges_created=result.new_edges,
                enriched_nodes=result.enriched_nodes,
                errors=result.errors,
                duration_ms=result.duration_ms,
            )
        elif request.data:
            # Inline data: create a temporary engine with a GenericAdapter
            from app.services.gnosiplexio.adapters.generic_adapter import GenericAdapter
            from app.services.gnosiplexio.engine import GnosiplexioEngine

            data = json.loads(request.data)
            if isinstance(data, dict):
                data = [data]

            tmp_engine = GnosiplexioEngine(
                adapter=GenericAdapter(data=data),
                graph_path=None,
                auto_save=False,
            )
            # Reuse singleton graph to avoid adapter mutation on shared engine
            tmp_engine._graph = engine.graph

            total = tmp_engine.ingest_all()
            # Return first work_id or "batch"
            first_id = data[0].get("id", "unknown") if data else "unknown"
            return IngestResponse(
                node_id=first_id,
                ingested_count=total.ingested_count,
                nodes_created=total.new_nodes,
                edges_created=total.new_edges,
                enriched_nodes=total.enriched_nodes,
                errors=total.errors,
                duration_ms=total.duration_ms,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either work_id (for adapter) or data (inline JSON)"
            )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON: {e}")
    except Exception as e:
        logger.error("Ingest failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/ingest-all", response_model=IngestAllResponse)
def ingest_all():
    """Ingest all works from the configured adapter."""
    engine = _get_engine()
    if engine._adapter is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No adapter configured")
    result = engine.ingest_all()
    return IngestAllResponse(
        ingested_count=result.ingested_count,
        new_nodes=result.new_nodes,
        new_edges=result.new_edges,
        enriched_nodes=result.enriched_nodes,
        errors=result.errors,
        duration_ms=result.duration_ms,
    )


@router.get("/node/{node_id}", response_model=NodeResponse)
def get_node(node_id: str):
    """Get a node with its full network knowledge."""
    engine = _get_engine()
    nk = engine.get_node(node_id)
    if not nk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node {node_id} not found")

    # Convert NetworkKnowledge to response
    return NodeResponse(
        id=nk.work_id,
        type=nk.direct_knowledge.get("node_type", "Unknown"),
        properties={k: v for k, v in nk.direct_knowledge.items()
                    if k not in ("network_citations", "cross_perspectives",
                                 "concept_evolution", "network_credibility")},
        network_citations=nk.network_citations,
        network_credibility=nk.network_credibility,
        relative_position=nk.relative_position,
        cross_perspectives=nk.cross_perspectives,
    )


@router.get("/neighborhood/{node_id}", response_model=GraphExportResponse)
def get_neighborhood(
    node_id: str,
    hops: int = Query(2, ge=1, le=5),
    max_nodes: int = Query(500, ge=1, le=5000),
):
    """Get the ego network around a node within a given number of hops."""
    engine = _get_engine()
    if engine.graph.get_node(node_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node {node_id} not found")

    result = engine.get_neighborhood(node_id, hops=hops, max_nodes=max_nodes)
    return GraphExportResponse(
        format="ego",
        nodes=result.get("nodes", []),
        edges=result.get("edges", []),
        stats={
            "center": result.get("center", node_id),
            "hops": hops,
            "node_count": result.get("node_count", 0),
            "edge_count": result.get("edge_count", 0),
        },
    )


@router.get("/search", response_model=SearchResponse)
def search_graph(q: str = Query(..., min_length=1)):
    """Semantic + graph search across the knowledge network."""
    engine = _get_engine()
    qr = engine.search(q)

    # Convert results to SearchResult models
    results = []
    for r in qr.results:
        results.append(SearchResult(
            id=r.get("id", r.get("work_id", "")),
            type=r.get("node_type", r.get("type", "Unknown")),
            label=r.get("title", r.get("name", r.get("id", ""))),
            score=float(r.get("score", 0.5)),
            snippet=r.get("abstract", r.get("snippet", ""))[:200] if r.get("abstract") or r.get("snippet") else None,
            source=r.get("source", "graph"),
        ))

    return SearchResponse(
        query=qr.query,
        total=qr.total,
        results=results,
        source=qr.source,
    )


@router.get("/credibility/{node_id}", response_model=CredibilityResponse)
def get_credibility(node_id: str):
    """Get the network credibility report for a work node."""
    engine = _get_engine()
    report = engine.get_credibility(node_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No credibility data for {node_id}")
    return CredibilityResponse(**report)


@router.get("/graph", response_model=GraphExportResponse)
def export_graph(format: str = Query("json", pattern="^(cytoscape|json|bibtex)$")):
    """Export the full graph in the specified format."""
    engine = _get_engine()
    result = engine.export_graph(format=format)

    if format == "cytoscape":
        # Cytoscape format wraps in "elements", flatten for response
        elements = result.get("elements", {})
        return GraphExportResponse(
            format="cytoscape",
            nodes=elements.get("nodes", []),
            edges=elements.get("edges", []),
            stats=result.get("stats", {}),
        )
    elif format == "json":
        return GraphExportResponse(
            format="json",
            nodes=result.get("nodes", []),
            edges=result.get("edges", []),
            stats=result.get("stats", {}),
        )
    else:  # bibtex
        return GraphExportResponse(
            format="bibtex",
            nodes=[{"content": result.get("content", "")}],
            edges=[],
            stats={"count": result.get("count", 0)},
        )


@router.get("/stats", response_model=StatsResponse)
def get_stats():
    """Get network statistics."""
    engine = _get_engine()
    stats = engine.get_stats()

    total_nodes = stats.get("total_nodes", 0)
    total_edges = stats.get("total_edges", 0)
    stats["avg_degree"] = round((2 * total_edges) / total_nodes, 4) if total_nodes > 0 else None

    return StatsResponse(**stats)


@router.post("/compare", response_model=CompareResponse)
def compare_nodes(request: CompareRequest):
    """Compare two nodes in the knowledge network."""
    engine = _get_engine()

    for nid in (request.node_id_1, request.node_id_2):
        if engine.graph.get_node(nid) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Node {nid} not found")

    result = engine.compare(request.node_id_1, request.node_id_2)
    return CompareResponse(
        node_id_1=result.node_a,
        node_id_2=result.node_b,
        shared_citations=result.shared_citations,
        shared_concepts=result.shared_concepts,
        divergent_edges_a=result.divergent_edges_a,
        divergent_edges_b=result.divergent_edges_b,
        shortest_path=result.shortest_path,
        similarity_score=result.similarity_score,
    )
