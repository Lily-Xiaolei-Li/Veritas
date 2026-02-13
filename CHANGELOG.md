# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(once v1.0.0 is tagged).

## [Unreleased]

### Added
- CI: backend lint (ruff), syntax check (compileall), unit tests, and a full API smoke test (boot + sessions + tool exec + artifacts).
- CI: frontend lint, vitest, and Next.js production build.
- Managed RAG Sources (M1): DB model + routes + spec + tests.
- **New Project button**: Reset workspace with confirmation dialog (`POST /api/v1/workspace/reset`).
- **Copy artifact**: Duplicate artifacts via context menu (`POST /api/v1/artifacts/{id}/copy`).
- **Knowledge Source modal**: Connect/Refresh button to retry RAG connection.
- **Explorer sorting**: A (Name), D (Date), T (Type) buttons in Explorer header.
- **PM2 ecosystem config**: `frontend/ecosystem.config.js` for reliable port configuration.

### Changed
- Startup: run Alembic migrations when DB is configured.
- Production: fail fast if DB initialization or migrations fail.
- Env precedence: do not let `.env` override explicit `DATABASE_URL` (including empty string).
- **artifact_preview_max_kb**: Increased from 100KB to 2MB (max 10MB) to support full academic papers.
- **Explorer maxSize**: Increased from 25% to 50% width.
- **Knowledge Source stats**: Now shows "Chunks indexed" instead of misleading "Vectors/Documents".

### Fixed
- Stable watchdog: backend health URL now uses `/api/v1/health`.
- Frontend: removed Next build warnings (hooks deps + next/image).
- Tests: reduced warning noise and improved stability around imports and config.
- **Conversation tab**: Added `API_BASE_URL` prefix to `authGet` call (was showing HTML instead of data).
- **Log tab layout**: Wrapped LogTab in `flex-1 overflow-hidden` container (tab bar was hiding on first selection).
- **workspace.ts**: All API calls now properly prefixed with `API_BASE_URL`.
- **Qdrant compatibility**: Use `getattr()` for `vectors_count` to handle different Qdrant versions.
- **Empiricals RAG path**: Fixed `INTERVIEWS_RAG_PATH` to point to correct `qdrant_interviews` directory.
- **Library documents empty**: Added `paper_name` to payload extraction keys.
- **Explorer folder dates**: Backend now returns `modified` field for folders.
- **CLI health command**: Fixed `get_api_base` import error.
- **Edit button disabled**: Large files (>100KB) can now be edited after increasing preview limit.

## [0.x]
- Pre-v1 development releases. (Version tags not stabilized yet.)
