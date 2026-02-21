# Technical Design Document: Sentence-Level Academic Checker

**Project:** Veritas (ABR)  
**Author:** 超级小蕾 (Design) + 老爷 (Vision)  
**Date:** 2026-02-14  
**Status:** Approved for Development  

---

## 1. Executive Summary

A sentence-level academic writing quality tool that replaces the current whole-section Referencer workflow. It processes each sentence individually through RAG search, LLM analysis, and rule-based checks, producing an annotated document with colour-coded highlights and actionable comments — like a supercharged "spelling check" for academic rigour.

### Core Problem
- Referencing gaps are the **biggest sin** in academic writing
- Current ABR Referencer processes entire sections at once → misses nuances, produces shallow results
- Manual sentence-by-sentence checking is extremely time-consuming for scholars
- No existing tool combines RAG-powered citation checking with AI writing quality analysis

### Solution
An integrated ABR tool that:
1. Splits text into sentences
2. Classifies each sentence by type (prior work / common knowledge / original material / original contribution)
3. Searches RAG library for each sentence's claims and terms
4. Detects AI writing patterns
5. Checks contextual flow between sentences
6. Produces an annotated document with colour-coded highlights and comments
7. **Human makes all final decisions** — the tool suggests, never auto-corrects

---

## 2. Sentence Classification System

Every sentence falls into one of four categories:

| Type | Colour | Label | Description | Action |
|------|--------|-------|-------------|--------|
| **Prior Work** | 🔴 Red | `CITE_NEEDED` | Claim/concept from existing literature that must be cited | Suggest specific citation(s) from RAG |
| **Common Knowledge** | ✅ Green | `COMMON` | Well-established fact, no citation needed | Confirm, no action |
| **Original Material** | 🔵 Blue | `OWN_EMPIRICAL` | Author's own data/findings/fieldwork | Tag source section (e.g., "See Section 6") |
| **Original Contribution** | 🟡 Gold | `OWN_CONTRIBUTION` | Author's novel argument/theorisation | Confirm authorial voice, no citation |

### Additional Flags (can co-occur with any type)

| Flag | Colour | Label | Description |
|------|--------|-------|-------------|
| **Citation Exists but Wrong** | 🟠 Orange | `MISATTRIBUTED` | Citation present but may be incorrectly attributed |
| **Citation Exists and Correct** | ⬜ None | `VERIFIED` | Citation present and verified against RAG library |
| **AI Pattern Detected** | 🟣 Purple | `AI_PATTERN` | Sentence shows typical AI writing markers |
| **Weak Transition** | ⚪ Grey underline | `FLOW_ISSUE` | Poor connection with preceding/following sentence |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                 ABR Frontend                      │
│  ┌──────────────────────────────────────────┐    │
│  │   Tiptap Editor + Annotation Layer       │    │
│  │   - Colour highlights per sentence       │    │
│  │   - Inline comments/suggestions          │    │
│  │   - Accept/Reject/Ignore controls        │    │
│  └──────────────────────────────────────────┘    │
└──────────────────┬──────────────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────────────┐
│              ABR Backend                          │
│  ┌──────────────────────────────────────────┐    │
│  │   /api/v1/checker/run                    │    │
│  │   /api/v1/checker/status/:runId          │    │
│  │   /api/v1/checker/results/:artifactId    │    │
│  └──────────────────────┬───────────────────┘    │
│                         │                         │
│  ┌──────────────────────▼───────────────────┐    │
│  │   Sentence Checker Engine (Python)        │    │
│  │                                           │    │
│  │   Step 1: Sentence Splitting              │    │
│  │   Step 2: Claim/Term Extraction           │    │
│  │   Step 3: RAG Search (per sentence)       │    │
│  │   Step 4: Sentence Classification         │    │
│  │   Step 5: AI Pattern Detection            │    │
│  │   Step 6: Flow/Transition Check           │    │
│  │   Step 7: Report Generation               │    │
│  └──────────────┬───────────┬───────────────┘    │
│                 │           │                     │
│  ┌──────────────▼──┐  ┌────▼────────────────┐    │
│  │  RAG Library    │  │  LLM (via Gateway)  │    │
│  │  (ChromaDB)     │  │  claude-opus-4-6    │    │
│  └─────────────────┘  └─────────────────────┘    │
└──────────────────────────────────────────────────┘
```

---

## 4. Processing Pipeline (Detailed)

### Step 1: Sentence Splitting

**Challenge:** Academic sentences are long, contain nested clauses, parenthetical citations, and semicolon-separated lists.

**Approach:** Two-pass splitting:

```python
# Pass 1: NLP sentence boundary detection
import spacy
nlp = spacy.load("en_core_web_sm")
doc = nlp(text)
raw_sentences = [sent.text.strip() for sent in doc.sents]

