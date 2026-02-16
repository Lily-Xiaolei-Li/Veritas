# PRD: Proliferomaxima ✨

**Spell Name:** Proliferomaxima — 极致增殖  
**Version:** 1.0  
**Author:** 超级小蕾  
**Date:** 2026-02-16  
**Status:** Draft  

---

## 1. Overview

Proliferomaxima is a spell that massively expands the VF (Veritas Fingerprint) Store by extracting reference lists from existing library papers, resolving them to academic sources via free APIs, fetching abstracts, and generating VF profiles in **no-full-text mode**.

**Core promise:** Turn 1,277 library papers into **tens of thousands** of VF profiles by harvesting their citation networks.

---

## 2. User Flow

1. User clicks **✨ Proliferomaxima** button in the **+ Source** toolbar
2. System scans `library-rag/data/parsed/` for reference list markdown files
3. Extracts structured reference items (title, authors, year, DOI)
4. Deduplicates against previously scanned items AND existing VF Store entries
5. Queries free APIs (CrossRef / Semantic Scholar) to resolve metadata + abstract
6. Filters: **only items with abstracts proceed** (no abstract = no VF value)
7. Generates VF profiles in no-full-text mode (inferred from abstract)
8. Stores profiles with metadata flag `full_article: false`
9. Reports summary: added / skipped / failed

---

## 3. Technical Design

### 3.1 Phase 1: Reference Extraction

**Input:** Markdown files in `library-rag/data/parsed/`  
**Output:** Structured reference items

```python
# Scan each markdown for reference section
# Headings to match: "References", "Bibliography", "Works Cited", "Reference List"
# Parse each reference item into:
{
    "raw_text": "Smith, J. (2020). Title of paper. Journal, 10(2), 1-15. doi:10.1234/...",
    "title": "Title of paper",
    "authors": ["Smith, J."],
    "year": 2020,
    "doi": "10.1234/...",
    "source_paper": "filename_of_citing_paper.md"
}
```

**Parsing strategy (ordered by reliability):**
1. **DOI regex** — most reliable identifier: `10\.\d{4,}/[^\s]+`
2. **Structured regex** — Author (Year). Title. Journal patterns
3. **LLM fallback** — for messy/non-standard formats, batch parse via LLM

### 3.2 Phase 2: Deduplication

Two-level dedup:
1. **Scan history** — maintain `proliferomaxima_scanned.json` tracking previously processed reference items (by DOI or title+year hash). Skip anything already scanned.
2. **VF Store check** — before generating a profile, query VF Store. If a profile already exists with `full_article: true`, **do not overwrite** (full record is superior). If profile exists with `full_article: false`, also skip (already populated).

### 3.3 Phase 3: API Resolution

**Primary:** CrossRef API (`https://api.crossref.org/works/{doi}`)
- Free, no API key needed
- Rate limit: 50 req/sec (polite pool with `mailto` header)
- Returns: title, authors, abstract, journal, year, ISSN, etc.

**Fallback:** Semantic Scholar API (`https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}`)
- Free tier: 100 req/sec
- Better abstract coverage for CS/AI papers

**For items without DOI:** Query by title via CrossRef `/works?query.bibliographic={title}`

**Filter gate:** Only proceed if abstract is non-empty. Log skipped items.

### 3.4 Phase 4: VF Profile Generation

Reuse existing `POST /api/v1/vf/generate` endpoint with a new flag:

```json
{
    "text": "<abstract + resolved metadata>",
    "source": "proliferomaxima",
    "mode": "abstract_only",
    "metadata": {
        "title": "...",
        "authors": ["..."],
        "year": 2020,
        "doi": "10.1234/...",
        "full_article": false,
        "inferred_from": "abstract",
        "cited_by": ["source_paper_1.md", "source_paper_2.md"]
    }
}
```

**VF chunks generated (inferred from abstract):**
- `meta` — from API metadata (reliable)
- `abstract` — directly from API (reliable)
- `theory` — inferred from abstract (flagged as inferred)
- `contributions` — inferred from abstract (flagged as inferred)
- `key_concepts` — inferred from abstract (flagged as inferred)
- `cited_for` — **derived from the citing paper's context** (why was this referenced?)

