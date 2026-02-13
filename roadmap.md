# Roadmap — Agent B Platform

**Version:** 2.0
**Last Updated:** January 26, 2026

**Vision:** Open-source foundation for building local-first AI workspaces.

**Audience:**

- Agent A (human owner)
- Agent B's coding agents (Claude Code, Cursor, etc.)

---

## Changelog

### Version 2.0 (January 26, 2026)

**Major Revision: Platform Pivot**

Agent B is now positioned as an open-source platform foundation rather than a fully-featured cognitive workbench. This revision:

1. Simplified roadmap to focus on platform v1.0 release
2. Kept Phase 0 (Foundations) and Phase 1 UI milestones (B1.0-B1.6) as-is - already complete
3. Replaced complex Phase 2-7 with streamlined milestones
4. Moved multi-brain architecture to "Advanced Extensions" (code kept, documented as optional)
5. Added Document Processing as platform capability
6. Target: v1.0 stable release

**Work Preserved:**
- LLM Provider Abstraction (B2.0) - complete, kept as-is
- LangGraph integration (B2.1) - complete, moved to optional advanced module
- All Phase 0 and Phase 1 work - complete, unchanged

---

### Version 1.7 (January 26, 2026)

B2.1 LangGraph Runtime Integration marked complete.

### Version 1.6 (January 26, 2026)

B2.0 Testing and Documentation - Gemini SDK update, Ollama provider added.

---

## Instructions for Coding Agents

Any coding agent working on this repository MUST:

1. Read this entire file before writing code
2. Inspect the repository to determine current state
3. Implement the **next smallest milestone only**
4. Add tests and logging to make progress verifiable
5. Update the **Status** section below
6. Never skip milestones
7. Prefer finishing a milestone over starting a new one

**If uncertain: pause → document → ask** rather than guess or silently change behavior.

## Session Protocol for Coding Agents

1. Read roadmap.md to understand current milestone
2. Read last 3 entries in devlog.md for recent context
3. Do work
4. Add devlog.md entry before ending session
5. Update roadmap.md status section

---

## Status (Update Every PR/Session)

```
Current Phase:      Phase 2 — Polish & Release
Current Milestone:  B2.4 - Testing & Stability (READY TO MARK COMPLETE)
Last Completed:     B2.4 - Testing & Stability (LOCAL COMPLETE; awaiting CI green)
Known Blockers:     None
Next Action:        When GitHub Actions is green, mark B2.4 COMPLETE and proceed to B2.5 (Release checklist)
```

**Completed Work Summary:**

| Milestone | Description | Status |
|-----------|-------------|--------|
| Phase 0 (B0.0-B0.4) | Foundations, Database, Auth, Execution | ✅ Complete |
| Phase 1 (B1.0-B1.6) | Workbench UI, Streaming, Files, Kill Switch, Sessions, Auth UI | ✅ Complete |
| B2.0 | LLM Provider Abstraction (Gemini, OpenRouter, Ollama, Mock) | ✅ Complete |
| B2.1 | LangGraph Runtime (optional advanced module) | ✅ Complete |
| B2.4 | Testing & Stability (CI gates + API smoke) | ✅ Complete (pending CI) |

**Legend:**

- `[ ]` Not started
- `[~]` In progress
- `[x]` Completed

---

## Core Development Rules (Non-Negotiable)

1. **Agent B is a platform, not a persona.** Do not hard-code profession-specific logic.

2. **Vertical slices only.** Each milestone produces a small, end-to-end capability.

3. **State, logs, and memory first.** Debuggability beats speed.

4. **Failure is data.** Never delete negative results; record them.

5. **Human authority is final.** No irreversible action without approval.

6. **Tests cover failure paths.** Happy-path-only tests are incomplete.

7. **Error messages are actionable.** "Something went wrong" is never acceptable.

---

## Architecture Principles

### Dependency Management Strategy

**Priority: Stability Over Novelty**

Agent B is a platform for production use, not an experimental playground. All dependency choices must prioritize stability, compatibility, and long-term maintainability.

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for version compatibility details.

**Known Stable Version Matrix:**

**Frontend (Verified Compatible):**
```json
{
  "next": "^14.2.13",
  "react": "^18.3.1",
  "tailwindcss": "^3.4.19"
}
```

**Backend (Verified Compatible):**
```python
fastapi==0.110.0
sqlalchemy[asyncio]==2.0.29
asyncpg==0.29.0
```

