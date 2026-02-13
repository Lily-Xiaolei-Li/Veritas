from __future__ import annotations

from uuid import uuid4

from .contract import CLIBusinessError, success_envelope
from .state_store import create_session_api, load_state, now_iso, save_state


def _find_session(state: dict, session_id: str):
    for s in state.get("sessions", []):
        if s.get("id") == session_id:
            return s
    return None


def session_create(args):
    state = load_state()
    sessions = state.setdefault("sessions", [])
    idem = state.setdefault("idempotency", {})

    key = args.idempotency_key
    if args.dedupe_name and not key:
        key = f"session:create:name:{args.name}"

    if key and key in idem:
        existing_id = idem[key]
        existing = _find_session(state, existing_id)
        if existing:
            state["current_session_id"] = existing["id"]
            save_state(state)
            return success_envelope(result="nochange", data={"session": existing}, meta={"idempotency_key": key})

    ts = now_iso()
    session_id = f"s_{uuid4().hex[:10]}"
    session = {
        "id": session_id,
        "name": args.name,
        "status": "active",
        "created_at": ts,
        "updated_at": ts,
        "active_persona_id": None,
    }
    
    # Try to create via API (for GUI sync)
    api_result = create_session_api(args.name, session_id)
    if api_result:
        session = api_result  # Use API response
    
    sessions.append(session)

    if key:
        idem[key] = session["id"]

    state["current_session_id"] = session["id"]
    save_state(state)
    return success_envelope(result="created", data={"session": session}, meta={"idempotency_key": key})


def session_show(args):
    state = load_state()
    session = _find_session(state, args.session)
    if not session:
        raise CLIBusinessError(
            code="SESSION_NOT_FOUND",
            message="Session not found",
            details={"session": args.session},
        )
    return success_envelope(result="ok", data={"session": session})


def session_list(args):
    state = load_state()
    sessions = sorted(state.get("sessions", []), key=lambda s: (s.get("created_at", ""), s.get("id", "")))
    return success_envelope(result="ok", data={"sessions": sessions, "current_session_id": state.get("current_session_id")})


def session_use(args):
    if not args.session:
        raise CLIBusinessError(code="SESSION_ID_REQUIRED", message="--session is required")

    state = load_state()
    session = _find_session(state, args.session)
    if not session:
        raise CLIBusinessError(code="SESSION_NOT_FOUND", message="Session not found", details={"session": args.session})

    state["current_session_id"] = session["id"]
    save_state(state)
    return success_envelope(result="updated", data={"current_session_id": session["id"]})


def session_current(args):
    state = load_state()
    current_id = state.get("current_session_id")
    if not current_id:
        raise CLIBusinessError(code="SESSION_CURRENT_NOT_SET", message="Current session is not set")

    session = _find_session(state, current_id)
    if not session:
        raise CLIBusinessError(code="SESSION_NOT_FOUND", message="Session not found", details={"session": current_id})

    return success_envelope(result="ok", data={"session": session, "current_session_id": current_id})
