# Quickstart (Windows)

Goal: get Agent B running locally in **10–15 minutes**.

## 1) Prereqs
- Python **3.12**
- Node.js **18+**
- PostgreSQL **16+** (optional for smoke/demo; required for full persistence)
- **Qdrant server** (required for Library RAG and VF Middleware — see below)

## 2) Clone
```powershell
git clone https://github.com/Bazza1982/Agent-B-Academic.git
cd Agent-B-Academic
```

## 3) Configure environment
### Backend (.env)
Copy the example:
```powershell
copy backend\.env.example backend\.env
```

If you want persistence, set `DATABASE_URL` in `backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://agentb:<YOUR_PASSWORD>@localhost:5433/agent_b
```

> No-DB mode: You can leave `DATABASE_URL` empty; the server will still start and `/api/v1/health` will work.
>
> **Production mode note:** If you run with `ENVIRONMENT=production`, Agent B will **fail fast** on database/migration errors when `DATABASE_URL` is set. This is intentional to avoid running with a broken schema.

## 4) Start (recommended: stable watchdog)
Double-click:
- **Start Agent-B (Stable).bat**

Then open:
- http://localhost:3000

## 5) Stop
Double-click:
- **Stop Agent-B (Stable).bat**

## Logs
Stable mode writes logs here:
- `./.run/frontend.out.log` + `./.run/frontend.err.log`
- `./.run/backend.out.log` + `./.run/backend.err.log`

## Qdrant Server (Required)

Agent B uses Qdrant in **server mode** (NOT embedded). Start it before the backend:

```powershell
cd C:\Users\Barry Li (UoN)\clawd\tools\qdrant
.\qdrant.exe --config-path config\config.yaml
```

This starts Qdrant on `localhost:6333`. The backend connects via `QDRANT_URL` env var (defaults to `http://localhost:6333`).

> ⚠️ **Never use Qdrant embedded mode** (`QdrantClient(path=...)`). It causes lock file conflicts when multiple processes access the same storage. See `TROUBLESHOOTING.md` for details.

## Quick sanity checks

Qdrant health:
- http://localhost:6333/collections

Backend health:
- http://localhost:8000/api/v1/health

Tools list (auth disabled default):
- http://localhost:8000/api/v1/tools
