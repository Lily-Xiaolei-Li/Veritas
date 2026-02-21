"""
Gnosiplexio Engine — Main orchestrator for the Knowledge Graph Engine.

This is the central coordinator that ties together graph storage, data adapters,
network enrichment, credibility scoring, and position calculation.

Architecture:
    Engine
    ├── GraphStore (NetworkX graph + JSON persistence)
    ├── DataSourceAdapter (VF / Zotero / OpenAlex / Generic)
    ├── NetworkEnricher (6-step organic enrichment pipeline)
    ├── CredibilityScorer (network-derived credibility)
    └── PositionCalculator (centrality, PageRank, communities)

Usage:
    # With VF Store
    engine = GnosiplexioEngine(adapter=VFStoreAdapter(qdrant_path="..."))
    engine.ingest("paper_id")
    result = engine.query("what is Power 1997 cited for?")
    engine.visualize(center="power_1997", hops=2)

    # With generic JSON
    engine = GnosiplexioEngine(adapter=GenericAdapter(file="papers.json"))
    engine.ingest_all()
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("gnosiplexio.engine")


# ---------------------------------------------------------------------------
# Data classes for engine I/O
# ---------------------------------------------------------------------------

@dataclass
class IngestResult:
    """Result of ingesting one or more papers into the graph."""
    ingested_count: int = 0
    enriched_nodes: int = 0
    new_edges: int = 0
    new_nodes: int = 0
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QueryResult:
    """Result of a graph query."""
    query: str
    results: List[Dict[str, Any]] = field(default_factory=list)
    total: int = 0
    source: str = "graph"  # graph | vector | hybrid

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NetworkKnowledge:
    """Complete network knowledge for a single work node."""
    work_id: str
    direct_knowledge: Dict[str, Any] = field(default_factory=dict)
    network_citations: List[Dict[str, Any]] = field(default_factory=list)
    network_credibility: Optional[Dict[str, Any]] = None
    cross_perspectives: List[Dict[str, Any]] = field(default_factory=list)
    relative_position: Optional[Dict[str, Any]] = None
    concept_evolution: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CompareResult:
    """Result of comparing two nodes."""
    node_a: str
    node_b: str
    shared_citations: List[str] = field(default_factory=list)
    shared_concepts: List[str] = field(default_factory=list)
    divergent_edges_a: List[Dict[str, Any]] = field(default_factory=list)
    divergent_edges_b: List[Dict[str, Any]] = field(default_factory=list)
    shortest_path: Optional[List[str]] = None
    similarity_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class GnosiplexioEngine:
    """
    Main orchestrator for Gnosiplexio knowledge graph operations.

    Coordinates graph storage, data adapters, enrichment, scoring,
    and position calculation into a unified API.
    """

    def __init__(
        self,
        adapter=None,
        graph_path: Optional[Union[str, Path]] = None,
        auto_save: bool = True,
    ):
        """
        Initialize the Gnosiplexio engine.

        Args:
            adapter: A DataSourceAdapter implementation (VF, Zotero, Generic, etc.)
            graph_path: Path to persist the graph JSON. If None, graph is in-memory only.
            auto_save: If True, automatically save graph after each ingest operation.
        """
        # Lazy imports to avoid circular dependencies and allow partial usage
        from .graph_store import GraphStore

        self._adapter = adapter
        self._graph_path = Path(graph_path) if graph_path else None
        self._auto_save = auto_save

        # Initialize graph store
        self._graph = GraphStore()

        # Load existing graph if path exists
        if self._graph_path and self._graph_path.exists():
            logger.info("Loading existing graph from %s", self._graph_path)
            self._graph.load_json(self._graph_path)

        # Lazy-loaded components (initialized on first use)
        self._enricher = None
        self._scorer = None
        self._position_calc = None

        logger.info(
            "GnosiplexioEngine initialized. Adapter: %s, Graph nodes: %d, edges: %d",
            type(adapter).__name__ if adapter else "None",
            self._graph.node_count,
            self._graph.edge_count,
        )

    # -- Properties ----------------------------------------------------------

    @property
    def graph(self):
        """Access the underlying GraphStore."""
        return self._graph

    @property
    def enricher(self):
        """Lazy-load the NetworkEnricher."""
        if self._enricher is None:
            from .network_enricher import NetworkEnricher
            self._enricher = NetworkEnricher(self._graph)
        return self._enricher

    @property
    def scorer(self):
        """Lazy-load the CredibilityScorer."""
        if self._scorer is None:
            from .credibility_scorer import CredibilityScorer
            self._scorer = CredibilityScorer(self._graph)
        return self._scorer

    @property
    def position_calculator(self):
        """Lazy-load the PositionCalculator."""
        if self._position_calc is None:
            from .position_calculator import PositionCalculator
            self._position_calc = PositionCalculator(self._graph)
        return self._position_calc

    # -- Core Operations -----------------------------------------------------

    def ingest(self, work_id: str) -> IngestResult:
        """
        Ingest a single paper into the knowledge graph.

        This triggers the full organic enrichment pipeline:
        1. EXTRACT: Parse references and citation contexts from the adapter
        2. IDENTIFY: Match references to existing graph nodes (or create new)
        3. ENRICH: Add NetworkCitation vectors, update edges
        4. POSITION: Mark affected nodes for recalculation
        5. CONNECT: Update ConceptEvolution if needed
        6. PROPAGATE: Bidirectional enrichment

        Args:
            work_id: The identifier of the work to ingest.

        Returns:
            IngestResult with counts of affected nodes/edges.
        """
        import time
        start = time.monotonic()
        result = IngestResult()

        if self._adapter is None:
            result.errors.append("No data source adapter configured")
            return result

        try:
            # Get the work profile from the adapter
            profile = self._adapter.get_profile(work_id)
            if profile is None:
                result.errors.append(f"Work not found in adapter: {work_id}")
                return result

            # Step 1: Add the work node itself
            node_data = self._extract_work_node(work_id, profile)
            is_new = self._graph.get_node(work_id) is None
            self._graph.add_node(work_id, **node_data)
            if is_new:
                result.new_nodes += 1

            # Step 2: Get citations from the adapter
            citations = self._adapter.get_citations(work_id)

            # Step 3-6: Run the enrichment pipeline
            enrich_result = self.enricher.enrich(work_id, profile, citations)
            result.enriched_nodes += enrich_result.get("enriched_nodes", 0)
            result.new_edges += enrich_result.get("new_edges", 0)
            result.new_nodes += enrich_result.get("new_nodes", 0)
            result.errors.extend(enrich_result.get("errors", []))

            # Graph changed -> invalidate cached topology calculations
            if self._position_calc is not None:
                self._position_calc.invalidate_cache()

            result.ingested_count = 1

            # Auto-save if configured
            if self._auto_save and self._graph_path:
                self._graph.save_json(self._graph_path)

            result.duration_ms = (time.monotonic() - start) * 1000
            logger.info(
                "Ingested %s: +%d nodes, +%d edges, %d enriched (%.1fms)",
                work_id, result.new_nodes, result.new_edges,
                result.enriched_nodes, result.duration_ms,
            )

        except Exception as e:
            logger.error("Failed to ingest %s: %s", work_id, e, exc_info=True)
            result.errors.append(f"Ingest error for {work_id}: {str(e)}")
            result.duration_ms = (time.monotonic() - start) * 1000

        return result

    def ingest_all(self) -> IngestResult:
        """
        Ingest all works from the configured adapter.

        Returns:
            Aggregated IngestResult.
        """
        import time
        start = time.monotonic()
        total_result = IngestResult()

        if self._adapter is None:
            total_result.errors.append("No data source adapter configured")
            return total_result

        works = self._adapter.list_works()
        logger.info("Ingesting %d works from adapter", len(works))

        for work in works:
            work_id = work.get("id", "")
            if not work_id:
                total_result.errors.append(f"Work missing id: {work}")
                continue

            result = self.ingest(work_id)
            total_result.ingested_count += result.ingested_count
            total_result.enriched_nodes += result.enriched_nodes
            total_result.new_edges += result.new_edges
            total_result.new_nodes += result.new_nodes
            total_result.errors.extend(result.errors)

        total_result.duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "Bulk ingest complete: %d works, +%d nodes, +%d edges (%.1fs)",
            total_result.ingested_count, total_result.new_nodes,
            total_result.new_edges, total_result.duration_ms / 1000,
        )

        return total_result

    # -- Query Operations ----------------------------------------------------

    def get_node(self, node_id: str) -> Optional[NetworkKnowledge]:
        """
        Get a node with its full network knowledge.

        Args:
            node_id: The node identifier.

        Returns:
            NetworkKnowledge object or None if node doesn't exist.
        """
        node_data = self._graph.get_node(node_id)
        if node_data is None:
            return None

        nk = NetworkKnowledge(work_id=node_id)
        nk.direct_knowledge = node_data

        # Gather network citations
        nk.network_citations = node_data.get("network_citations", [])

        # Calculate credibility
        try:
            nk.network_credibility = self.scorer.calculate_credibility(node_id)
        except Exception as e:
            logger.warning("Credibility calc failed for %s: %s", node_id, e)

        # Gather cross-perspectives
        nk.cross_perspectives = node_data.get("cross_perspectives", [])

        # Calculate position
        try:
            nk.relative_position = self.position_calculator.get_relative_position(node_id)
        except Exception as e:
            logger.warning("Position calc failed for %s: %s", node_id, e)

        # Concept evolution
        nk.concept_evolution = node_data.get("concept_evolution", [])

        return nk

    def get_neighborhood(self, node_id: str, hops: int = 2, max_nodes: int = 500) -> Dict[str, Any]:
        """
        Get the ego network around a node.

        Args:
            node_id: Center node.
            hops: Number of hops (default 2).
            max_nodes: Maximum number of nodes to return.

        Returns:
            Dict with 'nodes' and 'edges' suitable for Cytoscape.js rendering.
        """
        return self._graph.get_neighborhood(node_id, hops=hops, max_nodes=max_nodes)

    def search(self, query: str, node_type: Optional[str] = None, top_k: int = 20) -> QueryResult:
        """
        Search the knowledge graph.

        Combines graph-based text search with adapter semantic search.

        Args:
            query: Search query string.
            node_type: Filter by node type (Work, Concept, Author, etc.)
            top_k: Maximum results.

        Returns:
            QueryResult with matching nodes.
        """
        qr = QueryResult(query=query)

        # Graph text search
        graph_results = self._graph.search_nodes(query, node_type=node_type)

        # Adapter semantic search (if available)
        adapter_results = []
        if self._adapter is not None:
            try:
                adapter_results = self._adapter.search(query, top_k=top_k)
            except Exception as e:
                logger.warning("Adapter search failed: %s", e)

        # Merge and deduplicate
        seen = set()
        merged = []
        for r in graph_results:
            rid = r.get("id", "")
            if rid not in seen:
                seen.add(rid)
                r["source"] = "graph"
                merged.append(r)

        for r in adapter_results:
            rid = r.get("work_id", r.get("id", ""))
            if rid not in seen:
                seen.add(rid)
                r["source"] = "adapter"
                merged.append(r)

        qr.results = merged[:top_k]
        qr.total = len(merged)
        qr.source = "hybrid" if adapter_results else "graph"

        return qr

    def get_credibility(self, work_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the network credibility report for a work.

        Args:
            work_id: The work identifier.

        Returns:
            Credibility report dict or None.
        """
        if self._graph.get_node(work_id) is None:
            return None
        return self.scorer.calculate_credibility(work_id)

    def compare(self, node_a: str, node_b: str) -> CompareResult:
        """
        Compare two nodes in the knowledge graph.

        Identifies shared citations, shared concepts, divergent edges,
        shortest path, and similarity score.

        Args:
            node_a: First node id.
            node_b: Second node id.

        Returns:
            CompareResult with detailed comparison.
        """
        result = CompareResult(node_a=node_a, node_b=node_b)

        # Get neighbors for both
        neighbors_a = set(self._graph.get_neighbors(node_a, direction="both"))
        neighbors_b = set(self._graph.get_neighbors(node_b, direction="both"))

        # Shared citations (works cited by both)
        cited_a = set(self._graph.get_cited_works(node_a))
        cited_b = set(self._graph.get_cited_works(node_b))
        result.shared_citations = list(cited_a & cited_b)

        # Shared concepts
        concepts_a = {
            n for n in neighbors_a
            if (self._graph.get_node(n) or {}).get("node_type") == "Concept"
        }
        concepts_b = {
            n for n in neighbors_b
            if (self._graph.get_node(n) or {}).get("node_type") == "Concept"
        }
        result.shared_concepts = list(concepts_a & concepts_b)

        # Divergent edges
        unique_a = neighbors_a - neighbors_b
        unique_b = neighbors_b - neighbors_a
        result.divergent_edges_a = [
            {"node": n, "type": (self._graph.get_node(n) or {}).get("node_type", "Unknown")}
            for n in list(unique_a)[:20]
        ]
        result.divergent_edges_b = [
            {"node": n, "type": (self._graph.get_node(n) or {}).get("node_type", "Unknown")}
            for n in list(unique_b)[:20]
        ]

        # Shortest path
        try:
            import networkx as nx
            path = nx.shortest_path(self._graph._graph.to_undirected(), node_a, node_b)
            result.shortest_path = path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            result.shortest_path = None

        # Similarity score (Jaccard on neighbor sets)
        union = neighbors_a | neighbors_b
        if union:
            intersection = neighbors_a & neighbors_b
            result.similarity_score = round(len(intersection) / len(union), 4)

        return result

    # -- Export Operations ---------------------------------------------------

    def export_graph(self, format: str = "cytoscape") -> Dict[str, Any]:
        """
        Export the entire graph in the specified format.

        Args:
            format: Export format — 'cytoscape', 'json', or 'bibtex'.

        Returns:
            Dict containing the exported graph data.
        """
        if format == "cytoscape":
            return self._export_cytoscape()
        elif format == "json":
            return self._graph.to_dict()
        elif format == "bibtex":
            return self._export_bibtex()
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the knowledge graph.

        Returns:
            Dict with node counts, edge counts, type distributions, etc.
        """
        stats = self._graph.get_stats()

        # Add enrichment stats
        total_network_citations = 0
        nodes_with_credibility = 0
        for node_id in self._graph.get_all_node_ids():
            node = self._graph.get_node(node_id)
            if node:
                nc = node.get("network_citations", [])
                total_network_citations += len(nc)
                if node.get("network_credibility"):
                    nodes_with_credibility += 1

        stats["total_network_citations"] = total_network_citations
        stats["nodes_with_credibility"] = nodes_with_credibility

        return stats

    # -- Persistence ---------------------------------------------------------

    def save(self, path: Optional[Union[str, Path]] = None):
        """Save the graph to disk."""
        save_path = Path(path) if path else self._graph_path
        if save_path is None:
            raise ValueError("No graph path configured and none provided")
        self._graph.save_json(save_path)
        logger.info("Graph saved to %s", save_path)

    def load(self, path: Optional[Union[str, Path]] = None):
        """Load the graph from disk."""
        load_path = Path(path) if path else self._graph_path
        if load_path is None:
            raise ValueError("No graph path configured and none provided")
        self._graph.load_json(load_path)
        logger.info("Graph loaded from %s (%d nodes, %d edges)",
                     load_path, self._graph.node_count, self._graph.edge_count)

    # -- Private Helpers -----------------------------------------------------

    def _extract_work_node(self, work_id: str, profile: dict) -> dict:
        """Extract work node attributes from a profile dict."""
        return {
            "node_type": "Work",
            "title": profile.get("title", ""),
            "authors": profile.get("authors", []),
            "year": profile.get("year"),
            "doi": profile.get("doi", ""),
            "type": profile.get("type", "paper"),
            "full_article": profile.get("full_article", False),
            "abstract": profile.get("abstract", ""),
            "added_at": datetime.now(timezone.utc).isoformat(),
            "network_citations": [],
            "cross_perspectives": [],
            "concept_evolution": [],
        }

    def _export_cytoscape(self) -> Dict[str, Any]:
        """Export graph in Cytoscape.js compatible format."""
        nodes = []
        edges = []

        for node_id in self._graph.get_all_node_ids():
            node_data = self._graph.get_node(node_id) or {}
            nodes.append({
                "data": {
                    "id": node_id,
                    "label": node_data.get("title", node_data.get("name", node_id)),
                    "type": node_data.get("node_type", "Unknown"),
                    **{k: v for k, v in node_data.items()
                       if k not in ("network_citations", "cross_perspectives",
                                    "concept_evolution", "network_credibility")
                       and isinstance(v, (str, int, float, bool))},
                }
            })

        for u, v, edge_data in self._graph.get_all_edges():
            edges.append({
                "data": {
                    "id": f"{u}->{v}",
                    "source": u,
                    "target": v,
                    "type": edge_data.get("edge_type", "UNKNOWN"),
                    "label": edge_data.get("label", ""),
                    **{k: v_ for k, v_ in edge_data.items()
                       if k not in ("edge_type", "label")
                       and isinstance(v_, (str, int, float, bool))},
                }
            })

        return {
            "format": "cytoscape",
            "elements": {"nodes": nodes, "edges": edges},
            "stats": self._graph.get_stats(),
        }

    def _export_bibtex(self) -> Dict[str, Any]:
        """Export Work nodes as BibTeX entries."""
        entries = []
        for node_id in self._graph.get_all_node_ids():
            node = self._graph.get_node(node_id)
            if node and node.get("node_type") == "Work":
                authors = node.get("authors", [])
                author_str = " and ".join(authors) if isinstance(authors, list) else str(authors)
                year = node.get("year", "")
                title = node.get("title", "")
                doi = node.get("doi", "")

                # Generate BibTeX key
                first_author = authors[0].split(",")[0].split()[-1] if authors else "unknown"
                bib_key = f"{first_author.lower()}{year}"

                entry = (
                    f"@article{{{bib_key},\n"
                    f"  author = {{{author_str}}},\n"
                    f"  title = {{{title}}},\n"
                    f"  year = {{{year}}},\n"
                )
                if doi:
                    entry += f"  doi = {{{doi}}},\n"
                entry += "}\n"
                entries.append(entry)

        return {
            "format": "bibtex",
            "content": "\n".join(entries),
            "count": len(entries),
        }
