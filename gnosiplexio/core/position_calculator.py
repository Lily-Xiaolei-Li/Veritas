"""
Gnosiplexio Position Calculator — Graph topology analysis.

Calculates centrality metrics, community structure, and relative positioning
of nodes in the knowledge graph. Uses NetworkX algorithms.

Metrics:
- Betweenness centrality — papers that bridge research clusters
- PageRank — most influential papers
- Community detection — research clusters and subfields
- Temporal analysis — how the network evolved over time
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

import networkx as nx

logger = logging.getLogger("gnosiplexio.position_calculator")


class PositionCalculator:
    """
    Calculates topological properties of nodes in the knowledge graph.

    Provides centrality metrics, community detection, and relative
    positioning that updates as the graph grows.
    """

    def __init__(self, graph_store):
        """
        Initialize with a GraphStore reference.

        Args:
            graph_store: The GraphStore instance to analyze.
        """
        self._graph_store = graph_store
        self._cached_centrality: Optional[Dict[str, float]] = None
        self._cached_pagerank: Optional[Dict[str, float]] = None
        self._cached_communities: Optional[Dict[str, int]] = None
        self._cache_valid = False

    def invalidate_cache(self):
        """Invalidate cached calculations (call after graph changes)."""
        self._cache_valid = False
        self._cached_centrality = None
        self._cached_pagerank = None
        self._cached_communities = None

    # -- Centrality ----------------------------------------------------------

    def calculate_centrality(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate multiple centrality metrics for all nodes.

        Returns:
            Dict mapping node_id to {betweenness, pagerank, degree, in_degree, out_degree}.
        """
        G = self._graph_store._graph

        if G.number_of_nodes() == 0:
            return {}

        # Betweenness centrality
        try:
            betweenness = nx.betweenness_centrality(G)
        except Exception:
            betweenness = {n: 0.0 for n in G.nodes()}

        # PageRank
        try:
            pagerank = nx.pagerank(G, max_iter=100)
        except Exception:
            pagerank = {n: 1.0 / G.number_of_nodes() for n in G.nodes()}

        # Degree centrality
        degree = dict(G.degree())
        in_degree = dict(G.in_degree())
        out_degree = dict(G.out_degree())

        results = {}
        for node_id in G.nodes():
            results[node_id] = {
                "betweenness": round(betweenness.get(node_id, 0.0), 6),
                "pagerank": round(pagerank.get(node_id, 0.0), 6),
                "degree": degree.get(node_id, 0),
                "in_degree": in_degree.get(node_id, 0),
                "out_degree": out_degree.get(node_id, 0),
            }

        self._cached_centrality = betweenness
        self._cached_pagerank = pagerank
        self._cache_valid = True

        return results

    # -- Community Detection -------------------------------------------------

    def detect_communities(self) -> Dict[str, Any]:
        """
        Detect research communities/clusters in the graph.

        Uses the Louvain algorithm on the undirected version of the graph.

        Returns:
            Dict with community assignments and statistics.
        """
        G = self._graph_store._graph

        if G.number_of_nodes() == 0:
            return {"communities": {}, "num_communities": 0, "modularity": 0.0}

        undirected = G.to_undirected()

        try:
            # Use greedy modularity communities (available in base NetworkX)
            communities_gen = nx.community.greedy_modularity_communities(undirected)
            communities_list = list(communities_gen)

            # Build node -> community mapping
            node_community = {}
            for idx, community in enumerate(communities_list):
                for node in community:
                    node_community[node] = idx

            # Calculate modularity
            try:
                modularity = nx.community.modularity(undirected, communities_list)
            except Exception:
                modularity = 0.0

            # Community statistics
            community_stats = []
            for idx, community in enumerate(communities_list):
                nodes_in_community = list(community)
                community_stats.append({
                    "id": idx,
                    "size": len(nodes_in_community),
                    "members": nodes_in_community[:10],  # First 10 for preview
                })

            self._cached_communities = node_community

            return {
                "communities": node_community,
                "num_communities": len(communities_list),
                "modularity": round(modularity, 4),
                "community_details": community_stats,
            }

        except Exception as e:
            logger.warning("Community detection failed: %s", e)
            return {"communities": {}, "num_communities": 0, "modularity": 0.0, "error": str(e)}

    # -- Relative Position ---------------------------------------------------

    def get_relative_position(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Determine a node's relative position in the network.

        Categories:
        - central: High betweenness + high PageRank
        - bridge: High betweenness but lower PageRank (connects clusters)
        - peripheral: Low centrality metrics
        - hub: High degree (many connections)
        - isolated: No or very few connections

        Args:
            node_id: Node identifier.

        Returns:
            Position analysis dict, or None if node doesn't exist.
        """
        if not self._graph_store.has_node(node_id):
            return None

        # Ensure centrality is calculated
        if not self._cache_valid:
            self.calculate_centrality()

        G = self._graph_store._graph
        n_nodes = G.number_of_nodes()

        if n_nodes <= 1:
            return {
                "node_id": node_id,
                "position": "isolated",
                "betweenness": 0.0,
                "pagerank": 1.0,
                "degree": 0,
            }

        betweenness = self._cached_centrality.get(node_id, 0.0) if self._cached_centrality else 0.0
        pagerank = self._cached_pagerank.get(node_id, 0.0) if self._cached_pagerank else 0.0
        degree = G.degree(node_id)
        in_degree = G.in_degree(node_id)
        out_degree = G.out_degree(node_id)

        # Determine position category
        avg_betweenness = sum(self._cached_centrality.values()) / n_nodes if self._cached_centrality else 0.0
        avg_pagerank = 1.0 / n_nodes

        if degree == 0:
            position = "isolated"
        elif betweenness > avg_betweenness * 2 and pagerank > avg_pagerank * 1.5:
            position = "central"
        elif betweenness > avg_betweenness * 2:
            position = "bridge"
        elif degree > n_nodes * 0.1:
            position = "hub"
        elif betweenness < avg_betweenness * 0.5 and pagerank < avg_pagerank * 0.5:
            position = "peripheral"
        else:
            position = "standard"

        # Get community if available
        community = None
        if self._cached_communities:
            community = self._cached_communities.get(node_id)

        return {
            "node_id": node_id,
            "position": position,
            "betweenness": round(betweenness, 6),
            "pagerank": round(pagerank, 6),
            "degree": degree,
            "in_degree": in_degree,
            "out_degree": out_degree,
            "community": community,
        }

    # -- Temporal Analysis ---------------------------------------------------

    def get_temporal_analysis(self) -> Dict[str, Any]:
        """
        Analyze how the knowledge network evolved over time.

        Groups works by year and shows growth trends.

        Returns:
            Dict with yearly statistics and growth metrics.
        """
        G = self._graph_store._graph
        works_by_year: Dict[int, List[str]] = defaultdict(list)

        for node_id, data in G.nodes(data=True):
            if data.get("node_type") == "Work":
                year = data.get("year")
                if isinstance(year, int):
                    works_by_year[year].append(node_id)

        if not works_by_year:
            return {"years": {}, "total_works": 0}

        years_sorted = sorted(works_by_year.keys())

        yearly_stats = {}
        cumulative = 0
        for year in years_sorted:
            works = works_by_year[year]
            cumulative += len(works)

            # Count citations between works in this year and earlier works
            cross_year_citations = 0
            for work_id in works:
                for cited_id in self._graph_store.get_cited_works(work_id):
                    cited_node = self._graph_store.get_node(cited_id)
                    if cited_node:
                        cited_year = cited_node.get("year")
                        if isinstance(cited_year, int) and cited_year < year:
                            cross_year_citations += 1

            yearly_stats[year] = {
                "new_works": len(works),
                "cumulative_works": cumulative,
                "cross_year_citations": cross_year_citations,
            }

        return {
            "years": yearly_stats,
            "total_works": cumulative,
            "year_range": [years_sorted[0], years_sorted[-1]] if years_sorted else [],
        }
