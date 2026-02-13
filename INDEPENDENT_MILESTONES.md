# Independent Milestones Analysis

**Analysis Date:** 2026-01-25 (Updated with feedback)  
**Scope:** Milestones after B1.3 (Artifact Handling) that can be developed independently

---

## ⚠️ **CRITICAL HIDDEN DEPENDENCY**

**Almost all "independent" milestones depend on one thing being stable:**

### **Canonical Run/Session State Model**

A single source of truth for:
- **Session lifecycle:** Session exists → run starts → tools execute → run ends/cancels → errors recorded
- **Status values:** `queued` / `running` / `succeeded` / `failed` / `cancelled`
- **Timestamps:** Start, end, cancellation times
- **Event schemas:** SSE event types and payloads (from B1.1)

**If this isn't locked down early, UI milestones become rework magnets.**

**Current Status:** B1.1 (Streaming) defines basic SSE events, but run state machine may evolve with B2.1+.

**Ownership:** The run state machine is owned by the Phase 1/Phase 2 lead developer. It must be **frozen at the end of B1.1/B1.2** and documented in `docs/run-state-machine.md`. This document is the **only place allowed to define state transitions**. No milestone may introduce new states without updating this document first.

---

## Summary

After B1.3, **7 milestones** can be safely developed in parallel with low rework risk. These are organized into **4 tracks**:

1. **Track A — UI (Safe, Immediate)** - 3 milestones
2. **Track B — Backend Foundations (Interface-First)** - 2 milestones  
3. **Track B2 — Standalone Product Settings** - 1 milestone
4. **Track C — Integrations (Optional Parallel)** - 1 milestone

**Deferred until state model stabilizes:** B2.1, B3.0, B7.1, B7.3

---

## ✅ **SAFE TO PARALLELIZE NOW** (Low Rework Risk)

### **Track A — UI Features (Safe, Immediate)**

These three milestones can be developed **simultaneously** as they use different UI components and existing backend APIs:

#### **B1.4 — Kill Switch** ✅ SAFE (After Cancel Semantics Final)

- **Dependencies:** 
  - ✅ Backend execution routes (B0.1, B0.2) - **Already exists**
  - ✅ UI framework (B1.0) - **Already exists**
  - ⚠️ **Requires:** Cancel endpoint semantics to be **final** (idempotent; returns current state)

- **What it needs:** 
  - **Cancel Run API Contract** (path TBD - see mapping note below):
    - **Contract:** Must be idempotent (calling twice is safe)
    - **Contract:** Must return current run state after cancel
    - **Mapping Note:** If Phase 0 already has container cancellation support, B1.4 must consume the existing endpoint. Check for:
      - `POST /api/v1/exec/{id}/cancel` or
      - `DELETE /api/v1/exec/{id}` or
      - Session-scoped cancel endpoint
    - **Action:** Only add a new route (`POST /api/v1/runs/{run_id}/cancel`) if no equivalent exists
  - UI component: Fixed-position button in WorkbenchLayout

- **Touch List (Allowed):**
  - `backend/app/routes/exec_routes.py` - Add cancel endpoint (only if no equivalent exists)
  - `backend/app/executor.py` - Add cancel method (if not exists)
  - `frontend/src/components/workbench/WorkbenchLayout.tsx` - Add kill switch button
  - `frontend/src/lib/hooks/useCancelRun.ts` - New hook for cancel API

- **Do-Not-Touch List:**
  - Run state machine core logic (see `docs/run-state-machine.md` - only place allowed to define transitions)
  - SSE event schemas (B1.1)
  - Session/Run database models (B0.0.2)
  - **Rule:** B1.4 can call cancel and render state, but must NOT introduce new states. State transitions are owned by `docs/run-state-machine.md`.

