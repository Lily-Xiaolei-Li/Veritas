"""
Gnosiplexio Concept Drift Detector — Temporal analysis of concept evolution.

Tracks how concepts' connections change over time, detects emerging and
declining concepts, identifies paradigm shifts in the knowledge graph.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from app.services.gnosiplexio.graph_store import GraphStore

logger = logging.getLogger("gnosiplexio.concept_drift")

# Default time window for trend analysis
DEFAULT_WINDOW_DAYS = 90


def _parse_timestamp(ts: Any) -> Optional[datetime]:
    """Parse a timestamp string or datetime to a timezone-aware datetime."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        dt = ts
    elif isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _get_node_timestamp(data: Dict[str, Any]) -> Optional[datetime]:
    """Extract the best available timestamp from node data."""
    for field in ("created_at", "added_at", "updated_at", "publication_date", "year"):
        val = data.get(field)
        if val is not None:
            ts = _parse_timestamp(val)
            if ts:
                return ts
    return None


def _get_edge_timestamp(data: Dict[str, Any]) -> Optional[datetime]:
    """Extract timestamp from edge data."""
    for field in ("created_at", "added_at"):
        val = data.get(field)
        if val is not None:
            ts = _parse_timestamp(val)
            if ts:
                return ts
    return None


class ConceptDriftDetector:
    """
    Detects temporal concept drift in the knowledge graph.

    Analyzes how concepts evolve over time by examining changes in
    connectivity, centrality, and cluster patterns.
    """

    def __init__(self, graph: GraphStore):
        """
        Initialize the concept drift detector.

        Args:
            graph: The GraphStore instance to analyze.
        """
        self._graph = graph

    def analyze_concept_drift(self, concept_id: str) -> Dict[str, Any]:
        """
        Track how a concept's connections change over time.

        Args:
            concept_id: The concept node ID to analyze.

        Returns:
            Dict with temporal connection analysis.
        """
        data = self._graph.get_node(concept_id)
        if data is None:
            return {"error": f"Concept {concept_id} not found", "concept_id": concept_id}

        g = self._graph._graph
        neighbors = self._graph.get_neighbors(concept_id)

        # Group neighbors by their timestamp into time buckets
        time_buckets: Dict[str, List[str]] = defaultdict(list)
        undated: List[str] = []

        for neighbor_id in neighbors:
            ndata = self._graph.get_node(neighbor_id)
            if ndata is None:
                continue
            ts = _get_node_timestamp(ndata)
            if ts:
                bucket = ts.strftime("%Y-%m")
                time_buckets[bucket].append(neighbor_id)
            else:
                undated.append(neighbor_id)

        # Edge type distribution over time
        edge_evolution: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for u, v, edata in g.edges(data=True):
            if u == concept_id or v == concept_id:
                et = edata.get("edge_type", "UNKNOWN")
                ets = _get_edge_timestamp(edata)
                bucket = ets.strftime("%Y-%m") if ets else "undated"
                edge_evolution[bucket][et] += 1

        # Sort buckets chronologically
        sorted_buckets = sorted(time_buckets.keys())

        return {
            "concept_id": concept_id,
            "concept_name": data.get("name", data.get("title", concept_id)),
            "total_connections": len(neighbors),
            "connections_over_time": {b: len(time_buckets[b]) for b in sorted_buckets},
            "edge_type_evolution": {b: dict(edge_evolution[b]) for b in sorted(edge_evolution.keys())},
            "undated_connections": len(undated),
            "growth_trend": self._compute_trend(sorted_buckets, time_buckets),
        }

    def _compute_trend(
        self, sorted_buckets: List[str], buckets: Dict[str, List[str]]
    ) -> str:
        """Compute a simple growth trend from time buckets."""
        if len(sorted_buckets) < 2:
            return "insufficient_data"

        counts = [len(buckets[b]) for b in sorted_buckets]
        half = len(counts) // 2
        first_half = sum(counts[:half]) / max(half, 1)
        second_half = sum(counts[half:]) / max(len(counts) - half, 1)

        if second_half > first_half * 1.5:
            return "accelerating"
        elif second_half > first_half * 1.1:
            return "growing"
        elif second_half < first_half * 0.5:
            return "declining"
        elif second_half < first_half * 0.9:
            return "slowing"
        else:
            return "stable"

    def detect_emerging_concepts(
        self, window_days: int = DEFAULT_WINDOW_DAYS, min_new_edges: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find concepts with rapidly growing edge counts.

        Args:
            window_days: Time window to consider as "recent".
            min_new_edges: Minimum new edges to qualify as emerging.

        Returns:
            List of emerging concept dicts sorted by growth rate.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        g = self._graph._graph
        concept_ids = self._graph.get_nodes_by_type("Concept")
        emerging: List[Dict[str, Any]] = []

        for cid in concept_ids:
            recent_edges = 0
            total_edges = 0

            for u, v, edata in g.edges(data=True):
                if u != cid and v != cid:
                    continue
                total_edges += 1
                ts = _get_edge_timestamp(edata)
                if ts and ts >= cutoff:
                    recent_edges += 1

            if recent_edges >= min_new_edges:
                data = self._graph.get_node(cid) or {}
                emerging.append({
                    "concept_id": cid,
                    "name": data.get("name", data.get("title", cid)),
                    "recent_edges": recent_edges,
                    "total_edges": total_edges,
                    "growth_ratio": round(recent_edges / max(total_edges - recent_edges, 1), 3),
                })

        emerging.sort(key=lambda x: x["growth_ratio"], reverse=True)
        return emerging

    def detect_declining_concepts(
        self, window_days: int = DEFAULT_WINDOW_DAYS
    ) -> List[Dict[str, Any]]:
        """
        Find concepts losing centrality over time.

        Compares recent connectivity with historical connectivity.

        Args:
            window_days: Time window for "recent" activity.

        Returns:
            List of declining concept dicts.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        g = self._graph._graph
        concept_ids = self._graph.get_nodes_by_type("Concept")
        declining: List[Dict[str, Any]] = []

        for cid in concept_ids:
            old_edges = 0
            recent_edges = 0

            for u, v, edata in g.edges(data=True):
                if u != cid and v != cid:
                    continue
                ts = _get_edge_timestamp(edata)
                if ts:
                    if ts < cutoff:
                        old_edges += 1
                    else:
                        recent_edges += 1
                else:
                    old_edges += 1  # Assume undated edges are old

            # Declining = had significant old edges but very few recent ones
            if old_edges >= 3 and recent_edges <= 1:
                data = self._graph.get_node(cid) or {}
                declining.append({
                    "concept_id": cid,
                    "name": data.get("name", data.get("title", cid)),
                    "old_edges": old_edges,
                    "recent_edges": recent_edges,
                    "decline_ratio": round(1 - (recent_edges / max(old_edges, 1)), 3),
                })

        declining.sort(key=lambda x: x["decline_ratio"], reverse=True)
        return declining

    def detect_paradigm_shifts(self) -> List[Dict[str, Any]]:
        """
        Detect paradigm shifts by finding clusters where edge patterns changed.

        Looks for communities where the dominant edge types have shifted,
        or where new bridge edges connect previously separate communities.

        Returns:
            List of paradigm shift indicators.
        """
        g = self._graph._graph
        if g.number_of_nodes() < 3:
            return []

        shifts: List[Dict[str, Any]] = []

        # Detect via community structure
        undirected = g.to_undirected()
        try:
            communities = list(nx.community.greedy_modularity_communities(undirected))
        except Exception:
            communities = list(nx.connected_components(undirected))

        # Look for cross-community edges with CHALLENGES or EXTENDS types
        for i, comm_a in enumerate(communities):
            for j, comm_b in enumerate(communities):
                if j <= i:
                    continue
                cross_edges: Dict[str, int] = defaultdict(int)
                for u, v, edata in g.edges(data=True):
                    if (u in comm_a and v in comm_b) or (u in comm_b and v in comm_a):
                        cross_edges[edata.get("edge_type", "UNKNOWN")] += 1

                # CHALLENGES edges between communities suggest paradigm shifts
                challenge_count = cross_edges.get("CHALLENGES", 0)
                extends_count = cross_edges.get("EXTENDS", 0)
                total_cross = sum(cross_edges.values())

                if challenge_count >= 2 or (total_cross >= 3 and challenge_count > 0):
                    shifts.append({
                        "community_a_size": len(comm_a),
                        "community_b_size": len(comm_b),
                        "cross_edge_types": dict(cross_edges),
                        "challenge_count": challenge_count,
                        "indicator": "high" if challenge_count >= 3 else "moderate",
                        "description": (
                            f"Communities of size {len(comm_a)} and {len(comm_b)} "
                            f"have {challenge_count} CHALLENGES edges — possible paradigm shift"
                        ),
                    })

        shifts.sort(key=lambda x: x["challenge_count"], reverse=True)
        return shifts

    def mark_outdated_concepts(self, declining: List[Dict[str, Any]]) -> List[str]:
        """Mark declining concepts as potentially outdated in graph metadata."""
        outdated_ids: List[str] = []
        for concept in declining:
            if concept.get("decline_ratio", 0) < 0.7:
                continue
            concept_id = concept.get("concept_id")
            if not concept_id:
                continue
            node = self._graph.get_node(concept_id)
            if node is None:
                continue
            node["drift_status"] = "possibly_outdated"
            node["drift_marked_at"] = datetime.now(timezone.utc).isoformat()
            outdated_ids.append(concept_id)
        return outdated_ids

    def get_trend_report(self, mark_outdated: bool = True) -> Dict[str, Any]:
        """
        Generate a comprehensive trend report across all concepts.

        Returns:
            Dict with emerging, declining, and paradigm shift data.
        """
        emerging = self.detect_emerging_concepts()
        declining = self.detect_declining_concepts()
        paradigm_shifts = self.detect_paradigm_shifts()
        outdated_ids = self.mark_outdated_concepts(declining) if mark_outdated else []

        # Overall health score
        total_concepts = len(self._graph.get_nodes_by_type("Concept"))
        health_score = 1.0
        if total_concepts > 0:
            emerging_ratio = len(emerging) / total_concepts
            declining_ratio = len(declining) / total_concepts
            health_score = max(0.0, min(1.0, 0.5 + emerging_ratio - declining_ratio))

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_concepts": total_concepts,
            "emerging_concepts": emerging[:20],
            "emerging_count": len(emerging),
            "declining_concepts": declining[:20],
            "declining_count": len(declining),
            "outdated_concepts": outdated_ids[:50],
            "outdated_count": len(outdated_ids),
            "paradigm_shifts": paradigm_shifts[:10],
            "paradigm_shift_count": len(paradigm_shifts),
            "health_score": round(health_score, 4),
        }
