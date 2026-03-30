# Kasumi Integration Plan for Veritas

**Version:** 1.0
**Date:** 2026-03-28
**Author:** Ying (Academic Research Assistant)
**Status:** Draft — Pending review

---

## 1. Executive Summary

This document specifies how to embed **Kasumi Nexcel** (spreadsheet) and **Kasumi Wordo** (document editor) as first-class artifact types inside **Veritas**, the academic research workbench. The goal is to let researchers create, view, and edit rich spreadsheets and formatted documents directly within Veritas sessions, alongside existing markdown and code artifacts, and feed them into the persona-driven drafting workflow.

### Design Principles

1. **Black-box embedding** — Kasumi remains a standalone application. Veritas wraps it, never forks it.
2. **Reuse existing infrastructure** — Artifacts are stored in the existing Veritas PostgreSQL database and file system. No new databases.
3. **Minimal coupling** — Communication between Veritas and Kasumi happens through two narrow interfaces: (a) a JSON envelope stored on disk, and (b) an iframe + postMessage protocol for editing.
4. **Forward-compatible versioning** — Every stored artifact carries a schema version, enabling Kasumi upgrades without breaking old artifacts.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     Veritas Frontend (React)                     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Artifact Panel (ArtifactBrowser)              │  │
│  │  ┌──────────┬────────┬──────────────┬───────────────────┐ │  │
│  │  │ Markdown │  Code  │  Nexcel      │  Wordo            │ │  │
│  │  │ (Tiptap) │(Monaco)│  (iframe)    │  (iframe)         │ │  │
│  │  └──────────┴────────┴──────────────┴───────────────────┘ │  │
│  └──────────────────────┬─────────────────────────────────────┘  │
│                         │ postMessage                             │
│  ┌──────────────────────▼─────────────────────────────────────┐  │
│  │          Kasumi Embed Host (localhost:5174)                 │  │
│  │  ┌─────────────────┐  ┌──────────────────────┐            │  │
│  │  │  Nexcel Shell    │  │  Wordo Shell          │            │  │
│  │  │  (standalone)    │  │  (standalone)          │            │  │
│  │  └─────────────────┘  └──────────────────────┘            │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
         │                              │
    ┌────▼──────────┐          ┌───────▼────────┐
    │ Veritas       │          │ Kasumi         │
    │ Backend       │          │ API Server     │
    │ (port 8000)   │          │ (port 3001)    │
    │               │          │                │
    │ PostgreSQL    │          │ (stateless,    │
    │ + File Store  │          │  optional)     │
    └───────────────┘          └────────────────┘
