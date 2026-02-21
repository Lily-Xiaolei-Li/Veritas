# Veritas — Local-First Research Workspace

**Version:** 1.0.0  
**Status:** v1.0 (packaged research workbench)  
**Developed by Lily Xiaolei Li**

Veritas is a packaged research workbench for academic researchers. It helps you run an end-to-end workflow locally: manage artifacts, capture context, interact with LLMs (e.g., OpenRouter), and iteratively draft and edit research outputs.

> **Production note:** When `ENVIRONMENT=production` and `DATABASE_URL` is set, Veritas will **fail fast** if database initialization or Alembic migrations fail. This is intentional to avoid running with a broken schema.

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

> ⚠️ **No Docker Required!** Veritas is designed to run without Docker. Using Docker can add complexity and slow down local development/testing. If end-users want to deploy inside Docker later, that is optional and out of scope for this repo.

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

### Starting Veritas

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

### Stopping Veritas

Simply close the two terminal windows (Backend and Frontend).

---

## Database Configuration

Veritas uses a local PostgreSQL instance:

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
Veritas/
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

## 📝 Research Workflow — Academic Paper Drafting

Veritas uses a **persona-driven, artifact-centric workflow** to draft, review, and refine academic papers. The system is designed around **stateless isolation** — each AI call is a clean prompt with explicit context, preventing memory contamination across iterations.

### Core Concepts

| Concept | Role |
|---------|------|
| **Persona** | System prompt defining AI behavior (e.g., Drafter, Reviewer) |
| **Artifact** | A document in the session — paper drafts, templates, reviews |
| **Context** | Artifacts attached to a prompt so the AI can reference them |
| **RAG Library** | Searchable academic paper database for finding real citations |
| **Session** | An isolated workspace for one research task |

### Built-in Personas

| ID | Label | Purpose |
|----|-------|---------|
| `default` | Default Assistant | General-purpose academic help |
| `cleaner` | The Cleaner | Fix messy PDF/DOCX-to-markdown formatting |
| `thinker` | The Thinker | Find hidden patterns, novel insights |
| `templator` | The Templator | Reverse-engineer published papers into structural blueprints |
| `drafter` | The Drafter | Write in precise, journal-quality academic prose |
| `referencer` | The Referencer | Check and suggest citations |
| `skeptic` | The Skeptic | Devil's advocate — find weaknesses and counter-arguments |
| `reviewer` | The Reviewer | Simulate a senior journal reviewer |

### Step-by-Step: Drafting a Paper Section

This workflow demonstrates drafting a **Conclusion** section, but applies to any section (Introduction, Discussion, etc.):

#### Step 1 — Build the Template
- **Persona:** Templator
- **Artifacts:** A published template paper from the target journal
- **Prompt:** "Create a structural template for the [section] part. Reverse-engineer every sentence's rhetorical function. Output a reusable blueprint with [PLACEHOLDER] slots."
- **Output:** A structural blueprint (save as artifact)

#### Step 2 — Draft
- **Persona:** Drafter
- **Artifacts:** Your paper body + relevant sections (e.g., Discussions) + the template from Step 1
- **Prompt:** "Using ONLY information provided, draft the [section] following the template. Use [Journal] style. Harvard in-text references."
- **Output:** First draft (save as artifact)

#### Step 3 — Review
- **Persona:** Reviewer
- **Artifacts:** Your paper body (as BACKGROUND) + the draft (as REVIEW TARGET)
- **Prompt:** "Review the [section] ONLY. Evaluate: (1) claims supported by analysis, (2) implications substantive vs superficial, (3) future research genuine vs filler. Provide Major and Minor revisions."
- **⚠️ Important:** Explicitly state which artifacts are background and which are the review target, otherwise the reviewer may critique the wrong document.
- **Output:** Review report (save as artifact, edit to remove off-topic comments)

#### Step 4 — Revise
- **Persona:** Drafter
- **Artifacts:** Draft + Review report + paper body (background)
- **Prompt:** "Revise the draft addressing ALL Major and Minor revisions in the Review Report. [List specific changes required]."
- **Output:** Revised draft v2 (save as artifact)

#### Step 5 — Check References
- **Persona:** Referencer
- **Artifacts:** Revised draft
- **RAG:** `--rag library` (enables semantic search of your paper library)
- **Prompt:** "Evaluate how well the [section] is referenced. For each claim, check citation adequacy. List sentences that need references but lack them."
- **Output:** Reference check report (save as artifact)

#### Step 6 — Suggest Citations
- **Persona:** Referencer
- **Artifacts:** Revised draft + reference check report
- **RAG:** `--rag library --rag-top-k 15`
- **Prompt:** "For each under-referenced sentence, suggest 3 best citations from the RAG library with reasons. ALL citations must come from the library."
- **Output:** Citation suggestions (save as artifact)

#### Step 7 — Integrate Citations
- **Persona:** Drafter
- **Artifacts:** Revised draft + review report + citation suggestions
- **Prompt:** "Integrate citations from the suggestions. Only add references, do not alter argument structure."
- **Output:** Final draft v3 (save as artifact)

#### Step 8 — Human Review
The author reviews the final draft. AI cannot verify citation accuracy against source papers — only the human who has read the original papers can confirm references are used correctly.

### Design Principles

1. **Stateless isolation** — Each AI call gets a clean prompt. No conversation memory leaks between steps. This prevents the AI from carrying forward errors or biases.
2. **One persona, one job** — Don't ask the Drafter to also review. Don't ask the Reviewer to also fix references. Separation produces better results.
3. **Artifacts as explicit context** — The AI only sees what you attach. This gives you full control over what information shapes each output.
4. **RAG for real citations** — Never let the AI invent references. Use the RAG library to ground citations in your actual paper collection.
5. **Human in the loop** — AI drafts and checks; the human decides. Especially for citation accuracy and theoretical argumentation.

### CLI Usage

```powershell
cd backend

# Basic chat with persona
.\venv\Scripts\python.exe -m cli.main chat send --session <uuid> --persona drafter --message "..." --json 2>$null

# With artifact context
.\venv\Scripts\python.exe -m cli.main chat send --session <uuid> --persona reviewer --artifacts <id1>,<id2> --message "..." --json 2>$null

# With RAG library search
.\venv\Scripts\python.exe -m cli.main chat send --session <uuid> --persona referencer --artifacts <id1> --rag library --rag-top-k 10 --message "..." --json 2>$null

# With RAG + multiple sources
.\venv\Scripts\python.exe -m cli.main chat send --session <uuid> --persona drafter --artifacts <id1>,<id2> --rag library,interviews --message "..." --json 2>$null
```

For the full CLI reference, see [AI-CLI-GUIDE.md](AI-CLI-GUIDE.md).

### Automation Scripts

Pre-built Python scripts that automate the full 8-step workflow end-to-end:

| Script | Purpose |
|--------|---------|
| [`scripts/intro_pipeline.py`](scripts/intro_pipeline.py) | Automates Steps 2–7 for drafting an **Introduction** section. Calls `/api/chat` with appropriate personas, artifacts, and RAG sources, then saves each output as an artifact in the target session. |

**Usage:**
```powershell
# Edit SESSION_ID and artifact IDs in the script, then:
python scripts/intro_pipeline.py
```

These scripts bypass the CLI and call the `/api/chat` endpoint directly via Python's `urllib`, streaming SSE responses. They demonstrate how to orchestrate multi-step drafting pipelines programmatically.

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

**Remember:** Veritas exists to amplify your research, not replace judgment.

---

*Developed by Lily Xiaolei Li*
