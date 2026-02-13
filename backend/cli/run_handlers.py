from __future__ import annotations

from uuid import uuid4

from .contract import CLIBusinessError, success_envelope
from .state_store import load_state, now_iso, save_state


def _find_run(state: dict, run_id: str):
    return next((r for r in state.get("runs", []) if r.get("id") == run_id), None)


def run_list(args):
    state = load_state()
    runs = state.get("runs", [])
    if args.session:
        runs = [r for r in runs if r.get("session_id") == args.session]
    runs = sorted(runs, key=lambda r: (r.get("started_at", ""), r.get("id", "")))
    return success_envelope(result="ok", data={"runs": runs, "session_id": args.session})


def run_show(args):
    if not args.run:
        raise CLIBusinessError(code="RUN_ID_REQUIRED", message="--run is required")

    state = load_state()
    run = _find_run(state, args.run)
    if not run:
        raise CLIBusinessError(code="RUN_NOT_FOUND", message="Run not found", details={"run": args.run})
    return success_envelope(result="ok", data={"run": run})


def run_retry(args):
    if not args.run:
        raise CLIBusinessError(code="RUN_ID_REQUIRED", message="--run is required")

    state = load_state()
    base = _find_run(state, args.run)
    if not base:
        raise CLIBusinessError(code="RUN_NOT_FOUND", message="Run not found", details={"run": args.run})

    run_id = f"r_{uuid4().hex[:10]}"
    response_text = f"Echo: {base.get('request', '')}"

    run = {
        "id": run_id,
        "session_id": base["session_id"],
        "status": "completed",
        "started_at": now_iso(),
        "ended_at": now_iso(),
        "parent_run_id": base["id"],
        "request": base.get("request"),
        "response": response_text,
    }
    state.setdefault("runs", []).append(run)

    state.setdefault("messages", []).append(
        {
            "session_id": run["session_id"],
            "run_id": run_id,
            "user": run.get("request"),
            "assistant": run.get("response"),
            "created_at": run["ended_at"],
        }
    )

    state.setdefault("artifacts", []).append(
        {
            "id": f"art_{uuid4().hex[:10]}",
            "session_id": run["session_id"],
            "run_id": run_id,
            "name": f"run-{run_id}.md",
            "type": "markdown",
            "content": run["response"],
            "created_at": run["ended_at"],
            "provenance": {"type": "run"},
        }
    )

    save_state(state)
    return success_envelope(result="created", data={"run": run})


def run_resume(args):
    # v1 baseline: resume uses retry path.
    return run_retry(args)


def run_cancel(args):
    if not args.run:
        raise CLIBusinessError(code="RUN_ID_REQUIRED", message="--run is required")

    state = load_state()
    run = _find_run(state, args.run)
    if not run:
        raise CLIBusinessError(code="RUN_NOT_FOUND", message="Run not found", details={"run": args.run})

    run["status"] = "cancelled"
    run["ended_at"] = now_iso()
    save_state(state)
    return success_envelope(result="updated", data={"run": run})
