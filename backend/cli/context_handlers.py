from __future__ import annotations

from .contract import CLIBusinessError, success_envelope
from .state_store import load_state, now_iso, save_state


def _ensure_contexts(state: dict) -> dict:
    return state.setdefault("contexts", {"global": None, "sessions": {}, "runs": {}})


def context_set(args):
    state = load_state()
    contexts = _ensure_contexts(state)
    ts = now_iso()

    scope = args.scope
    entry = {"content": args.content, "updated_at": ts}

    if scope == "global":
        contexts["global"] = entry
    elif scope == "session":
        if not args.session:
            raise CLIBusinessError(code="CONTEXT_SESSION_REQUIRED", message="--session is required for session scope")
        contexts["sessions"][args.session] = entry
    elif scope == "run":
        if not args.run:
            raise CLIBusinessError(code="CONTEXT_RUN_REQUIRED", message="--run is required for run scope")
        contexts["runs"][args.run] = entry
    else:
        raise CLIBusinessError(code="CONTEXT_SCOPE_INVALID", message="Invalid context scope", details={"scope": scope})

    save_state(state)
    return success_envelope(result="updated", data={"scope": scope, "entry": entry})


def context_get(args):
    state = load_state()
    contexts = _ensure_contexts(state)
    scope = args.scope

    if scope == "global":
        entry = contexts.get("global")
    elif scope == "session":
        if not args.session:
            raise CLIBusinessError(code="CONTEXT_SESSION_REQUIRED", message="--session is required for session scope")
        entry = contexts["sessions"].get(args.session)
    elif scope == "run":
        if not args.run:
            raise CLIBusinessError(code="CONTEXT_RUN_REQUIRED", message="--run is required for run scope")
        entry = contexts["runs"].get(args.run)
    else:
        raise CLIBusinessError(code="CONTEXT_SCOPE_INVALID", message="Invalid context scope", details={"scope": scope})

    if entry is None:
        raise CLIBusinessError(code="CONTEXT_NOT_FOUND", message="Context not found", details={"scope": scope})

    return success_envelope(result="ok", data={"scope": scope, "entry": entry})


def context_clear(args):
    state = load_state()
    contexts = _ensure_contexts(state)
    scope = args.scope

    if scope == "global":
        contexts["global"] = None
    elif scope == "session":
        if not args.session:
            raise CLIBusinessError(code="CONTEXT_SESSION_REQUIRED", message="--session is required for session scope")
        contexts["sessions"].pop(args.session, None)
    elif scope == "run":
        if not args.run:
            raise CLIBusinessError(code="CONTEXT_RUN_REQUIRED", message="--run is required for run scope")
        contexts["runs"].pop(args.run, None)
    else:
        raise CLIBusinessError(code="CONTEXT_SCOPE_INVALID", message="Invalid context scope", details={"scope": scope})

    save_state(state)
    return success_envelope(result="deleted", data={"scope": scope})


def context_resolve(args):
    state = load_state()
    contexts = _ensure_contexts(state)

    global_ctx = contexts.get("global")
    session_ctx = contexts["sessions"].get(args.session) if args.session else None
    run_ctx = contexts["runs"].get(args.run) if args.run else None

    effective = run_ctx or session_ctx or global_ctx
    precedence = [
        {"scope": "run", "present": run_ctx is not None},
        {"scope": "session", "present": session_ctx is not None},
        {"scope": "global", "present": global_ctx is not None},
    ]

    return success_envelope(
        result="ok",
        data={
            "effective": effective,
            "effective_scope": "run" if run_ctx else ("session" if session_ctx else ("global" if global_ctx else None)),
            "precedence": precedence,
        },
    )
