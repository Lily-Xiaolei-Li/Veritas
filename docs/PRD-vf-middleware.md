# PRD: Veritafactum Middleware — Citation Profile Database

**Author:** Lily Xiaolei Li & 超级小蕾  
**Date:** 2026-02-15  
**Version:** 2.0 (revised from Knowledge Graph PRD)  
**Status:** Approved for development  

---

## 1. What Is It?

A structured **middleware database** that sits between Veritafactum and the raw library vector store. It replaces noisy semantic search over full-text chunks with **precise, AI-curated profiles** — one per academic work.

Think of it as a **super-powered semantic SQL database** for academic citations.

```
Writer's draft
    ↓
Veritafactum (sentence-level checker)
    ↓ queries
VF Middleware (curated profiles, low noise)    ← THIS
    ↓ falls back to (when needed)
Raw Library Vector Store (867 papers, 9809 chunks, noisy)
```

---

## 2. The Problem

The current VF pipeline searches the raw library vector store directly. This causes:

| Problem | Why It Happens |
|---------|---------------|
| `NOT_IN_LIBRARY` for papers we actually have | Semantic search returns papers that *discuss* a work, not the work itself |
| Irrelevant RAG results | Raw chunks contain noise — footnotes, tangential mentions, literature review lists |
| Cannot verify books or papers without full text | No full text = no vectors = invisible to VF |
| Citation appropriateness is guesswork | No structured data about what a paper should/shouldn't be cited for |
| Slow and expensive per check | Searching 9809 noisy vectors per sentence, many results useless |

**The middleware solves all of these** by providing clean, structured, purpose-built profiles.

---

## 3. Design Philosophy

1. **VF-first** — Every design decision serves Veritafactum's needs. No features for a future product that doesn't exist yet.
2. **One step at a time** — Get the middleware working perfectly, then consider expansion (KG, visualisation, etc.)
3. **Content determines size** — No hard word limits on chunks. A 50-word research question and a 500-word contribution list are both fine. The vector is the same size regardless.
4. **`in_library` is the key flag** — Profiles for papers we have (high confidence) and papers we don't (educated guess from abstract + metadata) coexist in the same system, with a clear confidence signal.
5. **Upgradeable** — When we obtain a paper's full text later, we regenerate chunks 3-8 and flip `in_library` to true.

---

## 4. The 8-Chunk Profile

Every academic work gets **8 structured chunks**. Chunk 1 is structured metadata (JSON). Chunks 2-8 are natural language prose, sized by content (typically 100-300 words, but as much as needed).

### Chunk Schema

| # | Chunk ID | Content | Notes |
|---|----------|---------|-------|
| **1** | `meta` | Structured metadata (JSON) | Author(s), year, title, journal, volume(issue), pages, paper_type, primary_method, secondary_methods, empirical_context, keywords_author, keywords_inferred, `in_library` | 
| **2** | `abstract` | Full abstract as-is | Verbatim from paper or public API. No summarisation. |
| **3** | `theory` | Theoretical framework(s) | What theory it builds on; what theory used to study the phenomenon; or atheoretical. |
| **4** | `literature` | Literature conversation | What literature stream(s) it engages with; what gap it addresses. |
| **5** | `research_questions` | Research question(s) | Explicit RQs or implied ones (common in qualitative work). |
| **6** | `contributions` | Stated contributions | Usually very explicit in the paper. 3-5 items typical. |
| **7** | `key_concepts` | Core concepts and definitions | Technical terms, coined phrases, conceptual frameworks introduced or used. |
| **8** | `cited_for` | AI-generated citation guidance | What this work should be cited for, based on content analysis. |

### Chunk 1: `meta` (Structured JSON)

```json
{
  "authors": ["Power, M."],
  "year": 1997,
  "title": "The Audit Society: Rituals of Verification",
  "journal": null,
  "volume": null,
  "issue": null,
  "pages": null,
  "paper_type": "book",
  "primary_method": "theoretical",
  "secondary_methods": ["historical analysis"],
  "empirical_context": "UK public sector, accounting profession",
  "keywords_author": ["audit", "verification", "accountability"],
  "keywords_inferred": ["audit society", "audit explosion", "constitutive audit"],
  "in_library": false
}
```

