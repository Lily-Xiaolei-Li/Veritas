# PRD: Gnosiplexio ✨

**Spell Name:** Gnosiplexio — 知识之网的编织者  
**Etymology:** Gnosi (γνῶσις, knowledge/insight) + Plexio (plexus, weave/network)  
**Version:** 2.0 (evolved from VF-KG v1)  
**Author:** Barry Li & 超级小蕾  
**Date:** 2026-02-16  
**Status:** Draft for review  

---

## 1. Vision

Gnosiplexio is a **living knowledge graph engine** that weaves academic literature — papers, books, concepts, authors, methods — into a navigable, self-growing network of human knowledge.

It is designed to be:
- **VF-native** — deeply integrated with the Veritas Fingerprint ecosystem (Veritafactum, Citalio, Proliferomaxima)
- **Database-agnostic** — can run independently against any structured knowledge database, not just VF Store
- **Organic** — every new paper digested enriches not just itself, but the entire network of connected works

**Core philosophy:** In a knowledge graph, the connections between nodes are more valuable than the nodes themselves. A paper's true significance emerges not from its own text alone, but from how the entire network of scholarship positions it.

---

## 2. The Problem

| Problem | Current State | Gnosiplexio Solution |
|---------|--------------|---------------------|
| Knowledge is siloed in individual papers | Each VF profile is a standalone record | Profiles are **nodes in a living network** with rich edges |
| Citation context is lost | VF stores what a paper says, not how others use it | **Network knowledge** accumulates from every paper that cites it |
| No way to see the big picture | Flat list of profiles | **Interactive visual graph** — zoom, filter, trace lineages |
| Credibility is binary | Paper exists or doesn't | **Network-derived credibility** — cited by 50 credible papers = practically unfakeable |
| Knowledge only flows inward | Adding a paper enriches only that paper | Adding one paper **ripples through the network**, enriching all connected nodes |
| Locked to VF | KG only works with VF Store | **Pluggable data sources** — VF, Zotero, OpenAlex, any structured DB |

---

## 3. Core Concept: Network Knowledge

### 3.1 The Insight

In academia, a paper's knowledge comes from two sources:

1. **Direct knowledge** — what the paper itself says (from full text or abstract)
2. **Network knowledge** — what the citing ecosystem reveals about it

Network knowledge is often *richer* than direct knowledge because:

- **Critics and limitations** — citing papers may identify flaws the original never acknowledged
- **Novel applications** — later work may use a paper for purposes the author never intended
- **Cross-domain connections** — a sociology paper cited by accounting researchers reveals interdisciplinary relevance
- **Credibility signal** — if 50 credible papers in credible journals cite a work, its core claims are effectively validated by the academic community
- **Evolving interpretation** — how a paper's contribution is understood changes over time as the field develops

### 3.2 The Killer Feature: Organic Enrichment

```
Day 1: Paper A is added to Gnosiplexio
  → Paper A cites Power (1997) for "audit as ritual"
  → Power (1997) gains a new NetworkCitation vector:
      {cited_by: "Paper A", cited_for: "audit as ritual", context: "...", credibility: 0.85}

Day 2: Paper B is added
  → Paper B also cites Power (1997), but for "performativity of audit"
  → Paper B cites Paper A, calling it "an extension of Power's framework"
  → THREE enrichments happen simultaneously:
      1. Power (1997) gains another NetworkCitation (now 2 sources for credibility)
      2. Paper A gains a NetworkCitation (Paper B's perspective on it)
      3. Edge Paper A → Power (1997) gains a label: "extends framework"

Day 30: 25 more papers added, all citing Power (1997)
  → Power (1997) now has rich, multi-perspective network knowledge
  → Its "cited_for" field is backed by 27 independent academic sources
  → A critic paper added "limitation" knowledge that Power's own text never mentioned
  → Gnosiplexio can now tell you: "Power (1997) is most cited for X (15 papers),
     also cited for Y (8 papers), criticized for Z (4 papers)"
```