```

### Key Boundaries

| Concern | Owner | Notes |
|---------|-------|-------|
| Artifact CRUD, persistence, auth | Veritas | Existing system, unchanged |
| Spreadsheet editing UI | Kasumi Nexcel | Runs in iframe |
| Document editing UI | Kasumi Wordo | Runs in iframe |
| Data serialization format | Shared contract | Versioned JSON envelope (§3) |
| LLM integration, personas, RAG | Veritas | Unchanged |

---

## 3. Versioned Artifact Envelope

All Kasumi artifacts are stored as **JSON files on the Veritas file system**, using the existing artifact storage mechanism. Each file follows a versioned envelope format.

### 3.1 Nexcel Envelope

```jsonc
{
  "kasumi_type": "nexcel",
  "envelope_version": 1,
  "kasumi_version": "1.2.0",       // Kasumi version that produced this
  "created_at": "2026-03-28T...",
  "updated_at": "2026-03-28T...",

  "table": {
    "name": "Emission Factors by Sector",
    "fields": [
      // Array of FieldMeta — Kasumi's canonical type
      { "id": 1, "name": "Sector", "type": "text", "order": 0, "primary": true, "readOnly": false },
      { "id": 2, "name": "Scope 1 (tCO2e)", "type": "number", "order": 1, "primary": false, "readOnly": false, "numberDecimalPlaces": 2 },
      { "id": 3, "name": "Source", "type": "single_select", "order": 2, "primary": false, "readOnly": false,
        "selectOptions": [
          { "id": 1, "value": "NGER", "color": "#3b82f6" },
          { "id": 2, "value": "EPA", "color": "#10b981" }
        ]
      }
    ],
    "rows": [
      // Array of RowRecord — Kasumi's canonical type
      { "id": 1, "order": "1.00", "fields": { "1": "Energy", "2": 12450.5, "3": "NGER" } },
      { "id": 2, "order": "2.00", "fields": { "1": "Transport", "2": 3200.0, "3": "EPA" } }
    ]
  },

  // Optional view state (not canonical data, can be discarded on upgrade)
  "view_state": {
    "sort": { "fieldId": 2, "direction": "desc" },
    "filters": [],
    "frozen_cols": 1,
    "col_widths": { "1": 200, "2": 120, "3": 150 },
    "hidden_field_ids": []
  }
}
```

### 3.2 Wordo Envelope

```jsonc
{
  "kasumi_type": "wordo",
  "envelope_version": 1,
  "kasumi_version": "1.2.0",
  "created_at": "2026-03-28T...",
  "updated_at": "2026-03-28T...",

  "document": {
    // KasumiDocument — Kasumi's canonical IR
    "id": "doc_abc123",
    "title": "Literature Review Draft — Carbon Assurance",
    "styleRegistry": [],
    "defaultPageStyle": {
      "id": "default",
      "size": "A4",
      "orientation": "portrait",
      "margins": { "top": 25.4, "bottom": 25.4, "left": 25.4, "right": 25.4, "header": 12.7, "footer": 12.7 },
      "differentFirstPage": false,
      "differentOddEven": false
    },
    "sections": [
      {
        "id": "sec_001",
        "pageStyle": { /* ... */ },
        "blocks": [
          { "type": "heading", "id": "blk_001", "level": 1, "content": [{ "text": "Introduction", "marks": [] }] },
          { "type": "paragraph", "id": "blk_002", "content": [{ "text": "This section reviews...", "marks": [] }], "alignment": "left", "indentLevel": 0, "lineSpacing": 1.5, "spaceBefore": 0, "spaceAfter": 6 }
        ],
        "footnotes": []
      }
    ],
    "createdAt": "2026-03-28T...",
    "updatedAt": "2026-03-28T..."
  },

  // Optional editor state (can be discarded on upgrade)
  "editor_state": {
    "focused_section_id": "sec_001",
    "comments": [],
    "track_changes": []
  }
}
```

### 3.3 Versioning Contract

| Field | Purpose | Compatibility Rule |
|-------|---------|-------------------|
| `envelope_version` | Veritas-side schema version for the wrapper | Veritas increments this when the envelope structure changes. Old envelopes must remain loadable. |
| `kasumi_version` | Kasumi release that last wrote this artifact | Kasumi must maintain backward-compatible deserialization for at least N-2 minor versions. |
| `kasumi_type` | Discriminator (`"nexcel"` or `"wordo"`) | Immutable once created. |

**Forward compatibility rules:**

1. **Kasumi upgrades** — When Kasumi opens an artifact written by an older version, it must silently migrate the data in memory (add new fields with defaults, ignore unknown fields). The envelope is re-written with the new `kasumi_version` on save.
2. **Envelope upgrades** — If Veritas changes the envelope structure, a migration function converts old envelopes on first read. The `envelope_version` is bumped on save.
3. **Unknown fields** — Both sides must tolerate and preserve unknown top-level keys (pass-through). This allows either side to add metadata without breaking the other.
4. **Canonical data vs. view state** — The `table`/`document` payload is canonical and must be migrated carefully. The `view_state`/`editor_state` is ephemeral and can be discarded if incompatible.

---

## 4. Veritas Backend Changes

### 4.1 Artifact Model — No Schema Change Required

The existing artifact model already supports this integration:

| Existing Field | Usage for Kasumi |
|----------------|-----------------|
| `extension` | `"nexcel.json"` or `"wordo.json"` |
| `mime_type` | `"application/x-kasumi-nexcel+json"` or `"application/x-kasumi-wordo+json"` |
| `artifact_type` | `"file"` (unchanged) |
| `artifact_meta` | `{ "kasumi_type": "nexcel", "envelope_version": 1 }` |
| `storage_path` | Standard path, file content is the JSON envelope |
| `draft_content` | Used for auto-save of in-progress edits |

No Alembic migration needed. The existing JSON `artifact_meta` field absorbs all Kasumi-specific metadata.

### 4.2 Artifact Service — Preview Support

Extend `get_preview_kind()` in `backend/app/artifact_service.py`:

```python
# Add to the extension → preview_kind mapping
KASUMI_EXTENSIONS = {"nexcel.json", "wordo.json"}