---

## Phase 0 — Foundations ✅ COMPLETE

**Goal:** Safe execution environment with full observability.

All milestones (B0.0 through B0.4) are complete. See devlog.md for implementation details.

| Milestone | Description | Status |
|-----------|-------------|--------|
| B0.0 | Repository Bootstrap | ✅ |
| B0.0.1 | Environment Readiness Check | ✅ |
| B0.0.2 | Database Initialization | ✅ |
| B0.0.3 | Configuration & Logging | ✅ |
| B0.0.4 | Authentication & Secrets (Backend) | ✅ |
| B0.1 | Container Execution Service | ✅ |
| B0.2 | Execution Safety Controls | ✅ |
| B0.3 | Session Management API | ✅ |
| B0.4 | Minimal Agent Loop (Mock) | ✅ |

---

## Phase 1 — Platform Foundation

**Goal:** Functional interface with LLM integration and document processing.

### Completed Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| B1.0 | Workbench Shell (3-panel layout) | ✅ |
| B1.1 | Streaming Reasoning & Events (SSE) | ✅ |
| B1.2 | File Browser & Workspace | ✅ |
| B1.3 | Artifact Handling | ✅ |
| B1.4 | Kill Switch | ✅ |
| B1.5 | Session Management UI | ✅ |
| B1.6 | Authentication & API Key UI | ✅ |
| B2.0 | LLM Provider Abstraction | ✅ |
| B2.1 | LangGraph Runtime (Advanced) | ✅ |

---

### B1.7 — Document Processing

**Goal:** Read and write common document formats.

- [ ] Word documents (python-docx)
  - [ ] Read .docx files
  - [ ] Write/create .docx files
  - [ ] Basic formatting support
- [ ] Excel files (openpyxl)
  - [ ] Read .xlsx files
  - [ ] Write/create .xlsx files
  - [ ] Basic cell operations
- [ ] PDF files (PyMuPDF)
  - [ ] Read/extract text from PDF
  - [ ] (Write deferred - complex)
- [ ] Document service API endpoints
- [ ] Integration with artifact system

**Acceptance Criteria:**

- [ ] Upload Word doc → text content extracted
- [ ] Generate Word doc → downloadable artifact
- [ ] Upload Excel → data accessible as JSON/tables
- [ ] Generate Excel → downloadable artifact
- [ ] Upload PDF → text content extracted
- [ ] Document operations logged to audit trail

**Status:** NOT STARTED

---

### B1.8 — Tool Framework

**Goal:** Extensible tool system for agent capabilities.

- [x] Tool interface definition
- [x] Tool registry with discovery
- [x] Built-in tools:
  - [x] file_read - Read file from workspace
  - [x] file_write - Write file to workspace
  - [x] shell_exec - Execute command in sandbox
  - [x] document_read - Read document content
  - [x] document_write - Create document
- [x] Tool result capture and display (Console tool_start/tool_end)
- [x] Tool invocation audit logging (best-effort)

**Acceptance Criteria:**

- [x] Tools registered and discoverable via API
- [x] Tool calls logged with input/output
- [x] Custom tools can be added without code changes (registry pattern)
- [x] Tool errors don't crash agent loop

**Status:** COMPLETE

---

### B1.9 — Simple Agent Loop

**Goal:** Basic chat → LLM → tools → response flow.

- [ ] Message submission triggers agent loop
- [ ] LLM generates response (streaming)
- [ ] Tool calls extracted and executed
- [ ] Tool results fed back to LLM
- [ ] Final response displayed
- [ ] Conversation history maintained

**Acceptance Criteria:**

- [ ] "Hello" → LLM response displayed
- [ ] "Create a file called test.txt" → tool called, file created
- [ ] Conversation history persists across refreshes
- [ ] Errors handled gracefully with user feedback

**Status:** NOT STARTED

---

## Phase 2 — Polish & Release

**Goal:** Documentation, developer experience, and v1.0 release.

### B2.2 — Documentation

**Goal:** Clear documentation for users and developers.

- [ ] README with quick start guide
- [ ] Setup instructions (manual, no Docker)
- [ ] "Building on Agent B" developer guide
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Extension examples

**Acceptance Criteria:**

- [ ] New user can set up Agent B in <10 minutes
- [ ] Developer can add custom tool following guide
- [ ] API docs accessible at /docs endpoint

**Status:** NOT STARTED

---

### B2.3 — Developer Experience