**Every paper enriches the entire network, not just itself.**

---

## 4. Architecture

### 4.1 Data Model

#### Node Types

| Node Type | Description | Key Properties |
|-----------|-------------|---------------|
| **Work** | Paper, book, chapter, report | id, title, authors, year, doi, type, full_article (bool) |
| **Concept** | Theory, framework, method, term | id, name, definition, domain |
| **Author** | Researcher | id, name, affiliations, orcid |
| **Domain** | Field/subfield of study | id, name, parent_domain |
| **Method** | Research methodology | id, name, type (qual/quant/mixed) |

#### Edge Types

| Edge | From → To | Description |
|------|-----------|-------------|
| **CITES** | Work → Work | Direct citation relationship |
| **CITED_FOR** | Work → Work | Why A cites B (with context) |
| **ARGUES** | Work → Concept | Paper makes this argument |
| **EXTENDS** | Work → Work | Builds upon prior work |
| **CHALLENGES** | Work → Work | Disputes or critiques |
| **DEFINES** | Work → Concept | Introduces or defines a concept |
| **APPLIES** | Work → Method | Uses this methodology |
| **AUTHORED_BY** | Work → Author | Authorship |
| **BELONGS_TO** | Work → Domain | Research domain |
| **NOT_FOR** | Work → Concept | Common misapplications (what it should NOT be cited for) |

#### Vector Objects (new — beyond VF Store)

Gnosiplexio introduces **additional vector objects** that live alongside VF profiles but serve the graph specifically:

| Vector Type | Purpose | Grows Organically? |
|-------------|---------|-------------------|
| **NetworkCitation** | What citing papers say about a work | ✅ Yes — every new paper adds citations |
| **NetworkCredibility** | Aggregated credibility score from citation network | ✅ Yes — recalculated as evidence grows |
| **ConceptEvolution** | How a concept's usage/meaning changes over time | ✅ Yes — timeline of interpretations |
| **CrossPerspective** | Perspectives from outside the paper (critics, extensions, novel uses) | ✅ Yes — each citing paper may add a new perspective |
| **RelativePosition** | A paper's position in the network (central? peripheral? bridge?) | ✅ Yes — recalculated with each new edge |

**NetworkCitation** schema:
```json
{
    "target_work_id": "power_1997",
    "citing_work_id": "paper_a_2023",
    "citation_context": "Power (1997) argued that audit serves as a ritual...",
    "cited_for": "audit as ritual performance",
    "sentiment": "supportive",        // supportive | critical | neutral | extends
    "credibility_weight": 0.85,       // based on citing paper's journal/citations
    "extracted_at": "2026-02-16",
    "source_type": "direct"           // direct (from full text) | inferred (from abstract)
}
```

**NetworkCredibility** schema:
```json
{
    "work_id": "power_1997",
    "total_citations_in_network": 27,
    "unique_citing_journals": 12,
    "credibility_score": 0.97,        // 0-1, based on citation count + journal quality
    "top_cited_for": [
        {"claim": "audit as ritual", "evidence_count": 15, "confidence": "HIGH"},
        {"claim": "performativity of audit", "evidence_count": 8, "confidence": "HIGH"},
        {"claim": "audit explosion", "evidence_count": 4, "confidence": "MEDIUM"}
    ],
    "known_limitations": [
        {"limitation": "UK-centric analysis", "sources": 3}
    ],
    "last_updated": "2026-02-16"
}
```