def get_preview_kind(extension: str, mime_type: str | None) -> str:
    if extension in ("nexcel.json",):
        return "nexcel"          # New preview kind
    if extension in ("wordo.json",):
        return "wordo"           # New preview kind
    # ... existing logic unchanged
```

Add preview kinds `"nexcel"` and `"wordo"` to the `ArtifactPreviewKind` enum.

### 4.3 Artifact Creation Endpoint — Convenience Helper

Add one new endpoint (optional, for cleaner UX):

```
POST /sessions/{session_id}/artifacts/kasumi
Body: {
  "kasumi_type": "nexcel" | "wordo",
  "display_name": "Emission Factors.nexcel.json",
  "initial_data": { ... }  // Optional: pre-populated envelope content
}
```

This is a thin wrapper around the existing `create_artifact_internal()` that:
1. Generates a blank envelope if `initial_data` is omitted
2. Sets the correct extension, mime_type, and artifact_meta
3. Writes the JSON to disk

Alternatively, the frontend can call the existing `POST /sessions/{session_id}/artifacts` with the envelope as text content. No new endpoint strictly required.

### 4.4 LLM Context Extraction

When a Kasumi artifact is attached to a persona prompt (e.g., Drafter with artifact context), the backend must serialize its content into a text representation the LLM can consume.

```python
# In the chat/prompt assembly logic
def extract_llm_context(artifact: Artifact) -> str:
    """Convert artifact content to LLM-readable text."""
    meta = artifact.artifact_meta or {}

    if meta.get("kasumi_type") == "nexcel":
        envelope = json.loads(read_artifact_content(artifact))
        table = envelope["table"]
        # Render as markdown table for LLM consumption
        headers = [f["name"] for f in sorted(table["fields"], key=lambda f: f["order"])]
        rows = []
        for row in table["rows"]:
            cells = [str(row["fields"].get(str(f["id"]), "")) for f in sorted(table["fields"], key=lambda f: f["order"])]
            rows.append(cells)
        return render_markdown_table(headers, rows)

    if meta.get("kasumi_type") == "wordo":
        envelope = json.loads(read_artifact_content(artifact))
        doc = envelope["document"]
        # Render as markdown for LLM consumption
        return wordo_to_markdown(doc)

    # Existing behavior for other types
    return read_artifact_content_as_text(artifact)
```

**`wordo_to_markdown()`** walks the `sections[].blocks[]` tree and renders:
- HeadingBlock → `# Heading`
- ParagraphBlock → plain text with inline marks
- ListItemBlock → `- ` or `1. `
- TableBlock → markdown table
- NexcelEmbedBlock → `[Embedded spreadsheet: {caption}]`
- CodeBlock → fenced code block

This ensures that when the Reviewer persona receives a Wordo artifact, it sees clean markdown — not raw JSON.

---

## 5. Veritas Frontend Changes

### 5.1 Type Extensions

In `frontend/src/lib/api/types.ts`:

```typescript
// Extend preview kinds
export type ArtifactPreviewKind =
  | "text" | "code" | "markdown" | "image" | "none"
  | "nexcel" | "wordo";   // ← new

// Kasumi envelope types (for type safety)
export interface NexcelEnvelope {
  kasumi_type: "nexcel";
  envelope_version: number;
  kasumi_version: string;
  created_at: string;
  updated_at: string;
  table: {
    name: string;
    fields: KasumiFieldMeta[];
    rows: KasumiRowRecord[];
  };
  view_state?: Record<string, unknown>;
}

export interface WordoEnvelope {
  kasumi_type: "wordo";
  envelope_version: number;
  kasumi_version: string;
  created_at: string;
  updated_at: string;
  document: KasumiDocument;
  editor_state?: Record<string, unknown>;
}

export type KasumiEnvelope = NexcelEnvelope | WordoEnvelope;
```

