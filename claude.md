# Claude AI Assistant Context

This file provides context for AI assistants (like Claude) working on the Agent B project to avoid common pitfalls and maintain consistency.

---

## Project Overview

**Agent B** is an open-source platform for building local-first, privacy-preserving AI workspaces. It provides the infrastructure for domain-specific AI applications.

**Vision:** Platform foundation, not a complete product. Domain-specific features belong in applications built on top (e.g., Agent B Auditor).

**Current Status:** Phase 1 In Progress (B1.7 Document Processing is next milestone)

**Completed:**
- Phase 0 (Foundations): Database, Auth, Execution sandbox
- Phase 1 (B1.0-B1.6): Workbench UI, Streaming, Files, Kill Switch, Sessions
- B2.0: LLM Provider Abstraction (Gemini, OpenRouter, Ollama, Mock)
- B2.1: LangGraph Runtime (optional advanced module)

---

## Critical Files to Read Before Starting

1. **roadmap.md** - Current milestone and development plan
2. **devlog.md** (last 3-5 entries) - Recent context and decisions
3. **PRD.md** - Product requirements and architecture
4. **TROUBLESHOOTING.md** - Common issues and solutions

---

## Development Protocol

### Before Starting Work

1. Read `roadmap.md` to identify current milestone
2. Read last 3-5 entries in `devlog.md` for session context
3. Check for blockers or deferred items
4. Follow vertical slice development (end-to-end capabilities only)

### During Work

1. **No over-engineering** - Implement only what's explicitly required
2. **Error messages must be actionable** - Include remediation steps
3. **Tests cover failure paths** - Happy-path-only tests are incomplete
4. **State, logs, and memory first** - Debuggability beats speed
5. **Never delete negative results** - Failure is data

### Before Ending Session

**⚠️ THIS IS NOT OPTIONAL - DOCUMENTATION IS PART OF THE WORK ⚠️**

1. Add entry to `devlog.md` with:
   - Date and milestone
   - What was completed
   - Blockers encountered
   - Next steps
2. Update `roadmap.md` status section
3. Commit both files together

**If you skip this step:**
- Future developers will have incorrect context
- The roadmap will show wrong status
- Design decisions will be lost
- Someone will have to add retroactive entries (wasted effort)

---

## Common Pitfalls (CRITICAL)

### 0h. Missing SDK Research Before Implementation (B2.0 Lesson)

**Problem:** LLM provider code was implemented using outdated SDK documentation. The Gemini provider used `google-generativeai` package which was deprecated and replaced by `google-genai`. Live testing revealed the old SDK no longer works.

**Root Cause:**
1. Implementation based on potentially outdated documentation or prior knowledge
2. No live API testing during development (only mock tests)
3. SDK deprecations can happen without backward compatibility warnings
4. Model names changed alongside SDK updates (`gemini-1.5-flash` → `gemini-2.0-flash`)

**Impact:**
- Complete provider rewrite required (different imports, different API surface)
- Model pricing tables needed updating
- Time wasted on code that couldn't work with real APIs
- pytest-asyncio was also missing from requirements.txt (19 async tests were silently skipped)

**Prevention - MANDATORY for any external API integration:**
```powershell
# 1. Research CURRENT SDK status before writing code
#    - Check official docs for deprecation notices
#    - Check PyPI for package updates and changelogs
#    - Verify current model names available

# 2. Add all test dependencies to requirements.txt
pytest-asyncio==0.24.0  # Required for async tests!

# 3. Run tests with REAL credentials during development
python test_provider_live.py  # Not just mock tests

# 4. Verify test counts match expectations
pytest --collect-only  # Shows what tests exist
pytest                  # Check skipped count - should be 0 or explained
```

**Key Lesson:** Mock tests only verify your code's logic. They don't verify the external API still works as expected. Always test with real credentials before marking provider integrations complete.

**Coding Principle:** External API integrations require live testing with real credentials. SDK deprecations happen - verify your dependencies are current.

---

### 0i. Missing Documentation on Commit (B1.5 Lesson)