**`in_library` flag meanings:**
- `true` — We have the full text in library-rag. Chunks 3-8 are generated from full paper analysis. **High confidence.**
- `false` — We don't have the full text. Chunks 3-8 are educated guesses from abstract + public metadata. **Medium confidence.** Clearly labelled as inferred. Upgradeable when full text is obtained.

### Chunk 1 enables exact matching

VF's first question is always: "Does this paper exist?" This is **not** a semantic search question. It's an exact lookup:

```
Input: "Power (1997)"
→ Parse: author="Power", year=1997
→ Query meta chunk: authors CONTAINS "Power" AND year = 1997
→ Result: FOUND / NOT_FOUND
```

Microseconds, not milliseconds. Zero noise.

### Chunks 2-8: Natural language, no hard limits

- Embedding model (BGE-M3) supports 8192 tokens per chunk — even 1000 words is fine
- Vector dimension is always 1024 regardless of text length
- Storage cost per vector is identical (4KB) whether the source text is 50 or 500 words
- **Guideline for AI profile generation:** "Write as much as the content requires. Typically 100-300 words. Do not pad. Do not truncate important information."

---

## 5. Two Source Types

### Type A: In-Library Papers (`in_library: true`)

We have 867 full-text papers in library-rag.

**Generation process:**
1. Read full paper text from library-rag
2. Send to sonnet with structured prompt → 8-chunk output
3. Chunk 1 (meta): extracted from paper metadata + AI inference
4. Chunk 2 (abstract): verbatim from paper
5. Chunks 3-8: AI analysis of full text
6. Store in Qdrant `vf_profiles` collection + metadata index

**Confidence: HIGH** — based on full text analysis.

### Type B: External Works (`in_library: false`)

Books, classic papers, works not yet obtained. These are works cited in our library but whose full text we don't have.

**Generation process:**
1. Obtain metadata from public APIs (CrossRef, Semantic Scholar, OpenAlex) or manual entry
2. Obtain abstract from same APIs (usually available)
3. Chunk 1 (meta): from API data
4. Chunk 2 (abstract): from API data
5. Chunks 3-8: AI educated guess based on abstract + metadata
6. Each chunk clearly tagged: *"Based on abstract analysis. Full text not available."*

**Confidence: MEDIUM** — abstracts are author-written summaries; authors are very careful with abstracts, so educated guesses from them are usually close.

**Upgrade path:** When we obtain the full text:
1. Re-run AI analysis on full text
2. Regenerate chunks 3-8
3. Flip `in_library` to `true`
4. Confidence automatically upgrades to HIGH

---

## 6. Storage Architecture

### Primary: Qdrant Collection `vf_profiles`

Separate from the raw `academic_papers` collection. Clean, curated, purpose-built.

```
Collection: vf_profiles
  Vectors: ~6,936+ (867 papers × 8 chunks, plus external works)
  Embedding: BGE-M3 (1024 dimensions)
  
  Payload per vector:
  {
    "paper_id": "Power_1997",        // Canonical ID
    "chunk_id": "cited_for",          // Which of the 8 chunks
    "chunk_index": 8,                 // Numeric index (1-8)
    "in_library": false,              // Key confidence flag
    "source_type": "external",        // "library" or "external"
    "text": "Power (1997) should be cited for..."  // The actual content
  }
```

### Secondary: Metadata Index (JSON or SQLite)

Fast exact lookup without embedding search:

```json
{
  "Power_1997": {
    "authors": ["Power, M."],
    "year": 1997,
    "title": "The Audit Society",
    "in_library": false,
    "profile_exists": true,
    "chunks_generated": 8,
    "last_updated": "2026-02-15"
  }
}
```

Answers "is this paper in our system?" in microseconds.

---

## 7. How VF Uses the Middleware

### Current Flow (noisy)
```
VF sentence: "Power (1997) argues audit has expanded..."
  → Semantic search 9809 raw chunks
  → Returns: chunks that MENTION Power, not Power's own work
  → Result: unreliable
```