### 5.2 ArtifactPreview — New Renderers

In `ArtifactPreview.tsx`, extend the renderer switch:

```tsx
// Existing renderers
if (preview.kind === "markdown") return <TiptapEditor ... />
if (preview.kind === "code")     return <MonacoEditor ... />

// New Kasumi renderers
if (preview.kind === "nexcel") return <NexcelArtifactView artifact={artifact} onSave={handleSave} />
if (preview.kind === "wordo")  return <WordoArtifactView  artifact={artifact} onSave={handleSave} />
```

### 5.3 NexcelArtifactView Component

```
┌─────────────────────────────────────────────┐
│ Emission Factors by Sector    [Edit] [Export]│
│─────────────────────────────────────────────│
│ Read-only table preview                      │
│ (rendered from envelope JSON,                │
│  uses a simple HTML table — NOT Kasumi)      │
│                                              │
│  Sector     │ Scope 1 (tCO2e) │ Source       │
│  Energy     │ 12,450.50       │ NGER         │
│  Transport  │ 3,200.00        │ EPA          │
│                                              │
│ 2 rows × 3 fields                            │
└─────────────────────────────────────────────┘
```

**Read mode:** Veritas renders a lightweight HTML table from the envelope JSON. No Kasumi dependency.

**Edit mode:** On clicking [Edit], Veritas opens a modal/panel containing an iframe pointed at the Kasumi embed host:

```
iframe src = http://localhost:5174/embed/nexcel
  ?data=<base64-encoded envelope JSON>
  &origin=veritas
```

The iframe loads Kasumi's Nexcel shell in embed mode, hydrated with the artifact data. On save, Kasumi posts the updated envelope back:

```typescript
// Inside Kasumi iframe
window.parent.postMessage({
  type: "kasumi:save",
  kasumi_type: "nexcel",
  envelope: { /* updated NexcelEnvelope */ }
}, targetOrigin)
```

Veritas receives the message, serializes the envelope to JSON, and calls `PUT /artifacts/{id}/content` to persist.

### 5.4 WordoArtifactView Component

Same pattern as Nexcel:

- **Read mode:** Render a simplified HTML preview from the document IR (headings, paragraphs, lists). Not pixel-perfect — just readable.
- **Edit mode:** iframe → `http://localhost:5174/embed/wordo?data=<base64>&origin=veritas`
- **Save:** postMessage → Veritas persists updated envelope

### 5.5 New Artifact Creation UI

Add two buttons to the ArtifactBrowser's "New" dropdown:

```
[+ New Artifact ▼]
  ├── Markdown
  ├── Code File
  ├── Nexcel Spreadsheet    ← NEW
  └── Wordo Document        ← NEW
```

Each creates a blank envelope and saves it as a new artifact.

---

## 6. Kasumi Embed Mode

Kasumi needs a new `/embed` route that loads a shell in isolated mode (no shell switcher, no splash, no localStorage persistence).

### 6.1 Embed Route

Add to Kasumi's `frontend/src/`:

```
/embed/nexcel  → NexcelEmbedRoute
/embed/wordo   → WordoEmbedRoute
```

### 6.2 Embed Behavior

| Concern | Standalone Mode | Embed Mode |
|---------|----------------|------------|
| Data source | Baserow API / localStorage | Received via postMessage from parent |
| Persistence | Baserow / localStorage | postMessage back to parent on save |
| Shell switcher | Visible | Hidden |
| Splash | Shown once | Never |
| URL routing | Normal | Hash-based or query-param |
| Access mode | User-selected | Inherited from parent message |

### 6.3 PostMessage Protocol