**Problem:** Code was committed without updating devlog.md or roadmap.md. During B1.5, the session management UI was fully implemented and committed, but:
1. No devlog.md entry was created
2. roadmap.md status was not updated
3. This caused the roadmap to show B1.4 as "next" when B1.5 and B1.6 were already done

**Root Cause:** Developer treated documentation as optional or "will do later":
1. Focused only on code, not the full delivery
2. Committed without the documentation files
3. Never came back to add the entries

**Impact:**
- Roadmap showed incorrect project status for multiple sessions
- No record of design decisions made during B1.5
- Future developers/agents had wrong context
- Required retroactive documentation (Session #010.5, #012)

**Prevention - MANDATORY before committing ANY milestone work:**
```powershell
# Your commit should include THREE things:
git add <your-code-changes>
git add devlog.md      # REQUIRED - session entry
git add roadmap.md     # REQUIRED - status update
git commit -m "..."
```

**Verification:**
```powershell
git diff --cached --name-only | Select-String -Pattern "(devlog|roadmap)"
# Must show BOTH files in staged changes
```

**Coding Principle:** Documentation is not separate from the work - it IS part of the work. A milestone without documentation is not complete.

---

### 0. Incomplete Commits - Missing Files (B1.0 Lesson)

**Problem:** Code references files that don't exist in the repository. During B1.0 testing, the frontend imported from paths like `@/lib/utils/constants` but the actual files were never created or committed.

**Root Cause:** Developer implemented component code with imports but:
1. Never created the imported files
2. Never ran `npm run build` or `npm run dev` to verify imports resolve
3. Committed without testing the full build

**Files that were missing in B1.0:**
- `frontend/src/lib/utils/constants.ts`
- `frontend/src/lib/utils/cn.ts`
- `frontend/src/lib/hooks/useHealth.ts`
- `frontend/src/lib/api/types.ts`

**Prevention - MANDATORY before committing frontend code:**
```powershell
cd frontend
npm run build   # Must complete without errors
```

**If build fails with "Module not found":**
1. Create the missing file
2. Implement the expected exports
3. Re-run build until it passes
4. Only then commit

**Coding Principle:** Never commit code that imports from non-existent files. The build must pass.

---

### 0a. API Contract Mismatch (B1.0 Lesson)

**Problem:** Backend returns `{"status": "ok"}` but frontend expects `{"status": "healthy"}`. This caused the health indicator to show "Unhealthy" even when everything was working.

**Root Cause:**
1. Backend and frontend developed separately without shared type definitions
2. No integration test to verify API response format matches frontend expectations
3. No API contract documentation

**Prevention:**
1. **Document API contracts** - Create `docs/api-contracts.md` specifying exact response formats
2. **Share types** - Consider a shared types package or OpenAPI spec generation
3. **Integration tests** - Add tests that verify frontend can parse backend responses

**Example of what should exist:**
```markdown
## Health Endpoint Contract
GET /health
Response: { "status": "ok" | "degraded" | "error", ... }

Frontend expects: "ok" maps to "healthy", "degraded" stays "degraded", anything else is "unhealthy"
```

**Coding Principle:** When frontend consumes backend API, document the contract and test the integration.

---

### 0b. npm Dependency Conflicts (B1.0 Lesson)

**Problem:** `npm install` failed with ERESOLVE error due to eslint@9 conflicting with eslint-config-next requiring eslint@^7 or ^8.

**Root Cause:** package.json had incompatible peer dependencies that were never tested with a fresh `npm install`.

**Solution:**
```powershell
npm install --legacy-peer-deps
```

**Prevention:**
1. After modifying package.json, delete node_modules and package-lock.json
2. Run fresh `npm install` to verify dependencies resolve
3. Document if `--legacy-peer-deps` is required in README

**Coding Principle:** Test dependency installation from scratch before committing package.json changes.

---

### 0c. PowerShell Version Compatibility (B1.0 Lesson)

**Problem:** `Set-Content -Encoding UTF8NoBOM` fails on older PowerShell versions (< 6.0). Windows PowerShell 5.1 (built into Windows) doesn't support this encoding.

**Detection:**
```powershell
$PSVersionTable.PSVersion  # Check version
```

**Solution for older PowerShell:**
```powershell
# Use .NET directly (works on all versions)
[System.IO.File]::WriteAllText("path/to/file", "content")

# Or set env var directly instead of using .env file
$env:DATABASE_URL = "postgresql+asyncpg://..."
```

**Coding Principle:** When writing PowerShell commands in documentation, provide alternatives for PowerShell 5.1 compatibility.

---

### 0d. psycopg2 Not Available on Python 3.13+/Windows (B1.1 Lesson)

**Problem:** `psycopg2-binary` fails to install on newer Python versions (3.13+) on Windows because no pre-built wheel exists and building from source requires PostgreSQL development tools.

**Symptoms:**
```
Warning: Could not determine current revision: No module named 'psycopg2'
```
Or during pip install:
```
error: Microsoft Visual C++ 14.0 or greater is required
```

**Root Cause:**
1. psycopg2-binary doesn't publish wheels for Python 3.13+ on Windows
2. Building from source requires pg_config (PostgreSQL dev tools)
3. Most Windows users don't have these tools installed

**Solution: Use psycopg v3 instead**

psycopg v3 is the modern replacement with better cross-platform support.

**Files to update:**
1. `requirements.txt`: Change `psycopg2-binary==2.9.9` → `psycopg[binary]>=3.1.0`
2. `alembic/env.py`: Change `postgresql+psycopg2://` → `postgresql+psycopg://`
3. `app/migrations.py`: Change BOTH occurrences of `postgresql+psycopg2://` → `postgresql+psycopg://`

**Critical:** Install in the venv, not globally:
```powershell
.\venv\Scripts\pip.exe install "psycopg[binary]>=3.1.0"
```

**Coding Principle:** When the sync PostgreSQL driver string changes, update ALL three locations (env.py, migrations.py line 38, migrations.py line 55). Missing any one will cause "No module named" errors.

---

### 0e. ESLint 9 Incompatible with Next.js 14 (B1.2 Lesson)

**Problem:** ESLint 9 causes `context.getScope is not a function` error when used with `eslint-config-next@14.x`.

**Symptoms:**
```
TypeError: context.getScope is not a function
    at checkVariables (eslint-plugin-react-hooks/cjs/eslint-plugin-react-hooks.development.js)
```

**Root Cause:**
1. `eslint-config-next@14.x` requires ESLint ^7.23.0 or ^8.0.0
2. ESLint 9 has breaking API changes that plugins haven't adopted yet
3. Using `FlatCompat` doesn't fix the underlying API incompatibility

**Solution - Downgrade to ESLint 8:**

1. Update `package.json`:
```json
"eslint": "^8.57.0"  // NOT "^9"
```

2. Replace `eslint.config.mjs` with `.eslintrc.json`:
```json
{
  "extends": ["next/core-web-vitals", "next/typescript"],
  "ignorePatterns": [".next/**", "out/**", "build/**", "next-env.d.ts"]
}
```

3. Delete `eslint.config.mjs` (flat config format)

4. Reinstall:
```powershell
rm -r node_modules
rm package-lock.json
npm install
```

**Prevention:** When using Next.js 14, always use ESLint 8.x. Check eslint-config-next peer dependencies before upgrading ESLint.

**Coding Principle:** Match ESLint version to framework requirements. Next.js 14 = ESLint 8, not 9.

---

### 0f. Test Isolation with pydantic-settings (B1.2 Lesson)

**Problem:** Tests fail because pydantic-settings automatically loads `.env` file, polluting test environment with real configuration values.

**Symptoms:**
```python
# Test expects default value but gets .env value
def test_default_settings(clean_env):
    settings = load_settings()
    assert settings.database_url is None  # FAILS - gets actual DATABASE_URL from .env
```

**Root Cause:**
1. pydantic-settings `BaseSettings` has `env_file=".env"` by default
2. Simply clearing environment variables doesn't prevent .env loading
3. The `.env` file is read at Settings instantiation time

**Solution - Patch model_config in test fixture:**
```python
@pytest.fixture
def clean_env(monkeypatch):
    """Clear env vars AND disable .env file loading."""
    # Clear environment variables
    for var in ["DATABASE_URL", "API_HOST", ...]:
        monkeypatch.delenv(var, raising=False)

    # Disable .env file loading
    from pydantic_settings import SettingsConfigDict
    new_config = SettingsConfigDict(
        env_file=None,  # This is the key!
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    monkeypatch.setattr(Settings, "model_config", new_config)
```

**Prevention:** Any test that checks default Settings values must disable .env file loading via model_config patch.

**Coding Principle:** Test isolation requires controlling ALL configuration sources, including automatic file loading.

---

### 0g. Run BOTH Build AND Lint (B1.2/B1.3 Lesson)

**Problem:** Build can pass while lint fails (and vice versa). Code committed with only build verification had lint errors that broke CI.

**Symptoms:**
```
# Build passes but lint fails
npm run build  # ✓ Success
npm run lint   # ✗ Error: 'Artifact' is defined but never used
```

**Root Cause:**
1. TypeScript compilation and ESLint are separate processes
2. `npm run build` runs TypeScript but may not run full ESLint
3. Unused imports don't break compilation but fail lint rules
4. A broken ESLint config (like ESLint 9 issues) means lint errors go undetected

**Solution - MANDATORY verification before committing frontend code:**
```powershell
cd frontend
npm run build   # Must pass - catches missing files, type errors
npm run lint    # Must pass - catches unused imports, style issues
```

**Common lint errors that build misses:**
- Unused imports: `'Artifact' is defined but never used`
- Unused variables: `'extension' is assigned but never used`
- Missing alt text: `Image elements must have an alt prop`

**Prevention:**
1. Run both `npm run build` AND `npm run lint` before every commit
2. Fix ESLint config issues immediately (broken lint = hidden bugs)
3. Consider adding `npm run lint` to pre-commit hook

**Coding Principle:** Build success ≠ code quality. Lint catches bugs that compile fine but cause runtime issues or maintenance problems.

---

### 1. Database Configuration Issues

**Problem:** Alembic uses async driver (asyncpg) which causes MissingGreenlet errors.

**Solution:** `backend/alembic/env.py` MUST:
- Import `load_dotenv()` from python-dotenv
- Call `load_dotenv()` at module level
- Convert `postgresql+asyncpg://` URLs to `postgresql+psycopg://` for Alembic (uses psycopg v3)

**Code that must exist in env.py:**
```python
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Convert async URL to sync URL for Alembic
database_url = os.getenv("DATABASE_URL")
if database_url:
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    config.set_main_option("sqlalchemy.url", sync_url)
```

### 2. Environment Variable Loading (PowerShell)

**Problem:** PowerShell creates .env files with BOM (Byte Order Mark) by default, breaking parsers.

**Solution for .env creation:**
```powershell
# CORRECT - No BOM
Set-Content -Path .env -Value "KEY=value" -Encoding UTF8NoBOM

# INCORRECT - May add BOM
Out-File -FilePath .env -InputObject "KEY=value"
```

**Alternative:** Set environment variables directly:
```powershell
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_b"
```

### 3. Working Directory for uvicorn

**Problem:** Must run uvicorn from `backend/` directory, not project root.

**Correct:**
```powershell
cd backend
uvicorn app.main:app --reload
```

**Incorrect:**
```powershell
# From project root - will fail with ModuleNotFoundError
uvicorn backend.app.main:app --reload
```

### 4. PowerShell vs Bash Syntax

When providing commands to Windows users, use PowerShell syntax:

**Bash:**
```bash
curl -X POST http://localhost:8000/api \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

**PowerShell:**
```powershell
Invoke-WebRequest -Uri http://localhost:8000/api `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"key": "value"}'
```

**Key differences:**
- Line continuation: `\` (bash) vs `` ` `` (PowerShell)
- JSON body: Use single quotes to preserve double quotes inside
- Command: `curl` vs `Invoke-WebRequest` (or `iwr` alias)

---

## Tech Stack

### Backend (Phase 0 - Current)
- **Framework:** FastAPI 0.110.0
- **Database:** PostgreSQL 16 (Docker)
- **ORM:** SQLAlchemy 2.0.29 (async with asyncpg)
- **Migrations:** Alembic 1.13.1 (sync with psycopg v3)
- **Config:** pydantic-settings 2.2.1
- **Auth:** bcrypt + PyJWT (not yet implemented in routes)
- **Execution:** Docker SDK 7.0.0

### Database Schema (Phase 0)
- `sessions` - User interaction sessions
- `messages` - Chat messages within sessions (B0.3)
- `runs` - Agent task executions
- `events` - Event log for observability
- `audit_log` - Security and system events
- `users` - User accounts (schema only, auth not implemented)
- `api_keys` - Encrypted LLM provider keys (schema only)
- `state_snapshots` - LangGraph checkpoints (future use)

### Frontend (Phase 1 - B1.0 Complete)
- **Framework:** Next.js 14.2.13
- **UI:** React 18, Tailwind CSS 3.4
- **State:** TanStack React Query 5.x, Zustand 5.x
- **Layout:** react-resizable-panels 2.x
- **Icons:** lucide-react
- **Utils:** clsx, tailwind-merge

### LLM Providers (B2.0 - Complete)
- **Gemini** - google-genai SDK
- **OpenRouter** - httpx.AsyncClient
- **Ollama** - Local inference (privacy-first)
- **Mock** - Testing and development

### Agent Runtime (Optional Advanced)
- **LangGraph** - State machine orchestration with PostgreSQL checkpoints
- Files: `backend/app/agent/graph.py`, `state.py`, `nodes.py`

---

## File Structure Quick Reference

```
Agent-B/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app with lifespan manager
│   │   ├── config.py            # pydantic-settings configuration
│   │   ├── database.py          # SQLAlchemy setup (async)
│   │   ├── models.py            # Database models
│   │   ├── migrations.py        # Alembic migration runner
│   │   ├── routes/
│   │   │   ├── session_routes.py    # Session CRUD (B0.3)
│   │   │   ├── message_routes.py    # Message endpoints with mock agent (B0.4)
│   │   │   ├── auth_routes.py       # Auth endpoints (stub only)
│   │   │   └── exec_routes.py       # Execution endpoints (stub only)
│   ├── alembic/
│   │   ├── env.py               # CRITICAL: Must load .env and convert URLs
│   │   └── versions/            # Migration files
│   ├── .env                     # Local config (not in git)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Main page component
│   │   │   ├── layout.tsx       # Root layout with providers
│   │   │   ├── providers.tsx    # React Query provider
│   │   │   └── globals.css      # Global styles
│   │   ├── components/
│   │   │   ├── workbench/       # Panel components (B1.0)
│   │   │   ├── health/          # Health indicator (B1.0)
│   │   │   └── ui/              # Reusable UI components
│   │   └── lib/
│   │       ├── api/
│   │       │   └── types.ts     # API response types
│   │       ├── hooks/
│   │       │   └── useHealth.ts # Health check hook
│   │       └── utils/
│   │           ├── constants.ts # App constants (API_URL, etc.)
│   │           └── cn.ts        # Tailwind class merger
│   ├── package.json
│   └── tailwind.config.ts
├── roadmap.md                   # Development plan
├── devlog.md                    # Session log
├── PRD.md                       # Product requirements
├── TROUBLESHOOTING.md          # Common issues and solutions
├── TESTPLAN.md                 # Manual testing procedures
└── README.md                    # Setup instructions
```

---

## Database URL Formats

**For FastAPI app (async):**
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agent_b
```

**For Alembic (sync, auto-converted in env.py):**
```
postgresql+psycopg://postgres:postgres@localhost:5432/agent_b
```

**Both drivers required:**
- `asyncpg==0.29.0` - For app runtime
- `psycopg[binary]>=3.1.0` - For Alembic migrations (psycopg v3)

---

## Testing Phase 1 (B1.0+)

### Full Stack Verification

**1. Start services (requires 2 terminals):**
```powershell
# Terminal 1 - Backend
cd backend
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_b"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

**2. Verify in browser:**
- Open http://localhost:3000
- Health indicator should be GREEN "Healthy"
- All 3 panels visible (Reasoning, Artifacts, Console)

**3. API verification:**
```powershell
# Health check - should return status: "ok"
Invoke-WebRequest -Uri http://localhost:8000/health | Select-Object -ExpandProperty Content
```

### Build Verification (Run before every commit)

```powershell
# Backend tests
cd backend
python -m pytest

# Frontend build
cd frontend
npm run build
```

---

## Testing Phase 0

Quick manual verification tests (PowerShell):

```powershell
# 1. Health check
Invoke-WebRequest -Uri http://localhost:8000/health

# 2. Create session
Invoke-WebRequest -Uri http://localhost:8000/api/v1/sessions `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"title": "Test Session"}'