### New Flow (with middleware)
```
VF sentence: "Power (1997) argues audit has expanded..."
  → Step 1: Parse citation → author="Power", year=1997
  → Step 2: Metadata lookup → Power_1997 FOUND (in_library: false)
  → Step 3: Retrieve chunk 8 (cited_for): 
      "Should be cited for: audit society concept, rituals of 
       verification, constitutive role of audit, audit explosion"
  → Step 4: Compare claim "audit has expanded" ↔ cited_for → MATCH
  → Step 5: Retrieve chunk 3 (theory) if deeper check needed
  → Result: VERIFIED (confidence: MEDIUM — abstract-based profile)
```

### Fallback
If a cited work is **not in the middleware at all** (no profile exists):
1. VF flags as `UNKNOWN` (not `NOT_IN_LIBRARY` — different meaning now)
2. Optionally: auto-create a stub profile from API lookup (async, for next run)
3. Fall back to raw library search as current behaviour

---

## 8. Build Plan

### Phase 0: Pilot (5-10 papers) — 1-2 hours
- Pick Power series + 5 core audit papers
- Generate 8-chunk profiles manually with sonnet
- Validate: are the chunks useful for VF? Does exact matching work?
- Test VF integration with profiles vs raw search
- **Exit criteria:** VF produces better results with profiles than without

### Phase 1: Batch Generation — In-Library Papers — 2-4 hours
- Script reads each of 867 papers from library-rag
- Sends to sonnet with structured prompt → 8-chunk JSON
- Stores in Qdrant `vf_profiles` + metadata index
- **Estimated cost:** ~$10-15 (sonnet, one-time)
- **Estimated time:** 2-4 hours (rate-limited API calls)

### Phase 2: External Works — 1-2 hours
- Scan all 867 profiles for outbound citations
- Identify cited works not in library (books, missing papers)
- Fetch metadata + abstract from CrossRef / Semantic Scholar / OpenAlex
- Generate profiles with `in_library: false`
- **Estimated:** 50-200 additional profiles

### Phase 3: VF Integration — 1 day
- New `profile_searcher.py` replacing current `rag_searcher.py`
- Metadata exact match → profile lookup → structured verification
- Fallback to raw library for unknown works
- Update VF classifier prompts to use structured profile data

### Phase 4: Testing & Tuning — 1 day
- Run VF on full Paper 2 Introduction with middleware
- Compare results: before (raw search) vs after (middleware)
- Tune profile generation prompts based on VF accuracy
- Document failure cases for iteration

---

## 9. What This Is NOT (Yet)

- **Not a knowledge graph** — No graph relationships, no visualisation, no traversal. That's a future product.
- **Not auto-correction** — VF suggests, human decides. Unchanged.
- **Not limited to accounting** — The 8-chunk structure is domain-agnostic. Swap the library = new field.
- **Not limited to full-text papers** — `in_library: false` profiles work for any citable work: books, reports, standards, anything.

### Future Expansion (parked, not designed)
When the time comes to build a Knowledge Graph product:
- Add more chunks (connections, lineage, debates, etc.)
- Add graph edges between profiles
- Add visualisation layer
- The 8-chunk middleware becomes the foundation, not a constraint

---

## 10. Success Metrics

| Metric | Current (raw search) | Target (with middleware) |
|--------|---------------------|------------------------|
| Citation existence check accuracy | ~60% (semantic search misses) | **>95%** (exact metadata match) |
| `NOT_IN_LIBRARY` false positives | Frequent | **Near zero** |
| Citation appropriateness check | AI guesswork | **Evidence-based** (cited_for chunk) |
| Coverage of works without full text | 0% | **80%+** (abstract-based profiles) |
| VF query speed per sentence | ~7.5s (RAG search) | **<2s** (metadata + profile lookup) |
| Noise in search results | High (raw chunks) | **Near zero** (curated profiles) |

---

## 11. Cost Summary

| Item | Cost | Frequency |
|------|------|-----------|
| Profile generation (867 in-library papers) | ~$10-15 | One-time |
| Profile generation (external works) | ~$5-10 | One-time |
| Profile updates (new papers added) | ~$0.02/paper | As needed |
| Storage (Qdrant vectors) | Negligible (local) | Ongoing |
| VF per-sentence query cost | Near zero (local lookup) | Per check |

**Total initial investment: ~$15-25.** Then near-zero marginal cost.

---

*"先把地基打牢，再盖高楼。VF middleware就是这个地基。"*

*Prepared by Super Xiaolei for Master Lily Xiaolei Li 🌟*  
*2026-02-15 v2.0*