**Goal:** Easy setup and development workflow.

- [ ] One-command setup script (no Docker)
- [ ] Environment template (.env.example updated)
- [ ] Development workflow documentation
- [ ] Contribution guidelines

**Acceptance Criteria:**

- [ ] One-command script starts full stack (backend + frontend)
- [ ] Fresh clone → working system documented
- [ ] Development hot-reload works

**Status:** NOT STARTED

---

### B2.4 — Testing & Stability

**Goal:** Confidence in platform reliability.

- [ ] Core path test coverage (>80%)
- [ ] Integration tests for LLM providers
- [ ] End-to-end flow tests
- [ ] Performance baseline documented

**Acceptance Criteria:**

- [ ] All tests pass on CI
- [ ] No critical bugs in issue tracker
- [ ] Performance acceptable for typical use

**Status:** NOT STARTED

---

### B2.5 — v1.0 Release

**Goal:** Public release of Agent B Platform.

- [ ] Version tagged as v1.0.0
- [ ] GitHub release with notes
- [ ] LICENSE file (MIT)
- [ ] Announcement prepared

**Acceptance Criteria:**

- [ ] Release downloadable from GitHub
- [ ] License clearly stated
- [ ] Breaking changes from pre-release documented

**Status:** NOT STARTED

---

## Advanced Extensions (Optional)

The following capabilities are implemented but considered optional/advanced. They can be enabled for domain-specific applications that need them.

### LangGraph Runtime (B2.1) ✅ IMPLEMENTED

The LangGraph integration provides state machine orchestration with checkpoint persistence. This is useful for:

- Complex multi-step workflows
- Resumable runs after crashes
- State inspection and debugging

**Files:** `backend/app/agent/graph.py`, `backend/app/agent/state.py`, `backend/app/agent/nodes.py`

**Implementation Details:**
- LangGraph state machine: receive → process → respond → END
- PostgreSQL checkpoint persistence via langgraph-checkpoint-postgres
- Bounded session queues (maxsize=2000) to prevent memory blowup
- Crash reconciliation: stale runs marked as "interrupted" on startup
- Run history API: GET /sessions/{id}/runs, GET /runs/{id}, POST /runs/{id}/resume
- Frontend History tab with status badges and resume button
- 409 Conflict enforces one active run per session

**To enable:** Import and use the graph-based agent loop instead of the simple loop.

### Multi-Brain Architecture (Archived)

The multi-brain escalation system (Brain 1/2/3) is documented in PRD.md Appendix A. Implementation files exist but are not integrated into the main agent loop:

**Files:** `backend/app/agent/brains.py`, `backend/app/agent/consensus.py`

**Status:** Code exists, not connected to main flow. Reserved for domain applications like Agent B Auditor.

### Monitoring & Metrics (B7.2) ✅ IMPLEMENTED

Prometheus-compatible metrics endpoint for observability:

- `/metrics` endpoint with Bearer token authentication
- HTTP request metrics, execution metrics, SSE connection metrics
- Session and message counters
- Database pool metrics

**Files:** `backend/app/metrics.py`

---

## Definition of Done

A milestone is complete only when:

- [ ] All checklist items completed
- [ ] Acceptance criteria pass
- [ ] Unit tests cover happy path AND failure paths
- [ ] Error messages are specific and actionable
- [ ] Logging sufficient to debug failures
- [ ] No secrets introduced to repository
- [ ] Status section updated in this file
- [ ] README updated if setup changed

---

## Testing Guidelines

**Unit Tests:**

- Required for all business logic
- Mock external dependencies (LLM providers, execution layer)
- Cover expected inputs AND edge cases

**Integration Tests:**

- Required for API endpoints
- Use test database (not production)
- Clean up after test

**LLM Tests:**

- Use mock responses for deterministic testing
- Cost tracking for live tests

---

## Dependency Graph

```
Phase 0 (Complete)
    ↓
Phase 1 Foundation
    B1.0-B1.6 (Complete) → B2.0 (Complete) → B1.7 → B1.8 → B1.9
                                               ↓
Phase 2 Polish & Release
    B2.2 → B2.3 → B2.4 → B2.5 (v1.0)
```

---

## Final Instruction to Coding Agents

When uncertain:

**pause → document → ask**

rather than guess or silently change behavior.

Agent B is a platform. Keep it simple. Domain complexity belongs in applications built on top.

---

**End of Roadmap**
