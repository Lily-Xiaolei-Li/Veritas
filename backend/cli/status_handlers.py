from __future__ import annotations

import os
import sys

from .contract import success_envelope
from .state_store import (
    load_state, state_file,
    get_sessions_api, get_personas_api,
    get_session_artifacts_api, get_session_runs_api,
)

DISTRIBUTION_MODE = "bundled-backend-v1"


def status_show(args):
    state = load_state()
    path = state_file()

    sessions = state.get("sessions", [])
    sources = state.get("sources", [])
    personas = state.get("personas", [])

    # Aggregate runs and artifacts across all sessions from API
    all_runs = []
    all_artifacts = []
    for sess in sessions:
        sid = sess.get("id")
        if sid:
            sess_runs = get_session_runs_api(sid)
            if sess_runs:
                all_runs.extend(sess_runs)
            sess_arts = get_session_artifacts_api(sid)
            if sess_arts:
                all_artifacts.extend(sess_arts)
    runs = all_runs if all_runs else state.get("runs", [])
    artifacts = all_artifacts if all_artifacts else state.get("artifacts", [])

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
