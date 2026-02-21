"""
Gnosiplexio Network Enricher — Organic enrichment pipeline.

Implements the 6-step enrichment process that makes the knowledge graph
grow organically with each new paper:

1. EXTRACT: Parse references and citation contexts
2. IDENTIFY: Match references to existing graph nodes (or create new)
3. ENRICH: Add NetworkCitation vectors, update edges
4. POSITION: Mark affected nodes for recalculation
5. CONNECT: Update ConceptEvolution if concept usage has shifted
6. PROPAGATE: Bidirectional enrichment
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("gnosiplexio.network_enricher")


@dataclass
class NetworkCitation:
    """What a citing paper says about a cited work."""
    target_work_id: str
    citing_work_id: str
    citation_context: str
    cited_for: str
    sentiment: str = "supportive"  # supportive | critical | neutral | extends
    credibility_weight: float = 0.5
    extracted_at: str = ""
    source_type: str = "direct"  # direct | inferred

    def __post_init__(self):
        if not self.extracted_at:
            self.extracted_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CrossPerspective:
    """A perspective on a work from outside (critic, extension, novel use)."""
    work_id: str
    source_work_id: str
    perspective_type: str  # criticism | extension | novel_application | replication
    description: str
    extracted_at: str = ""

    def __post_init__(self):
        if not self.extracted_at:
            self.extracted_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


class NetworkEnricher:
    """
    Organic enrichment pipeline for the Gnosiplexio knowledge graph.

    When a new paper is ingested, this enricher runs 6 steps to
    propagate knowledge through the entire network.
    """

    def __init__(self, graph_store):
        """
        Initialize with a GraphStore reference.

        Args:
            graph_store: The GraphStore instance to enrich.
        """
        self._graph = graph_store

    def enrich(
        self,
        work_id: str,
        profile: Dict[str, Any],
        citations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Run the full 6-step enrichment pipeline for a newly ingested work.

        Args:
            work_id: The ID of the newly ingested work.
            profile: The work's profile data.
            citations: Citation relationships from the adapter.

        Returns:
            Dict with enrichment statistics.
        """
        result = {
            "enriched_nodes": 0,
            "new_edges": 0,
            "new_nodes": 0,
            "errors": [],
        }

        # Step 1: EXTRACT — citations already provided by adapter
        logger.info("EXTRACT: %d citations for %s", len(citations), work_id)

        # Step 2: IDENTIFY — match or create nodes for each reference
        for citation in citations:
            try:
                cited_id = citation.get("cited_id", "")
                if not cited_id:
                    continue

                is_new_node = not self._graph.has_node(cited_id)
                if is_new_node:
                    # Create placeholder node for the cited work
                    self._graph.add_node(cited_id, node_type="Work", _placeholder=True)
                    result["new_nodes"] += 1

                # Step 3: ENRICH — add NetworkCitation + edges
                self._enrich_citation(work_id, citation)
                result["enriched_nodes"] += 1

                # Add citation edge
                edge_type = self._determine_edge_type(citation)
                if not self._graph.get_edge(work_id, cited_id):
                    self._graph.add_edge(
                        work_id, cited_id,
                        edge_type=edge_type,
                        cited_for=citation.get("cited_for", ""),
                        context=citation.get("context", ""),
                        sentiment=citation.get("sentiment", "supportive"),
                    )
                    result["new_edges"] += 1

            except Exception as e:
                err_msg = f"Error enriching citation {work_id} -> {citation.get('cited_id', '?')}: {e}"
                logger.error(err_msg)
                result["errors"].append(err_msg)

        # Step 4: POSITION — mark affected nodes (deferred to position_calculator)
        # (Position recalculation is expensive, so we just mark nodes as dirty)

        # Step 5: CONNECT — extract concepts and create concept nodes/edges
        self._extract_concepts(work_id, profile)

        # Step 6: PROPAGATE — bidirectional enrichment
        propagated = self._propagate(work_id)
        result["enriched_nodes"] += propagated

        logger.info(
            "Enrichment complete for %s: +%d nodes, +%d edges, %d enriched",
            work_id, result["new_nodes"], result["new_edges"], result["enriched_nodes"],
        )

        return result

    def _enrich_citation(self, citing_id: str, citation: Dict[str, Any]) -> None:
        """Add a NetworkCitation vector to the cited work's node."""
        cited_id = citation.get("cited_id", "")
        if not cited_id:
            return

        nc = NetworkCitation(
            target_work_id=cited_id,
            citing_work_id=citing_id,
            citation_context=citation.get("context", ""),
            cited_for=citation.get("cited_for", ""),
            sentiment=citation.get("sentiment", "supportive"),
            credibility_weight=citation.get("credibility_weight", 0.5),
            source_type=citation.get("source_type", "direct"),
        )

        # Add to the cited node's network_citations list
        node = self._graph.get_node(cited_id)
        if node is not None:
            existing = node.get("network_citations", [])
            # Avoid duplicate citations from the same citing paper
            if not any(
                nc_dict.get("citing_work_id") == citing_id
                for nc_dict in existing
            ):
                existing.append(nc.to_dict())
                # Use direct graph attribute update to avoid list-extend duplication
                self._graph._graph.nodes[cited_id]["network_citations"] = existing

        # Add CrossPerspective if sentiment is critical or extends
        if citation.get("sentiment") in ("critical", "extends"):
            perspective_type = "criticism" if citation["sentiment"] == "critical" else "extension"
            cp = CrossPerspective(
                work_id=cited_id,
                source_work_id=citing_id,
                perspective_type=perspective_type,
                description=citation.get("context", ""),
            )
            node = self._graph.get_node(cited_id)
            if node is not None:
                existing_cp = node.get("cross_perspectives", [])
                cp_dict = cp.to_dict()
                duplicate = any(
                    p.get("source_work_id") == cp_dict.get("source_work_id")
                    and p.get("perspective_type") == cp_dict.get("perspective_type")
                    and p.get("description", "") == cp_dict.get("description", "")
                    for p in existing_cp
                )
                if not duplicate:
                    existing_cp.append(cp_dict)
                    self._graph.add_node(cited_id, cross_perspectives=existing_cp)

    def _determine_edge_type(self, citation: Dict[str, Any]) -> str:
        """Determine the edge type based on citation sentiment and context."""
        sentiment = citation.get("sentiment", "supportive")
        cited_for = citation.get("cited_for", "").lower()

        if sentiment == "critical":
            return "CHALLENGES"
        elif sentiment == "extends":
            return "EXTENDS"
        elif "define" in cited_for or "concept" in cited_for:
            return "CITED_FOR"
        else:
            return "CITES"

    def _extract_concepts(self, work_id: str, profile: Dict[str, Any]) -> None:
        """Extract concepts from the work profile and create Concept nodes."""
        # Extract key concepts from profile
        concepts = profile.get("key_concepts", [])
        if isinstance(concepts, str):
            concepts = [c.strip() for c in concepts.split(",") if c.strip()]

        for concept_name in concepts:
            concept_id = f"concept:{concept_name.lower().replace(' ', '_')}"
            if not self._graph.has_node(concept_id):
                self._graph.add_node(
                    concept_id,
                    node_type="Concept",
                    name=concept_name,
                )

            # Add ARGUES edge
            if not self._graph.get_edge(work_id, concept_id):
                self._graph.add_edge(work_id, concept_id, edge_type="ARGUES")

        # Extract authors and create Author nodes
        authors = profile.get("authors", [])
        if isinstance(authors, list):
            for author_name in authors:
                author_id = f"author:{author_name.lower().replace(' ', '_').replace(',', '')}"
                if not self._graph.has_node(author_id):
                    self._graph.add_node(
                        author_id,
                        node_type="Author",
                        name=author_name,
                    )
                if not self._graph.get_edge(work_id, author_id):
                    self._graph.add_edge(work_id, author_id, edge_type="AUTHORED_BY")

        # Extract method if available
        method = profile.get("method", profile.get("methodology", ""))
        if method:
            method_id = f"method:{method.lower().replace(' ', '_')}"
            if not self._graph.has_node(method_id):
                self._graph.add_node(
                    method_id,
                    node_type="Method",
                    name=method,
                )
            if not self._graph.get_edge(work_id, method_id):
                self._graph.add_edge(work_id, method_id, edge_type="APPLIES")

    def _propagate(self, work_id: str) -> int:
        """
        Bidirectional enrichment: if the newly added work is already cited
        by other works in the graph, update those edges too.

        Returns the number of nodes enriched via propagation.
        """
        enriched = 0

        # Check if any existing works in the graph cite this new work
        citing_works = self._graph.get_citing_works(work_id)
        for citing_id in citing_works:
            edge = self._graph.get_edge(citing_id, work_id)
            if edge and edge.get("_propagated"):
                continue  # Already propagated

            # Mark the edge as propagated
            self._graph.add_edge(
                citing_id, work_id,
                edge_type=edge.get("edge_type", "CITES") if edge else "CITES",
                _propagated=True,
            )
            enriched += 1

        return enriched
