# Developer Guide

## Repo layout
- `backend/` FastAPI API + services + tools + tests
- `frontend/` Next.js workbench UI + tests
- `docs/` canonical docs (run state machine, guides)

## Common commands
### Backend
```powershell
cd backend
.\venv\Scripts\activate
pytest -q
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Health check
# http://localhost:8000/api/v1/health
```

### Frontend
```powershell
cd frontend
npm ci
npm test
npm run dev -- -H 127.0.0.1 -p 3000
```

## CI
GitHub Actions workflow:
- `.github/workflows/ci.yml`

What CI does (high level):
- **Backend**: lint (ruff) → syntax check (compileall) → unit tests (pytest) → API smoke (boots app + hits key endpoints, including tool exec and artifact creation)
- **Frontend**: lint → unit tests (vitest) → production build (next build)

## Run lifecycle (canonical)
See: `docs/run-state-machine.md`