### 4.2 Storage Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Gnosiplexio                        │
│                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Vector Store │  │ Graph Store   │  │ Metadata     │ │
│  │ (Qdrant/    │  │ (NetworkX /   │  │ Index        │ │
│  │  ChromaDB)  │  │  Neo4j /      │  │ (JSON/       │ │
│  │             │  │  JSON export) │  │  SQLite)     │ │
│  │ - VF chunks │  │              │  │              │ │
│  │ - Network   │  │ - Nodes      │  │ - Author_Year│ │
│  │   Citations │  │ - Edges      │  │ - DOI lookup │ │
│  │ - Cross     │  │ - Weights    │  │ - Title hash │ │
│  │   Perspec.  │  │ - Positions  │  │              │ │
│  └─────────────┘  └──────────────┘  └──────────────┘ │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │              Data Source Adapters                 │ │
│  │  ┌────┐  ┌────────┐  ┌─────────┐  ┌──────────┐ │ │
│  │  │ VF │  │ Zotero │  │OpenAlex │  │ Custom   │ │ │
│  │  │Store│  │        │  │         │  │ JSON/CSV │ │ │
│  │  └────┘  └────────┘  └─────────┘  └──────────┘ │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Key design: Data Source Adapters**

Gnosiplexio is NOT locked to VF Store. Each adapter implements a simple interface:

```python
class DataSourceAdapter(Protocol):
    def list_works(self) -> list[WorkRecord]: ...
    def get_profile(self, work_id: str) -> Optional[Profile]: ...
    def get_citations(self, work_id: str) -> list[Citation]: ...
    def search(self, query: str, top_k: int) -> list[SearchResult]: ...
```

The VF adapter is the primary one, but any structured knowledge database can plug in.

### 4.3 Graph Computation Engine

#### Centrality & Positioning
- **Betweenness centrality** — papers that bridge between research clusters
- **PageRank** — most influential papers in the network
- **Community detection** — research clusters and subfields
- **Temporal analysis** — how the network evolved over time

#### Organic Enrichment Pipeline

When a new paper is ingested:

```
1. EXTRACT: Parse the paper's references and citation contexts
2. IDENTIFY: Match each reference to existing graph nodes (or create new ones)
3. ENRICH: For each matched node:
   a. Add NetworkCitation vector (what this paper says about the cited work)
   b. Update NetworkCredibility (recalculate citation count + credibility score)
   c. Add/update edges (CITES, CITED_FOR, EXTENDS, CHALLENGES)
   d. Check for new CrossPerspective (critics, novel applications)
4. POSITION: Recalculate RelativePosition for affected nodes
5. CONNECT: Update ConceptEvolution if concept usage has shifted
6. PROPAGATE: If the new paper itself was already cited by others in the graph,
              update those edges too (bidirectional enrichment)
```

---

## 5. Consumer Interfaces

### 5.1 Visual Knowledge Explorer (GUI)

The crown jewel — an interactive graph visualisation:

- **Network view** — force-directed graph, nodes sized by centrality, colored by domain
- **Timeline view** — horizontal timeline showing concept evolution and citation chains
- **Ego view** — select any paper → see its 2-hop neighborhood (what it cites, what cites it)
- **Cluster view** — community detection reveals research schools and paradigm groups
- **Comparison view** — place two papers side by side, highlight shared/divergent networks
- **Heatmap** — which concepts/papers are most cited in which time periods

**Interactions:**
- Click node → sidebar shows full profile + network knowledge
- Hover edge → shows citation context ("Paper A cites Paper B for...")
- Filter by year, domain, author, concept, credibility
- Search → highlights matching nodes and paths
- Export subgraph as image, JSON, or BibTeX

**Tech:** D3.js or Cytoscape.js (browser-native, no server-side rendering needed)

### 5.2 Veritafactum Integration (API)

```
VF checks: "Power (1997) argues that audit has expanded..."
  1. Graph lookup: Power_1997 → node found
  2. NetworkCredibility: score 0.97, cited by 27 papers
  3. CITED_FOR edges: "audit expansion" supported by 15 independent sources
  4. Verdict: VERIFIED — HIGH confidence, rich evidence trail
```

### 5.3 Citalio Integration (API)

```
Citalio needs citation for: "Audit serves a ceremonial function in organizations"
  1. Concept search: "audit ceremonial function" → Concept node
  2. Graph traversal: which Works ARGUE this concept?
  3. NetworkCredibility ranking: return works by credibility score
  4. Result: Power (1997) [score 0.97], Meyer & Rowan (1977) [score 0.92]...
```

