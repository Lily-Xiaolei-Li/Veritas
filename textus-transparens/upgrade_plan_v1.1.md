# Implementation Plan: Textus Transparens (TT) v1.1 "Academic Excellence"

This document outlines the architectural, database, and procedural upgrades required to transition TT from a functional qualitative MVP to an AOS/AAAJ-compliant academic workbench.

---

## 1. Database Schema Extensions

To support theoretical frameworks, case mappings, and explicit bridging of concepts, the following SQLAlchemy models must be introduced or extended.

```python
# 1. Theoretical Frameworks
class TheoreticalFramework(Base):
    __tablename__ = "theoretical_frameworks"
    framework_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

class FrameworkDimension(Base):
    __tablename__ = "framework_dimensions"
    dimension_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    framework_id: Mapped[int] = mapped_column(ForeignKey("theoretical_frameworks.framework_id"))
    name: Mapped[str] = mapped_column(String(255))
    definition: Mapped[Text] = mapped_column(Text)
    # Maps which codes represent this dimension
    mapped_code_id: Mapped[Optional[int]] = mapped_column(ForeignKey("codes.code_id"))

# 2. Case Assignments (Linking Sources to Cases for Advanced Matrices)
class CaseAssignment(Base):
    __tablename__ = "case_assignments"
    assignment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.case_id"))
    source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sources.source_id"))
    extract_id: Mapped[Optional[int]] = mapped_column(ForeignKey("extracts.extract_id"))
    assigned_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

# 3. Code Intersections (Storing Tensions & Overlaps for `ai sense` / manual bridge)
class CodeIntersection(Base):
    __tablename__ = "code_intersections"
    intersection_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    extract_id: Mapped[int] = mapped_column(ForeignKey("extracts.extract_id"))
    code_a_id: Mapped[int] = mapped_column(ForeignKey("codes.code_id"))
    code_b_id: Mapped[int] = mapped_column(ForeignKey("codes.code_id"))
    relationship_type: Mapped[str] = mapped_column(String(50)) # "tension", "overlap", "causal"
    rationale: Mapped[Text] = mapped_column(Text)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
```

---

## 2. New Module Architectures

The v1.1 release will introduce four major management modules to encapsulate the new logic, keeping the CLI layer thin and the core auditable.

*   **`framework_manager.py`:** 
    *   *Purpose:* CRUD operations for Theoretical Frameworks and their dimensions.
    *   *Key Methods:* `create_framework()`, `map_dimension_to_code()`, `get_framework_hierarchy()`.
*   **`ai_sense_manager.py`:**
    *   *Purpose:* Orchestrates the 'ai sense' workflow. Fetches unmapped extracts, constructs the framework context prompt, queries the LLM, and persists results to the `CodeIntersection` table as pending review.
*   **`advanced_matrix_manager.py`:**
    *   *Purpose:* The engine for generating cross-tabulated reports.
    *   *Key Methods:* `build_matrix(x_axis, y_axis)`, calculating Density (raw count), Breadth (distinct sources/cases), and fetching top enriched quotes via BGE-M3 semantic scoring.
*   **`narrative_manager.py`:**
    *   *Purpose:* Generates the chronological audit trail.
    *   *Key Methods:* `synthesize_evolution()`. Merges data from `AuditLog`, `Memo`, and `JudgementNote` sorted by `created_at` to feed into the reporting engine.
*   **`gpviz_export_manager.py`:**
    *   *Purpose:* Uses `networkx` and `numpy` to calculate co-occurrence frequencies and cosine similarities between codes, generating the target JSON graph output.

---

## 3. CLI Specifications

Every command prioritizes explicit parameters and audit-logging. Manual counterparts guarantee fallback.

### 3.1 Framework & 'AI Sense'
*   **`tt framework create --name "Power's 7" --file dims.json`**
    *   Registers a theoretical framework.
*   **`tt ai sense --framework <id> [--source <id>]`**
    *   Scans extracts against the framework. Identifies overlaps and tensions. Places suggestions in a review queue.
*   **`tt ai sense-review`**
    *   Interactive prompt to accept/reject/edit the AI-identified tensions (enforces Human-in-the-Loop).

### 3.2 Manual Counterparts (Reproducibility Fallback)
*   **`tt code intersect --code-a <id> --code-b <id>`**
    *   *Action:* Queries and lists extracts where both codes co-occur.
*   **`tt judgement manually-bridge --extract <id> --code-a <id> --code-b <id> --type "tension" --rationale "..."`**
    *   *Action:* Manually asserts an intersection, logging it to `CodeIntersection` with a rigorous rationale.

### 3.3 Advanced Matrices & Cases
*   **`tt case assign --case <case_id> --source <source_id>`**
    *   *Action:* Maps a source document to a defined case.
*   **`tt report matrix --advanced --x-axis "case_attr:Role" --y-axis "theme"`**
    *   *Action:* Generates a matrix report.
    *   *Outputs:* Density, Breadth, and a Markdown table of highly-representative extracts.

