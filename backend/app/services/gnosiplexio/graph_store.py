"""
Gnosiplexio Graph Store — NetworkX-based graph storage with JSON persistence.

Manages the knowledge graph with typed nodes (Work, Concept, Author, Domain, Method)
and typed edges (CITES, CITED_FOR, ARGUES, EXTENDS, CHALLENGES, etc.).

Supports:
- CRUD operations on nodes and edges
- Neighborhood queries (ego networks)
- Text search across node properties
- JSON serialization/deserialization
- Cytoscape.js compatible export
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Union

import networkx as nx

logger = logging.getLogger("gnosiplexio.graph_store")

# Valid node and edge types
NODE_TYPES = {"Work", "Concept", "Author", "Domain", "Method"}
EDGE_TYPES = {
    "CITES", "CITED_FOR", "ARGUES", "EXTENDS", "CHALLENGES",
    "DEFINES", "APPLIES", "AUTHORED_BY", "BELONGS_TO", "NOT_FOR",
}


class GraphStore:
    """
    NetworkX-based graph store for the Gnosiplexio knowledge graph.

    All node and edge attributes are stored in the NetworkX DiGraph.
    Persistence is via JSON serialization.
    """

    def __init__(self):
        """Initialize an empty directed graph."""
        self._graph = nx.DiGraph()

    # -- Properties ----------------------------------------------------------

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        """Number of edges in the graph."""
        return self._graph.number_of_edges()

    # -- Node Operations -----------------------------------------------------

    def add_node(self, node_id: str, **attrs) -> None:
        """
        Add or update a node in the graph.

        Args:
            node_id: Unique identifier for the node.
            **attrs: Node attributes (must include 'node_type').
        """
        if "node_type" in attrs and attrs["node_type"] not in NODE_TYPES:
            logger.warning("Unknown node_type '%s' for node '%s'", attrs["node_type"], node_id)

        if self._graph.has_node(node_id):
            # Update existing node attributes (merge, don't overwrite lists blindly)
            existing = self._graph.nodes[node_id]
            for k, v in attrs.items():
                if isinstance(v, list) and isinstance(existing.get(k), list):
                    # For list attributes like network_citations, extend rather than replace
                    if k in ("network_citations", "cross_perspectives", "concept_evolution"):
                        existing[k].extend(v)
                    else:
                        existing[k] = v
                else:
                    existing[k] = v
        else:
            self._graph.add_node(node_id, **attrs)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node's attributes.

        Args:
            node_id: Node identifier.

        Returns:
            Dict of node attributes, or None if not found.
        """
        if not self._graph.has_node(node_id):
            return None
        return dict(self._graph.nodes[node_id])

    def remove_node(self, node_id: str) -> bool:
        """
        Remove a node and all its edges.

        Args:
            node_id: Node identifier.

        Returns:
            True if removed, False if not found.
        """
        if not self._graph.has_node(node_id):
            return False
        self._graph.remove_node(node_id)
        return True

    def has_node(self, node_id: str) -> bool:
        """Check if a node exists."""
        return self._graph.has_node(node_id)

    def get_all_node_ids(self) -> List[str]:
        """Get all node identifiers."""
        return list(self._graph.nodes())

    def get_nodes_by_type(self, node_type: str) -> List[str]:
        """
        Get all node IDs of a specific type.

        Args:
            node_type: One of Work, Concept, Author, Domain, Method.

        Returns:
            List of node IDs matching the type.
        """
        return [
            n for n, d in self._graph.nodes(data=True)
            if d.get("node_type") == node_type
        ]

    # -- Edge Operations -----------------------------------------------------

    def add_edge(self, source: str, target: str, edge_type: str, **attrs) -> None:
        """
        Add or update an edge in the graph.

        Args:
            source: Source node ID.
            target: Target node ID.
            edge_type: Type of edge (e.g., CITES, CITED_FOR, EXTENDS).
            **attrs: Additional edge attributes.
        """
        if edge_type not in EDGE_TYPES:
            logger.warning("Unknown edge_type '%s' for edge %s -> %s", edge_type, source, target)

        # Auto-create placeholder nodes if they don't exist
        if not self._graph.has_node(source):
            self._graph.add_node(source, node_type="Work", _placeholder=True)
        if not self._graph.has_node(target):
            self._graph.add_node(target, node_type="Work", _placeholder=True)

        attrs["edge_type"] = edge_type
        self._graph.add_edge(source, target, **attrs)

    def get_edge(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        """
        Get edge attributes between two nodes.

        Args:
            source: Source node ID.
            target: Target node ID.

        Returns:
            Dict of edge attributes, or None.
        """
        if not self._graph.has_edge(source, target):
            return None
        return dict(self._graph.edges[source, target])

    def get_all_edges(self) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Get all edges with their attributes."""
        return [(u, v, dict(d)) for u, v, d in self._graph.edges(data=True)]

    def get_edges_by_type(self, edge_type: str) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Get all edges of a specific type."""
        return [
            (u, v, dict(d))
            for u, v, d in self._graph.edges(data=True)
            if d.get("edge_type") == edge_type
        ]

    # -- Neighbor Queries ----------------------------------------------------

    def get_neighbors(self, node_id: str, direction: str = "both") -> List[str]:
        """
        Get neighboring node IDs.

        Args:
            node_id: Node identifier.
            direction: 'in', 'out', or 'both'.

        Returns:
            List of neighbor node IDs.
        """
        if not self._graph.has_node(node_id):
            return []

        if direction == "out":
            return list(self._graph.successors(node_id))
        elif direction == "in":
            return list(self._graph.predecessors(node_id))
        else:
            out_set = set(self._graph.successors(node_id))
            in_set = set(self._graph.predecessors(node_id))
            return list(out_set | in_set)

    def get_citing_works(self, work_id: str) -> List[str]:
        """
        Get works that cite the given work (incoming CITES edges).

        Args:
            work_id: The cited work's ID.

        Returns:
            List of citing work IDs.
        """
        return [
            u for u in self._graph.predecessors(work_id)
            if self._graph.edges[u, work_id].get("edge_type") in ("CITES", "CITED_FOR", "EXTENDS", "CHALLENGES")
        ]

    def get_cited_works(self, work_id: str) -> List[str]:
        """
        Get works cited by the given work (outgoing CITES edges).

        Args:
            work_id: The citing work's ID.

        Returns:
            List of cited work IDs.
        """
        return [
            v for v in self._graph.successors(work_id)
            if self._graph.edges[work_id, v].get("edge_type") in ("CITES", "CITED_FOR", "EXTENDS", "CHALLENGES")
        ]

    def get_neighborhood(self, node_id: str, hops: int = 2) -> Dict[str, Any]:
        """
        Get the ego network (neighborhood) around a node.

        Args:
            node_id: Center node.
            hops: Number of hops (default 2).

        Returns:
            Dict with 'nodes' and 'edges' for the subgraph.
        """
        if not self._graph.has_node(node_id):
            return {"nodes": [], "edges": [], "center": node_id, "hops": hops}

        # Get all nodes within N hops
        ego = nx.ego_graph(self._graph.to_undirected(), node_id, radius=hops)
        ego_nodes = set(ego.nodes())

        nodes = []
        for n in ego_nodes:
            node_data = dict(self._graph.nodes[n])
            # Remove large list attributes for lighter export
            compact = {
                k: v for k, v in node_data.items()
                if k not in ("network_citations", "cross_perspectives", "concept_evolution")
                or not isinstance(v, list) or len(v) <= 5
            }
            compact["id"] = n
            nodes.append(compact)

        edges = []
        for u, v, d in self._graph.edges(data=True):
            if u in ego_nodes and v in ego_nodes:
                edge_data = dict(d)
                edge_data["source"] = u
                edge_data["target"] = v
                edges.append(edge_data)

        return {
            "center": node_id,
            "hops": hops,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    # -- Search --------------------------------------------------------------

    def search_nodes(self, query: str, node_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Simple text search across node properties.

        Searches title, name, abstract, and definition fields.

        Args:
            query: Search string (case-insensitive).
            node_type: Optional filter by node type.

        Returns:
            List of matching nodes with their attributes.
        """
        query_lower = query.lower()
        results = []

        for node_id, data in self._graph.nodes(data=True):
            if node_type and data.get("node_type") != node_type:
                continue

            # Search across key text fields
            searchable = " ".join(str(v) for k, v in data.items()
                                  if k in ("title", "name", "abstract", "definition",
                                           "description", "cited_for")
                                  and isinstance(v, str))

            if query_lower in searchable.lower():
                result = dict(data)
                result["id"] = node_id
                results.append(result)

        return results

    # -- Statistics ----------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive graph statistics.

        Returns:
            Dict with node counts, edge counts, type distributions.
        """
        node_types = Counter(
            d.get("node_type", "Unknown")
            for _, d in self._graph.nodes(data=True)
        )
        edge_types = Counter(
            d.get("edge_type", "Unknown")
            for _, _, d in self._graph.edges(data=True)
        )

        # Calculate density and components
        undirected = self._graph.to_undirected()
        components = list(nx.connected_components(undirected))

        return {
            "total_nodes": self.node_count,
            "total_edges": self.edge_count,
            "node_types": dict(node_types),
            "edge_types": dict(edge_types),
            "connected_components": len(components),
            "largest_component_size": max(len(c) for c in components) if components else 0,
            "density": nx.density(self._graph) if self.node_count > 1 else 0.0,
        }

    # -- Persistence (JSON) --------------------------------------------------

    def save_json(self, path: Union[str, Path]) -> None:
        """
        Save the graph to a JSON file.

        Args:
            path: File path for the JSON output.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = self.to_dict()

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.info("Graph saved to %s (%d nodes, %d edges)", path, self.node_count, self.edge_count)

    def load_json(self, path: Union[str, Path]) -> None:
        """
        Load the graph from a JSON file.

        Args:
            path: File path to the JSON input.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Graph file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.from_dict(data)
        logger.info("Graph loaded from %s (%d nodes, %d edges)", path, self.node_count, self.edge_count)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the graph to a dict.

        Returns:
            Dict with 'nodes' and 'edges' arrays.
        """
        nodes = []
        for node_id, attrs in self._graph.nodes(data=True):
            node = {"id": node_id}
            node.update(attrs)
            nodes.append(node)

        edges = []
        for u, v, attrs in self._graph.edges(data=True):
            edge = {"source": u, "target": v}
            edge.update(attrs)
            edges.append(edge)

        return {
            "version": "gnosiplexio-2.0",
            "nodes": nodes,
            "edges": edges,
            "stats": self.get_stats(),
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Deserialize the graph from a dict.

        Args:
            data: Dict with 'nodes' and 'edges' arrays.
        """
        self._graph.clear()

        for node in data.get("nodes", []):
            node_id = node.pop("id")
            self._graph.add_node(node_id, **node)

        for edge in data.get("edges", []):
            source = edge.pop("source")
            target = edge.pop("target")
            self._graph.add_edge(source, target, **edge)

    # -- Internal ------------------------------------------------------------

    def __repr__(self) -> str:
        return f"GraphStore(nodes={self.node_count}, edges={self.edge_count})"