# 3. List sessions
Invoke-WebRequest -Uri http://localhost:8000/api/v1/sessions

# 4. Send message (replace SESSION_ID)
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/sessions/SESSION_ID/messages" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"content": "Hello"}'
```

**Expected results:**
- Test 1: 200 OK with Docker and resource checks
- Test 2: 201 Created with session ID
- Test 3: 200 OK with array of sessions
- Test 4: 201 Created with mock response (prefixed with [MOCK])

---

## Known Issues and Workarounds

### Issue: pydantic-settings not loading .env

**Symptom:** DATABASE_URL shows as None even with .env file present.

**Root causes:**
1. BOM character in .env file (PowerShell default)
2. Working directory mismatch
3. .env file in wrong location

**Workarounds (in order of preference):**
1. Set environment variable directly: `$env:DATABASE_URL = "..."`
2. Recreate .env with UTF8NoBOM: `Set-Content -Path .env -Value "..." -Encoding UTF8NoBOM`
3. Use explicit path in Settings config (not recommended for production)

### Issue: Alembic MissingGreenlet error

**Symptom:** Migrations fail with greenlet error.

**Cause:** Alembic trying to use asyncpg driver.

**Fix:** Ensure `backend/alembic/env.py` has the load_dotenv() and URL conversion code (see section 1 above).

---

## Frontend Development Rules (Added B1.0)

### Before Committing Frontend Code

**MANDATORY verification steps:**
```powershell
cd frontend
npm run build    # Must pass - catches missing imports
npm run lint     # Should pass - catches code issues
```

If `npm run build` fails with "Module not found":
1. The import path is wrong, OR
2. The file doesn't exist - CREATE IT
3. Never commit until build passes

### Frontend File Organization

**Components:** `src/components/{feature}/{ComponentName}.tsx`
**Hooks:** `src/lib/hooks/use{HookName}.ts`
**API Types:** `src/lib/api/types.ts`
**Utilities:** `src/lib/utils/{utilName}.ts`
**Constants:** `src/lib/utils/constants.ts`

### API Integration Pattern

```typescript
// 1. Define types in src/lib/api/types.ts
export interface HealthResponse {
  status: string;
  // ... match backend response exactly
}