### 3.4 Audit & Narrative
*   **`tt report evolution --start-date YYYY-MM-DD --format markdown`**
    *   *Action:* Triggers `narrative_manager.py`. Uses an LLM (with rigorous chain-of-thought) to summarize the chronological development of the codebook.

---

## 4. AI Prompt Engineering Strategies

To ensure AOS/AAAJ compliance, prompts must prohibit hallucination and mandate citing internal database primary keys.

### 4.1 Strategy: `ai sense` (Theoretical Mapping)
*   **Technique:** Context-Constrained Analytical Extraction
*   **System Prompt Focus:** 
    > "You are an expert qualitative researcher applying the provided theoretical framework. Analyze the following `<extract>`. Identify if multiple dimensions of the framework intersect within this text. Focus strictly on 'overlaps' (concepts reinforcing each other) or 'tensions' (concepts in conflict). For every intersection identified, you MUST output a JSON object containing `code_a`, `code_b`, `relationship_type`, and a `rationale` citing the exact wording from the text. Do not invent dimensions not provided."

### 4.2 Strategy: `report evolution` (Narrative Generation)
*   **Technique:** Chronological Synthesis with Mandatory Citations
*   **System Prompt Focus:**
    > "You are compiling an audit-trail narrative for a methodology chapter. You are provided with a chronological list of `[AuditLogs]`, `[JudgementNotes]`, and `[Memos]`. Synthesize these into a coherent narrative explaining *how and why* the theory evolved over time. 
    > **Strict Rule:** Every analytical claim you make MUST be followed by the ID of the note or log that supports it (e.g., [Memo-42], [Judgement-12]). Do not summarize; explain the structural shifts in the researcher's theoretical sensitivity."

---

## 5. Export Format Specification: `gp-viz`

The JSON schema outputted by `tt export gp-viz` is designed for ingestion by modern graph visualization libraries (e.g., Three.js, Cytoscape).

**File:** `semantic_landscape.json`
**Schema Specification:**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "GP-Viz Semantic Landscape",
  "type": "object",
  "properties": {
    "metadata": {
      "type": "object",
      "properties": {
        "project_id": { "type": "integer" },
        "generated_at": { "type": "string", "format": "date-time" },
        "total_extracts": { "type": "integer" }
      }
    },
    "nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "label": { "type": "string" },
          "weight": { "type": "integer", "description": "Frequency of code assignment" },
          "sentiment_score": { "type": "number", "description": "Optional NLP sentiment average" },
          "cluster": { "type": "string", "description": "Assigned Theme/Cluster name" }
        },
        "required": ["id", "label", "weight", "cluster"]
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "source": { "type": "string" },
          "target": { "type": "string" },
          "type": { "type": "string", "enum": ["co-occurrence", "semantic_similarity", "tension"] },
          "strength": { "type": "number", "description": "Raw frequency or cosine similarity score" },
          "extract_ids": { "type": "array", "items": { "type": "integer" } }
        },
        "required": ["source", "target", "type", "strength"]
      }
    },
    "trajectories": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "code_id": { "type": "string" },
          "timeline": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp": { "type": "string", "format": "date-time" },
                "weight": { "type": "integer" },
                "context_summary": { "type": "string" }
              }
            }
          }
        },
        "required": ["code_id", "timeline"]
      }
    }
  },
  "required": ["metadata", "nodes", "edges", "trajectories"]
}
```

---

## 6. Phased Development Roadmap

This targets the v1.1 goal in controlled, verifiable stages.

**Phase 1: Foundation (DB Schema & Manual Counterparts)**
*   Implement `TheoreticalFramework`, `CaseAssignment`, `CodeIntersection` models.
*   Update SQLAlchemy migrations via Alembic.
*   Implement `tt framework create` and `tt case assign` commands.
*   Implement manual bridging and intersection detection: `tt code intersect` & `tt judgement manually-bridge`.
*   *Validation:* Verify an analyst can manually create a framework, assign cases, and bridge codes without any AI assistance.

**Phase 2: Reporting & Exports**
*   Develop `advanced_matrix_manager.py`.
*   Implement `tt report matrix --advanced` (calculating Breadth/Density).
*   Develop `gpviz_export_manager.py` (fetching BGE-M3 semantic similarity scores).
*   Implement `tt export gp-viz` to generate `semantic_landscape.json`.
*   *Validation:* Validate matrix outputs against expected cross-tabulations. Verify JSON schema parsing.

**Phase 3: AI Capabilities**
*   Develop `ai_sense_manager.py`. Integrate the theoretical mapping prompts (incorporating Scholar-in-the-Loop constraints).
*   Implement `tt ai sense` and `tt ai sense-review` queue.
*   Develop `narrative_manager.py` and implement `tt report evolution`.
*   *Validation:* Ensure all AI recommendations populate the pending queue, and that the evolution report correctly cites valid DB entries.

**Phase 4: Academic Polish & Integration Tests**
*   Write comprehensive end-to-end integration tests (e.g., executing a full "Academic Excellence" workflow using CLI scripts).
*   Draft documentation on AOS/AAAJ compliance (e.g., explaining the rigorous auditing of `ai sense`).
*   Deploy v1.1 release package.
