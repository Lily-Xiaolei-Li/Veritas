# RAG Sources (Managed) — Spec (v0.1)

**Goal:** Make “RAG Sources” a first-class resource in Agent B.

A **RAG Source** is an independently searchable corpus (papers, interviews, books, etc.) with its own ingestion config and index.

This spec defines:
- data model (DB)
- API endpoints
- ingestion job contract (future milestones)
- UI integration points (Workbench)
- acceptance criteria for M1 (Source registry + API)

---

## 1) Concepts

### 1.1 RAG Source
A named corpus with a preset tuned for content type.

Examples:
- `papers` — published academic papers
- `interviews` — interview transcripts
- `books-carbon-markets` — one or more books

### 1.2 Managed vs External
- **Managed**: Agent B owns ingestion + embeddings + vector index lifecycle.
- **External** (future): Agent B calls a remote RAG service via HTTP connector.

This spec focuses on **Managed**.

---

## 2) Data Model (DB)

### 2.1 Table: `rag_sources`
Minimal fields (M1):
- `id` (UUID string)
- `name` (string, unique)
- `description` (nullable)
- `preset` (enum-like string): `papers | interviews | books | generic`
- `status` (string): `creating | ready | indexing | failed | deleted`
- `created_at`, `updated_at`
- `source_metadata` (JSON, optional): future config fields

Future (M2+): stats fields like `doc_count`, `chunk_count`, `last_indexed_at`.

### 2.2 Table: `rag_documents` (M2)
Document-level ingest tracking: title/path/hash/status/error.

### 2.3 Vector store
Vector store is not mandated by M1.

Recommended:
- Qdrant (local) with payload metadata containing `source_id`, `doc_id`, `chunk_id`.

---

## 3) API Endpoints

All endpoints live under `/api/v1/rag`.

### 3.1 List sources (M1)
`GET /api/v1/rag/sources`
- Returns `[]RagSource`.
- If DB not configured → 503 with actionable message.

### 3.2 Create source (M1)
`POST /api/v1/rag/sources`
Body:
```json
{
  "name": "papers",
  "description": "Academic papers library",
  "preset": "papers"
}
```
- Returns created source.
- If name exists → 409.

### 3.3 Get source (M1)
`GET /api/v1/rag/sources/{source_id}`

### 3.4 (Future) Ingest
`POST /api/v1/rag/sources/{source_id}/ingest`
- Accepts artifact ids or workspace paths.
- Returns a job id.

### 3.5 (Future) Search
`POST /api/v1/rag/search`
- Accepts `source_ids[]`, `query`, `filters`, `top_k`.

---

## 4) UI Integration

### 4.1 Explorer entry (M2)
- Select file/folder → **Index as Source…**

### 4.2 Search panel (M3)
- Source dropdown / multi-select
- Results standardized + Export to Artifact

---

## 5) Acceptance Criteria

### M1 — Source registry + API
- [ ] Can create a source via API.
- [ ] Can list sources.
- [ ] Can fetch source by id.
- [ ] Works with auth on/off (follows global auth rules).
- [ ] When DB is not configured, endpoints return 503 with a clear remediation hint.

---

## 6) Next Move
Implement M1 backend:
- SQLAlchemy model + Alembic migration
- `/api/v1/rag/sources` routes
- minimal unit tests (503 behavior without DB)