// 2. Create hook in src/lib/hooks/useHealth.ts
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });
}

// 3. Map backend format to frontend needs in the hook
// Example: backend returns "ok", frontend needs "healthy"
```

### Common Frontend Mistakes to Avoid

1. **Importing non-existent files** - Always create the file first
2. **Mismatched API types** - Check backend response format before coding
3. **Forgetting providers** - React Query needs QueryClientProvider in layout
4. **Path alias issues** - `@/` maps to `src/`, verify in tsconfig.json

---

## Code Style Guidelines

### Imports
```python
# Standard library
import os
import sys
from datetime import datetime

# Third-party
from fastapi import FastAPI
from sqlalchemy import String

# Local
from .config import get_settings
from .database import Base
```

### Database Models
- Use SQLAlchemy 2.0 syntax (`Mapped[]`, `mapped_column()`)
- UUID primary keys as strings
- Timezone-aware timestamps with `server_default=func.now()`
- Add indexes for foreign keys and common query columns
- Document schema versions in model docstrings

### Error Handling
```python
# GOOD - Actionable error
raise ValueError(
    "DATABASE_URL not set. Please set the DATABASE_URL environment variable "
    "or create a .env file with DATABASE_URL=postgresql+asyncpg://..."
)

# BAD - Not actionable
raise ValueError("Database configuration error")
```

### Logging
```python
from .logging_config import get_logger