### 5.4 Standalone API (database-agnostic)

```python
# Works with any adapter
gnosiplexio = Gnosiplexio(adapter=ZoteroAdapter(library_path="..."))
gnosiplexio.ingest("new_paper.pdf")  # enriches entire network
gnosiplexio.query("what is Power 1997 cited for?")
gnosiplexio.visualize(center="power_1997", hops=2)
gnosiplexio.export(format="cytoscape_json")
```

---

## 6. New Files

### Backend Services
| File | Purpose |
|------|---------|
| `services/gnosiplexio/__init__.py` | Package init |
| `services/gnosiplexio/engine.py` | Main orchestrator: ingest, enrich, query |
| `services/gnosiplexio/graph_store.py` | Graph storage (NetworkX + JSON export) |
| `services/gnosiplexio/network_enricher.py` | Organic enrichment pipeline |
| `services/gnosiplexio/credibility_scorer.py` | Network credibility calculation |
| `services/gnosiplexio/position_calculator.py` | Centrality, PageRank, community detection |
| `services/gnosiplexio/adapters/__init__.py` | Adapter interface |
| `services/gnosiplexio/adapters/vf_adapter.py` | VF Store adapter |
| `services/gnosiplexio/adapters/generic_adapter.py` | Generic JSON/CSV adapter |

### API Routes
| File | Purpose |
|------|---------|
| `routes/gnosiplexio_routes.py` | REST API for graph queries, ingestion, export |

**Endpoints:**
- `POST /api/v1/gnosiplexio/ingest` — add paper(s), trigger network enrichment
- `GET /api/v1/gnosiplexio/node/{id}` — get node with full network knowledge
- `GET /api/v1/gnosiplexio/neighborhood/{id}?hops=2` — ego network
- `GET /api/v1/gnosiplexio/search?q=...` — semantic + graph search
- `GET /api/v1/gnosiplexio/credibility/{id}` — network credibility report
- `GET /api/v1/gnosiplexio/graph?format=cytoscape` — export graph data
- `GET /api/v1/gnosiplexio/stats` — network statistics
- `POST /api/v1/gnosiplexio/compare` — compare two nodes

### CLI
| File | Purpose |
|------|---------|
| `cli/gnosiplexio_handlers.py` | `gnosiplexio ingest`, `query`, `stats`, `export`, `visualize` |

### Frontend
| File | Purpose |
|------|---------|
| `components/gnosiplexio/GnosiplexioPanel.tsx` | Main graph explorer panel |
| `components/gnosiplexio/GraphCanvas.tsx` | D3/Cytoscape graph renderer |
| `components/gnosiplexio/NodeSidebar.tsx` | Node detail + network knowledge sidebar |
| `components/gnosiplexio/TimelineView.tsx` | Temporal evolution view |
| `components/gnosiplexio/FilterBar.tsx` | Year/domain/author/concept filters |
| `lib/api/gnosiplexio.ts` | Frontend API client |

---

## 7. Build Phases

### Phase 1: Core Graph Engine (Week 1)
- Graph store (NetworkX + JSON export)
- VF adapter — read existing VF profiles into graph
- Basic node/edge creation from VF profile chunks
- Metadata index integration
- CLI: `gnosiplexio ingest --source vf`

### Phase 2: Network Enrichment (Week 1-2)
- NetworkCitation vector extraction from citation contexts
- NetworkCredibility scoring algorithm
- Organic enrichment pipeline (ingest → enrich → propagate)
- CrossPerspective detection (supportive/critical/extends)
- CLI: `gnosiplexio query "what is X cited for?"`

### Phase 3: API & Integration (Week 2)
- REST API endpoints
- Veritafactum integration (graph-aware citation verification)
- Citalio integration (graph-ranked citation recommendations)
- Generic adapter for non-VF data sources

