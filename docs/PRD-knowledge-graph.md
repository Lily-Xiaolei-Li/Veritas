# PRD: Veritafactum Knowledge Graph (VF-KG)

**Author:** Barry Li & 超级小蕾  
**Date:** 2026-02-15  
**Status:** Draft for review  

---

## 1. What is it?

A structured knowledge system that represents academic literature as a network of **papers, concepts, authors, and their relationships** — built from AI-generated profiles, not raw text chunks.

It can run standalone or embed into Agent-B-Research (ABR). It serves three consumers: **human researchers** (visual exploration), **Veritafactum** (citation verification), and **ABR's AI personas** (grounded academic reasoning).

---

## 2. The problem it solves

| Problem | Current state | VF-KG solution |
|---------|--------------|----------------|
| "Is this citation in our library?" | Semantic search — unreliable, returns papers that *discuss* the cited work | Metadata index with exact Author_Year matching |
| "Is this citation appropriate for this claim?" | AI guesses without evidence | Structured `cited_for` field built from peer-reviewed sources |
| "We don't have the full text (books, old papers)" | Cannot verify at all | **Inferred profiles** constructed from papers that cite it |
| "How does this concept connect to other work?" | Manual literature review | Knowledge graph with traversable relationships |
| "What has Power (1997) actually been cited for?" | Depends on AI's training data | Evidence-based: "23 papers in our library cite it for X, Y, Z" |

---

## 3. Core concept: The 10-Chunk Profile

Every work in the system (paper, book, chapter) gets a standardised profile of **10 structured chunks**, each ≤150 words. No overlap. Each chunk has a defined role:

| # | Chunk role | Content | Graph output |
|---|-----------|---------|-------------|
| 1 | `identity` | Author, year, title, journal, type (article/book/chapter) | Paper node |
| 2 | `core_argument` | Central thesis and main claims (3-5 sentences) | ARGUES → Concept nodes |
| 3 | `methodology` | Research approach, data, analytical framework | Method node |
| 4 | `key_findings` | Primary findings and conclusions | Finding nodes |
| 5 | `cited_for` | What this work is typically cited to support — with evidence sources | CITED_FOR edges |
| 6 | `not_for` | Common misapplications or unsuitable uses | Constraint edges |
| 7 | `key_concepts` | Core terms and definitions introduced or used | DEFINES → Concept nodes |
| 8 | `context` | Empirical setting, industry, geography, time period | Domain nodes |
| 9 | `lineage` | Theoretical ancestry — what it builds on, extends, responds to | EXTENDS / BUILDS_ON edges |
| 10 | `connections` | Citation relationships: who it cites, who cites it, debates | CITES / DEBATES edges |

---

## 4. Two profile types

### Direct profiles (we have the full text)
- AI reads the full paper once → generates 10 chunks
- High confidence, low cost (~$0.01-0.02 per paper with sonnet)
- Covers all 867 papers currently in library-rag

### Inferred profiles (no full text available)
- System scans existing library for papers that cite this work
- Extracts citation contexts (the sentences/paragraphs around each citation)
- AI synthesises a profile from these credible academic sources
- Each `cited_for` entry carries evidence: *"cited by [Paper A, Paper B, Paper C] for claim X"*
- Confidence scales with evidence count: 1 source = LOW, 2-3 = MEDIUM, 4+ = HIGH
- Covers books (Power 1997), classic works, and papers not yet obtained

---

## 5. Self-growing knowledge base

Every VF scan of a new document can feed back into the knowledge graph:

```
VF scans Paper X
  → Paper X cites Power (1997) in context of "audit as constitutive practice"
  → System checks: is this usage already in Power (1997) profile?
     → Yes: increment evidence count
     → No: add new cited_for entry with Paper X as evidence source
  → Power (1997) profile gets richer automatically
```

The more documents are scanned, the more accurate verification becomes.

---

## 6. Storage architecture

### Vector layer (Qdrant)
- New collection: `vfkg_profiles` (separate from raw `academic_papers`)
- ~8,670 vectors (867 papers × 10 chunks) + inferred profiles
- Each vector carries metadata: `paper_id`, `chunk_role`, `source_type` (direct/inferred)
- Enables: semantic search, VF citation lookup, RAG queries