# Pass 2: Academic-aware post-processing
# - Don't split on "et al." or "e.g." or "i.e."
# - Don't split inside parenthetical citations "(Power, 2021; Butler, 2010)"
# - Merge fragments that are clearly continuations
# - Handle footnotes (split separately, tag as footnote)
sentences = academic_sentence_cleanup(raw_sentences)
```

**Output:** List of `Sentence` objects:
```python
@dataclass
class Sentence:
    id: int                    # Sequential index
    text: str                  # The sentence text
    start_offset: int          # Character offset in original text
    end_offset: int            # Character offset end
    paragraph_id: int          # Which paragraph it belongs to
    existing_citations: list   # Citations already present in the sentence
    is_footnote: bool          # Whether it's a footnote
```

### Step 2: Claim & Term Extraction

For each sentence, extract searchable elements:

```python
@dataclass  
class SentenceAnalysis:
    sentence: Sentence
    claims: list[str]          # Paraphrased claims for RAG search
    key_terms: list[str]       # Technical terms, proper nouns, concepts
    named_scholars: list[str]  # Scholar names mentioned (even without citation)
    search_queries: list[str]  # Generated RAG search queries
```

**Method:** LLM call per sentence (can batch 5-10 sentences per call for efficiency):

```
System: You are an academic citation analyst. For each sentence, extract:
1. The core claim(s) being made
2. Key technical terms or concepts that may have originated from specific scholars
3. Any scholar names mentioned
4. 2-3 semantic search queries to find relevant sources

Be precise. If the sentence is common knowledge or the author's own argument, say so.
```

### Step 3: RAG Search (Per Sentence)

For each sentence's `search_queries`:

```python
async def search_for_sentence(analysis: SentenceAnalysis) -> list[RAGResult]:
    results = []
    for query in analysis.search_queries:
        # Search the academic library
        hits = await rag_library.search(
            query=query,
            top_k=5,
            threshold=0.7  # Similarity threshold
        )
        results.extend(hits)
    
    # Also search by key terms (exact/fuzzy match)
    for term in analysis.key_terms:
        term_hits = await rag_library.search(
            query=term,
            top_k=3,
            threshold=0.75
        )
        results.extend(term_hits)
    
    # Also search by scholar names if mentioned
    for scholar in analysis.named_scholars:
        scholar_hits = await rag_library.search(
            query=scholar,
            top_k=3,
            filter={"author": scholar}  # Metadata filter
        )
        results.extend(scholar_hits)
    
    # Deduplicate and rank
    return deduplicate_and_rank(results)
```

**Output per sentence:** Top 5-10 relevant source chunks with metadata (author, year, title, page, relevance score).

### Step 4: Sentence Classification

LLM call with rich context (the sentence + its RAG results + surrounding sentences):

```
System: You are a senior academic reviewer. Classify this sentence and provide recommendations.

Context:
- Previous sentence: "..."
- CURRENT SENTENCE: "..."  
- Next sentence: "..."
- Existing citations in sentence: [list]
- RAG library search results: [top results with source info]