### Phase 4: Visualisation (Week 2-3)
- Interactive graph canvas (D3.js / Cytoscape.js)
- Network view, ego view, timeline view
- Node sidebar with network knowledge
- Filter and search
- Export (image, JSON, BibTeX)

### Phase 5: Self-Growth & Intelligence (Week 3+)
- Automatic re-enrichment when new papers are added
- ConceptEvolution tracking
- RelativePosition recalculation
- Community detection and research cluster identification
- Anomaly detection (papers that should cite each other but don't)

---

## 8. Relationship to Other Spells

```
                    ┌─────────────────┐
                    │   Gnosiplexio   │
                    │  (Knowledge     │
                    │   Graph)        │
                    └───────┬─────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
    ┌─────────────┐ ┌──────────┐ ┌───────────────┐
    │Veritafactum │ │ Citalio  │ │Proliferomaxima│
    │ (Verify)    │ │ (Cite)   │ │ (Expand)      │
    └─────────────┘ └──────────┘ └───────────────┘

    Veritafactum → uses graph for citation verification
    Citalio → uses graph for citation recommendation
    Proliferomaxima → feeds new profiles INTO graph → triggers enrichment
    Gnosiplexio → enriches ALL spells with network intelligence
```

Gnosiplexio is the **connective tissue** that makes the entire spell system greater than the sum of its parts.

---

## 9. Independence Guarantee

While Gnosiplexio is VF-native, it MUST work without VF:

```python
# With VF Store
g = Gnosiplexio(adapter=VFStoreAdapter(chroma_path="..."))

# With Zotero library
g = Gnosiplexio(adapter=ZoteroAdapter(library_path="..."))

# With OpenAlex API
g = Gnosiplexio(adapter=OpenAlexAdapter(query="audit accounting"))

# With plain JSON/CSV
g = Gnosiplexio(adapter=GenericAdapter(file="my_papers.json"))

# All adapters support the same operations:
g.ingest(source)    # → builds/enriches graph
g.query(question)   # → searches graph
g.visualize()       # → renders graph
g.export()          # → outputs graph data
```

The adapter pattern ensures Gnosiplexio can serve any research community, any discipline, any knowledge base.

---

## 10. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Knowledge per paper | 8 VF chunks (static) | 8 chunks + N network vectors (growing) |
| Citation verification confidence | Based on single paper's text | Based on N independent academic sources |
| Coverage of uncited knowledge gaps | 0% | Detected via graph analysis |
| Time to understand a paper's significance | Read paper + literature review (hours) | Glance at graph position + network knowledge (seconds) |
| Network enrichment per new paper | 0 (each paper is isolated) | Average 5-15 nodes enriched per ingestion |
| Cross-discipline discovery | Manual | Automatic via community detection + bridge nodes |
| Works with non-VF data sources | No | Yes — any adapter |

---

## 11. What Gnosiplexio Is NOT

- **Not a citation manager** — use Zotero/Mendeley for that; Gnosiplexio consumes their output
- **Not a paper recommender** — that's Citalio's job; Gnosiplexio provides the knowledge Citalio queries
- **Not a replacement for reading** — it's a navigation and discovery layer
- **Not limited to any discipline** — the graph structure is universal; swap the data source and it works for medicine, law, CS, anything

---

## 12. The Magic

What makes Gnosiplexio unique is not any single feature — it's the **organic growth** principle.

Most knowledge graphs are static snapshots. You build them once and they decay. Gnosiplexio is alive. Every paper that enters the system makes every connected paper smarter. The graph doesn't just grow in size — it grows in **depth of understanding**.

A paper cited once is a claim. A paper cited 50 times by credible sources, each adding their own perspective, is **knowledge verified by the collective intelligence of academia itself**.

That's the magic of Gnosiplexio: it weaves individual threads of scholarship into a tapestry of verified, interconnected human knowledge.

---

*Gnosiplexio — γνῶσις woven into plexus. Knowledge, interconnected.* ✨
