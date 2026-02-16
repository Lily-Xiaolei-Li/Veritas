"""
Comprehensive tests for the Gnosiplexio knowledge graph engine.

Tests cover:
- GraphStore CRUD and persistence
- GenericAdapter loading and search
- NetworkEnricher organic enrichment
- CredibilityScorer scoring
- PositionCalculator centrality and communities
- GnosiplexioEngine end-to-end workflow
"""

import json
import tempfile
from pathlib import Path

import pytest

# Add backend to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.gnosiplexio.graph_store import GraphStore
from app.services.gnosiplexio.adapters.generic_adapter import GenericAdapter
from app.services.gnosiplexio.network_enricher import NetworkEnricher, NetworkCitation
from app.services.gnosiplexio.credibility_scorer import CredibilityScorer
from app.services.gnosiplexio.position_calculator import PositionCalculator
from app.services.gnosiplexio.engine import GnosiplexioEngine


# ============================================================================
# Test Data
# ============================================================================

SAMPLE_PAPERS = [
    {
        "id": "power_1997",
        "title": "The Audit Society: Rituals of Verification",
        "authors": ["Michael Power"],
        "year": 1997,
        "doi": "10.1093/acprof:oso/9780198296034.001.0001",
        "abstract": "This book examines the rise of auditing and its societal implications.",
        "type": "book",
        "key_concepts": ["audit society", "rituals of verification", "audit explosion"],
        "references": [],
    },
    {
        "id": "meyer_1977",
        "title": "Institutionalized Organizations: Formal Structure as Myth and Ceremony",
        "authors": ["John W. Meyer", "Brian Rowan"],
        "year": 1977,
        "abstract": "Formal organizational structure arises from institutional myths.",
        "type": "paper",
        "key_concepts": ["institutional theory", "ceremonial conformity"],
        "references": [],
    },
    {
        "id": "paper_a_2023",
        "title": "Rethinking Audit as Institutional Ritual",
        "authors": ["Alice Smith"],
        "year": 2023,
        "abstract": "This paper extends Power's framework using institutional theory.",
        "type": "paper",
        "key_concepts": ["audit ritual", "institutional theory"],
        "method": "qualitative case study",
        "references": [
            {
                "id": "power_1997",
                "context": "Power (1997) argued that audit serves as a ritual of verification",
                "cited_for": "audit as ritual",
                "sentiment": "supportive",
                "credibility_weight": 0.85,
            },
            {
                "id": "meyer_1977",
                "context": "Meyer and Rowan (1977) established the concept of ceremonial conformity",
                "cited_for": "institutional theory foundation",
                "sentiment": "supportive",
                "credibility_weight": 0.90,
            },
        ],
    },
    {
        "id": "paper_b_2024",
        "title": "The Performativity of Audit in Digital Environments",
        "authors": ["Bob Johnson"],
        "year": 2024,
        "abstract": "Examines how audit practices perform differently in digital contexts.",
        "type": "paper",
        "key_concepts": ["performativity", "digital audit"],
        "method": "mixed methods",
        "references": [
            {
                "id": "power_1997",
                "context": "Power (1997) first identified the performative nature of audit",
                "cited_for": "performativity of audit",
                "sentiment": "extends",
                "credibility_weight": 0.80,
            },
            {
                "id": "paper_a_2023",
                "context": "Smith (2023) extended Power's framework into institutional analysis",
                "cited_for": "extension of Power framework",
                "sentiment": "supportive",
                "credibility_weight": 0.70,
            },
        ],
    },
    {
        "id": "paper_c_2024",
        "title": "Limitations of the Audit Society Thesis",
        "authors": ["Carol Williams"],
        "year": 2024,
        "abstract": "A critical examination of Power's audit society thesis.",
        "type": "paper",
        "key_concepts": ["audit society critique"],
        "references": [
            {
                "id": "power_1997",
                "context": "Power's (1997) analysis is limited by its UK-centric focus",
                "cited_for": "UK-centric analysis limitation",
                "sentiment": "critical",
                "credibility_weight": 0.75,
            },
        ],
    },
]


# ============================================================================
# GraphStore Tests
# ============================================================================