- **Why safe:**
  - Uses existing execution infrastructure
  - Isolated UI component (doesn't conflict with other panels)
  - Can be tested with mock runs
  - **Requirement:** Cancel endpoint semantics must be finalized first

- **Contract Tests Required:**
  - Cancel endpoint is idempotent
  - Cancel returns current run state
  - Cancel works for queued/running/cancelled states

- **Validation:** 
  - Test with active container execution
  - Verify termination within 2 seconds
  - Check audit log entries
  - Test idempotency (cancel twice)

- **Definition of Done:**
  - ✅ API contract tests passing (cancel endpoint idempotent, returns state)
  - ✅ No changes outside touch list
  - ✅ Works with AUTH_ENABLED true/false
  - ✅ One happy-path manual test script written in `/docs/manual-tests/b1.4-kill-switch.md`
  - ✅ View Model API pattern followed (UI reads REST, not raw SSE)

#### **B1.5 — Session Management UI** ✅ SAFE (CRUD Only)

- **Dependencies:**
  - ✅ Backend session API (B0.3) - **Already exists** (`/api/v1/sessions`)
  - ✅ UI framework (B1.0) - **Already exists**

- **What it needs:**
  - New UI component: Session sidebar/list
  - Uses existing: `GET /api/v1/sessions`, `POST /api/v1/sessions`, `DELETE /api/v1/sessions/{id}`
  - Optional: `PATCH /api/v1/sessions/{id}` for rename (may need backend addition)

- **Touch List (Allowed):**
  - `frontend/src/components/workbench/SessionSidebar.tsx` - New component
  - `frontend/src/lib/hooks/useSessions.ts` - Extend with rename/delete
  - `backend/app/routes/session_routes.py` - Add PATCH endpoint if needed

- **Do-Not-Touch List:**
  - Run views/details (wait until SSE event schemas stabilize)
  - Session/Run database models (B0.0.2)
  - SSE event schemas (B1.1)
  - Session state machine (queued/running/etc.)

- **Why safe:**
  - Uses existing backend APIs
  - Isolated UI component (sidebar doesn't conflict with panels)
  - Can be tested independently
  - **Requirement:** Keep it CRUD-only; don't bake in run views yet

- **Contract Tests Required:**
  - Session API responses match frontend expectations
  - Session CRUD operations work correctly
  - Session switching doesn't break existing UI

- **Validation:**
  - Create/switch/delete sessions
  - Verify state persistence
  - Test with multiple sessions
  - **Do NOT** test run views/details (defer until B2.1+)

- **Definition of Done:**
  - ✅ API contract tests passing (session CRUD operations)
  - ✅ No changes outside touch list
  - ✅ Works with AUTH_ENABLED true/false
  - ✅ One happy-path manual test script written in `/docs/manual-tests/b1.5-session-management.md`
  - ✅ View Model API pattern followed (UI reads REST, not raw SSE)

#### **B1.6 — Authentication & API Key UI** ✅ SAFE (Do Early)

- **Dependencies:**
  - ✅ Backend auth API (B0.0.4) - **Already exists** (`/api/v1/auth/*`)
  - ✅ UI framework (B1.0) - **Already exists**

- **What it needs:**
  - New UI components: Login screen, API Keys settings page
  - Uses existing: `/api/v1/auth/login`, `/api/v1/auth/api-keys`

- **Touch List (Allowed):**
  - `frontend/src/components/auth/LoginScreen.tsx` - New component
  - `frontend/src/components/settings/ApiKeysPage.tsx` - New component
  - `frontend/src/lib/hooks/useAuth.ts` - New hook for auth
  - `frontend/src/lib/hooks/useApiKeys.ts` - New hook for API keys

- **Do-Not-Touch List:**
  - Auth headers/token format (freeze early to avoid connector conflicts)
  - JWT claims structure (B0.0.4)
  - Encryption/decryption logic (B0.0.4)
  - Session token generation (B0.0.4)

- **Why safe (and recommended early):**
  - Uses existing backend APIs
  - Isolated UI components (login modal, settings page)
  - Can be tested independently
  - **High value:** Improves dev workflow and future integrations
  - **Requirement:** Freeze auth headers/token format early

- **Contract Tests Required:**
  - Auth headers format matches backend expectations
  - Token validation works correctly
  - API key encryption/decryption works
  - Login flow works with AUTH_ENABLED=true/false

- **Validation:**
  - Test login flow with AUTH_ENABLED=true/false
  - Test API key CRUD operations
  - Verify encryption/decryption
  - **Freeze:** Auth header format (`Authorization: Bearer <token>`)

- **Definition of Done:**
  - ✅ API contract tests passing (auth headers, token validation)
  - ✅ No changes outside touch list
  - ✅ Works with AUTH_ENABLED true/false
  - ✅ One happy-path manual test script written in `/docs/manual-tests/b1.6-auth-ui.md`
  - ✅ Auth header format frozen and documented

**Note:** B1.4, B1.5, and B1.6 can all be developed **in parallel** by different developers without conflicts.

### **🔒 View Model API Guardrail (Critical Rule)**

**Rule:** UI should **NOT** parse raw SSE events directly for core state.

Instead, UI must read:
- `GET /api/v1/runs/{run_id}` - Returns status + timestamps + last_error
- Optionally: `GET /api/v1/sessions/{id}/runs` - Returns list of runs with status

**SSE becomes "nice-to-have" for live logs, NOT the source of truth.**

This single rule eliminates 80% of the "SSE changes break UI" risk.

**Implementation:**
- Backend must provide REST endpoints that return current run state
- Frontend uses REST for state, SSE only for streaming logs/events
- If SSE event schemas change, UI continues working (only live updates affected)

**Contract:** All UI milestones (B1.4, B1.5, B1.6) must follow this pattern.

---

### **Track B — Backend Foundations (Interface-First)**

These are **backend-only** features that can start now, but need **interface boundaries** to avoid collisions:

#### **B2.0 — LLM Provider Abstraction** ⚠️ INDEPENDENT-ISH (Interface-First)

- **Dependencies:**
  - ✅ Backend infrastructure (Phase 0) - **Already exists**
  - ✅ API key storage (B0.0.4) - **Already exists**

- **What it needs:**
  - New backend module: `app/providers/` with provider interface
  - Provider implementations: Gemini, OpenRouter
  - Cost tracking and logging

- **Touch List (Allowed):**
  - `backend/app/providers/__init__.py` - Provider interface
  - `backend/app/providers/base.py` - Base provider abstract class
  - `backend/app/providers/gemini.py` - Gemini implementation
  - `backend/app/providers/openrouter.py` - OpenRouter implementation
  - `backend/app/providers/types.py` - **MUST define canonical types now** (see below)

- **Do-Not-Touch List:**
  - Tool call encoding implementation (wait until B2.2+ defines tool schema)
  - Streaming delta format (wait until B1.1/B2.1 schemas stabilize)
  - Run state machine
  - SSE event schemas

- **Required Types (Lock Now in `backend/app/providers/types.py`):**
  ```python
  # Minimal canonical types - must be defined now for system to compile
  LLMMessage(role: str, content: str)
  LLMResponse(text: str, tool_calls?: List[ToolCall], usage?: Usage, raw?: dict)
  ToolCall(name: str, arguments_json: str)  # Even if providers don't produce it yet
  ```
  - **Action:** Define these types now so the rest of the system can compile against them
  - **Note:** Tool call implementation can be deferred, but the type must exist

- **Why independent-ish:**
  - Backend-only feature
  - No UI dependencies
  - Can be tested with CLI/API calls
  - **Collision risk:** Tool call encoding and streaming deltas may change
  - **Requirement:** Freeze internal interface now:
    - `generate(prompt, options) -> response`
    - `stream(prompt, options) -> AsyncIterator[chunk]`
    - `tool_call_encoding` (defer implementation, define interface)
    - `retry/backoff` strategy
    - `rate_limit` handling

- **Contract Tests Required:**
  - Provider interface has golden tests (mock responses)
  - All providers implement same interface
  - Retry logic works consistently
  - Cost tracking accurate

- **Validation:**
  - Test provider interface with mock responses
  - Test retry logic and error handling
  - Verify cost tracking
  - Test with real API keys (optional)
  - **Defer:** Tool call implementation until B2.2+

#### **B2.1 — LangGraph Runtime Integration** ❌ DEFER (Until SSE Schemas Stable)

- **Status:** ⚠️ **NOT RECOMMENDED FOR PARALLEL DEVELOPMENT YET**

- **Why defer:**
  - Will touch: run lifecycle, event streaming, tool execution hooks, persistence
  - Collides with B1.1/B1.2 style work because it **defines events**
  - If B2.1 changes event names/payloads, it will break B1.4/1.5 UI
  - **Recommendation:** Do scaffolding in parallel (interfaces + adapters), but delay final wiring until SSE schemas are locked

- **What can be done now (scaffolding only):**
  - LangGraph installation
  - Interface definitions (abstract graph structure)
  - Adapter stubs (not wired to events yet)
  - Database checkpoint saver interface (not implementation)

- **What must wait:**
  - Event streaming integration
  - Tool execution hooks
  - Run lifecycle management
  - Final persistence implementation

- **When to start full implementation:**
  - After B1.1/B1.2 SSE event schemas are frozen
  - After run state machine is documented and consistent
  - After B2.0 provider interface is stable

**Note:** B2.0 can start now (interface-first), but B2.1 should be deferred.

---

### **Track C — Integrations (Optional Parallel)**

#### **B6.0 — GitHub Read Access** ✅ SAFE (Genuinely Independent)

- **Dependencies:**
  - ✅ Backend infrastructure (Phase 0) - **Already exists**
  - ✅ API key storage (B0.0.4) - **Already exists**

- **What it needs:**
  - GitHub App integration or PAT handling
  - GitHub API client
  - Read-only endpoints (list repos, read files, read issues)

- **Touch List (Allowed):**
  - `backend/app/integrations/github/` - New module
  - `backend/app/routes/github_routes.py` - New routes
  - `frontend/src/components/integrations/GitHubConnector.tsx` - Optional UI

- **Do-Not-Touch List:**
  - Auth headers/token format (must match B1.6 frozen format)
  - Secrets storage patterns (use B0.0.4 encryption)

- **Why safe:**
  - Standalone feature
  - No agent runtime required
  - Can be tested independently
  - **Risk:** Auth flow (OAuth vs PAT) and secrets storage, but still separable

- **Contract Tests Required:**
  - GitHub API integration works
  - Read operations work correctly
  - Rate limiting respected
  - Auth flow works (OAuth or PAT)

- **Validation:**
  - Test GitHub API integration
  - Test read operations
  - Verify rate limiting
  - Test auth flow (OAuth vs PAT)

- **Definition of Done:**
  - ✅ API contract tests passing (GitHub API integration)
  - ✅ No changes outside touch list
  - ✅ Works with AUTH_ENABLED true/false
  - ✅ One happy-path manual test script written in `/docs/manual-tests/b6.0-github-read.md`

---

### **Track D — Monitoring (Can Start Now)**

#### **B7.2 — Monitoring & Metrics** ✅ SAFE (Phase 0 Instrumentation)

- **Dependencies:**
  - ✅ Backend infrastructure (Phase 0) - **Already exists**

- **What it needs:**
  - Metrics endpoint (Prometheus-compatible)
  - Metrics collection (sessions, runs, errors, costs)
  - Optional: Grafana dashboard

- **Touch List (Allowed):**
  - `backend/app/metrics.py` - New module
  - `backend/app/routes/metrics_routes.py` - New routes
  - Instrumentation in existing routes (exec latency, queue, failures)

- **Do-Not-Touch List:**
  - Run events/metrics (avoid tight coupling until B1.1/B2 runtime is stable)
  - SSE event schemas

- **Why safe:**
  - Can start now by instrumenting Phase 0 services (exec latency, queue, failures)
  - Standalone operational feature
  - **Requirement:** Avoid tight coupling to "run" events until B1.1/B2 runtime is stable

- **Contract Tests Required:**
  - Metrics endpoint returns Prometheus format
  - Metrics collection accurate
  - No performance impact

- **Validation:**
  - Test metrics endpoint
  - Verify metric collection (Phase 0 services only)
  - Test with Grafana (optional)
  - **Defer:** Run-specific metrics until B2.1+ stable

- **Definition of Done:**
  - ✅ API contract tests passing (metrics endpoint Prometheus format)
  - ✅ No changes outside touch list
  - ✅ One happy-path manual test script written in `/docs/manual-tests/b7.2-monitoring.md`

---

## ❌ **DEFERRED MILESTONES** (Will Create Expensive Rework)

These milestones should **NOT** be started until state model and schemas stabilize:

#### **B2.1 — LangGraph Runtime Integration** ❌ DEFER

- **Reason:** Will touch run lifecycle, event streaming, tool execution hooks
- **Collision:** Defines events that will break B1.4/1.5 UI if changed
- **When to start:** After SSE schemas frozen (B1.1/B1.2 stability)

#### **B3.0 — Memory Storage & Retrieval** ❌ DEFER

- **Reason:** Depends on:
  - What counts as "memory"
  - Embedding pipeline
  - Privacy boundaries
  - Retrieval triggers
  - Agent runtime hooks
- **Collision:** Without B2.0/B2.1 conventions, storage won't match how agent queries it
- **What can be done now:** Groundwork only (tables, vector store interface)
- **When to start:** After B2.0/B2.1 conventions are stable

#### **B7.1 — Backup & Recovery** ❌ DEFER

- **Reason:** Backup strategy depends on final data model (sessions, runs, traces, memory, keys)
- **Collision:** Will need to redo after B2/B3 settle
- **When to start:** After B2/B3 data model is stable

#### **B7.3 — Upgrade Path** ❌ DEFER (Or Keep Minimal)

- **Reason:** Depends on:
  - Migration strategy
  - Versioning of APIs/events
  - DB schema evolution
- **Collision:** Will need to redo after schemas stabilize
- **What can be done now:** Minimal version ("DB migrations run safely; app version displayed")
- **When to start:** After B2/B3 schemas are stable

---

---

### **Track B2 — Standalone Product Settings**

#### **B3.3 — User Preferences (Agent A Contract)** ⚠️ INDEPENDENT-ISH (Keep Truly Standalone)

- **Dependencies:**
  - ✅ Database (B0.0.2) - **Already exists**
  - ✅ UI framework (B1.0) - **Already exists**

- **Note:** This is a backend feature with UI, not "just UI" - it introduces DB migration and backend routes.

- **What it needs:**
  - Preferences table schema (new migration)
  - Preferences API endpoints
  - Preferences UI page

- **Touch List (Allowed):**
  - `backend/app/models.py` - Add Preferences model
  - `backend/alembic/versions/xxx_add_preferences.py` - New migration (see migration protocol)
  - `backend/app/routes/preferences_routes.py` - New routes
  - `frontend/src/components/settings/PreferencesPage.tsx` - New component

- **Do-Not-Touch List:**
  - Memory integration (keep separate)
  - Agent policy logic (keep preferences "dumb settings")
  - Run state machine

- **Why independent-ish:**
  - Can be built and tested independently
  - UI can be developed without agent runtime
  - Backend can store/retrieve preferences
  - **Risk:** Preferences often become entangled with memory + agent policy
  - **Requirement:** Keep it "dumb settings" first:
    - Theme, default model/provider, verbosity, notification toggles
    - **Do NOT** integrate with memory or agent policy yet

- **Contract Tests Required:**
  - Preferences CRUD works via API
  - UI preferences page works
  - Preferences persist across restarts
  - No coupling to memory/agent policy

- **Validation:**
  - Test preferences CRUD via API
  - Test UI preferences page
  - **Defer:** Full validation with agent using preferences (B2.2+)

- **Definition of Done:**
  - ✅ API contract tests passing (preferences CRUD)
  - ✅ Migration follows concurrency protocol (timestamp prefix, rebase if needed)
  - ✅ No changes outside touch list
  - ✅ Works with AUTH_ENABLED true/false
  - ✅ One happy-path manual test script written in `/docs/manual-tests/b3.3-preferences.md`

---

## ❌ **DEPENDENT MILESTONES** (Cannot Develop Independently)

These milestones **require** other milestones to be completed first:

### **Phase 2 Agent Runtime (Sequential)**
- **B2.2 — Brain 1** ❌ Requires B2.0 + B2.1
- **B2.3 — Brain 2** ❌ Requires B2.2
- **B2.4 — Brain 3** ❌ Requires B2.3
- **B2.5 — Human Escalation** ❌ Requires B2.3/B2.4 + Phase 1 UI

### **Phase 3 Agent Features (Require Agent Runtime)**
- **B3.1 — Reflection** ❌ Requires B3.0 + B2.2+
- **B3.2 — Trust Ledger** ❌ Requires B2.2+

### **Phase 4 Provenance (Require Agent Runtime)**
- **B4.0 — Provenance Objects** ❌ Requires B2.2+
- **B4.1 — Provenance Enforcement** ❌ Requires B4.0

### **Phase 5 Capabilities (Require Agent Runtime)**
- **B5.0 — Capability Catalog** ❌ Requires B2.2+
- **B5.1 — Consultation Planner** ❌ Requires B5.0

### **Phase 6 Write Actions (Require Read Access)**
- **B6.1 — Approval-Gated Write Actions** ❌ Requires B6.0

### **Phase 7 Forensics (Require Agent Runtime)**
- **B7.0 — Run Replay & Forensics** ❌ Requires B2.2+

---

## 🎯 **Recommended Parallel Development Strategy (Updated)**

### **Track A — UI (Safe, Immediate) — Start Now**

Develop these **simultaneously**:
- **Developer A:** B1.6 (Authentication & API Key UI) - **Do first** (improves everything else)
- **Developer B:** B1.5 (Session Management UI) - CRUD only
- **Developer C:** B1.4 (Kill Switch) - After cancel semantics final

**Result:** Complete Phase 1 UI faster with parallel work. Freeze auth headers early.

### **Track B — Backend Foundations (Interface-First) — Start Now**

While Phase 1 UI is being developed:
- **Developer D:** B2.0 (LLM Provider Abstraction) - Interface-first; adapter stubs; tests with mocks
- **Developer E:** B7.2 (Monitoring & Metrics) - Phase 0 + B1.1 instrumentation

**Result:** Backend foundations ready. B2.0 interface frozen. Monitoring ready.

### **Track C — Integrations (Optional Parallel)**

- **Developer F:** B6.0 (GitHub Read Access) - Connector + secrets patterns

**Result:** External integrations ready early.

### **Track D — Deferred (Wait for State Model Stability)**

**Do NOT start these until:**
- SSE event schemas are frozen (B1.1/B1.2-level stability)
- Run lifecycle/state machine is documented and consistent

- **B2.1** (LangGraph Runtime) - Defer until SSE schemas stable
- **B3.0** (Memory Storage) - Defer until B2.0/B2.1 conventions stable
- **B7.1** (Backup & Recovery) - Defer until B2/B3 data model stable
- **B7.3** (Upgrade Path) - Defer or keep minimal until schemas stable
- **B3.3** (User Preferences) - Can start if kept truly standalone (dumb settings only)

---

## 📋 **Validation Strategy for Independent Milestones**

Each independent milestone should be validated with:

1. **Unit Tests:** Test individual components
2. **Integration Tests:** Test API endpoints (for backend features)
3. **Manual Testing:** Test UI components (for frontend features)
4. **Isolation Testing:** Verify no conflicts with existing features
5. **Contract Tests:** Verify boundaries and interfaces (see below)

### **Contract Tests for Boundaries**

Each milestone must include contract tests that verify:

- **UI → Backend:** UI mocks the API; API responses match UI expectations
- **Provider Abstraction:** Golden tests for provider interface (all providers implement same contract)
- **Auth:** Auth header format matches backend expectations (frozen early)
- **Event Schemas:** If touching events, verify schemas match B1.1 definitions

### **Example Contract Test Structure:**

```python
# backend/tests/contracts/test_provider_interface.py
def test_all_providers_implement_interface():
    """Golden test: All providers must implement same interface."""
    for provider in [GeminiProvider(), OpenRouterProvider()]:
        assert hasattr(provider, 'generate')
        assert hasattr(provider, 'stream')
        # ... verify interface contract

# frontend/src/__tests__/contracts/api.test.ts
test('Session API contract matches frontend expectations', () => {
  // Mock API response
  // Verify frontend can parse it correctly
});
```

### **Example Validation Plan for B1.4 (Kill Switch):**

```markdown
1. **Backend API Test:**
   - POST /api/v1/runs/{run_id}/cancel
   - Verify container stops
   - Verify audit log entry

2. **UI Component Test:**
   - Button appears in WorkbenchLayout
   - Click triggers API call
   - UI shows terminated state

3. **Integration Test:**
   - Start execution → Click kill switch → Verify termination
   - Test with multiple concurrent runs
   - Test error handling (run not found, etc.)

4. **Isolation Test:**
   - Verify no conflicts with B1.5 (Session Management)
   - Verify no conflicts with B1.6 (Authentication)
```

---

## 🔀 **Merge Strategy & Conflict Prevention**

Independent milestones can be merged via:

1. **Feature Branches:** Each milestone in its own branch
2. **Parallel Development:** Multiple branches developed simultaneously
3. **Independent Validation:** Each branch validated separately
4. **Sequential Merge:** Merge one at a time, test after each merge
5. **Conflict Resolution:** Resolve any merge conflicts (should be minimal due to isolation)

### **Merge/Conflict Risk Notes (What to Watch)**

#### **Event Schemas**
- **Risk:** If B2.1 changes event names/payloads, it will break B1.4/1.5 UI
- **Mitigation:** UI should consume a stable "view model" API rather than raw SSE
- **Action:** Freeze SSE event schemas before B2.1 full implementation

#### **DB Migrations**
- **Risk:** Memory + preferences + runtime all want tables
- **Mitigation:** Enforce:
  - One migration per feature
  - Strict naming conventions
  - No "shared refactors" across milestones

### **Migration Concurrency Protocol**

**Problem:** When multiple feature branches add migrations, merge order determines migration numbers.

**Protocol:**
1. **Migration Filename Format:** Every migration filename must start with a timestamp prefix (or monotonic integer) generated at **merge-time**, not branch creation time.
2. **Feature Branch Rule:** Feature branches must **NOT** assume their migration number is final.
3. **Rebase Policy:** If two branches add migrations, the later merge rebases and renames its migration to the next available number.
4. **Coordination:** Before merging, check `alembic/versions/` for existing migrations and adjust your migration number accordingly.

**Example:**
```bash
# Branch A creates: 20260125_120000_add_preferences.py
# Branch B creates: 20260125_130000_add_memory.py
# If A merges first, B must rebase and rename to: 20260125_120001_add_memory.py
```

**Action:** Coordinate migration naming: `xxx_add_memory_table.py`, `xxx_add_preferences_table.py`

#### **Auth Changes**
- **Risk:** If you ship B1.6, freeze headers/token format early so connectors (GitHub) don't fork
- **Mitigation:** Document and freeze auth header format (`Authorization: Bearer <token>`)
- **Action:** Add contract tests for auth header format

#### **Run State Machine**
- **Risk:** Multiple milestones may want to modify run state transitions
- **Mitigation:** Document run state machine early; make it read-only for UI milestones
- **Action:** Create `docs/run-state-machine.md` before B1.4/B1.5

### **Example Git Workflow:**

```bash
# Developer A (B1.4)
git checkout -b feature/b1.4-kill-switch
# ... develop and test ...
git push origin feature/b1.4-kill-switch

# Developer B (B1.5)
git checkout -b feature/b1.5-session-management
# ... develop and test ...
git push origin feature/b1.5-session-management

# Merge sequentially
git checkout main
git merge feature/b1.4-kill-switch  # Test
git merge feature/b1.5-session-management  # Test
```

---

## ✅ **Summary Table (Updated)**

| Milestone | Track | Status | Dependencies | Can Develop Now? | Notes |
|-----------|-------|--------|--------------|------------------|-------|
| **B1.4** | Track A | ✅ Safe | B0.1, B0.2, B1.0 | ⚠️ After cancel semantics final | Freeze cancel endpoint contract |
| **B1.5** | Track A | ✅ Safe | B0.3, B1.0 | ✅ Yes | CRUD only; no run views |
| **B1.6** | Track A | ✅ Safe | B0.0.4, B1.0 | ✅ Yes (do first) | Freeze auth headers early |
| **B2.0** | Track B | ⚠️ Independent-ish | Phase 0, B0.0.4 | ✅ Yes (interface-first) | Freeze interface; defer tool calls |
| **B2.1** | Track D | ❌ Defer | B0.0.2, B0.0.4 | ❌ No | Wait for SSE schemas stable |
| **B3.0** | Track D | ❌ Defer | B0.0.2 | ❌ No | Wait for B2.0/B2.1 conventions |
| **B3.3** | Track B2 | ⚠️ Independent-ish | B0.0.2, B1.0 | ✅ Yes | Keep truly standalone (dumb settings) |
| **B6.0** | Track C | ✅ Safe | Phase 0, B0.0.4 | ✅ Yes | Genuinely independent |
| **B7.1** | Track D | ❌ Defer | B0.0.2 | ❌ No | Wait for B2/B3 data model stable |
| **B7.2** | Track B | ✅ Safe | Phase 0 | ✅ Yes | Phase 0 instrumentation only |
| **B7.3** | Track D | ❌ Defer | Existing system | ❌ No (or minimal) | Wait for schemas stable |

**Total Safe to Parallelize: 6 milestones** (B1.4, B1.5, B1.6, B2.0, B6.0, B7.2)  
**Total Deferred: 4 milestones** (B2.1, B3.0, B7.1, B7.3)  
**Total Independent-ish: 1 milestone** (B3.3 - Track B2, if kept standalone)

---

## 🎯 **Final Recommendation (Tighter Plan)**

**Start with these 6 milestones in parallel** (highest value, lowest rework risk):

### **Immediate Priority (Track A):**
1. **B1.6** - Authentication & API Key UI (do first - improves everything)
2. **B1.5** - Session Management UI (CRUD only)
3. **B1.4** - Kill Switch (after cancel semantics final)

### **Backend Foundations (Track B):**
4. **B2.0** - LLM Provider Abstraction (interface-first; adapter stubs)
5. **B7.2** - Monitoring & Metrics (Phase 0 instrumentation)

### **Optional (Track C):**
6. **B6.0** - GitHub Read Access (connector + secrets patterns)

### **Standalone Settings (Track B2):**
7. **B3.3** - User Preferences (backend + UI, if kept truly standalone)

### **Explicitly Defer:**
- **B2.1** - LangGraph Runtime (until SSE schemas frozen)
- **B3.0** - Memory Storage (until B2.0/B2.1 conventions stable)
- **B7.1** - Backup & Recovery (until B2/B3 data model stable)
- **B7.3** - Upgrade Path (until schemas stable, or keep minimal)

### **Hard Rules Per Milestone:**
- **Touch List:** Files/modules you are allowed to change
- **Do-Not-Touch List:** Run state machine, SSE schemas, core DB tables
- **Contract Tests:** Verify boundaries (UI mocks API; provider interface golden tests)

---

## 🚀 **Parallel Development Checklist**

> **Note:** This is a quick reference checklist for parallel development. For full details, touch lists, contract tests, and validation strategies, see the detailed sections above.

This checklist is designed for parallel development alongside the core roadmap. It focuses on milestones with low rework risk, provided the established technical boundaries and "contracts" are respected.

### 🛠 **Core Safety Rules (The Guardrails)**

Before starting any milestone, ensure these three rules are followed to prevent merge conflicts with the main roadmap:

1. **View Model API Guardrail:** The UI must **NOT** parse raw SSE events for core state. It must read current status and metadata from REST endpoints (e.g., `GET /api/v1/runs/{id}`). SSE is for live logs only, not source of truth.

2. **Migration Concurrency Protocol:** Any new database migrations must use a timestamp-based prefix (e.g., `YYYYMMDD_HHMMSS_name.py`) at **merge-time**, not branch creation time. If a conflict occurs, the feature branch must rebase and rename its migration to the next monotonic number.

3. **Zero-Touch Policy:** Do not modify the Run State Machine core logic, existing SSE event schemas in `sse_events.py`, or core Session/Run models unless explicitly listed in a "Touch List". State transitions are owned by `docs/run-state-machine.md`.

---

### 🎨 **Track A: UI Features (Immediate)**

These can be developed simultaneously by different developers.

#### [ ] **B1.6 — Authentication & API Key UI**

**Goal:** Create the login screen and the API Key management settings page.

**Backend Targets:** `/api/v1/auth/login`, `/api/v1/auth/api-keys`

**Touch List:**
- `frontend/src/components/auth/LoginScreen.tsx`
- `frontend/src/components/settings/ApiKeysPage.tsx`
- `frontend/src/lib/hooks/useAuth.ts`
- `frontend/src/lib/hooks/useApiKeys.ts`

**Validation:**
- ✅ Verify login works with `AUTH_ENABLED` set to both `true` and `false`
- ✅ Verify View Model API pattern (UI reads REST, not raw SSE)
- ✅ Freeze auth header format: `Authorization: Bearer <token>`

**Definition of Done:**
- API contract tests passing
- Works with AUTH_ENABLED true/false
- One happy-path manual test script in `/docs/manual-tests/b1.6-auth-ui.md`

---

#### [ ] **B1.5 — Session Management UI (CRUD Only)**

**Goal:** Implement the session sidebar and basic list/delete functionality.

**Backend Targets:** `GET /api/v1/sessions`, `POST /api/v1/sessions`, `DELETE /api/v1/sessions/{id}`

**Touch List:**
- `frontend/src/components/workbench/SessionSidebar.tsx`
- `frontend/src/lib/hooks/useSessions.ts` (extend with rename/delete)
- `backend/app/routes/session_routes.py` (only for adding a `PATCH` rename endpoint if needed)

**Constraint:** Do not implement run views or details yet; focus strictly on session organization.

**Validation:**
- ✅ Verify View Model API pattern (UI reads REST, not raw SSE)
- ✅ Create/switch/delete sessions work correctly
- ✅ Session switching doesn't break existing UI

**Definition of Done:**
- API contract tests passing
- Works with AUTH_ENABLED true/false
- One happy-path manual test script in `/docs/manual-tests/b1.5-session-management.md`

---

#### [ ] **B1.4 — Kill Switch**

**Goal:** Add a button to the Workbench to terminate active Docker executions.

**Backend Targets:** 
- **First:** Check for existing cancel endpoint (`POST /api/v1/exec/{id}/cancel` or `DELETE /api/v1/exec/{id}`)
- **Only if none exists:** Add `POST /api/v1/runs/{run_id}/cancel` to `exec_routes.py`

**Touch List:**
- `backend/app/routes/exec_routes.py` (add cancel endpoint only if no equivalent exists)
- `backend/app/executor.py` (add cancel method if not exists)
- `frontend/src/components/workbench/WorkbenchLayout.tsx` (add kill switch button)
- `frontend/src/lib/hooks/useCancelRun.ts` (new hook for cancel API)

**Validation:**
- ✅ Verify View Model API pattern (UI reads REST for run state, not raw SSE)
- ✅ Ensure the button triggers cancel and stops the container within 2 seconds
- ✅ Test idempotency (calling cancel twice is safe)
- ✅ Cancel returns current run state

**Definition of Done:**
- API contract tests passing (cancel endpoint idempotent, returns state)
- One happy-path manual test script in `/docs/manual-tests/b1.4-kill-switch.md`

---

### ⚙️ **Track B: Backend Foundations**

#### [ ] **B2.0 — LLM Provider Abstraction**

**Goal:** Create a unified interface for multiple LLM providers (Gemini, OpenRouter).

**Touch List:**
- `backend/app/providers/` (new module)
- `backend/app/providers/__init__.py`
- `backend/app/providers/base.py` (base provider abstract class)
- `backend/app/providers/gemini.py`
- `backend/app/providers/openrouter.py`
- `backend/app/providers/types.py` **MUST define canonical types now**

**Contract:** You **must** define `LLMMessage`, `LLMResponse`, and `ToolCall` types in `types.py` so the system can compile against them, even if tool-call encoding logic is deferred.

**Constraint:** Defer actual tool-call encoding logic until Brain 1 (B2.2).

**Validation:**
- ✅ Provider interface has golden tests (all providers implement same contract)
- ✅ Canonical types defined in `types.py`

**Definition of Done:**
- API contract tests passing (provider interface golden tests)
- Canonical types defined in `backend/app/providers/types.py`
- One happy-path manual test script in `/docs/manual-tests/b2.0-provider-abstraction.md`

---

#### [ ] **B7.2 — Monitoring & Metrics**

**Goal:** Instrument existing routes for latency, queue depth, and failure rates.

**Touch List:**
- `backend/app/metrics.py` (new)
- `backend/app/routes/metrics_routes.py` (new)
- Instrumentation in existing routes (exec latency, queue, failures)

**Constraint:** Avoid tight coupling to "run" events until B1.1/B2 runtime is stable. Focus on Phase 0 services only.

**Validation:**
- ✅ The `/metrics` endpoint returns Prometheus-compatible text format
- ✅ Metrics collection accurate for Phase 0 services

**Definition of Done:**
- API contract tests passing (metrics endpoint Prometheus format)
- One happy-path manual test script in `/docs/manual-tests/b7.2-monitoring.md`

---

### 🔌 **Track C: Integrations**

#### [ ] **B6.0 — GitHub Read Access**

**Goal:** Build a read-only connector for GitHub repositories and issues.

**Touch List:**
- `backend/app/integrations/github/` (new module)
- `backend/app/routes/github_routes.py` (new routes)
- `frontend/src/components/integrations/GitHubConnector.tsx` (optional UI)

**Requirement:** Use the encryption patterns in `app/crypto.py` to store Personal Access Tokens (PATs). Use frozen auth header format from B1.6.

**Validation:**
- ✅ GitHub API integration works
- ✅ Read operations work correctly
- ✅ Rate limiting respected
- ✅ Auth flow works (OAuth vs PAT)

**Definition of Done:**
- API contract tests passing (GitHub API integration)
- Works with AUTH_ENABLED true/false
- One happy-path manual test script in `/docs/manual-tests/b6.0-github-read.md`

---

### 🎚️ **Track B2: Standalone Settings**

#### [ ] **B3.3 — User Preferences**

**Goal:** Implement "dumb settings" like theme, default model, and verbosity.

**Touch List:**
- `backend/app/models.py` (add Preferences model)
- `backend/alembic/versions/xxx_add_preferences.py` (new migration - **follow migration concurrency protocol**)
- `backend/app/routes/preferences_routes.py` (new routes)
- `frontend/src/components/settings/PreferencesPage.tsx`

**Constraint:** Do not attempt to integrate these with the Agent Policy or Memory yet; keep them as simple database-backed flags.

**Migration Note:** Migration filename must use timestamp prefix at merge-time. If conflicts occur, rebase and rename to next monotonic number.

**Validation:**
- ✅ Preferences CRUD works via API
- ✅ UI preferences page works
- ✅ Preferences persist across restarts
- ✅ No coupling to memory/agent policy

**Definition of Done:**
- API contract tests passing (preferences CRUD)
- Migration follows concurrency protocol (timestamp prefix, rebase if needed)
- Works with AUTH_ENABLED true/false
- One happy-path manual test script in `/docs/manual-tests/b3.3-preferences.md`

---

**Last Updated:** 2026-01-25 (Updated with feedback on hidden dependencies)
