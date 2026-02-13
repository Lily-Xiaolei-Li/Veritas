# Security Model (v0.x)

## Principles
- Local-first: assume the operator is the owner of the machine.
- Prefer safe defaults: bind services to localhost; restrict filesystem scope.
- Tool execution is guarded: blocklist + high-risk approvals (shell_exec).

## Network exposure
- Backend should bind to `127.0.0.1` by default.
- Frontend should bind to `127.0.0.1` by default.

## Production fail-fast (DB/migrations)
- When `ENVIRONMENT=production` and `DATABASE_URL` is set, startup will **fail fast** if DB initialization or Alembic migrations fail.
- This prevents running with a broken schema (missing tables / wrong revision).

## Workspace boundaries
- Built-in file tools restrict paths to workspace-relative paths.
- shell_exec `cwd` is workspace-relative and validated against traversal.

## Auth
- Auth is optional (`AUTH_ENABLED=false` by default).
- When enabled, protected endpoints require Bearer JWT.

## Logging / redaction
- Sensitive values should be redacted before logging.
- Tool routes emit previews (truncated) to avoid huge payloads.
