from __future__ import annotations

import os
from uuid import uuid4

import httpx

from .contract import CLIBusinessError, render_json, success_envelope
from .state_store import load_state, now_iso, save_state

# XiaoLei Chat API configuration (matches GUI)
XIAOLEI_API_URL = os.getenv("XIAOLEI_GATEWAY_URL", "http://localhost:18789")
XIAOLEI_AUTH_TOKEN = os.getenv("XIAOLEI_AUTH_TOKEN", "")
XIAOLEI_AGENT_ID = os.getenv("XIAOLEI_AGENT_ID", "phd")


def _session_exists(state: dict, session_id: str) -> bool:
    return any(s.get("id") == session_id for s in state.get("sessions", []))


def _tokenize(text: str) -> list[str]:
    # Word-based tokenization is enough for W6 partial acceptance.
    parts = text.split()
    if not parts:
        return [text]
    return parts


def _call_xiaolei_chat(message: str, system_prompt: str | None = None) -> str:
    """
    Call XiaoLei Chat API via Gateway (connects to 博士小蕾).
    Uses OpenAI-compatible chat completions endpoint.
    """
    try:
        # Build request body (OpenAI format)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        
        body = {
            "model": "anthropic/claude-sonnet-4",  # Will be routed via Gateway
            "messages": messages,
            "stream": False,
        }
        
        # Build headers
        headers = {"Content-Type": "application/json"}
        if XIAOLEI_AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {XIAOLEI_AUTH_TOKEN}"
        if XIAOLEI_AGENT_ID:
            headers["X-Agent-Id"] = XIAOLEI_AGENT_ID
        
        # Call Gateway's chat completions endpoint
        url = f"{XIAOLEI_API_URL}/v1/chat/completions"
        
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, json=body, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            # Extract content from OpenAI format
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content if content else "[No response from model]"
            
    except httpx.TimeoutException:
        return "[Error: Request timed out. XiaoLei Gateway may be slow or unavailable.]"
    except httpx.HTTPStatusError as e:
        return f"[Error: HTTP {e.response.status_code} - {e.response.text[:200]}]"
    except Exception as e:
        return f"[Error calling XiaoLei Chat: {str(e)}]"


def chat_send(args):
    if not args.session:
        raise CLIBusinessError(
            code="CHAT_SESSION_REQUIRED",
            message="--session is required for chat send",
        )
    if not args.message:
        raise CLIBusinessError(
            code="CHAT_MESSAGE_REQUIRED",
            message="--message is required for chat send",
        )

    state = load_state()
    if not _session_exists(state, args.session):
        raise CLIBusinessError(
            code="SESSION_NOT_FOUND",
            message="Session not found",
            details={"session": args.session},
        )

    run_id = f"r_{uuid4().hex[:10]}"
    started_at = now_iso()
    
    # Get active persona's system prompt if any
    session_data = next((s for s in state.get("sessions", []) if s.get("id") == args.session), {})
    active_persona_id = session_data.get("active_persona_id")
    system_prompt = None
    if active_persona_id:
        persona = next((p for p in state.get("personas", []) if p.get("id") == active_persona_id), None)
        if persona:
            system_prompt = persona.get("system_prompt")
    
    # Call XiaoLei Chat API (connects to 博士小蕾 via Gateway)
    response_text = _call_xiaolei_chat(args.message, system_prompt)
    ended_at = now_iso()

    run = {
        "id": run_id,
        "session_id": args.session,
        "status": "completed",
        "started_at": started_at,
        "ended_at": ended_at,
        "parent_run_id": None,
        "request": args.message,
        "response": response_text,
    }
    state.setdefault("runs", []).append(run)

    state.setdefault("messages", []).append(
        {
            "session_id": args.session,
            "run_id": run_id,
            "user": args.message,
            "assistant": response_text,
            "created_at": ended_at,
        }
    )

    state.setdefault("artifacts", []).append(
        {
            "id": f"art_{uuid4().hex[:10]}",
            "session_id": args.session,
            "run_id": run_id,
            "name": f"run-{run_id}.md",
            "type": "markdown",
            "content": response_text,
            "created_at": ended_at,
            "provenance": {"type": "run"},
        }
    )
    save_state(state)

    if args.stream:
        if args.json:
            for token in _tokenize(response_text):
                print(render_json({"schema_version": "1.0", "event": "token", "run_id": run_id, "content": token}))
            print(render_json({"schema_version": "1.0", "event": "done", "run_id": run_id}))
        else:
            for token in _tokenize(response_text):
                print(token, end=" ", flush=True)
            print()
            print(f"[STREAM_DONE] run_id={run_id}")

    return success_envelope(
        result="created",
        data={
            "run_id": run_id,
            "session_id": args.session,
            "response": response_text,
        },
        meta={"stream": bool(args.stream)},
    )


def chat_history(args):
    if not args.session:
        raise CLIBusinessError(
            code="CHAT_SESSION_REQUIRED",
            message="--session is required for chat history",
        )

    state = load_state()
    if not _session_exists(state, args.session):
        raise CLIBusinessError(
            code="SESSION_NOT_FOUND",
            message="Session not found",
            details={"session": args.session},
        )

    rows = [m for m in state.get("messages", []) if m.get("session_id") == args.session]
    rows = sorted(rows, key=lambda m: (m.get("created_at", ""), m.get("run_id", "")))
    return success_envelope(result="ok", data={"session_id": args.session, "messages": rows})
