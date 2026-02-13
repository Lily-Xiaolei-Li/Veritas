# Agent B Troubleshooting Guide

This guide documents common issues encountered during development and deployment, along with their solutions.

> Note: This repo is **NO DOCKER** by default. If you see older Docker snippets below, treat them as legacy notes; prefer local PostgreSQL + the stable start scripts.

---

## Table of Contents

1. [Phase 0 Setup Issues](#phase-0-setup-issues)
2. [Database Configuration](#database-configuration)
3. [Alembic Migrations](#alembic-migrations)
4. [Environment Variables](#environment-variables)
5. [PowerShell-Specific Issues](#powershell-specific-issues)
6. [No Docker Required](#-no-docker-required)

---

## Phase 0 Setup Issues

### Issue: ModuleNotFoundError when running uvicorn

**Error:**
```
ModuleNotFoundError: No module named 'app'
```

**Cause:** Running uvicorn from the wrong directory.

**Solution:**
```powershell
# Must run from backend directory
cd backend
uvicorn app.main:app --reload
```

**Prevention:** Always ensure you're in the `backend/` directory before running the development server.

---

### Issue: Missing dependencies after git clone

**Error:**
```
ModuleNotFoundError: No module named 'docker'
ModuleNotFoundError: No module named 'sqlalchemy'
```

**Cause:** Dependencies not installed in virtual environment.

**Solution:**
```powershell
# Ensure virtual environment is activated
# Windows:
.venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

**Prevention:** Always run `pip install -r requirements.txt` after cloning or pulling major changes.

---

## Database Configuration

### Issue: Database not configured on startup

**Error in logs:**
```
INFO: Database not configured (DATABASE_URL not set)
```

**Cause:** Environment variable `DATABASE_URL` is not being loaded.

**Solutions (in order of preference):**

#### Option 1: Set environment variable directly (PowerShell)
```powershell
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_b"
uvicorn app.main:app --reload
```

#### Option 2: Create .env file properly
```powershell
# Use UTF-8 encoding WITHOUT BOM
Set-Content -Path .env -Value "DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agent_b" -Encoding UTF8NoBOM
```

#### Option 3: Fix existing .env file with BOM
```powershell
# Read and rewrite without BOM
$content = Get-Content .env -Raw
[System.IO.File]::WriteAllText("$(pwd)/.env", $content, (New-Object System.Text.UTF8Encoding $false))
```

**Verification:**
```powershell
# Check if variable is loaded
uvicorn app.main:app --reload
# Look for: "Database initialized successfully" in logs
```

---

### Issue: PostgreSQL connection refused

**Error:**
```
sqlalchemy.exc.OperationalError: could not connect to server: Connection refused
```

**Cause:** PostgreSQL server is not running.

**Solution:**
```powershell
# Start PostgreSQL using Docker
docker run -d `
  --name agent-b-postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=agent_b `
  -p 5432:5432 `
  postgres:16

# Verify it's running
docker ps | Select-String agent-b-postgres
```

**Check if port 5432 is already in use:**
```powershell
# Windows
netstat -ano | findstr :5432

# If occupied, either:
# 1. Stop the other service
# 2. Use a different port in DATABASE_URL
```

---

## Alembic Migrations

### Production mode: startup fails after migration/DB error

**Symptom:**
- App exits during startup when `ENVIRONMENT=production` and DB/migrations fail.

**Why this happens:**
- In production, Agent B is configured to **fail fast** if the database schema is not healthy. This prevents running with missing tables / mismatched migrations.

**How to fix (checklist):**
1. Confirm PostgreSQL is running and reachable (host/port).
2. Confirm `DATABASE_URL` is correct (user/password/db name).
3. Run migrations manually:
   ```powershell
   cd backend
   .\venv\Scripts\activate
   python -m alembic upgrade head
   ```
4. If migrations still fail, inspect the error and compare:
   - current revision vs head
   - whether the DB/user has permissions to create tables.

**Tip:** For local development you can use `ENVIRONMENT=development` to keep the server booting while you debug, but production deployments should keep the fail-fast behavior.

### Issue: psycopg2 not available on Python 3.13+ / Windows (B1.1 Fix)

**Error on startup:**
```
Warning: Could not determine current revision: No module named 'psycopg2'
```

**Or during pip install:**
```
error: subprocess-exited-with-error
building 'psycopg2._psycopg' extension
error: Microsoft Visual C++ 14.0 or greater is required
```

**Cause:** psycopg2-binary doesn't have pre-built wheels for:
- Python 3.13+ on Windows
- Python 3.14+ on any platform
- Building from source requires PostgreSQL dev tools (pg_config) which aren't typically installed

**Impact:**
- Can't run migrations (`alembic upgrade head` fails)
- Can't create migrations (`alembic revision --autogenerate` fails)
- Warning on every startup (noisy logs)
- Database schema drift if future schema changes are needed

**Solution: Use psycopg v3 instead of psycopg2**

psycopg v3 is the modern replacement with:
- Pure Python fallback mode (no compilation needed)
- Better Windows support
- Pre-built wheels for newer Python versions

**Step 1: Update requirements.txt**
```
# BEFORE (broken on Python 3.14/Windows)
psycopg2-binary==2.9.9

# AFTER (works everywhere)
psycopg[binary]>=3.1.0
```

**Step 2: Update all URL conversion code**

The driver string changes from `postgresql+psycopg2://` to `postgresql+psycopg://`.

Update in THREE places:
1. `backend/alembic/env.py`
2. `backend/app/migrations.py` (line 38)
3. `backend/app/migrations.py` (line 55)

```python
# BEFORE
sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

# AFTER
sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
```

**Step 3: Install in your venv**
```powershell
# If using start.bat (which uses venv), install there:
.\venv\Scripts\pip.exe install "psycopg[binary]>=3.1.0"

# Or activate venv and install:
.\venv\Scripts\activate
pip install "psycopg[binary]>=3.1.0"
```

**Verification:**
```powershell
# Restart the backend and check logs
# Should see migration messages WITHOUT warnings:
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

**Common Mistake:** Installing psycopg globally instead of in the venv. The `start.bat` script uses `venv\Scripts\activate.bat`, so psycopg must be installed in that venv.

---

### Issue: MissingGreenlet error during migrations

**Error:**
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called;
can't call await_only() here.
```

**Cause:** Alembic is trying to use the async driver (asyncpg) instead of a sync driver.

**Solution:**

The fix has been applied to `backend/alembic/env.py`:

1. Load environment variables with `python-dotenv`
2. Convert async URL to sync URL for Alembic

**Verify the fix is in place:**
```python
# In backend/alembic/env.py
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Convert asyncpg (async) to psycopg v3 (sync) for Alembic
database_url = os.getenv("DATABASE_URL")
if database_url:
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    config.set_main_option("sqlalchemy.url", sync_url)
```

**If still broken, ensure psycopg is installed in the correct environment:**
```powershell
# Check which Python/pip is active
where python
where pip

# Install psycopg v3
pip install "psycopg[binary]>=3.1.0"
```

---

### Issue: Alembic can't find migrations directory

**Error:**
```
alembic.util.exc.CommandError: Can't locate revision identified by 'head'
```

**Cause:** Running alembic from wrong directory or migrations not initialized.

**Solution:**
```powershell
# Run from backend directory
cd backend

# Check migrations directory exists
ls alembic/versions/

# If no migrations exist, they may need to be generated
alembic revision --autogenerate -m "Initial schema"

# Then apply them
alembic upgrade head
```

---

## Environment Variables

### Issue: .env file has BOM character (PowerShell)

**Symptom:** Variables in .env file are not loaded, even though file exists.

**Cause:** PowerShell `Out-File` or `Set-Content` may add BOM (Byte Order Mark) to UTF-8 files by default.

**Solution:**
```powershell
# Create .env WITHOUT BOM
Set-Content -Path .env -Value "DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agent_b" -Encoding UTF8NoBOM

# Or use echo (Git Bash/WSL)
echo "DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agent_b" > .env
```

**Detection:**
```powershell
# Check file for BOM
Get-Content .env -Encoding Byte -TotalCount 3
# If you see: 239 187 191 - that's BOM, file needs to be recreated
```

---

### Issue: pydantic-settings not loading .env file

**Symptom:** `Settings` class shows default/None values even with .env file present.

**Causes:**
1. .env file has BOM character
2. .env file is in wrong directory
3. Working directory is not where .env file is located

**Solutions:**

1. **Fix BOM issue** (see above)

2. **Verify .env location:**
```powershell
# .env must be in backend/ directory
ls backend/.env
```

3. **Use environment variables instead:**
```powershell
# Set directly in PowerShell
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/agent_b"

# Or add to shell profile for persistence
```

4. **Debug config loading:**
```python
# Add to app/config.py temporarily
print(f"Loading config from: {os.getcwd()}")
print(f".env exists: {os.path.exists('.env')}")
```

---

### Issue: Agent runs stuck in `running` / repeated LLM retries

**Symptom:**
- `/api/v1/sessions/{session_id}/messages` returns a `run_id`, but `/api/v1/runs/{run_id}` stays `running`.
- Backend logs show `agent_b.llm.retry` with long delays (e.g. 60s).

**Cause (common in dev):**
Default LLM provider is **Gemini**, but local environment has no key or hits quota/rate-limit.

**Fix (recommended for local dev):**
Use the built-in **mock** provider to make end-to-end flows deterministic.

Add to `backend/.env`:
```env
LLM_DEFAULT_PROVIDER=mock
LLM_DEFAULT_MODEL=mock-v1
LLM_MAX_RETRIES=1
LLM_REQUEST_TIMEOUT=30
```

---

## PowerShell-Specific Issues

### Issue: Invoke-WebRequest doesn't work like curl

**Problem:** Unix `curl` commands don't translate directly to PowerShell.

**Unix (bash):**
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "Test"}'
```

**PowerShell equivalent:**
```powershell
Invoke-WebRequest -Uri http://localhost:8000/api/v1/sessions `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"title": "Test"}'

# Or use shorter alias
iwr -Uri http://localhost:8000/api/v1/sessions `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"title": "Test"}'
```

**Viewing response:**
```powershell
# Get status code
$response = Invoke-WebRequest -Uri http://localhost:8000/health
$response.StatusCode

# Get response body
$response.Content

# Parse JSON response
$response.Content | ConvertFrom-Json
```

---

### Issue: Line continuation in PowerShell

**Problem:** Bash uses `\` for line continuation, PowerShell uses backtick `` ` ``.

**Bash:**
```bash
docker run -d \
  --name test \
  postgres:16
```

**PowerShell:**
```powershell
docker run -d `
  --name test `
  postgres:16
```

---

### Issue: String quotes in JSON

**Problem:** PowerShell may interpret quotes in JSON strings incorrectly.

**Solution - Use single quotes for JSON body:**
```powershell
# GOOD - single quotes preserve JSON double quotes
-Body '{"title": "Test Session"}'

# BAD - double quotes require escaping
-Body "{\"title\": \"Test Session\"}"
```

---

## ⚠️ No Docker Required

**Agent B does NOT use Docker!** We use a local PostgreSQL installation because Docker is too slow.

If you see any instructions mentioning Docker, they are outdated. Agent B uses:
- **Local PostgreSQL** (Windows service on port 5433)
- **No Docker containers**

### PostgreSQL Service Commands

```powershell
# Check PostgreSQL service status
Get-Service | Where-Object { $_.Name -like "*postgres*" }

# Start PostgreSQL service (if stopped)
net start postgresql-x64-16

# Verify connection
$env:PGPASSWORD = "AgentB#Lily2026!"
psql -h localhost -p 5433 -U agentb -d agent_b -c "SELECT 1;"
```

---

### Issue: Port already in use

**Error:**
```
Error: Bind for 0.0.0.0:5432 failed: port is already allocated
```

**Solution:**
```powershell
# Find what's using the port
netstat -ano | findstr :5432

# Option 1: Stop the other service
# Option 2: Use different port
docker run -d --name agent-b-postgres -p 5433:5432 postgres:16

# Update DATABASE_URL to use new port
$env:DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/agent_b"
```

---

## Frontend Build Issues (Phase 1)

### Issue: Tailwind CSS v4 incompatibility with Next.js 14

**Error:**
```
Cannot apply unknown utility class: border-gray-200
Module not found: Can't resolve '@tailwindcss/postcss'
```

**Cause:** Next.js 16 (canary) auto-installed Tailwind CSS v4 which has breaking syntax changes and incompatible plugin structure.

**Solution - Downgrade to Stable Versions:**

```bash
# Navigate to frontend directory
cd frontend

# Uninstall bleeding-edge versions
npm uninstall next tailwindcss @tailwindcss/postcss @tailwindcss/node

# Install stable versions
npm install next@14.2.13 tailwindcss@^3.4.0 autoprefixer@^10.4.17 postcss@^8.4.33
```

**Update postcss.config.mjs:**
```javascript
// BEFORE (Tailwind v4 - BROKEN)
export default {
  plugins: {
    "@tailwindcss/postcss": {}
  }
}

// AFTER (Tailwind v3 - WORKING)
const config = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
export default config;
```

**Prevention:**
- Always pin major versions in package.json
- Use `^14.2.0` instead of `latest` or `@latest`
- Test builds immediately after dependency updates

---

### Issue: React 19 incompatibility with Next.js 14

**Error:**
```
npm error peer react@"^18.2.0" from next@14.2.13
npm error Found: react@19.2.3
```

**Cause:** Next.js 16 canary installed React 19, which is incompatible with stable Next.js 14.

**Solution:**
```bash
cd frontend
npm install react@^18.2.0 react-dom@^18.2.0
```

**Why this matters:** React 19 has breaking changes and is not stable. Next.js 14 requires React 18.

---

### Issue: next.config.ts not supported in Next.js 14

**Error:**
```
Configuring Next.js via 'next.config.ts' is not supported in Next.js 14.x
```

**Cause:** TypeScript config files (next.config.ts) are only supported in Next.js 15+.

**Solution:**
```bash
# Delete TypeScript config
rm next.config.ts

# Create JavaScript config instead
# File: next.config.mjs
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Your config here
};

export default nextConfig;
```

**Prevention:** Check Next.js version before using TypeScript config files.

---

### Issue: react-resizable-panels v4 export name changes

**Error:**
```
'PanelGroup' is not exported from 'react-resizable-panels'
'PanelResizeHandle' is not exported from 'react-resizable-panels'
```

**Cause:** react-resizable-panels v4 changed export names without proper deprecation warnings.

**Solution - Downgrade to v2:**
```bash
cd frontend
npm install react-resizable-panels@^2.0.0
```

**Why v2?**
- v2 has stable exports: `PanelGroup`, `Panel`, `PanelResizeHandle`
- v4 changed export names without migration guide
- v2 is battle-tested and used by VS Code, Discord

**Prevention:** When upgrading UI libraries, check changelog for breaking changes.

---

### Issue: TypeScript HeadersInit type error

**Error:**
```
Element implicitly has an 'any' type because expression of type '"Authorization"'
can't be used to index type 'HeadersInit'
```

**Cause:** TypeScript strict mode doesn't allow indexing HeadersInit with string keys.

**Solution - Use Record<string, string>:**
```typescript
// BEFORE (BROKEN)
const headers: HeadersInit = {
  "Content-Type": "application/json",
};
headers["Authorization"] = `Bearer ${token}`; // ERROR

// AFTER (WORKING)
const headers: Record<string, string> = {
  "Content-Type": "application/json",
  ...(fetchOptions.headers as Record<string, string>),
};
if (token) {
  headers["Authorization"] = `Bearer ${token}`;
}
```

**Why this works:** `Record<string, string>` is indexable, while `HeadersInit` is a complex union type.

---

### Issue: Node.js not in PATH on Windows

**Error:**
```
npm: command not found
node: command not found
```

**Cause:** Node.js installation didn't add to system PATH automatically.

**Temporary Solution (Git Bash):**
```bash
export PATH="/c/Program Files/nodejs:$PATH"
```

**Temporary Solution (PowerShell):**
```powershell
$env:Path += ";C:\Program Files\nodejs"
```

**Permanent Solution:**
1. Open "Environment Variables" in Windows
2. Edit System PATH
3. Add: `C:\Program Files\nodejs`
4. Restart terminal

**Verification:**
```bash
node --version  # Should show v18.x.x or v20.x.x
npm --version   # Should show 9.x.x or 10.x.x
```

---

### Frontend Dependency Version Matrix (Verified Working)

**IMPORTANT:** Use these exact version ranges to avoid compatibility issues.

```json
{
  "dependencies": {
    "next": "14.2.13",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.33",
    "autoprefixer": "^10.4.17",
    "react-resizable-panels": "^2.0.0",
    "@tanstack/react-query": "^5.17.0",
    "zustand": "^4.5.0"
  },
  "devDependencies": {
    "typescript": "^5",
    "@types/react": "^18",
    "@types/node": "^20",
    "eslint": "^8",
    "eslint-config-next": "14.2.13"
  }
}
```

**Why these versions:**
- **Next.js 14.2.13** - Latest stable Next.js 14 (not canary 16.x)
- **React 18.2.0** - Required by Next.js 14
- **Tailwind 3.4.0** - Latest stable (v4 is alpha/breaking)
- **react-resizable-panels 2.x** - Stable exports (v4 has breaking changes)

---

## Quick Diagnostic Checklist

When things aren't working, run through this checklist:

### 1. Environment Check
```powershell
# Are you in the right directory?
pwd  # Should end in \backend

# Is virtual environment activated?
# Prompt should show (.venv) or similar

# Are dependencies installed?
pip list | Select-String sqlalchemy
pip list | Select-String fastapi
```

### 2. Database Check
```powershell
# Is PostgreSQL running?
docker ps | Select-String postgres

# Is DATABASE_URL set?
echo $env:DATABASE_URL

# Can you connect to PostgreSQL?
docker exec -it agent-b-postgres psql -U postgres -d agent_b
# Type \q to exit
```

### 3. Server Check
```powershell
# Is uvicorn running?
# Check logs for "Database initialized successfully"

# Can you reach health endpoint?
Invoke-WebRequest -Uri http://localhost:8000/health
```

### 4. File Check
```powershell
# Does .env exist?
ls .env

# Check for BOM
Get-Content .env -Encoding Byte -TotalCount 3
# Should NOT see: 239 187 191

# Check .env contents
Get-Content .env
```

---

## Getting Help

If you've tried the solutions above and still have issues:

1. **Check the logs:** Uvicorn outputs detailed error messages
2. **Check devlog.md:** Recent entries may document similar issues
3. **Check git history:** Recent commits may have introduced changes
4. **Create an issue:** Include:
   - Error message (full stack trace)
   - Steps to reproduce
   - Environment info (OS, Python version, Docker version)
   - Output of diagnostic checklist above

---

## Prevention Best Practices

### For Development

1. **Always activate virtual environment** before running commands
2. **Run uvicorn from backend/ directory**
3. **Use UTF8NoBOM encoding** for .env files on Windows
4. **Set DATABASE_URL** before starting server
5. **Start PostgreSQL** before running migrations

### For Configuration

1. **Keep .env file out of git** (already in .gitignore)
2. **Document required variables** in .env.example
3. **Use environment variables** for CI/CD instead of .env files
4. **Test without .env** to ensure env vars work standalone

### For Alembic

1. **Always run from backend/ directory**
2. **Keep env.py in sync** with main app database config
3. **Use load_dotenv()** in env.py for consistency
4. **Convert async URLs to sync** for Alembic compatibility

---

---

## Phase 2 Issues (LLM Provider Abstraction)

### Issue: Python 3.14 incompatibility with asyncpg

**Error during pip install:**
```
error: subprocess-exited-with-error
Building wheel for asyncpg (pyproject.toml) did not run successfully.
```

**Cause:** asyncpg does not have pre-built wheels for Python 3.14 on Windows, and building from source requires Rust toolchain.

**Solution - Use Python 3.12:**
```powershell
# Check available Python versions
py --list

# Recreate venv with Python 3.12
py -3.12 -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**Prevention:**
- Always check dependency compatibility before upgrading Python versions
- asyncpg, many C extensions, and Rust-backed packages may not have wheels for newest Python
- Stick with stable Python versions (3.11, 3.12) for production projects

---

### Issue: pytest-asyncio missing (async tests skipped)

**Symptom:** Running `pytest` shows many tests skipped with no clear message:
```
19 passed, 0 failed, 19 skipped
```

**Cause:** Async tests using `@pytest.mark.asyncio` decorator cannot run without pytest-asyncio installed.

**Solution:**
```powershell
pip install pytest-asyncio==0.24.0
```

**Why 0.24.0?** Version 0.23.0 has compatibility issues with pytest 8.2.0 causing:
```
AttributeError: 'Function' object has no attribute 'get_closest_marker'
```

**Prevention:**
- pytest-asyncio must be in requirements.txt for any project with async tests
- Always verify test counts match expectations (skipped tests = potential missing deps)

**Update requirements.txt:**
```
pytest-asyncio==0.24.0
```

---

### Issue: Google Gemini SDK deprecated (google-generativeai → google-genai)

**Error:**
```
google.generativeai is deprecated. Please use google.genai instead.
404 models/gemini-1.5-flash is not found
```

**Cause:** Google replaced the entire SDK in late 2025:
- OLD: `google-generativeai` package with `import google.generativeai as genai`
- NEW: `google-genai` package with `from google import genai`

The old SDK no longer works with current models.

**Solution - Update to new SDK:**

1. **Update requirements.txt:**
```
# OLD (broken)
google-generativeai>=0.5.0

# NEW (working)
google-genai>=1.0.0
```

2. **Update import and initialization:**
```python
# OLD (broken)
import google.generativeai as genai
genai.configure(api_key=api_key)
self._genai = genai

# NEW (working)
from google import genai
self._client = genai.Client(api_key=api_key)
```

3. **Update API calls:**
```python
# OLD (broken)
model = self._genai.GenerativeModel(model_name)
response = await asyncio.to_thread(
    model.generate_content,
    contents=contents,
)

# NEW (working)
response = self._client.models.generate_content(
    model=model_name,
    contents=contents,
    config=config,
)
```

4. **Update model names:**
```python
# OLD (deprecated/removed)
"gemini-1.5-flash"
"gemini-1.5-pro"

# NEW (current as of Jan 2026)
"gemini-2.0-flash"
"gemini-2.0-flash-lite"
"gemini-2.5-flash"
"gemini-2.5-pro"
```

**Prevention:**
- Check SDK documentation and changelogs before implementing provider integrations
- Run live API tests with real credentials during development, not just mocks
- SDK deprecations can happen without backward compatibility

---

### Issue: Ollama model not found

**Error:**
```
Model 'llama2' not found for this Ollama server
```

**Cause:** The model isn't pulled/installed on the Ollama server.

**Solution:**
```powershell
# List available models
docker exec <container-name> ollama list

# Pull a model
docker exec <container-name> ollama pull llama3

# Or use a model you already have
# Update your code to use the installed model name exactly
```

**Prevention:**
- Always verify model availability with `ollama list` before testing
- Model names are case-sensitive and may include version tags (e.g., `mistral:7b-instruct`)

---

**Last Updated:** 2026-01-26 (B2.0 - LLM Provider testing issues)
