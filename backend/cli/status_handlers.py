from __future__ import annotations

import os
import sys

from .contract import success_envelope
from .state_store import load_state, state_file

DISTRIBUTION_MODE = "bundled-backend-v1"


def status_show(args):
    state = load_state()
    path = state_file()

    sessions = state.get("sessions", [])
    runs = state.get("runs", [])
    sources = state.get("sources", [])
    artifacts = state.get("artifacts", [])
    personas = state.get("personas", [])

    return success_envelope(
        result="ok",
        data={
            "status": {
                "schema_version": "1.0",
                "distribution": DISTRIBUTION_MODE,
                "python_version": sys.version.split()[0],
                "state_file": str(path),
                "state_exists": bool(path.exists()),
                "current_session_id": state.get("current_session_id"),
                "counts": {
                    "sessions": len(sessions),
                    "runs": len(runs),
                    "sources": len(sources),
                    "artifacts": len(artifacts),
                    "personas": len(personas),
                },
                "cwd": os.getcwd(),
            }
        },
    )


def status_doctor(args):
    path = state_file()
    checks = []

    # check state file directory writable
    dir_ok = path.parent.exists() and os.access(path.parent, os.W_OK)
    if not path.parent.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            dir_ok = os.access(path.parent, os.W_OK)
        except Exception:
            dir_ok = False

    checks.append({"name": "state_dir_writable", "ok": bool(dir_ok), "detail": str(path.parent)})

    py_ok = sys.version_info >= (3, 10)
    checks.append({"name": "python_version", "ok": py_ok, "detail": sys.version.split()[0]})

    checks.append({"name": "schema_version", "ok": True, "detail": "1.0"})

    overall_ok = all(c["ok"] for c in checks)

    return success_envelope(
        result="ok",
        data={
            "doctor": {
                "ok": overall_ok,
                "checks": checks,
                "state_file": str(path),
                "distribution": DISTRIBUTION_MODE,
            }
        },
    )