Classify the sentence into exactly ONE primary type:
1. CITE_NEEDED — This claim/concept comes from prior literature and needs citation
2. COMMON — This is common knowledge in the field, no citation needed
3. OWN_EMPIRICAL — This is the author's own data/findings, needs section reference
4. OWN_CONTRIBUTION — This is the author's original argument/theorisation

Also check:
- If citations exist: Are they correctly attributed? (VERIFIED / MISATTRIBUTED)
- Confidence level: HIGH / MEDIUM / LOW

Output JSON:
{
  "type": "CITE_NEEDED|COMMON|OWN_EMPIRICAL|OWN_CONTRIBUTION",
  "confidence": "HIGH|MEDIUM|LOW",
  "reasoning": "Brief explanation",
  "suggested_citations": ["Author (Year) - reason"],
  "citation_verification": [{"citation": "Power (2021)", "status": "VERIFIED|MISATTRIBUTED|NOT_IN_LIBRARY", "note": "..."}],
  "section_reference": "Section 6" // only for OWN_EMPIRICAL
}
```

### Step 5: AI Pattern Detection

Check each sentence for common AI writing markers:

```python
AI_PATTERNS = {
    "hedge_stacking": r"(it is important to note|it should be noted|it is worth mentioning)",
    "empty_transitions": r"(furthermore|moreover|additionally|in addition),?\s",
    "filler_phrases": r"(in the context of|in terms of|with respect to|in light of)",
    "ai_superlatives": r"(crucial|pivotal|paramount|indispensable|transformative)",
    "passive_overuse": "passive voice ratio > 60%",
    "list_of_three": r"pattern of exactly three examples/adjectives",
    "generic_hedging": r"(may|might|could)\s+(potentially|possibly|arguably)",
    "robotic_topic_sentences": r"^(This|These|The) (section|paper|study|analysis) (examines|explores|investigates)",
}

# Also LLM-based detection for subtler patterns
def detect_ai_patterns(sentence: str, context: str) -> list[AIFlag]:
    # Rule-based check first (fast, cheap)
    flags = rule_based_ai_check(sentence)
    
    # LLM check for subtle patterns (batch with Step 4 to save calls)
    # "Does this sentence read naturally for academic prose, 
    #  or does it have markers of AI-generated text?"
    return flags
```

### Step 6: Flow & Transition Check

Analyse sentence-to-sentence coherence:

```python
@dataclass
class FlowCheck:
    sentence_id: int
    prev_connection: str       # "strong" | "adequate" | "weak" | "missing"
    next_connection: str
    suggestion: str | None     # e.g., "Consider a transition phrase"
    topic_shift: bool          # Abrupt topic change?
```

**Method:** Batch LLM call per paragraph (check all sentence transitions at once):

```
Analyse the flow between these sentences. For each transition, rate:
- STRONG: Natural logical progression
- ADEQUATE: Acceptable but could be smoother  
- WEAK: Abrupt shift, needs transitional language
- MISSING: No logical connection, possible restructuring needed
```

### Step 7: Report Generation

Compile all results into two outputs:

#### Output A: Annotated Markdown (for backend storage as artifact)

```markdown
# Sentence Checker Report: Paper2_Introduction_Final.md
**Run Date:** 2026-02-14 23:30 AEST  
**Sentences Analysed:** 47  
**Issues Found:** 12 citations needed, 3 AI patterns, 2 flow issues

## Annotated Text

[🔴 CITE_NEEDED | HIGH] "A substantial body of research has shown how auditing 
enables, formats, and frames organisational conduct, market credibility, and 
governmental accountability."
> **Suggestion:** Already cited (Power 1995-2003; Simnett et al. 2009; etc.) ✅ VERIFIED
> **RAG Match:** Power (1997) Ch.2 p.34 — "audit shapes what counts as..."

[✅ COMMON] "Over the past three decades, empirical work has tracked audit's 
expansion from financial statements into sustainability reporting..."
> **Status:** Common knowledge claim, adequately supported by following citations.