class TestGraphStore:
    def test_add_and_get_node(self):
        gs = GraphStore()
        gs.add_node("test1", node_type="Work", title="Test Paper")
        node = gs.get_node("test1")
        assert node is not None
        assert node["title"] == "Test Paper"
        assert node["node_type"] == "Work"

    def test_node_not_found(self):
        gs = GraphStore()
        assert gs.get_node("nonexistent") is None

    def test_add_and_get_edge(self):
        gs = GraphStore()
        gs.add_node("a", node_type="Work")
        gs.add_node("b", node_type="Work")
        gs.add_edge("a", "b", "CITES", context="test")
        edge = gs.get_edge("a", "b")
        assert edge is not None
        assert edge["edge_type"] == "CITES"
        assert edge["context"] == "test"

    def test_get_neighbors(self):
        gs = GraphStore()
        gs.add_node("a", node_type="Work")
        gs.add_node("b", node_type="Work")
        gs.add_node("c", node_type="Work")
        gs.add_edge("a", "b", "CITES")
        gs.add_edge("c", "a", "CITES")

        out_neighbors = gs.get_neighbors("a", direction="out")
        assert "b" in out_neighbors

        in_neighbors = gs.get_neighbors("a", direction="in")
        assert "c" in in_neighbors

        all_neighbors = gs.get_neighbors("a", direction="both")
        assert "b" in all_neighbors
        assert "c" in all_neighbors

    def test_get_neighborhood(self):
        gs = GraphStore()
        gs.add_node("a", node_type="Work", title="Paper A")
        gs.add_node("b", node_type="Work", title="Paper B")
        gs.add_node("c", node_type="Work", title="Paper C")
        gs.add_edge("a", "b", "CITES")
        gs.add_edge("b", "c", "CITES")

        hood = gs.get_neighborhood("a", hops=2)
        assert hood["node_count"] == 3
        assert hood["center"] == "a"

    def test_search_nodes(self):
        gs = GraphStore()
        gs.add_node("p1", node_type="Work", title="The Audit Society")
        gs.add_node("p2", node_type="Work", title="Digital Transformation")

        results = gs.search_nodes("audit")
        assert len(results) == 1
        assert results[0]["id"] == "p1"

    def test_json_persistence(self):
        gs = GraphStore()
        gs.add_node("a", node_type="Work", title="Test")
        gs.add_node("b", node_type="Concept", name="test concept")
        gs.add_edge("a", "b", "ARGUES")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        gs.save_json(path)

        gs2 = GraphStore()
        gs2.load_json(path)

        assert gs2.node_count == 2
        assert gs2.edge_count == 1
        assert gs2.get_node("a")["title"] == "Test"

        Path(path).unlink()

    def test_get_stats(self):
        gs = GraphStore()
        gs.add_node("a", node_type="Work")
        gs.add_node("b", node_type="Work")
        gs.add_node("c", node_type="Concept", name="test")
        gs.add_edge("a", "b", "CITES")
        gs.add_edge("a", "c", "ARGUES")

        stats = gs.get_stats()
        assert stats["total_nodes"] == 3
        assert stats["total_edges"] == 2
        assert stats["node_types"]["Work"] == 2
        assert stats["node_types"]["Concept"] == 1

    def test_get_citing_and_cited_works(self):
        gs = GraphStore()
        gs.add_node("a", node_type="Work")
        gs.add_node("b", node_type="Work")
        gs.add_edge("a", "b", "CITES")

        assert "b" in gs.get_cited_works("a")
        assert "a" in gs.get_citing_works("b")

    def test_nodes_by_type(self):
        gs = GraphStore()
        gs.add_node("w1", node_type="Work")
        gs.add_node("w2", node_type="Work")
        gs.add_node("c1", node_type="Concept", name="test")

        works = gs.get_nodes_by_type("Work")
        assert len(works) == 2
        concepts = gs.get_nodes_by_type("Concept")
        assert len(concepts) == 1


# ============================================================================
# GenericAdapter Tests
# ============================================================================

