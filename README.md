# Agent B Research — Local-First Research Workspace

**Version:** 1.0.0
**Status:** v1.0 (packaged research workbench)

Agent B Research is a packaged research workbench based on the original Agent B platform. It helps researchers run an end-to-end workflow locally: manage artifacts, capture context, interact with LLMs (e.g., OpenRouter), and iteratively draft and edit research outputs.

> **Production note:** When `ENVIRONMENT=production` and `DATABASE_URL` is set, Agent B Research will **fail fast** if database initialization or Alembic migrations fail. This is intentional to avoid running with a broken schema.

For complete product specifications, see [PRD.md](PRD.md).
For development roadmap, see [roadmap.md](roadmap.md).

## Docs (start here)
- Quickstart (Windows): `docs/QUICKSTART_WINDOWS.md`
- Developer Guide: `docs/DEV_GUIDE.md`
- Extension Guide (Tools): `docs/EXTENSION_GUIDE.md`
- Security Model: `docs/SECURITY_MODEL.md`

## Project meta
- License: `LICENSE` (MIT)
- Changelog: `CHANGELOG.md`
- Upgrading / migration notes: `docs/UPGRADING.md`
- Release checklist: `docs/RELEASE_CHECKLIST.md`
- Release notes template: `docs/RELEASE_NOTES_TEMPLATE.md`

---

## Prerequisites

- **Python 3.12** (required)
- **Node.js 18 or higher** (for frontend)
- **PostgreSQL 16+** (local installation, NOT Docker)
- **Git**
- Minimum 4GB RAM available
- Minimum 5GB disk space

> ⚠️ **No Docker Required!** Agent B is designed to run without Docker. Using Docker can add complexity and slow down local development/testing. If end-users want to deploy inside Docker later, that is optional and out of scope for this repo.

---

## Quick Start (Windows)

### One-Time Setup

1. **Install Python 3.12** from https://www.python.org/downloads/
2. **Install Node.js 18+** from https://nodejs.org/
3. **Install PostgreSQL** from https://www.postgresql.org/download/windows/
   - During installation, set port to **5433** (to avoid conflicts)
   - Remember the postgres (superuser) password

4. **Create a user + database (example):**
   ```powershell
   # Connect to PostgreSQL
   psql -h localhost -p 5433 -U postgres

   -- Create user + DB (choose your own password)
   CREATE USER agentb WITH PASSWORD '<YOUR_PASSWORD>';
   CREATE DATABASE agent_b OWNER agentb;
   GRANT ALL PRIVILEGES ON DATABASE agent_b TO agentb;
   \q
   ```

### Starting Agent B

**Double-click `start.bat`** or run in terminal:
```powershell
.\start.bat
```

This will:
1. Check PostgreSQL connection
2. Install/update Python dependencies
3. Run database migrations
4. Open backend server (port 8000)
5. Open frontend server (port 3000)
6. Open http://localhost:3000 in your browser

### Stopping Agent B

Simply close the two terminal windows (Backend and Frontend).

---

## Database Configuration

Agent B uses a local PostgreSQL instance:

| Setting | Value |
|---------|-------|
| Host | localhost |
| Port | 5433 |
| Database | agent_b |
| User | agentb |
| Password | <YOUR_PASSWORD> |

Connection string in `backend/.env`:
```
DATABASE_URL=postgresql+asyncpg://agentb:<YOUR_PASSWORD>@localhost:5433/agent_b
```

---

## Manual Start (Alternative)

If you prefer to start services manually:

**Terminal 1 (Backend):**
```powershell
cd backend
.\venv\Scripts\activate
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 (Frontend):**
```powershell
cd frontend
npm run dev
```

---

## Project Structure

```
Agent-B-Academic/
├── backend/                     # FastAPI backend
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration
│   │   ├── models.py            # Database models
│   │   ├── agent/               # LangGraph agent runtime
│   │   ├── llm/                 # LLM provider abstraction
│   │   ├── routes/              # API routes
│   │   └── services/            # Business logic
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Backend tests
│   ├── xiaolei_api/             # XiaoLei integration API
│   └── requirements.txt         # Python dependencies
│
├── frontend/                    # Next.js frontend
│   ├── src/
│   │   ├── app/                 # Next.js App Router
│   │   ├── components/          # React components
│   │   └── lib/                 # Hooks, store, utils
│   └── package.json             # Node dependencies
│
├── docs/                        # Documentation
├── data/                        # Data files
├── start.bat                    # Start all services
├── PRD.md                       # Product Requirements
├── roadmap.md                   # Development roadmap
├── devlog.md                    # Development log
└── PROJECT-LOG.md               # Project history
```

---

## Current Status

### Completed ✅

- **Phase 0**: Foundations, Database, Auth, Execution
- **Phase 1 (B1.0-B1.6)**: Workbench UI, Streaming, Files, Kill Switch, Sessions, Auth
- **B1.8**: Tool Framework (built-ins + tool_start/tool_end console + tests)
- **B2.0**: LLM Provider Abstraction
- **B2.1**: LangGraph Runtime (optional advanced module)

### Next Steps

- **B2.2**: Documentation (Quickstart, Dev Guide, Extension Guide)
- **B2.4**: Testing & Stability (API smoke + CI)
- **B1.9**: Simple Agent Loop acceptance + smoke tests (align with run-state-machine)
- **B2.5**: v1.0 Release checklist

---

## Architecture

| Layer | Technology | Status |
|-------|-----------|--------|
| Frontend | React/Next.js 14 | ✅ Complete |
| API Gateway | FastAPI | ✅ Complete |
| Agent Runtime | LangGraph | ✅ Complete |
| LLM Providers | Gemini, OpenRouter, Ollama | ✅ Complete |
| Database | PostgreSQL 17 (local) | ✅ Complete |
| XiaoLei API | Clawdbot Gateway integration | ✅ Complete |

---

## 🔒 Development Rules

### Code Integration Workflow

**Only main agent (小蕾) and super agent (超级小蕾) can modify this project!**

1. Coder agents work in their own workspaces
2. Main/super reviews code quality
3. Approved code is integrated by main/super only
4. Direct modifications by coder agents are prohibited

---

## Troubleshooting

### PostgreSQL Connection Failed

1. Check if PostgreSQL service is running:
   ```powershell
   Get-Service -Name "postgresql*"
   ```

2. Start the service if needed:
   ```powershell
   net start postgresql-x64-17
   ```

3. Verify connection:
   ```powershell
   psql -h localhost -p 5433 -U agentb -d agent_b
   ```

### Backend Won't Start

1. Ensure Python 3.12 venv is activated
2. Check that all requirements are installed
3. Verify DATABASE_URL in `backend/.env`

### Frontend Won't Start

1. Ensure node_modules is installed: `npm install --legacy-peer-deps`
2. Check for port 3000 conflicts

---

## License

MIT License

---

**Remember:** Agent B exists to amplify Agent A (you), not replace judgment.
