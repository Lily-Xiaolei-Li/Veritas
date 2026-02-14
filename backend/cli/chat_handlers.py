from __future__ import annotations

import os
from uuid import uuid4

import httpx

from .contract import CLIBusinessError, render_json, success_envelope
from .state_store import load_state, now_iso, save_state, get_chat_history_api

# XiaoLei Chat API configuration (matches GUI)
# Read from environment first, then fall back to backend .env file
def _load_env_config():
    """Load config from backend .env file (same source as GUI backend)."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env_vars[key.strip()] = val.strip()
    return env_vars

_env = _load_env_config()
XIAOLEI_API_URL = os.getenv("XIAOLEI_GATEWAY_URL") or _env.get("XIAOLEI_GATEWAY_URL", "http://localhost:18789")
XIAOLEI_AUTH_TOKEN = os.getenv("XIAOLEI_AUTH_TOKEN") or _env.get("XIAOLEI_AUTH_TOKEN", "")
XIAOLEI_AGENT_ID = os.getenv("XIAOLEI_AGENT_ID") or _env.get("XIAOLEI_AGENT_ID", "phd")


def _session_exists(state: dict, session_id: str) -> bool:
    return any(s.get("id") == session_id for s in state.get("sessions", []))


def _tokenize(text: str) -> list[str]:
    # Word-based tokenization is enough for W6 partial acceptance.
    parts = text.split()
    if not parts:
        return [text]
    return parts


BACKEND_API_URL = os.getenv("AGENTB_API_URL") or _env.get("AGENTB_API_URL", "http://localhost:8001")
RAG_DEFAULT_TOP_K = 5


def _search_rag(query: str, sources: list[str], top_k: int = RAG_DEFAULT_TOP_K) -> str | None:
    """Search RAG knowledge sources and return formatted context (mimics GUI behavior)."""
    context_parts = []
    source_descriptions = {
        "library": "academic papers library (~1000 articles)",
        "interviews": "interview transcripts and empirical data",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            for src in sources:
                try:
                    url = f"{BACKEND_API_URL}/api/v1/knowledge/sources/{src}/search"
                    r = client.post(url, json={"query": query, "top_k": top_k})
                    if r.status_code == 200:
                        data = r.json()
                        results = data.get("results", [])
                        if results:
                            desc = source_descriptions.get(src, src)
                            header = f"[RAG SEARCH RESULTS from {desc}]\nThe following excerpts were retrieved via semantic search for relevance to the user's query:\n"
                            items = []
                            for i, result in enumerate(results):
                                source_ref = f" — Source: {result['source']}" if result.get("source") else ""
                                items.append(f"[{i+1}{source_ref}]\n{result.get('text', '')}")
                            context_parts.append(header + "\n\n".join(items))
                except Exception:
                    continue
    except Exception:
        pass
    return "\n\n---\n\n".join(context_parts) if context_parts else None


def _fetch_artifact_content(artifact_id: str) -> str | None:
    """Fetch artifact content from backend API."""
    try:
        url = f"{BACKEND_API_URL}/api/v1/artifacts/{artifact_id}/preview"
        with httpx.Client(timeout=30.0) as client:
            r = client.get(url)
            if r.status_code == 200:
                data = r.json()
                return data.get("text") or data.get("content") or ""
    except Exception:
        pass
    return None


def _fetch_persona(persona_id: str) -> dict | None:
    """Fetch persona from backend API."""
    try:
        url = f"{BACKEND_API_URL}/api/v1/personas"
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url)
            if r.status_code == 200:
                personas = r.json() if isinstance(r.json(), list) else r.json().get("personas", [])
                for p in personas:
                    if p.get("id") == persona_id:
                        return p
    except Exception:
        pass
    return None


def _call_xiaolei_chat(message: str, system_prompt: str | None = None,
                       context: str | None = None) -> str:
    """
    Call XiaoLei Chat API via backend proxy /api/chat (same path as GUI).
    Backend handles Gateway auth, agent routing, and SSE streaming.
    """
    try:
        body: dict = {"message": message}
        if system_prompt:
            body["system_prompt"] = system_prompt
        if context:
            body["context"] = context

        url = f"{BACKEND_API_URL}/api/chat"

        with httpx.Client(timeout=180.0) as client:
            # Use streaming to match GUI behavior
            with client.stream("POST", url, json=body,
                               headers={"Content-Type": "application/json"}) as response:
                if response.status_code >= 400:
                    body_text = response.read().decode(errors="ignore")
                    return f"[Error: HTTP {response.status_code} - {body_text[:200]}]"

                # Parse SSE stream
                full_content = []
                for line in response.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_text = line[5:].strip()
                    if data_text == "[DONE]":
                        break
                    try:
                        parsed = __import__("json").loads(data_text)
                        # Custom format
                        if parsed.get("type") == "token":
                            full_content.append(parsed.get("content", ""))
                        elif parsed.get("type") == "error":
                            return f"[Error: {parsed.get('message', 'Unknown')}]"
                        elif parsed.get("type") == "done":
                            break
                        # OpenAI format
                        elif "choices" in parsed:
                            delta = parsed["choices"][0].get("delta", {})
                            if delta.get("content"):
                                full_content.append(delta["content"])
                            if parsed["choices"][0].get("finish_reason") == "stop":
                                break
                    except Exception:
                        continue

                result = "".join(full_content)
                return result if result else "[No response from model]"

    except httpx.TimeoutException:
        return "[Error: Request timed out (180s). The model may be processing a large context.]"
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

    # Get persona system prompt (from --persona arg or active session persona)
    system_prompt = None
    persona_id = getattr(args, "persona", None)
    if not persona_id:
        session_data = next((s for s in state.get("sessions", []) if s.get("id") == args.session), {})
        persona_id = session_data.get("active_persona_id")
    if persona_id:
        persona = _fetch_persona(persona_id)
        if persona:
            system_prompt = persona.get("system_prompt")

    # Build context from --artifacts (fetch content like GUI does)
    context = None
    artifact_ids = getattr(args, "artifacts", None)
    if artifact_ids:
        context_parts = []
        for aid in artifact_ids.split(","):
            aid = aid.strip()
            if not aid:
                continue
            content = _fetch_artifact_content(aid)
            if content:
                context_parts.append(f"[Artifact: {aid}]\n{content}")
        if context_parts:
            context = "\n\n".join(context_parts)

    # RAG search (--rag library,interviews or --rag library)
    rag_sources = getattr(args, "rag", None)
    if rag_sources:
        src_list = [s.strip() for s in rag_sources.split(",") if s.strip()]
        rag_top_k = getattr(args, "rag_top_k", RAG_DEFAULT_TOP_K) or RAG_DEFAULT_TOP_K
        rag_context = _search_rag(args.message, src_list, top_k=rag_top_k)
        if rag_context:
            if context:
                context = context + "\n\n---\n\n" + rag_context
            else:
                context = rag_context

    # Call XiaoLei Chat API via backend proxy (same path as GUI)
    response_text = _call_xiaolei_chat(args.message, system_prompt, context)
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

    # Try API first (shared with GUI), fall back to local state
    api_messages = get_chat_history_api(args.session)
    if api_messages is not None:
        rows = api_messages
    else:
        rows = [m for m in state.get("messages", []) if m.get("session_id") == args.session]
    rows = sorted(rows, key=lambda m: (m.get("created_at", ""), m.get("run_id", "")))
    return success_envelope(result="ok", data={"session_id": args.session, "messages": rows})