logger = get_logger(__name__)

logger.info("Server starting")
logger.error("Database connection failed", exc_info=True)
logger.debug(f"Config loaded: {settings.dict()}")
```

---

## Git Commit Guidelines

**Good commits:**
- `Complete B0.0.2 database initialization and migrations`
- `Add configuration validation and structured logging`
- `Fix Alembic env.py to load dotenv and convert async URL`

**Bad commits:**
- `fix bug` (not specific)
- `updates` (not descriptive)
- `WIP` (work should be complete before committing)

**Multi-file commits:** Group related changes:
```bash
git add backend/alembic/env.py backend/app/database.py
git commit -m "Fix database URL handling in both app and Alembic"
```

---

## Session Handoff Checklist

When finishing a session, ensure:

**Code Quality:**
- [ ] All code is committed
- [ ] No debug print statements left in code
- [ ] All imports are used (no commented-out imports)
- [ ] Error messages are actionable

**Build Verification (CRITICAL - added after B1.0 issues):**
- [ ] Backend: `cd backend && python -m pytest` passes (or no tests fail)
- [ ] Frontend: `cd frontend && npm run build` completes without errors
- [ ] All imported files actually exist (no "Module not found" possible)
- [ ] API contracts match between backend responses and frontend expectations

**Documentation:**
- [ ] devlog.md updated with session summary
- [ ] roadmap.md status section updated
- [ ] Any new API endpoints documented

**Security:**
- [ ] .env file not committed (verify with `git status`)
- [ ] No secrets or API keys in code

**Integration:**
- [ ] If backend API changed, frontend updated to match
- [ ] If frontend expects new data, backend provides it

---

## Phase Progression Rules

**DO NOT start Phase 1 until:**
- Phase 0 is marked complete in roadmap.md
- User explicitly requests Phase 1 work
- All Phase 0 tests pass

**Each phase must deliver:**
- End-to-end working feature
- Tests (including failure paths)
- Updated documentation
- Migration path from previous phase

**Vertical slice principle:**
- Phase 0: Backend foundations + database + basic API
- Phase 1: Minimal UI that uses Phase 0 API
- Phase 2: Agent runtime that integrates with Phase 0 + Phase 1
- NOT: Complete backend, then complete frontend, then complete agent

---

## Debugging Tips

### Database not initializing
```python
# Add to app/main.py lifespan temporarily
logger.info(f"DATABASE_URL: {settings.database_url}")
logger.info(f"DB configured: {db.is_configured}")
```

### Migrations not applying
```powershell
# Check current migration state
alembic current

# Check migration history
alembic history

# Try upgrading with SQL output
alembic upgrade head --sql
```

### Environment variables not loading
```python
# Add to config.py temporarily
import os
print(f"Working dir: {os.getcwd()}")
print(f".env exists: {os.path.exists('.env')}")
print(f"DATABASE_URL from env: {os.getenv('DATABASE_URL')}")
```

---

## Resources

- **SQLAlchemy 2.0 docs:** https://docs.sqlalchemy.org/en/20/
- **FastAPI docs:** https://fastapi.tiangolo.com/
- **Alembic docs:** https://alembic.sqlalchemy.org/
- **pydantic-settings:** https://docs.pydantic.dev/latest/concepts/pydantic_settings/

---

**Remember:** This project follows strict protocols. When in doubt:
1. Read the roadmap
2. Read recent devlog entries
3. Ask the user before making architectural decisions
4. Document everything

**Last Updated:** 2026-01-26 (v2.0 Platform Pivot - simplified vision, focused roadmap)
