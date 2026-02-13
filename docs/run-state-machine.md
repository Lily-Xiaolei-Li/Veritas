# Run/Session/Artifacts State Machine (Canonical)

**Project:** Agent-B-Academic  
**Purpose:** Freeze the *single source of truth* for run/session lifecycle semantics so UI and APIs don’t drift.  
**Scope:** REST endpoints, SSE events, and DB fields related to Sessions, Runs, Messages, and Artifacts.

---

## 1. Entities

### Session
A session represents a user workspace context (tabs in UI).

**DB:** `sessions` table  
**Key fields:**
- `id` (UUID)
- `status`: `active | paused | completed | error`
- `created_at`, `updated_at`, `ended_at`

### Run
A run represents a single agent execution attempt. A run is always associated with exactly one session.

**DB:** `runs` table  
**Key fields:**
- `id` (UUID)
- `session_id`
- `status`: `pending | running | completed | failed | escalated | interrupted | cancelled`
- `created_at`, `started_at`, `completed_at`
- `task` (string)
- `result` (nullable)
- `error` (nullable)

> Note: `interrupted` is used for reconciliation of stale runs after restart.

### Artifact
Artifacts are **files** recorded in the `artifacts` table and stored on disk under `artifacts_dir/`.

**DB:** `artifacts` table  
**Key fields:**
- `id` (UUID)
- `run_id`, `session_id`
- `display_name` (what the user sees)
- `storage_path` (relative path under artifacts_dir)
- `extension` (no dot, e.g. `md`, `json`)
- `size_bytes`, `mime_type`, `content_hash`
- `artifact_type`: `file | stdout | stderr | log`
- `is_deleted` (soft delete)

**Storage path format (deterministic):**
```
{session_id}/{run_id}/{artifact_id}_{filename}
```

---

## 2. Run Lifecycle

### Allowed statuses
- `pending`: created but not yet started
- `running`: actively executing
- `completed`: finished successfully
- `failed`: finished with error
- `escalated`: finished but needs human intervention
- `cancelled`: explicitly terminated by user request
- `interrupted`: auto-marked by reconciliation after crash/restart

### State transitions
```
(pending)  -> (running)
(running)  -> (completed | failed | escalated | cancelled)
(pending)  -> (cancelled)
(running)  -> (interrupted)    # only via reconciliation after restart
(pending)  -> (interrupted)    # only via reconciliation after restart
```

### Timestamp rules
- When a run enters `running`: set `started_at`.
- When a run enters a terminal state (`completed|failed|escalated|cancelled|interrupted`): set `completed_at`.

### Idempotency rules
- Termination endpoint must be idempotent: terminating an already-terminal run returns 200 with current run state.
- Import endpoints should create a dedicated run to own artifacts (see §4).

---

## 3. Session Lifecycle

Session status is orthogonal to run status.

### Allowed statuses
- `active`: normal state
- `paused`: user paused activity
- `completed`: user archived/completed
- `error`: session-level error (rare)

### Rules
- Creating a session sets `status=active`.
- Deleting a session cascades deletion of runs/messages/artifacts (DB FK ondelete CASCADE) but artifacts are **soft-deleted** at API level.

---

## 4. Artifact Creation Semantics

### Principle
Artifacts shown in UI are backed by the **`artifacts` table**. Writing a file to disk is not sufficient.

### Valid ways to create artifacts
1) **Agent pipeline/tool output** → calls `create_artifact_internal(...)`.
2) **Explorer import** → converts input file(s) to payload(s), then calls `create_artifact_internal(...)` for each payload.

### Import run
Explorer import MUST create a run so imported artifacts have a `run_id`.

- Run task: `Import artifacts from file: <filename>`
- Run status:
  - `completed` on success
  - `failed` on conversion/IO/DB error

---

## 5. Messages

Submitting a message:
- Creates a `user` message row
- Starts a run
- When run finishes, creates `assistant` message (or updates messages list)

> Exact assistant message policy can evolve, but must remain consistent with run terminal state.

---

## 6. API contracts (high level)

### Sessions
- `GET /api/v1/sessions` → list
- `POST /api/v1/sessions` → create
- `PATCH /api/v1/sessions/{id}` → update title/config
- `DELETE /api/v1/sessions/{id}` → delete

### Runs
- `GET /api/v1/runs/{run_id}` → run status
- `POST /api/v1/sessions/{session_id}/terminate` → terminate active run(s) for a session (idempotent)

### Artifacts
- `GET /api/v1/sessions/{session_id}/artifacts` → list (DB-backed)
- `GET /api/v1/artifacts/{artifact_id}` → metadata
- `GET /api/v1/artifacts/{artifact_id}/preview` → preview
- `GET /api/v1/artifacts/{artifact_id}/content` → download
- `DELETE /api/v1/artifacts/{artifact_id}` → soft delete

### Explorer Import
- `POST /api/v1/explorer/import` → converts and registers artifacts, returns created artifact IDs.

---

## 7. SSE Events (planned)

Recommended event types:
- `run_state_changed`
- `artifact_created`
- `artifact_deleted`

Payloads must include `session_id`, `run_id`, and relevant IDs.

---

## 8. Testing requirements

For any change touching run/session/artifact state:
- Backend: pytest for run transitions + import success/failure
- Frontend: `npm run build` (typecheck) + minimal E2E script

---

## Appendix: Terminology
- **Terminal run state**: a state that will not transition further (`completed|failed|escalated|cancelled|interrupted`).
- **Interrupted**: system-marked terminal state due to restart/crash reconciliation.
