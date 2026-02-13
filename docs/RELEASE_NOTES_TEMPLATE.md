# Release Notes Template

Use this template when creating a GitHub Release.

---

## Release: vX.Y.Z

### Highlights
- 

### Added
- 

### Changed
- 

### Fixed
- 

### Upgrade / Migration notes
- Database migrations:
  - Run: `cd backend && .\venv\Scripts\activate && python -m alembic upgrade head`
- Production behavior:
  - With `ENVIRONMENT=production` + `DATABASE_URL` set, startup fails fast if DB init/migrations fail.

### Known issues
- 

### Verification
- CI: ✅ green
- Backend: `pytest -q`
- Frontend: `npm run lint && npm test && npm run build`

---

## Copy/paste (GitHub Release body)

**Highlights**
- 

**Upgrade notes**
- 

**Known issues**
- 