[🟡 OWN_CONTRIBUTION] "We argue that our understanding of audit's constitutive 
capacity can be enriched by attending to settings in which audit does not verify 
pre-existing objects but brings them into existence."
> **Status:** Original contribution statement. Clearly marked as authorial claim. ✅

...
```

#### Output B: Structured JSON (for frontend annotation layer)

```json
{
  "artifact_id": "366b2cf5-...",
  "run_id": "checker-run-001",
  "timestamp": "2026-02-14T23:30:00+11:00",
  "summary": {
    "total_sentences": 47,
    "cite_needed": 12,
    "common": 15,
    "own_empirical": 8,
    "own_contribution": 12,
    "ai_patterns": 3,
    "flow_issues": 2,
    "misattributed": 0,
    "verified_citations": 28
  },
  "annotations": [
    {
      "sentence_id": 1,
      "start_offset": 0,
      "end_offset": 142,
      "type": "CITE_NEEDED",
      "confidence": "HIGH",
      "colour": "#EF4444",
      "reasoning": "Core literature claim requires citation",
      "suggested_citations": [
        {"ref": "Power (1997)", "source": "RAG", "relevance": 0.92, "snippet": "..."},
        {"ref": "Simnett et al. (2009)", "source": "RAG", "relevance": 0.87, "snippet": "..."}
      ],
      "existing_citations_status": [
        {"citation": "Power, 1995", "status": "VERIFIED"}
      ],
      "ai_flags": [],
      "flow": {"prev": null, "next": "STRONG"}
    },
    // ... more annotations
  ]
}
```

---

## 5. Frontend Integration

### 5.1 Annotation Layer (Tiptap)

Leverage existing Tiptap extensions + add new ones:

```typescript
// Already installed:
import Highlight from '@tiptap/extension-highlight'     // Multi-colour highlights
import Color from '@tiptap/extension-color'             // Text colour
import TextStyle from '@tiptap/extension-text-style'    // Custom styles

// New extension needed:
// SentenceAnnotation — custom mark that stores checker metadata
const SentenceAnnotation = Mark.create({
  name: 'sentenceAnnotation',
  addAttributes() {
    return {
      type: { default: 'COMMON' },           // CITE_NEEDED, COMMON, etc.
      confidence: { default: 'HIGH' },
      annotationId: { default: null },        // Links to annotation data
      colour: { default: '#22C55E' },         // Highlight colour
    }
  },
  // Renders as coloured background highlight with hover tooltip
})
```

### 5.2 UI Components

#### Checker Panel (new panel, alongside existing Prompt/Conversation/History)

```
┌─────────────────────────────────────────────┐
│ 📋 Checker Results          [Re-run] [Export]│
├─────────────────────────────────────────────┤
│ Summary: 47 sentences | 12 🔴 3 🟣 2 ⚪     │
├─────────────────────────────────────────────┤
│ Filter: [All] [🔴 Cite] [🟡 Own] [🟣 AI]  │
├─────────────────────────────────────────────┤
│ #1 🔴 HIGH "A substantial body of..."      │
│   └ Suggest: Power (1997) ✅ Already cited  │
│   └ [Accept] [Dismiss] [Edit]               │
│                                              │
│ #5 🔴 HIGH "activities are simultaneously..."│
│   └ Suggest: Power (1996, 1997)             │
│   └ RAG: 92% match in Power_1997.md:p34    │
│   └ [Accept] [Dismiss] [Edit]               │
│                                              │
│ #12 🟣 MED "Furthermore, this analysis..."  │
│   └ AI pattern: "Furthermore" + hedge stack │
│   └ Suggest: Rephrase opening               │
│   └ [Accept] [Dismiss] [Edit]               │
│                                              │
│ #23 ⚪ LOW "We then analyse..."             │
│   └ Flow: Weak transition from #22          │
│   └ Suggest: Add connecting phrase           │
│   └ [Accept] [Dismiss] [Edit]               │
└─────────────────────────────────────────────┘
```

#### Inline Annotations (in Tiptap editor)

- Sentences highlighted with type colour (background)
- Hover on highlighted sentence → tooltip with classification + reasoning
- Click → expand annotation panel to that sentence
- Small gutter icons (🔴🟡🔵✅🟣⚪) in left margin per sentence

#### Accept/Reject Flow

- **Accept citation suggestion** → auto-insert citation at cursor (if supported) or copy to clipboard
- **Dismiss** → mark as reviewed, remove highlight
- **Edit** → open inline edit for the suggestion text
- **Bulk actions**: "Accept all VERIFIED", "Dismiss all COMMON"

### 5.3 Checker Trigger

Two ways to invoke:

1. **Context menu on artifact** → "Run Sentence Checker" (right-click or toolbar button)
2. **Integrated into ABR workflow** → New persona "The Checker" replaces "The Referencer"

---

## 6. Backend API Endpoints

### New Routes

```python
# POST /api/v1/checker/run
# Body: { "artifact_id": "...", "options": { "check_citations": true, "check_ai": true, "check_flow": true } }
# Response: { "run_id": "...", "status": "queued", "estimated_time": "2-5 min" }