### Graph layer (lightweight)
- Option A: NetworkX (Python, in-memory, good for <10K nodes) — simplest
- Option B: Neo4j (persistent, scalable, native graph queries) — if we need scale
- Option C: JSON graph file (zero dependencies, export to any visualiser)
- Nodes: Paper, Concept, Author, Method, Domain
- Edges: ARGUES, EXTENDS, BUILDS_ON, CITES, DEBATES, CITED_FOR, DEFINES

### Metadata index (JSON/SQLite)
- Fast exact lookup: `Author_Year` → paper_id → profile exists? → direct or inferred?
- No embedding needed — pure string matching
- Answers "is this paper in our library?" in microseconds

---

## 7. Consumer interfaces

### 7a. Veritafactum (API)
```
VF checks sentence: "Power (1997) argues that audit has expanded..."
  1. Metadata lookup: Power_1997 → FOUND (inferred profile)
  2. Retrieve chunk 5 (cited_for): "audit expansion — HIGH confidence (5 sources)"
  3. Compare claim ↔ cited_for → APPROPRIATE
  4. Return: VERIFIED with evidence trail
```

### 7b. Human researcher (GUI)
- **Search**: "What is performativity in audit?" → returns relevant papers + concept network
- **Explore**: Click a paper → see its 10-chunk profile, connections, who cites it
- **Visualise**: Interactive graph — zoom, filter by year/author/concept, trace citation chains
- **Timeline**: How a concept evolved: 1997 → 2003 → 2021 → your paper
- Embedded in ABR as a new tab, or standalone web page

### 7c. ABR AI personas (API)
- Drafter asks: "What papers discuss recursive performativity?"
- System returns structured results from KG, not raw text chunks
- Higher quality grounding than current semantic search

---

## 8. Build phases

### Phase 0: Pilot (10-20 papers)
- Pick Power series + core audit papers
- Generate 10-chunk profiles manually/with AI
- Validate structure — are the chunks useful for VF? Are the graph edges meaningful?
- Estimated effort: 1-2 hours

### Phase 1: Batch generation (867 papers)
- Script reads each paper's full text from library-rag
- Sends to sonnet with structured prompt → 10-chunk JSON output
- Store in Qdrant + metadata index
- Estimated cost: $10-15 (sonnet, one-time)
- Estimated time: 2-4 hours (rate-limited)

### Phase 2: Inferred profiles
- Scan all 867 profiles for outbound citations
- Identify cited works not in library (books, missing papers)
- Generate inferred profiles from citation contexts
- Estimated: 50-200 additional profiles

### Phase 3: VF integration
- Replace current rag_searcher.py with KG-aware searcher
- Metadata exact match → profile lookup → structured verification
- Major accuracy improvement for citation checking

### Phase 4: Knowledge graph visualisation
- Frontend component in ABR (D3.js or Cytoscape.js)
- Interactive exploration, filtering, timeline view
- API endpoints for graph queries

### Phase 5: Self-growth loop
- VF scans automatically feed back new evidence into profiles
- Periodic re-synthesis of inferred profiles as evidence accumulates

---

## 9. What this is NOT

- **Not a replacement for reading papers** — it's a navigation and verification layer
- **Not auto-correction** — VF suggests, human decides (unchanged)
- **Not limited to accounting/audit** — the 10-chunk structure is domain-agnostic; swap the library and it works for any field
- **Not dependent on having every paper** — inferred profiles handle gaps gracefully

---

## 10. Success metrics

| Metric | Current | Target |
|--------|---------|--------|
| VF citation verification rate | ~10% (only papers with exact RAG match) | >90% (metadata + profiles) |
| "NOT_IN_LIBRARY" for papers we have | Frequent (semantic search misses) | Near zero |
| Coverage of cited works without full text | 0% | 80%+ via inferred profiles |
| Time to answer "what is X cited for?" | Manual literature review (~hours) | Seconds (graph query) |
| Knowledge growth per VF scan | Zero (static library) | Incremental (self-growing) |

---

## 11. Portability

The 10-chunk profile structure and knowledge graph are **not tied to ABR**. The same system can be embedded in:

- **Veritas** (audit working paper suite) — same verification logic, different domain
- **Any academic writing tool** — the structure is discipline-agnostic
- **Standalone knowledge explorer** — just the graph + visualisation, no VF

---

*"Veritas + Factum = truth grounded in evidence, verified by the network of human knowledge itself."*