class TestGenericAdapter:
    def test_load_from_data(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        works = adapter.list_works()
        assert len(works) == 5

    def test_get_profile(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        profile = adapter.get_profile("power_1997")
        assert profile is not None
        assert profile["title"] == "The Audit Society: Rituals of Verification"

    def test_get_citations(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        citations = adapter.get_citations("paper_a_2023")
        assert len(citations) == 2
        assert citations[0]["cited_id"] == "power_1997"

    def test_search(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        results = adapter.search("audit")
        assert len(results) >= 2  # power_1997 and paper_a_2023 at least

    def test_json_file_loading(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as f:
            json.dump(SAMPLE_PAPERS, f)
            path = f.name

        adapter = GenericAdapter(file=path)
        assert len(adapter.list_works()) == 5

        Path(path).unlink()

    def test_csv_file_loading(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, encoding="utf-8", newline="") as f:
            f.write("id,title,authors,year,doi,abstract\n")
            f.write('power_1997,"The Audit Society","Michael Power",1997,"10.1093/test","Test abstract"\n')
            path = f.name

        adapter = GenericAdapter(file=path)
        works = adapter.list_works()
        assert len(works) == 1
        assert works[0]["title"] == "The Audit Society"

        Path(path).unlink()


# ============================================================================
# NetworkEnricher Tests
# ============================================================================

class TestNetworkEnricher:
    def test_basic_enrichment(self):
        gs = GraphStore()
        gs.add_node("power_1997", node_type="Work", title="The Audit Society",
                     network_citations=[], cross_perspectives=[])
        enricher = NetworkEnricher(gs)

        citations = [
            {
                "cited_id": "power_1997",
                "context": "Power (1997) argued audit is a ritual",
                "cited_for": "audit as ritual",
                "sentiment": "supportive",
                "credibility_weight": 0.85,
            }
        ]

        result = enricher.enrich("paper_a", {"authors": ["Alice"], "key_concepts": []}, citations)
        assert result["enriched_nodes"] >= 1

        node = gs.get_node("power_1997")
        assert len(node["network_citations"]) == 1
        assert node["network_citations"][0]["cited_for"] == "audit as ritual"

    def test_critical_citation_creates_cross_perspective(self):
        gs = GraphStore()
        gs.add_node("power_1997", node_type="Work",
                     network_citations=[], cross_perspectives=[])
        enricher = NetworkEnricher(gs)

        citations = [
            {
                "cited_id": "power_1997",
                "context": "Power's analysis is UK-centric",
                "cited_for": "limitation",
                "sentiment": "critical",
                "credibility_weight": 0.75,
            }
        ]

        enricher.enrich("critic_paper", {"authors": [], "key_concepts": []}, citations)

        node = gs.get_node("power_1997")
        assert len(node.get("cross_perspectives", [])) >= 1

    def test_concept_extraction(self):
        gs = GraphStore()
        enricher = NetworkEnricher(gs)

        profile = {
            "authors": ["Alice Smith"],
            "key_concepts": ["audit ritual", "institutional theory"],
            "method": "case study",
        }

        enricher.enrich("paper_x", profile, [])

        # Check concept nodes were created
        assert gs.has_node("concept:audit_ritual")
        assert gs.has_node("concept:institutional_theory")
        assert gs.has_node("author:alice_smith")
        assert gs.has_node("method:case_study")


# ============================================================================
# CredibilityScorer Tests
# ============================================================================

class TestCredibilityScorer:
    def _setup_scored_graph(self) -> GraphStore:
        gs = GraphStore()
        gs.add_node("power_1997", node_type="Work", title="The Audit Society",
                     network_citations=[
                         {"citing_work_id": "p1", "cited_for": "audit as ritual",
                          "sentiment": "supportive", "credibility_weight": 0.85},
                         {"citing_work_id": "p2", "cited_for": "audit as ritual",
                          "sentiment": "supportive", "credibility_weight": 0.80},
                         {"citing_work_id": "p3", "cited_for": "performativity",
                          "sentiment": "extends", "credibility_weight": 0.75},
                         {"citing_work_id": "p4", "cited_for": "UK-centric",
                          "sentiment": "critical", "credibility_weight": 0.70},
                     ])
        return gs

    def test_credibility_calculation(self):
        gs = self._setup_scored_graph()
        scorer = CredibilityScorer(gs)
        report = scorer.calculate_credibility("power_1997")

        assert report is not None
        assert report["total_citations_in_network"] == 4
        assert 0 < report["credibility_score"] <= 1.0
        assert len(report["top_cited_for"]) > 0

    def test_limitations_extracted(self):
        gs = self._setup_scored_graph()
        scorer = CredibilityScorer(gs)
        report = scorer.calculate_credibility("power_1997")

        assert len(report["known_limitations"]) >= 1
        assert any("UK-centric" in lim["limitation"] for lim in report["known_limitations"])

    def test_sentiment_distribution(self):
        gs = self._setup_scored_graph()
        scorer = CredibilityScorer(gs)
        report = scorer.calculate_credibility("power_1997")

        dist = report["sentiment_distribution"]
        assert dist.get("supportive", 0) == 2
        assert dist.get("extends", 0) == 1
        assert dist.get("critical", 0) == 1

    def test_zero_citations(self):
        gs = GraphStore()
        gs.add_node("lonely_paper", node_type="Work", network_citations=[])
        scorer = CredibilityScorer(gs)
        report = scorer.calculate_credibility("lonely_paper")

        assert report["credibility_score"] == 0.0
        assert report["total_citations_in_network"] == 0


# ============================================================================
# PositionCalculator Tests
# ============================================================================

class TestPositionCalculator:
    def _setup_network(self) -> GraphStore:
        gs = GraphStore()
        # Create a small network
        for i in range(5):
            gs.add_node(f"w{i}", node_type="Work", title=f"Paper {i}", year=2020+i)

        gs.add_edge("w1", "w0", "CITES")
        gs.add_edge("w2", "w0", "CITES")
        gs.add_edge("w3", "w0", "CITES")
        gs.add_edge("w4", "w0", "CITES")
        gs.add_edge("w2", "w1", "CITES")
        gs.add_edge("w3", "w2", "CITES")
        gs.add_edge("w4", "w3", "EXTENDS")
        return gs

    def test_centrality_calculation(self):
        gs = self._setup_network()
        calc = PositionCalculator(gs)
        centrality = calc.calculate_centrality()

        assert len(centrality) == 5
        # w0 should have highest in_degree (cited by all)
        assert centrality["w0"]["in_degree"] == 4

    def test_relative_position(self):
        gs = self._setup_network()
        calc = PositionCalculator(gs)
        pos = calc.get_relative_position("w0")

        assert pos is not None
        assert pos["node_id"] == "w0"
        assert pos["in_degree"] == 4

    def test_community_detection(self):
        gs = self._setup_network()
        calc = PositionCalculator(gs)
        communities = calc.detect_communities()

        assert communities["num_communities"] >= 1

    def test_temporal_analysis(self):
        gs = self._setup_network()
        calc = PositionCalculator(gs)
        temporal = calc.get_temporal_analysis()

        assert temporal["total_works"] == 5
        assert len(temporal["years"]) > 0


# ============================================================================
# Engine End-to-End Tests
# ============================================================================

class TestGnosiplexioEngine:
    def test_ingest_single_paper(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        engine = GnosiplexioEngine(adapter=adapter)

        result = engine.ingest("paper_a_2023")
        assert result.ingested_count == 1
        assert result.new_edges > 0

    def test_ingest_all(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        engine = GnosiplexioEngine(adapter=adapter)

        result = engine.ingest_all()
        assert result.ingested_count == 5
        assert engine.graph.node_count > 5  # Papers + concepts + authors

    def test_organic_enrichment_power_1997(self):
        """
        The key test: after ingesting all papers, Power (1997) should have
        rich network knowledge from being cited by multiple papers.
        """
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        engine = GnosiplexioEngine(adapter=adapter)
        engine.ingest_all()

        nk = engine.get_node("power_1997")
        assert nk is not None

        # Power should have network citations from papers A, B, and C
        assert len(nk.network_citations) >= 3

        # Credibility should be calculated
        cred = engine.get_credibility("power_1997")
        assert cred is not None
        assert cred["total_citations_in_network"] >= 3
        assert cred["credibility_score"] > 0

        # Should have top cited_for reasons
        assert len(cred["top_cited_for"]) > 0

        # Should have known limitations (from paper_c's critical citation)
        assert len(cred["known_limitations"]) >= 1

    def test_search(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        engine = GnosiplexioEngine(adapter=adapter)
        engine.ingest_all()

        result = engine.search("audit")
        assert result.total > 0

    def test_compare(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        engine = GnosiplexioEngine(adapter=adapter)
        engine.ingest_all()

        result = engine.compare("paper_a_2023", "paper_b_2024")
        assert result.node_a == "paper_a_2023"
        assert result.node_b == "paper_b_2024"
        # Both cite power_1997, so they should share a citation
        assert "power_1997" in result.shared_citations

    def test_export_cytoscape(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        engine = GnosiplexioEngine(adapter=adapter)
        engine.ingest_all()

        export = engine.export_graph(format="cytoscape")
        assert "elements" in export
        assert len(export["elements"]["nodes"]) > 0
        assert len(export["elements"]["edges"]) > 0

    def test_export_bibtex(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        engine = GnosiplexioEngine(adapter=adapter)
        engine.ingest_all()

        export = engine.export_graph(format="bibtex")
        assert export["count"] >= 5
        assert "@article" in export["content"]

    def test_get_stats(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        engine = GnosiplexioEngine(adapter=adapter)
        engine.ingest_all()

        stats = engine.get_stats()
        assert stats["total_nodes"] > 5
        assert stats["total_edges"] > 0
        assert "node_types" in stats

    def test_persistence(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)

        with tempfile.TemporaryDirectory() as tmpdir:
            graph_path = str(Path(tmpdir) / "test_graph.json")

        engine = GnosiplexioEngine(adapter=adapter, graph_path=graph_path)
        engine.ingest_all()
        original_count = engine.graph.node_count

        # Create new engine loading from same path
        engine2 = GnosiplexioEngine(graph_path=graph_path)
        assert engine2.graph.node_count == original_count

        Path(graph_path).unlink()

    def test_neighborhood(self):
        adapter = GenericAdapter(data=SAMPLE_PAPERS)
        engine = GnosiplexioEngine(adapter=adapter)
        engine.ingest_all()

        hood = engine.get_neighborhood("power_1997", hops=1)
        assert hood["node_count"] > 0
        assert hood["center"] == "power_1997"


# ============================================================================
# Run
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
