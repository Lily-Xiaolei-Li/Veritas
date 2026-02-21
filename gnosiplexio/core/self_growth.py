"""
Gnosiplexio Self-Growth Engine — Automated knowledge graph expansion and maintenance.

Provides scheduled enrichment, gap detection, suggestion generation,
growth metrics tracking, and duplicate node merging.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from app.services.gnosiplexio.graph_store import GraphStore

logger = logging.getLogger("gnosiplexio.self_growth")

# Staleness threshold
STALE_DAYS = 7
# Fuzzy match threshold for duplicate detection
SIMILARITY_THRESHOLD = 0.85


class SelfGrowthEngine:
    """
    Self-growth and maintenance engine for the Gnosiplexio knowledge graph.

    Works with an existing GraphStore to detect gaps, suggest additions,
    merge duplicates, and track growth over time.
    """

    def __init__(self, graph: GraphStore):
        """
        Initialize the self-growth engine.

        Args:
            graph: The GraphStore instance to operate on.
        """
        self._graph = graph
        self._growth_history: List[Dict[str, Any]] = []
        self._snapshot_history()

    def _snapshot_history(self) -> None:
        """Record the current graph size as a growth snapshot."""
        self._growth_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node_count": self._graph.node_count,
            "edge_count": self._graph.edge_count,
        })

    # -- Scheduled Enrichment ------------------------------------------------

    def get_stale_nodes(self, stale_days: int = STALE_DAYS) -> List[str]:
        """
        Find nodes that haven't been updated in more than `stale_days` days.

        Args:
            stale_days: Number of days after which a node is considered stale.

        Returns:
            List of stale node IDs.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
        stale = []

        for node_id in self._graph.get_all_node_ids():
            data = self._graph.get_node(node_id)
            if data is None:
                continue

            updated = data.get("updated_at") or data.get("created_at") or data.get("added_at")
            if updated is None:
                # No timestamp — treat as stale
                stale.append(node_id)
                continue

            if isinstance(updated, str):
                try:
                    updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    stale.append(node_id)
                    continue
            elif isinstance(updated, datetime):
                updated_dt = updated
            else:
                stale.append(node_id)
                continue

            if updated_dt.tzinfo is None:
                updated_dt = updated_dt.replace(tzinfo=timezone.utc)

            if updated_dt < cutoff:
                stale.append(node_id)

        return stale

    def run_enrichment_cycle(self, stale_days: int = STALE_DAYS) -> Dict[str, Any]:
        """
        Re-enrichment cycle: find stale nodes and mark them for re-enrichment.

        This method identifies stale nodes and returns them for the engine
        to re-run its enrichment pipeline on.

        Args:
            stale_days: Number of days after which a node is considered stale.

        Returns:
            Dict with cycle results including stale node IDs and counts.
        """
        stale_nodes = self.get_stale_nodes(stale_days)

        # Record snapshot after cycle
        self._snapshot_history()

        logger.info(
            "Enrichment cycle complete: %d stale nodes found out of %d total",
            len(stale_nodes), self._graph.node_count
        )

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_nodes": self._graph.node_count,
            "stale_nodes_count": len(stale_nodes),
            "stale_node_ids": stale_nodes[:100],  # Cap to prevent huge responses
            "stale_threshold_days": stale_days,
        }

    # -- Gap Detection -------------------------------------------------------

    def detect_knowledge_gaps(self) -> Dict[str, Any]:
        """
        Detect knowledge gaps in the graph.

        Identifies:
        - Isolated nodes (no edges)
        - Weakly connected components (fragmented subgraphs)
        - Missing citation chains (works that cite nothing and aren't cited)
        - Concept nodes with no associated works

        Returns:
            Dict with detailed gap analysis.
        """
        g = self._graph._graph

        # Isolated nodes (degree 0)
        isolated = [n for n in g.nodes() if g.degree(n) == 0]

        # Weakly connected components
        undirected = g.to_undirected()
        components = list(nx.connected_components(undirected))
        small_components = [
            list(c) for c in components
            if 1 < len(c) <= 3
        ]

        # Works with no outgoing citations (potential gaps)
        works_no_outgoing = []
        works_no_incoming = []
        for node_id in self._graph.get_nodes_by_type("Work"):
            out_edges = list(g.successors(node_id))
            in_edges = list(g.predecessors(node_id))
            citation_out = [
                e for e in out_edges
                if g.edges[node_id, e].get("edge_type") in ("CITES", "CITED_FOR", "EXTENDS")
            ]
            citation_in = [
                e for e in in_edges
                if g.edges[e, node_id].get("edge_type") in ("CITES", "CITED_FOR", "EXTENDS")
            ]
            if not citation_out:
                works_no_outgoing.append(node_id)
            if not citation_in:
                works_no_incoming.append(node_id)

        # Orphaned concepts (no connected works)
        orphaned_concepts = []
        for concept_id in self._graph.get_nodes_by_type("Concept"):
            neighbors = self._graph.get_neighbors(concept_id)
            has_work = any(
                self._graph.get_node(n) and self._graph.get_node(n).get("node_type") == "Work"
                for n in neighbors
            )
            if not has_work:
                orphaned_concepts.append(concept_id)

        gap_score = 0.0
        if self._graph.node_count > 0:
            gap_score = (
                len(isolated) * 3 +
                len(small_components) * 2 +
                len(orphaned_concepts) * 2 +
                len(works_no_outgoing) +
                len(works_no_incoming)
            ) / max(self._graph.node_count, 1)

        return {
            "isolated_nodes": isolated[:50],
            "isolated_count": len(isolated),
            "small_components": small_components[:20],
            "small_component_count": len(small_components),
            "works_without_outgoing_citations": works_no_outgoing[:50],
            "works_without_incoming_citations": works_no_incoming[:50],
            "orphaned_concepts": orphaned_concepts[:50],
            "gap_score": round(gap_score, 4),
            "total_components": len(components),
        }

    # -- Suggestion Generation -----------------------------------------------

    def suggest_papers_to_add(self, max_suggestions: int = 10) -> List[Dict[str, Any]]:
        """
        Suggest concept areas where adding papers would fill knowledge gaps.

        Based on graph structure: looks for bridge concepts, orphaned areas,
        and highly-cited but sparsely-connected domains.

        Args:
            max_suggestions: Maximum number of suggestions to return.

        Returns:
            List of suggestion dicts with concept area and reasoning.
        """
        suggestions: List[Dict[str, Any]] = []
        g = self._graph._graph

        # 1. Orphaned concepts need papers
        for concept_id in self._graph.get_nodes_by_type("Concept"):
            neighbors = self._graph.get_neighbors(concept_id)
            work_neighbors = [
                n for n in neighbors
                if (self._graph.get_node(n) or {}).get("node_type") == "Work"
            ]
            if len(work_neighbors) <= 1:
                data = self._graph.get_node(concept_id) or {}
                suggestions.append({
                    "concept_area": data.get("name", data.get("title", concept_id)),
                    "concept_id": concept_id,
                    "reason": "Concept has very few associated works",
                    "connected_works": len(work_neighbors),
                    "priority": "high" if len(work_neighbors) == 0 else "medium",
                })

        # 2. Bridge concepts between disconnected components
        undirected = g.to_undirected()
        if undirected.number_of_nodes() > 2:
            try:
                betweenness = nx.betweenness_centrality(undirected)
                high_betweenness = sorted(
                    betweenness.items(), key=lambda x: x[1], reverse=True
                )[:5]
                for node_id, score in high_betweenness:
                    data = self._graph.get_node(node_id) or {}
                    if data.get("node_type") == "Concept" and score > 0.1:
                        suggestions.append({
                            "concept_area": data.get("name", data.get("title", node_id)),
                            "concept_id": node_id,
                            "reason": f"High bridge centrality ({score:.3f}) — adding papers here connects subgraphs",
                            "priority": "high",
                        })
            except Exception as e:
                logger.warning("Betweenness calculation failed: %s", e)

        # Deduplicate by concept_id
        seen: Set[str] = set()
        unique: List[Dict[str, Any]] = []
        for s in suggestions:
            cid = s.get("concept_id", "")
            if cid not in seen:
                seen.add(cid)
                unique.append(s)

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        unique.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))

        return unique[:max_suggestions]

    # -- Growth Metrics ------------------------------------------------------

    def get_growth_report(self) -> Dict[str, Any]:
        """
        Generate a growth report tracking graph expansion over time.

        Returns:
            Dict with growth metrics and history.
        """
        # Take a fresh snapshot
        self._snapshot_history()

        # Compute per-node-type counts
        type_counts: Dict[str, int] = defaultdict(int)
        for node_id in self._graph.get_all_node_ids():
            data = self._graph.get_node(node_id)
            if data:
                ntype = data.get("node_type", "Unknown")
                type_counts[ntype] += 1

        # Growth rate from history
        growth_rate_nodes = 0.0
        growth_rate_edges = 0.0
        if len(self._growth_history) >= 2:
            prev = self._growth_history[-2]
            curr = self._growth_history[-1]
            prev_nodes = prev.get("node_count", 0)
            prev_edges = prev.get("edge_count", 0)
            if prev_nodes > 0:
                growth_rate_nodes = (curr["node_count"] - prev_nodes) / prev_nodes
            if prev_edges > 0:
                growth_rate_edges = (curr["edge_count"] - prev_edges) / prev_edges

        return {
            "current_nodes": self._graph.node_count,
            "current_edges": self._graph.edge_count,
            "node_type_distribution": dict(type_counts),
            "growth_rate_nodes": round(growth_rate_nodes, 4),
            "growth_rate_edges": round(growth_rate_edges, 4),
            "history": self._growth_history[-50:],
            "snapshots_recorded": len(self._growth_history),
        }

    # -- Auto-Merge Duplicates -----------------------------------------------

    def _get_node_label(self, node_id: str) -> str:
        """Get the display label for a node."""
        data = self._graph.get_node(node_id) or {}
        return data.get("title", data.get("name", node_id)).strip().lower()

    def find_duplicate_candidates(
        self, threshold: float = SIMILARITY_THRESHOLD
    ) -> List[Tuple[str, str, float]]:
        """
        Find pairs of nodes that may be duplicates based on fuzzy title matching.

        Args:
            threshold: Minimum similarity ratio (0-1) to consider as duplicate.

        Returns:
            List of (node_a, node_b, similarity) tuples.
        """
        candidates: List[Tuple[str, str, float]] = []
        node_ids = self._graph.get_all_node_ids()

        # Group by node_type to only compare within same type
        type_groups: Dict[str, List[str]] = defaultdict(list)
        for nid in node_ids:
            data = self._graph.get_node(nid) or {}
            ntype = data.get("node_type", "Unknown")
            type_groups[ntype].append(nid)

        for ntype, ids in type_groups.items():
            labels = [(nid, self._get_node_label(nid)) for nid in ids]
            for i in range(len(labels)):
                for j in range(i + 1, len(labels)):
                    id_a, label_a = labels[i]
                    id_b, label_b = labels[j]
                    if not label_a or not label_b:
                        continue
                    ratio = SequenceMatcher(None, label_a, label_b).ratio()
                    if ratio >= threshold:
                        candidates.append((id_a, id_b, round(ratio, 4)))

        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates

    def merge_duplicate_nodes(
        self, threshold: float = SIMILARITY_THRESHOLD, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Detect and merge duplicate nodes with similar titles/names.

        The node with more edges is kept; the other's edges are redirected.

        Args:
            threshold: Minimum similarity ratio for duplicates.
            dry_run: If True, only report without merging.

        Returns:
            Dict with merge results.
        """
        candidates = self.find_duplicate_candidates(threshold)
        merged: List[Dict[str, Any]] = []
        removed_ids: Set[str] = set()

        for node_a, node_b, similarity in candidates:
            if node_a in removed_ids or node_b in removed_ids:
                continue

            if dry_run:
                merged.append({
                    "kept": node_a,
                    "removed": node_b,
                    "similarity": similarity,
                    "dry_run": True,
                })
                continue

            # Keep the node with more connections
            g = self._graph._graph
            degree_a = g.degree(node_a)
            degree_b = g.degree(node_b)
            keep, remove = (node_a, node_b) if degree_a >= degree_b else (node_b, node_a)

            # Redirect edges from removed node to kept node
            for pred in list(g.predecessors(remove)):
                if pred != keep and not g.has_edge(pred, keep):
                    edge_data = dict(g.edges[pred, remove])
                    g.add_edge(pred, keep, **edge_data)

            for succ in list(g.successors(remove)):
                if succ != keep and not g.has_edge(keep, succ):
                    edge_data = dict(g.edges[remove, succ])
                    g.add_edge(keep, succ, **edge_data)

            # Remove the duplicate
            self._graph.remove_node(remove)
            removed_ids.add(remove)

            merged.append({
                "kept": keep,
                "removed": remove,
                "similarity": similarity,
            })

            logger.info("Merged duplicate: '%s' into '%s' (similarity=%.3f)", remove, keep, similarity)

        return {
            "duplicates_found": len(candidates),
            "merges_performed": len(merged) if not dry_run else 0,
            "merges": merged[:50],
            "dry_run": dry_run,
        }