**Note on `cited_for`:** The citing paper's reference context (the sentence surrounding the citation) provides valuable signal for what this paper is cited for. Extract this context during Phase 1.

### 3.5 Metadata Flag

Each VF profile stores:
```json
{
    "full_article": false,
    "confidence": "inferred",
    "source_spell": "proliferomaxima"
}
```

This allows Citalio and Checker to weight full-article profiles higher than abstract-only profiles when ranking results.

---

## 4. New Files

### Backend Services
| File | Purpose |
|------|---------|
| `services/proliferomaxima/__init__.py` | Package init |
| `services/proliferomaxima/ref_extractor.py` | Parse markdown → structured references |
| `services/proliferomaxima/dedup.py` | Scan history + VF Store dedup |
| `services/proliferomaxima/api_resolver.py` | CrossRef / Semantic Scholar API calls |
| `services/proliferomaxima/batch_engine.py` | Orchestrator: extract → dedup → resolve → generate |

### API Route
| File | Purpose |
|------|---------|
| `routes/proliferomaxima_routes.py` | `POST /run`, `GET /status/{run_id}`, `GET /results/{run_id}` |

### CLI
| File | Purpose |
|------|---------|
| `cli/proliferomaxima_handlers.py` | `proliferomaxima run`, `status`, `results` |

### Frontend
| File | Purpose |
|------|---------|
| `components/proliferomaxima/ProliferomaximaPanel.tsx` | UI panel in + Source toolbar |

### Data
| File | Purpose |
|------|---------|
| `data/proliferomaxima_scanned.json` | Scan history for dedup |
| `data/proliferomaxima_skipped.json` | Items skipped (no abstract, API fail, etc.) |

---

## 5. Integration Points

- **+ Source toolbar** — new button triggers Proliferomaxima
- **VF Store** — writes new profiles with `full_article: false` flag
- **VF Generate API** — reuses existing endpoint with `mode: "abstract_only"`
- **Citalio / Checker** — automatically benefits from expanded VF Store; can optionally weight `full_article: true` profiles higher

---

## 6. Rate Limits & Error Handling

| Scenario | Action |
|----------|--------|
| CrossRef rate limit (429) | Pause 20s, retry 3x |
| Semantic Scholar rate limit | Pause 10s, retry 3x |
| No abstract returned | Skip, log to `skipped.json` |
| VF generate API rate limit | Pause 20min (existing behavior) |
| Duplicate in VF Store | Skip silently |
| Malformed reference | Log warning, skip |
| Network timeout | Retry 2x, then skip |

---

## 7. Estimated Performance

| Metric | Estimate |
|--------|----------|
| References per paper (avg) | 30-50 |
| Total raw references (1,277 papers) | ~40,000-60,000 |
| Unique after dedup | ~8,000-15,000 |
| With retrievable abstract | ~60-70% → 5,000-10,000 |
| VF profiles generated | **5,000-10,000** |
| Total processing time | **6-12 hours** |

---

## 8. Success Criteria

- [ ] VF Store expanded by **10x or more** from current count
- [ ] Zero overwrite of existing `full_article: true` profiles
- [ ] All new profiles flagged `full_article: false`
- [ ] Scan history persisted for incremental re-runs
- [ ] Citalio/Checker immediately benefits from expanded store
- [ ] Processing completes within 12 hours for full library

---

## 9. Future Enhancements

- **Citation context extraction** — capture the sentence in the citing paper where each reference appears, enriching `cited_for`
- **Recursive proliferation** — run Proliferomaxima on the *newly added* papers' reference lists (2nd degree citations)
- **Full-text upgrade path** — when a user later adds the full paper, auto-upgrade `full_article: false → true`
- **Confidence scoring** — weight inferred profiles lower in search ranking

---

*Proliferomaxima — 从种子到森林，一咒增殖万千。* ✨
