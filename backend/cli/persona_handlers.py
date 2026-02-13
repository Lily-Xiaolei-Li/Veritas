from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from .contract import CLIBusinessError, success_envelope
from .state_store import (
    create_persona_api,
    load_state,
    now_iso,
    save_state,
    update_session_persona_api,
)


def _personas(state: dict) -> list[dict]:
    return state.setdefault("personas", [])


def _find_persona(state: dict, persona_id: str) -> dict | None:
    return next((p for p in _personas(state) if p.get("id") == persona_id), None)


def _find_session(state: dict, session_id: str) -> dict | None:
    return next((s for s in state.get("sessions", []) if s.get("id") == session_id), None)


def persona_create(args):
    state = load_state()
    ts = now_iso()
    persona_id = f"p_{uuid4().hex[:10]}"

    persona = {
        "id": persona_id,
        "name": args.name,
        "version": 1,
        "system_prompt": args.system_prompt,
        "created_at": ts,
        "updated_at": ts,
    }

    # Try to create via API (for GUI sync)
    api_result = create_persona_api(args.name, args.system_prompt, persona_id)
    if api_result:
        persona = api_result  # Use API response

    _personas(state).append(persona)
    save_state(state)
    return success_envelope(result="created", data={"persona": persona})


def persona_list(args):
    state = load_state()
    personas = sorted(_personas(state), key=lambda p: (p.get("created_at", ""), p.get("id", "")))
    return success_envelope(result="ok", data={"personas": personas})


def persona_show(args):
    if not args.persona:
        raise CLIBusinessError(code="PERSONA_ID_REQUIRED", message="--persona is required")

    state = load_state()
    persona = _find_persona(state, args.persona)
    if not persona:
        raise CLIBusinessError(code="PERSONA_NOT_FOUND", message="Persona not found", details={"persona": args.persona})

    return success_envelope(result="ok", data={"persona": persona})


def persona_update(args):
    if not args.persona:
        raise CLIBusinessError(code="PERSONA_ID_REQUIRED", message="--persona is required")

    state = load_state()
    persona = _find_persona(state, args.persona)
    if not persona:
        raise CLIBusinessError(code="PERSONA_NOT_FOUND", message="Persona not found", details={"persona": args.persona})

    changed = False
    if args.name:
        persona["name"] = args.name
        changed = True
    if args.system_prompt:
        persona["system_prompt"] = args.system_prompt
        changed = True

    if changed:
        persona["updated_at"] = now_iso()
        save_state(state)
        return success_envelope(result="updated", data={"persona": persona})

    return success_envelope(result="nochange", data={"persona": persona})


def persona_version(args):
    if not args.persona:
        raise CLIBusinessError(code="PERSONA_ID_REQUIRED", message="--persona is required")

    state = load_state()
    persona = _find_persona(state, args.persona)
    if not persona:
        raise CLIBusinessError(code="PERSONA_NOT_FOUND", message="Persona not found", details={"persona": args.persona})

    if args.bump:
        persona["version"] = int(persona.get("version", 1)) + 1
        persona["updated_at"] = now_iso()
        save_state(state)
        return success_envelope(result="updated", data={"persona": persona})

    return success_envelope(result="ok", data={"persona": persona})


def persona_select(args):
    if not args.persona:
        raise CLIBusinessError(code="PERSONA_ID_REQUIRED", message="--persona is required")
    if not args.session:
        raise CLIBusinessError(code="SESSION_ID_REQUIRED", message="--session is required")

    state = load_state()
    persona = _find_persona(state, args.persona)
    if not persona:
        raise CLIBusinessError(code="PERSONA_NOT_FOUND", message="Persona not found", details={"persona": args.persona})

    session = _find_session(state, args.session)
    if not session:
        raise CLIBusinessError(code="SESSION_NOT_FOUND", message="Session not found", details={"session": args.session})

    session["active_persona_id"] = persona["id"]
    session["updated_at"] = now_iso()
    
    # Sync to API (for GUI)
    update_session_persona_api(session["id"], persona["id"])
    
    save_state(state)

    return success_envelope(
        result="updated",
        data={
            "session_id": session["id"],
            "active_persona_id": persona["id"],
        },
    )


def persona_export(args):
    if not args.persona:
        raise CLIBusinessError(code="PERSONA_ID_REQUIRED", message="--persona is required")
    if not args.out:
        raise CLIBusinessError(code="PERSONA_OUT_REQUIRED", message="--out is required")

    state = load_state()
    persona = _find_persona(state, args.persona)
    if not persona:
        raise CLIBusinessError(code="PERSONA_NOT_FOUND", message="Persona not found", details={"persona": args.persona})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(persona, ensure_ascii=False, indent=2), encoding="utf-8")

    return success_envelope(result="ok", data={"persona_id": persona["id"], "out": str(out)})


def persona_import(args):
    if not args.file:
        raise CLIBusinessError(code="PERSONA_FILE_REQUIRED", message="--file is required")

    p = Path(args.file)
    if not p.exists() or not p.is_file():
        raise CLIBusinessError(code="PERSONA_FILE_NOT_FOUND", message="Persona file not found", details={"file": args.file})

    try:
        loaded = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CLIBusinessError(code="PERSONA_FILE_INVALID", message="Invalid persona file", details=str(exc))

    state = load_state()
    personas = _personas(state)

    # imported persona always gets a new id in v1 for simplicity.
    ts = now_iso()
    imported = {
        "id": f"p_{uuid4().hex[:10]}",
        "name": loaded.get("name", "Imported Persona"),
        "version": int(loaded.get("version", 1)),
        "system_prompt": loaded.get("system_prompt", ""),
        "created_at": ts,
        "updated_at": ts,
    }
    personas.append(imported)
    save_state(state)
    return success_envelope(result="created", data={"persona": imported})