**Parent → Kasumi (init):**
```typescript
{
  type: "kasumi:init",
  kasumi_type: "nexcel" | "wordo",
  envelope: NexcelEnvelope | WordoEnvelope,
  access_mode: "data-entry" | "analyst" | "admin",
  options: {
    show_toolbar: boolean,
    allow_import: boolean,
    allow_export: boolean
  }
}
```

**Kasumi → Parent (save):**
```typescript
{
  type: "kasumi:save",
  kasumi_type: "nexcel" | "wordo",
  envelope: NexcelEnvelope | WordoEnvelope
}
```

**Kasumi → Parent (close):**
```typescript
{
  type: "kasumi:close",
  kasumi_type: "nexcel" | "wordo",
  dirty: boolean  // true if unsaved changes
}
```

**Kasumi → Parent (resize):**
```typescript
{
  type: "kasumi:resize",
  height: number  // preferred content height in px
}
```

### 6.4 Security

- postMessage `targetOrigin` must be explicitly set to the Veritas origin (e.g., `http://localhost:3000`), never `"*"`.
- Kasumi embed validates that `event.origin` matches the expected Veritas host before processing messages.
- The `data` query parameter is only used for initial bootstrap; subsequent communication uses postMessage exclusively.

---

## 7. LLM Workflow Integration

### 7.1 Artifact Context in Prompts

When a researcher attaches a Kasumi artifact to a prompt, Veritas converts it to LLM-friendly text:

| Artifact Type | LLM Representation |
|---------------|-------------------|
| `nexcel` | Markdown table (headers + rows) + metadata line ("X rows × Y fields") |
| `wordo` | Markdown document (headings, paragraphs, lists) |

This uses the `extract_llm_context()` function from §4.4.

### 7.2 Persona Workflows with Kasumi Artifacts

**Example: Using Nexcel data in a Drafter prompt**

```
Persona: Drafter
Artifacts:
  - paper_body.md (markdown, BACKGROUND)
  - emission_data.nexcel.json (nexcel, DATA SOURCE)
  - template.md (markdown, TEMPLATE)

Prompt: "Draft the Results section. Use the emission data table as
the primary evidence source. Reference specific values from the table."
```

The Drafter sees the Nexcel data as a clean markdown table and can reference specific values.

**Example: Using Wordo for formatted output**

```
Persona: Drafter
Artifacts:
  - draft_v2.wordo.json (wordo, DRAFT TARGET)
  - review_report.md (markdown, REVIEW)

Prompt: "Revise the Introduction section in the draft document
addressing all Major revisions in the Review Report."
```

The LLM sees the Wordo document as markdown, generates a revised version in markdown, and the researcher can paste the output into Wordo for final formatting.

### 7.3 AI-Generated Artifacts

When an LLM response contains structured data (e.g., a comparison table), Veritas can offer to save it as a Nexcel artifact:

```
[Save as Nexcel] button appears when LLM output contains a markdown table
```

This parses the markdown table → Nexcel envelope → saves as artifact. The researcher can then open it in the full Nexcel editor.

---

## 8. Long-Term Compatibility Strategy

### 8.1 Envelope Version Migration

```
envelope_version 1 → 2:  (hypothetical future)
  - Added: "table.field_groups" array for column grouping
  - Migration: set field_groups = [] if missing
```

Migration functions live in **Veritas** (since Veritas owns the envelope):

```python
# backend/app/kasumi_compat.py

CURRENT_ENVELOPE_VERSION = 1

def migrate_envelope(envelope: dict) -> dict:
    """Migrate envelope to current version. Idempotent."""
    v = envelope.get("envelope_version", 1)

    if v < 2:
        # v1 → v2: add field_groups
        if envelope["kasumi_type"] == "nexcel":
            envelope["table"].setdefault("field_groups", [])
        envelope["envelope_version"] = 2

    # Future migrations chain here

    return envelope
```

### 8.2 Kasumi Internal Version Migration

Kasumi's data formats (`FieldMeta`, `RowRecord`, `KasumiDocument`, `AnyBlock`) will evolve. Migration responsibility is split:

| Data Layer | Migration Owner | Strategy |
|------------|----------------|----------|
| Envelope wrapper | Veritas | `migrate_envelope()` in Python |
| `table.fields` / `table.rows` | Kasumi | Kasumi's embed mode deserializer must accept old formats |
| `document.sections` / `document.blocks` | Kasumi | Kasumi's embed mode deserializer must accept old formats |
| `view_state` / `editor_state` | Disposable | If incompatible, discard and use defaults |

**Kasumi's contract:** When Kasumi receives an envelope via postMessage, it must:
1. Read `kasumi_version` from the envelope
2. If older than current, silently migrate the `table`/`document` payload in memory
3. On save, write the envelope with the **current** `kasumi_version`

**Testing:** Kasumi must maintain a `/tests/compat/` directory with sample envelopes from each past version. CI runs deserialization tests against all of them.

### 8.3 Breaking Change Protocol

If Kasumi makes a breaking change to its data model:

1. Kasumi bumps its major version (e.g., 1.x → 2.0)
2. Kasumi ships a migration function that converts 1.x data → 2.0 data
3. Kasumi's embed mode deserializer calls this migration on init
4. Veritas does not need to change (the envelope wrapper is stable; only Kasumi's internal payload changes)

If Veritas changes the envelope structure:

1. Veritas bumps `envelope_version`
2. Veritas adds a migration step in `migrate_envelope()`
3. Kasumi's embed mode must tolerate unknown top-level envelope keys (pass-through)
4. Both sides should use the **robustness principle**: be liberal in what you accept

---

## 9. Implementation Phases

### Phase 1 — Backend Foundation (Est. 1 day)

- [ ] Extend `get_preview_kind()` to return `"nexcel"` / `"wordo"` for `.nexcel.json` / `.wordo.json` extensions
- [ ] Add `"nexcel"` and `"wordo"` to `ArtifactPreviewKind` enum (backend + frontend types)
- [ ] Implement `extract_llm_context()` for Kasumi artifact types
- [ ] Add blank envelope generators (`create_blank_nexcel_envelope()`, `create_blank_wordo_envelope()`)
- [ ] Write unit tests for envelope serialization/deserialization

### Phase 2 — Kasumi Embed Mode (Est. 2 days)

- [ ] Add `/embed/nexcel` and `/embed/wordo` routes to Kasumi frontend
- [ ] Implement `EmbedHost` wrapper component (listens for postMessage init, hides shell switcher)
- [ ] Implement `NexcelEmbedAdapter` — hydrates useExcelStore from envelope data instead of Baserow API
- [ ] Implement `WordoEmbedAdapter` — hydrates useWordoStore from envelope data instead of localStorage
- [ ] Implement save-via-postMessage (serialize store state → envelope → postMessage to parent)
- [ ] Test: open Kasumi embed in a standalone HTML page, send init message, edit, receive save message

### Phase 3 — Veritas Frontend Integration (Est. 2 days)

- [ ] Create `NexcelArtifactView` component (read-only table + [Edit] button)
- [ ] Create `WordoArtifactView` component (read-only document preview + [Edit] button)
- [ ] Create `KasumiEmbedModal` component (iframe host with postMessage bridge)
- [ ] Wire into `ArtifactPreview.tsx` renderer switch
- [ ] Add "New Nexcel" / "New Wordo" options to artifact creation UI
- [ ] Test end-to-end: create Nexcel artifact → edit in iframe → save → verify JSON on disk

### Phase 4 — LLM Context & Persona Integration (Est. 1 day)

- [ ] Implement `nexcel_to_markdown()` — Nexcel envelope → markdown table string
- [ ] Implement `wordo_to_markdown()` — Wordo envelope → markdown document string
- [ ] Wire into chat prompt assembly (where artifacts are injected into persona prompts)
- [ ] Test: attach Nexcel artifact to Drafter prompt → verify LLM sees markdown table
- [ ] Test: attach Wordo artifact to Reviewer prompt → verify LLM sees markdown text

### Phase 5 — Quality & Compatibility (Est. 1 day)

- [ ] Create `kasumi_compat.py` with `migrate_envelope()` function
- [ ] Create sample envelope fixtures for version 1 (Nexcel + Wordo)
- [ ] Write compatibility tests (deserialize old → serialize new → verify roundtrip)
- [ ] Add "Save as Nexcel" action for LLM-generated markdown tables
- [ ] Export: Nexcel artifact → .xlsx / .csv (delegate to Kasumi's existing export)
- [ ] Export: Wordo artifact → .docx (delegate to Kasumi's existing export)

---

## 10. File Change Summary

### Veritas Backend (Python)

| File | Change |
|------|--------|
| `backend/app/artifact_service.py` | Add `"nexcel"` / `"wordo"` to preview kind detection |
| `backend/app/schemas/sse_events.py` | Add preview kinds to enum (if typed) |
| `backend/app/routes/artifact_routes.py` | No change (existing endpoints suffice) |
| `backend/app/kasumi_compat.py` | **NEW** — Envelope migration, blank generators, LLM context extraction |
| `backend/app/chat_service.py` (or equivalent) | Call `extract_llm_context()` for Kasumi artifacts in prompt assembly |

### Veritas Frontend (TypeScript/React)

| File | Change |
|------|--------|
| `frontend/src/lib/api/types.ts` | Add `"nexcel"` / `"wordo"` to `ArtifactPreviewKind`; add envelope types |
| `frontend/src/components/artifacts/ArtifactPreview.tsx` | Add Kasumi renderer branches |
| `frontend/src/components/artifacts/NexcelArtifactView.tsx` | **NEW** — Read-only table + edit trigger |
| `frontend/src/components/artifacts/WordoArtifactView.tsx` | **NEW** — Read-only doc preview + edit trigger |
| `frontend/src/components/artifacts/KasumiEmbedModal.tsx` | **NEW** — iframe host with postMessage bridge |
| `frontend/src/components/artifacts/ArtifactBrowser.tsx` | Add "New Nexcel" / "New Wordo" to creation menu |

### Kasumi Frontend (TypeScript/React)

| File | Change |
|------|--------|
| `frontend/src/EmbedHost.tsx` | **NEW** — Embed entry point (no switcher, no splash) |
| `frontend/src/modules/excel-shell/adapters/EmbedAdapter.ts` | **NEW** — Hydrate from envelope instead of Baserow |
| `frontend/src/modules/wordo-shell/adapters/EmbedAdapter.ts` | **NEW** — Hydrate from envelope instead of localStorage |
| `frontend/vite.config.ts` | Add `/embed/*` routes |

### No Changes Required

- Veritas database schema (no Alembic migration)
- Veritas authentication system
- Veritas session management
- Kasumi core stores (useExcelStore, useWordoStore) — adapters wrap them
- Kasumi API server (not used in embed mode)
- Kasumi platform layer (object registry, command bus)

---

## 11. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Kasumi iframe blocked by browser security | Edit mode broken | Both apps on localhost; configure correct CORS and CSP headers |
| Large Nexcel datasets slow to serialize as base64 in URL | Poor UX | Use postMessage for init data (not URL params) for datasets > 100KB |
| Kasumi data format changes break old artifacts | Data loss | Versioned envelope + migration chain + compat test suite |
| Two dev servers to run (Veritas + Kasumi) | Developer friction | Add a `start-all.bat` that launches both; document in QUICKSTART |
| Kasumi Electron packaging conflicts with embed mode | Embed broken | Embed mode uses Vite dev server or static build, not Electron |

---

## 12. Future Extensions (Out of Scope for v1)

- **Real-time co-editing** — Multiple users editing the same Kasumi artifact simultaneously (requires WebSocket bridge)
- **Inline Nexcel embeds in Wordo artifacts** — Wordo already supports NexcelEmbedBlock; in embed mode, resolve these from sibling Veritas artifacts
- **Kasumi PRESENTO** — Future presentation shell, same embed pattern
- **Bi-directional AI editing** — LLM directly modifies Kasumi data via the Kasumi API server (requires auth bridge)
- **Diff view** — Show changes between artifact versions using Kasumi-aware diff

---

_End of Integration Plan_
