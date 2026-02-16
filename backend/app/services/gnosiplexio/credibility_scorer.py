"""
Gnosiplexio Credibility Scorer — Network-derived credibility calculation.

Calculates a work's credibility based on its citation network:
- Total citations in the graph
- Diversity of citing journals
- Sentiment distribution (supportive vs critical)
- Top cited-for reasons with evidence counts
- Known limitations from critical citations
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("gnosiplexio.credibility_scorer")


class CredibilityScorer:
    """
    Calculates network-derived credibility for works in the knowledge graph.

    Credibility is not binary (exists/doesn't) — it's a rich, multi-dimensional
    score backed by independent academic sources.
    """

    def __init__(self, graph_store):
        """
        Initialize with a GraphStore reference.

        Args:
            graph_store: The GraphStore instance to analyze.
        """
        self._graph = graph_store

    def calculate_credibility(self, work_id: str) -> Optional[Dict[str, Any]]:
        """
        Calculate the full network credibility report for a work.

        Args:
            work_id: The work identifier.

        Returns:
            Credibility report dict, or None if node doesn't exist.
        """
        node = self._graph.get_node(work_id)
        if node is None:
            return None

        network_citations = node.get("network_citations", [])
        total_citations = len(network_citations)

        # Unique citing journals (approximate from citing work metadata)
        citing_journals = set()
        for nc in network_citations:
            citing_id = nc.get("citing_work_id", "")
            citing_node = self._graph.get_node(citing_id)
            if citing_node:
                journal = citing_node.get("journal", citing_node.get("venue", ""))
                if journal:
                    citing_journals.add(journal)

        # Credibility score calculation
        credibility_score = self._compute_score(
            total_citations=total_citations,
            unique_journals=len(citing_journals),
            network_citations=network_citations,
        )

        # Top cited-for reasons
        top_cited_for = self._aggregate_cited_for(network_citations)

        # Known limitations (from critical citations)
        known_limitations = self._extract_limitations(network_citations)

        # Sentiment distribution
        sentiment_dist = self._sentiment_distribution(network_citations)

        return {
            "work_id": work_id,
            "total_citations_in_network": total_citations,
            "unique_citing_journals": len(citing_journals),
            "credibility_score": round(credibility_score, 4),
            "top_cited_for": top_cited_for,
            "known_limitations": known_limitations,
            "sentiment_distribution": sentiment_dist,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def _compute_score(
        self,
        total_citations: int,
        unique_journals: int,
        network_citations: List[Dict],
    ) -> float:
        """
        Compute a 0-1 credibility score.

        Factors:
        - Citation count (logarithmic scale, diminishing returns)
        - Journal diversity (more diverse = more credible)
        - Average credibility weight of citing papers
        - Supportive ratio (mostly supportive = higher)
        """
        if total_citations == 0:
            return 0.0

        import math

        # Citation count factor (log scale, max ~1.0 at 50+ citations)
        citation_factor = min(1.0, math.log(1 + total_citations) / math.log(51))

        # Journal diversity factor
        if total_citations > 0:
            diversity_factor = min(1.0, unique_journals / max(1, total_citations * 0.5))
        else:
            diversity_factor = 0.0

        # Average credibility weight
        weights = [nc.get("credibility_weight", 0.5) for nc in network_citations]
        avg_weight = sum(weights) / len(weights) if weights else 0.5

        # Supportive ratio
        sentiments = [nc.get("sentiment", "supportive") for nc in network_citations]
        supportive_count = sum(1 for s in sentiments if s in ("supportive", "extends"))
        supportive_ratio = supportive_count / len(sentiments) if sentiments else 0.5

        # Weighted combination
        score = (
            0.40 * citation_factor +
            0.20 * diversity_factor +
            0.20 * avg_weight +
            0.20 * supportive_ratio
        )

        return min(1.0, max(0.0, score))

    def _aggregate_cited_for(self, network_citations: List[Dict]) -> List[Dict[str, Any]]:
        """
        Aggregate cited_for reasons across all network citations.

        Returns a ranked list of claims with evidence counts and confidence levels.
        """
        cited_for_counter: Counter = Counter()
        for nc in network_citations:
            cited_for = nc.get("cited_for", "").strip()
            if cited_for:
                cited_for_counter[cited_for] += 1

        results = []
        for claim, count in cited_for_counter.most_common(10):
            confidence = "HIGH" if count >= 5 else "MEDIUM" if count >= 2 else "LOW"
            results.append({
                "claim": claim,
                "evidence_count": count,
                "confidence": confidence,
            })

        return results

    def _extract_limitations(self, network_citations: List[Dict]) -> List[Dict[str, Any]]:
        """Extract known limitations from critical citations."""
        limitations: Dict[str, int] = {}
        for nc in network_citations:
            if nc.get("sentiment") == "critical":
                context = nc.get("citation_context", nc.get("cited_for", ""))
                if context:
                    # Use cited_for as the limitation description
                    limitation = nc.get("cited_for", context[:100])
                    limitations[limitation] = limitations.get(limitation, 0) + 1

        return [
            {"limitation": lim, "sources": count}
            for lim, count in sorted(limitations.items(), key=lambda x: -x[1])
        ]

    def _sentiment_distribution(self, network_citations: List[Dict]) -> Dict[str, int]:
        """Count the distribution of citation sentiments."""
        counter = Counter(nc.get("sentiment", "unknown") for nc in network_citations)
        return dict(counter)

    def batch_calculate(self, work_ids: Optional[List[str]] = None) -> Dict[str, Dict]:
        """
        Calculate credibility for multiple works.

        Args:
            work_ids: List of work IDs. If None, calculates for all Work nodes.

        Returns:
            Dict mapping work_id to credibility report.
        """
        if work_ids is None:
            work_ids = self._graph.get_nodes_by_type("Work")

        results = {}
        for work_id in work_ids:
            report = self.calculate_credibility(work_id)
            if report:
                results[work_id] = report

        return results
