from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from config import get_settings
from models import ChatEvent, ChatRequest

# OpenClaw Gateway configuration for LLM routing.
# XiaoLei API should rely on Gateway auth (Codex login, etc.) instead of per-provider API keys.
OPENCLAW_GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789").rstrip("/")
OPENCLAW_GATEWAY_TOKEN = os.getenv("OPENCLAW_GATEWAY_TOKEN", "")
OPENCLAW_AGENT_ID = os.getenv("OPENCLAW_AGENT_ID", "main")
OPENCLAW_MODEL = os.getenv("OPENCLAW_MODEL", "openclaw")

router = APIRouter()
logger = logging.getLogger("xiaolei_api.chat")


def _model_dump(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)
    return model.dict(exclude_none=True)


def _format_sse(event: ChatEvent) -> str:
    payload = _model_dump(event)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _build_system_prompt(request: ChatRequest) -> str:
    parts: list[str] = ["You are XiaoLei, an academic research assistant."]

    if request.system_prompt:
        parts.append(request.system_prompt)

    if request.edit_target_artifact_id:
        artifact_name = request.edit_target_artifact_name or request.edit_target_artifact_id
        parts.append(
            "\n\n[EDIT MODE]\n"
            f"The user has selected '{artifact_name}' as the edit target.\n"
            "Output ONLY the updated artifact content when requested.\n"
            "Do not add explanatory text around your output."
        )

    if request.button_prompt:
        parts.append(
            "\n\n[BUTTON MODE]\n"
            f"Treat the following button prompt as a high-priority instruction: {request.button_prompt}\n"
            "Return concise and practical results."
        )

    return "\n".join(parts)


def _build_user_message(request: ChatRequest) -> str:
    message = request.message.strip()

    if request.context:
        message = f"Context:\n{request.context}\n\n---\n\n{message}"

    return message


def _should_emit_artifact(request: ChatRequest) -> bool:
    if not request.button_prompt:
        return False

    key = request.button_prompt.lower()
    if "citation" in key or "引用" in key or "find" in key and "reference" in key:
        return True

    # Backward compatible: keep old behaviour for all button actions.
    return True


async def _complete_via_openclaw(request: ChatRequest) -> str:
    """
    Route LLM calls through OpenClaw Gateway's OpenAI-compatible endpoint.

    This path does not require OPENROUTER_API_KEY / OPENAI_API_KEY.
    It relies on OpenClaw's own configured authentication and routing.
    """
    settings = get_settings()

    max_tokens = settings.xiaolei_llm_max_tokens
    if max_tokens is not None and max_tokens <= 0:
        max_tokens = None

    payload = {
        "model": OPENCLAW_MODEL,
        "messages": [
            {"role": "system", "content": _build_system_prompt(request)},
            {"role": "user", "content": _build_user_message(request)},
        ],
        "temperature": settings.xiaolei_llm_temperature,
        "stream": False,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    timeout = httpx.Timeout(timeout=settings.xiaolei_llm_timeout_s + 60)
    headers = {
        "Content-Type": "application/json",
        "x-openclaw-agent-id": OPENCLAW_AGENT_ID,
    }
    if OPENCLAW_GATEWAY_TOKEN:
        headers["Authorization"] = f"Bearer {OPENCLAW_GATEWAY_TOKEN}"
    else:
        logger.warning("OPENCLAW_GATEWAY_TOKEN is empty; assuming Gateway accepts local unauthenticated requests")

    endpoint = f"{OPENCLAW_GATEWAY_URL}/v1/chat/completions"
    logger.info("Calling OpenClaw Gateway at %s with agent=%s model=%s", endpoint, OPENCLAW_AGENT_ID, OPENCLAW_MODEL)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(endpoint, json=payload, headers=headers)

    if response.status_code >= 400:
        error_text = response.text[:500] if response.text else "No response body"
        raise RuntimeError(f"OpenClaw Gateway error: {response.status_code} {error_text}")

    body = response.json()
    if "choices" in body and body["choices"]:
        return body["choices"][0]["message"]["content"]

    raise RuntimeError(f"Unexpected OpenClaw response format: {body}")


class _EventComposer:
    async def stream_chat(self, request: ChatRequest) -> AsyncGenerator[ChatEvent, None]:
        try:
            content = await _complete_via_openclaw(request)

            if not content:
                yield ChatEvent(type="token", content="")
            else:
                for token in content.split():
                    yield ChatEvent(type="token", content=token)
                    await asyncio.sleep(0)

            if _should_emit_artifact(request):
                yield ChatEvent(
                    type="artifact",
                    content=content or "",
                    filename="xiaolei-result.md",
                )

            yield ChatEvent(type="done")

        except Exception as exc:
            logger.exception("XiaoLei chat error")
            yield ChatEvent(type="error", message=f"XiaoLei chat failed: {exc}", content=None)


def _get_clawdbot_client() -> _EventComposer:
    settings = get_settings()
    if settings.clawdbot_mode != "mock":
        logger.info("Clawdbot mode set to '%s'. Using OpenClaw Gateway client.", settings.clawdbot_mode)

    return _EventComposer()


@router.post("/chat")
async def chat(request: ChatRequest):
    client = _get_clawdbot_client()

    async def event_stream():
        async for event in client.stream_chat(request=request):
            yield _format_sse(event)

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Content-Type": "text/event-stream",
        "Connection": "keep-alive",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
