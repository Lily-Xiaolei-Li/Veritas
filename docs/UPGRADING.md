# Upgrading / Migration Notes

This document describes how to upgrade Agent B safely, especially when database schema migrations are involved.

> Scope: This repo is still in **0.x** (pre-v1). Breaking changes may occur.

---

## TL;DR

- **Development mode** is forgiving: the app may keep running even if DB/migrations are not healthy (to support debugging).
- **Production mode** is strict: if `ENVIRONMENT=production` and `DATABASE_URL` is set, Agent B will **fail fast** if:
  - database initialization fails, or
  - Alembic migrations fail.

---

## 1) Before you upgrade

1. Pull the latest changes:
   ```powershell
   git pull
   ```

2. Reinstall backend dependencies:
   ```powershell
   cd backend
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Reinstall frontend dependencies:
   ```powershell
   cd ..\frontend
   npm ci
   ```

---

## 2) Database migrations (Alembic)

### When do I need to run migrations?

If a change includes new/updated DB models or a new Alembic revision under `backend/alembic/versions/`, you should run migrations.

### Run migrations manually

```powershell
cd backend
.\venv\Scripts\activate
python -m alembic upgrade head
```

### Troubleshooting migrations

- Check PostgreSQL is running and reachable.
- Confirm your `DATABASE_URL` is correct.
- If you run in production mode, failures will stop startup by design.

See also: `TROUBLESHOOTING.md` → Alembic Migrations.

---

## 3) Environment variables and `.env` precedence

Agent B uses `.env` files for convenience, but explicit environment variables always win.

### Key rule

- If `DATABASE_URL` is explicitly set (even to an empty string), Agent B will **not** override it from `.env`.

This matters for:
- CI test runs (`DATABASE_URL=''` means “no DB mode”)
- Local overrides when debugging

---

## 4) Stable start scripts

If you use the stable scripts:
- `Start Veritas (Stable).bat`
- `Stop Veritas (Stable).bat`

Logs are written to:
- `./.run/backend.out.log` + `./.run/backend.err.log`
- `./.run/frontend.out.log` + `./.run/frontend.err.log`

Health endpoints:
- Backend: http://localhost:8000/api/v1/health
- Tools: http://localhost:8000/api/v1/tools

---

## 5) Recommended upgrade workflow (safe)

1. Stop Agent B.
2. Pull changes.
3. Install deps (backend + frontend).
4. Run migrations (`alembic upgrade head`).
5. Start Agent B.

