# Release Checklist (v0.x → v1.0 prep)

This checklist is a practical guide to shipping a clean release of Agent B.

> Note: While this repo is still 0.x, you can still publish “stable” releases. Once v1.0.0 is tagged, SemVer compatibility expectations increase.

---

## 0) Pre-flight

- [ ] Git working tree clean (`git status`)
- [ ] CI is green on main (backend + frontend)
- [ ] Quickstart works on a clean machine (or at least a fresh clone)

---

## 1) QA / Smoke

### Backend
- [ ] `pytest -q` passes locally
- [ ] Start backend (`uvicorn app.main:app`) and confirm:
  - [ ] `GET /api/v1/health` returns 200
  - [ ] `GET /api/v1/tools` returns a list
  - [ ] Create a session and run tool smoke (file_write/file_read/shell_exec)

### Frontend
- [ ] `npm run lint`
- [ ] `npm test`
- [ ] `npm run build`

---

## 2) Database / migrations

- [ ] Alembic head is correct (no pending migrations)
  - [ ] `python -m alembic upgrade head`
- [ ] Production behavior confirmed:
  - [ ] With `ENVIRONMENT=production` + DB configured, startup fails fast if migrations fail

See: `docs/UPGRADING.md`

---

## 3) Documentation

- [ ] README is current (Quickstart links, stable start, endpoints)
- [ ] `TROUBLESHOOTING.md` covers common failures
- [ ] `docs/UPGRADING.md` is accurate
- [ ] `docs/SECURITY_MODEL.md` is accurate

---

## 4) Release hygiene

- [ ] `LICENSE` present
- [ ] `CHANGELOG.md` updated (move key items from Unreleased to the release section)
- [ ] Decide version number (keep 0.x or tag v1.0.0)

---

## 5) Tag + publish (when you’re ready)

- [ ] Create git tag (example)
  - `git tag v0.x.y`
  - `git push --tags`
- [ ] Create GitHub Release with:
  - [ ] release notes
  - [ ] migration notes (if any)
  - [ ] known issues

---

## 6) Post-release

- [ ] Start a new `[Unreleased]` section in `CHANGELOG.md`
- [ ] Confirm users can still run stable start scripts