# GET /api/v1/checker/status/:runId
# Response: { "status": "running", "progress": { "current": 23, "total": 47, "step": "classification" } }

# GET /api/v1/checker/results/:artifactId
# Response: { full annotation JSON from Step 7 Output B }

# POST /api/v1/checker/accept
# Body: { "annotation_id": "...", "action": "accept|dismiss|edit", "edit_text": "..." }

# WebSocket: /ws/checker/:runId  
# Real-time progress updates as sentences are processed
```

### Database Schema

```sql
-- Checker runs
CREATE TABLE checker_runs (
    id TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    status TEXT DEFAULT 'queued',  -- queued, running, completed, failed
    options JSON,
    summary JSON,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Individual sentence annotations
CREATE TABLE checker_annotations (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    sentence_id INTEGER,
    sentence_text TEXT,
    start_offset INTEGER,
    end_offset INTEGER,
    type TEXT,                      -- CITE_NEEDED, COMMON, OWN_EMPIRICAL, OWN_CONTRIBUTION
    confidence TEXT,
    colour TEXT,
    reasoning TEXT,
    suggested_citations JSON,
    citation_verification JSON,
    ai_flags JSON,
    flow_check JSON,
    user_action TEXT,               -- null, accepted, dismissed, edited
    user_action_at TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES checker_runs(id)
);
```

---

## 7. Cost & Performance Estimates

### Per-sentence costs (approximate)

| Step | Method | Cost per sentence | Time |
|------|--------|-------------------|------|
| Splitting | Local (spaCy) | $0 | <1s total |
| Claim extraction | LLM (batched 5/call) | ~$0.005 | ~2s |
| RAG search | ChromaDB local | $0 | ~0.5s |
| Classification | LLM (per sentence) | ~$0.02 | ~3s |
| AI detection | Rule-based + LLM | ~$0.005 | ~1s |
| Flow check | LLM (batched per ¶) | ~$0.005 | ~1s |

### Per-paper estimates (50-sentence Introduction)

| Metric | Estimate |
|--------|----------|
| Total LLM calls | ~60-70 |
| Total API cost | ~$1.50-2.50 |
| Total processing time | ~3-5 minutes |
| RAG searches | ~150-200 queries |

**Verdict:** Very affordable. A human reviewer would spend 2-4 hours on the same task.

### Optimisation Strategies

1. **Batch LLM calls** — Send 5-10 sentences per call where possible (claim extraction, flow check)
2. **Parallel processing** — RAG searches can run concurrently (asyncio)
3. **Cache RAG results** — Same terms across sentences don't need re-searching
4. **Incremental re-runs** — Only re-check modified sentences on subsequent runs
5. **Confidence-based skip** — Skip detailed RAG search for sentences already well-cited (quick pre-filter)

---

## 8. Implementation Plan

### Phase 1: Core Engine (Python backend) — ~3-4 days

| Task | Effort | Priority |
|------|--------|----------|
| Sentence splitter with academic-aware rules | 0.5 day | P0 |
| Claim/term extraction (LLM prompts) | 0.5 day | P0 |
| RAG search integration (per-sentence) | 0.5 day | P0 |
| Sentence classifier (LLM prompts) | 1 day | P0 |
| AI pattern detector (rule-based) | 0.5 day | P1 |
| Flow/transition checker | 0.5 day | P1 |
| Report generator (Markdown + JSON) | 0.5 day | P0 |
| Backend API routes + DB schema | 0.5 day | P0 |

### Phase 2: Frontend Integration (React/Tiptap) — ~3-4 days

| Task | Effort | Priority |
|------|--------|----------|
| SentenceAnnotation Tiptap extension | 1 day | P0 |
| Checker Results panel component | 1 day | P0 |
| Inline highlight rendering | 0.5 day | P0 |
| Hover tooltips + gutter icons | 0.5 day | P1 |
| Accept/Reject/Edit flow | 0.5 day | P0 |
| WebSocket progress updates | 0.5 day | P1 |
| "Run Checker" button in UI | 0.5 day | P0 |

### Phase 3: Polish & Testing — ~1-2 days

| Task | Effort | Priority |
|------|--------|----------|
| Test with real Paper 2 Introduction | 0.5 day | P0 |
| Tune LLM prompts based on results | 0.5 day | P0 |
| Batch/performance optimisation | 0.5 day | P1 |
| Export annotated report as PDF/Word | 0.5 day | P2 |

**Total estimated effort: ~8-10 days**

---

## 9. File Structure

```
Veritas/
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   │   └── checker_routes.py        # New API endpoints
│   │   ├── services/
│   │   │   └── checker/
│   │   │       ├── __init__.py
│   │   │       ├── engine.py            # Main orchestrator
│   │   │       ├── splitter.py          # Sentence splitting
│   │   │       ├── extractor.py         # Claim/term extraction
│   │   │       ├── classifier.py        # Sentence classification
│   │   │       ├── ai_detector.py       # AI pattern detection
│   │   │       ├── flow_checker.py      # Transition analysis
│   │   │       ├── rag_searcher.py      # Per-sentence RAG search
│   │   │       └── report_generator.py  # Output formatting
│   │   └── models/
│   │       └── checker.py               # DB models
│   └── tests/
│       └── test_checker/
│           ├── test_splitter.py
│           ├── test_classifier.py
│           └── test_integration.py
├── frontend/
│   └── src/
│       ├── components/
│       │   └── checker/
│       │       ├── CheckerPanel.tsx      # Results panel
│       │       ├── AnnotationTooltip.tsx # Hover tooltip
│       │       ├── CheckerControls.tsx   # Run/filter controls
│       │       └── AnnotationCard.tsx    # Individual annotation UI
│       └── lib/
│           └── extensions/
│               └── sentenceAnnotation.ts # Tiptap extension
└── docs/
    └── DESIGN-sentence-checker.md        # This document
```

---

## 10. Future Enhancements (Post-MVP)

1. **Reference list validator** — Cross-check all in-text citations against the reference list at the end of the paper
2. **Style guide enforcement** — Harvard vs APA vs AOS-specific formatting rules
3. **Cross-section consistency** — Check that claims made in Introduction match Discussion/Conclusion
4. **Collaborative review** — Multiple reviewers can add annotations, resolve conflicts
5. **Learning from corrections** — Track which suggestions the user accepts/rejects, improve prompts over time
6. **Full paper pipeline** — Run checker across all sections, not just Introduction
7. **Export to Word** — Generate .docx with Track Changes / Comments for supervisor review

---

## Appendix A: Example LLM Prompts

### Claim Extraction Prompt

```
You are an academic citation analyst specialising in accounting and auditing research.

For each sentence below, extract:

1. **Claims**: What factual or theoretical claims does this sentence make? 
   (A claim is any statement that could be true or false, supported or unsupported)
2. **Key Terms**: Technical terms, named concepts, or jargon that may originate from specific scholars
3. **Named Scholars**: Any scholars mentioned by name (with or without citation)
4. **Search Queries**: 2-3 semantic search queries to find relevant sources in an academic library

If the sentence is clearly common knowledge (e.g., "Australia is a country"), mark it as COMMON.
If the sentence is clearly the author's own argument (e.g., "We argue that..."), mark it as OWN.

Sentences:
[1] "A substantial body of research has shown how auditing enables, formats, and frames organisational conduct (Power, 1995, 1997)."
[2] "..."

Output as JSON array.
```

### Classification Prompt

```
You are a senior academic reviewer at a top accounting journal (AOS, AAAJ, or similar).

Your task: Classify this sentence and check its citations.

CONTEXT:
- Paper topic: [extracted from artifact metadata]
- Previous sentence: "[text]"  
- >>> CURRENT SENTENCE: "[text]" <<<
- Next sentence: "[text]"
- Existing citations in this sentence: [list]

RAG LIBRARY SEARCH RESULTS (most relevant sources found):
[1] Author (Year), Title — "relevant snippet..." (similarity: 0.92)
[2] Author (Year), Title — "relevant snippet..." (similarity: 0.85)
[3] ...

CLASSIFY into exactly ONE type:
- CITE_NEEDED: This sentence makes a claim from prior literature that requires citation.
  → Which citation(s) should be added? Use RAG results if relevant.
- COMMON: This is field-level common knowledge. No citation needed.
- OWN_EMPIRICAL: This reports the author's own fieldwork data or findings. 
  → Which section of the paper does this come from?
- OWN_CONTRIBUTION: This is the author's original theoretical argument.
  → No citation needed, but verify it reads as authorial voice.

ALSO CHECK:
- For each existing citation: Is it correctly attributed based on RAG results? 
  (VERIFIED / MISATTRIBUTED / NOT_IN_LIBRARY)
- Confidence: HIGH (certain) / MEDIUM (likely but debatable) / LOW (uncertain)

Output valid JSON only.
```

---

## Appendix B: AI Pattern Detection Rules

```python
AI_PATTERNS = {
    # Structural patterns
    "triple_structure": {
        "regex": r"(first|second|third|firstly|secondly|thirdly)",
        "note": "Excessive use of numbered enumerations",
        "severity": "low"
    },
    "hedge_stacking": {
        "regex": r"(it is (important|worth|crucial) to (note|mention|highlight|emphasize))",
        "note": "Filler phrase — adds no content",
        "severity": "medium"  
    },
    "moreover_chain": {
        "regex": r"^(Moreover|Furthermore|Additionally|In addition),",
        "note": "Generic transition — consider removing or replacing with content-specific connector",
        "severity": "medium"
    },
    
    # Vocabulary patterns
    "ai_adjectives": {
        "regex": r"\b(crucial|pivotal|paramount|groundbreaking|transformative|indispensable|noteworthy|compelling)\b",
        "note": "Overused AI-favoured adjective",
        "severity": "low"
    },
    "ai_verbs": {
        "regex": r"\b(delve|underscore|shed light|navigate|unpack|leverage|foster)\b",
        "note": "Stereotypical AI verb choice",
        "severity": "medium"
    },
    
    # Structural patterns  
    "empty_topic_sentence": {
        "regex": r"^(This (section|paper|study|analysis|article) (examines|explores|investigates|addresses|discusses))",
        "note": "Generic topic sentence — consider leading with the actual argument",
        "severity": "low"
    },
    "in_conclusion_opener": {
        "regex": r"^In (conclusion|summary|sum),",
        "note": "Clichéd opener — the section heading already signals this",
        "severity": "low"
    }
}
```
