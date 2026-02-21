# Veritas Stable Start (Dev)

This project is currently run in **dev mode** (Next.js + Uvicorn). Dev processes sometimes exit or get killed.

To keep it running, use the stable scripts:

- **Start Veritas (Stable).bat** (keeps a watchdog window open)
- **Stop Veritas (Stable).bat**

## Where are the logs?
Stable mode writes logs here:

- `./.run/frontend.out.log` + `./.run/frontend.err.log`
- `./.run/backend.out.log` + `./.run/backend.err.log`

If the UI says Offline or the page won’t load, check these logs first.

## Prerequisites
**Qdrant server must be running** before starting Agent B:
```powershell
cd C:\Users\Lily Xiaolei Li (UoN)\clawd\tools\qdrant
.\qdrant.exe --config-path config\config.yaml
```
Verify: http://localhost:6333/collections

## Health endpoints
- Qdrant: http://localhost:6333/collections
- Backend health: http://localhost:8001/health
- Tools list: http://localhost:8001/api/v1/tools

## Common issues
### Frontend not starting
If `http://localhost:3011` won’t open, check:
- `./.run/frontend.err.log` (errors)
- `./.run/frontend.out.log` (stdout)

If the backend is down too, also check:
- `./.run/backend.err.log`
- `./.run/backend.out.log`

### Port already in use (3011 / 8001)
The stable start/stop scripts will try to stop anything using those ports.

### “Cannot find module ./.next/…”
The stable start clears `frontend/.next` before starting.

