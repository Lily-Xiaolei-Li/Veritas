"""
XiaoLei Chat Proxy (Step 2 - Chat Integration).

Proxies POST /api/chat to the XiaoLei API and streams SSE responses.
"""

from __future__ import annotations

import asyncio
import json

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.logging_config import get_logger

router = APIRouter(prefix="/api", tags=["chat"])
logger = get_logger("xiaolei.chat")


class EditTargetSelection(BaseModel):
    artifactId: str
    startLine: int
    endLine: int
    text: str


class XiaoLeiChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    context: str | None = None
    button_prompt: str | None = None
    system_prompt: str | None = None  # Persona system prompt
    # Edit target (B1.7 - Edit Toggle)
    edit_target_artifact_id: str | None = None
    edit_target_artifact_name: str | None = None
    edit_target_artifact_content: str | None = None
    edit_target_selections: list[EditTargetSelection] | None = None


def _format_error(message: str) -> str:
    payload = {"type": "error", "message": message}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_headers() -> dict:
    return {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


@router.post("/chat")
async def chat(request: XiaoLeiChatRequest):
    settings = get_settings()
    # Use Gateway URL with OpenAI-compatible endpoint
    url = f"{settings.xiaolei_gateway_url}/v1/chat/completions"
    
    # DEBUG: Log edit target info
    logger.info(f"[xiaolei_chat] edit_target_artifact_id={request.edit_target_artifact_id}")
    if request.edit_target_artifact_id:
        logger.info(f"[xiaolei_chat] edit_target_artifact_name={request.edit_target_artifact_name}")
        logger.info(f"[xiaolei_chat] edit_target_selections_count={len(request.edit_target_selections or [])}")
    
    # Build messages array
    messages = []
    
    # Build system prompt with optional edit target instructions (B1.7)
    system_content_parts = []
    
    if request.system_prompt:
        system_content_parts.append(request.system_prompt)
    
    # Add edit target instructions if present
    if request.edit_target_artifact_id:
        edit_instructions = []
        edit_instructions.append("\n\n[EDIT MODE ACTIVE]")
        artifact_name = request.edit_target_artifact_name or request.edit_target_artifact_id
        edit_instructions.append(f"The user has set '{artifact_name}' as the EDIT TARGET.")
        edit_instructions.append("Your response should UPDATE this artifact, not just reply conversationally.")
        edit_instructions.append("")
        edit_instructions.append("OUTPUT FORMAT FOR EDIT MODE:")
        edit_instructions.append("Reply with ONLY a JSON object (no markdown fences, no extra text):")
        edit_instructions.append(f'{{"type":"artifact_update","artifact_id":"{request.edit_target_artifact_id}","content":"<updated full content>"}}')
        edit_instructions.append("")
        edit_instructions.append("The content should be the COMPLETE updated artifact (not just the changes).")
        
        if request.edit_target_selections:
            edit_instructions.append("")
            edit_instructions.append("SPECIFIC SECTIONS TO EDIT:")
            for sel in request.edit_target_selections[:5]:
                edit_instructions.append(f"  - Lines {sel.startLine}-{sel.endLine}: {sel.text[:100]}...")
            edit_instructions.append("Focus your changes on these sections while keeping the rest of the document intact.")
        
        if request.edit_target_artifact_content:
            edit_instructions.append("")
            edit_instructions.append(f"[CURRENT CONTENT OF '{artifact_name}']")
            edit_instructions.append("---")
            edit_instructions.append(request.edit_target_artifact_content[:15000])
            edit_instructions.append("---")
        
        system_content_parts.append("\n".join(edit_instructions))
    
    if system_content_parts:
        messages.append({"role": "system", "content": "\n".join(system_content_parts)})
    
    # Build user message with optional context
    user_content = request.message
    if request.context:
        user_content = f"Context:\n{request.context}\n\n---\n\nUser message:\n{request.message}"
    
    messages.append({"role": "user", "content": user_content})
    
    # OpenAI-compatible payload
    payload = {
        "model": "anthropic/claude-sonnet-4-20250514",  # Gateway will route appropriately
        "messages": messages,
        "stream": True
    }
    
    # Build headers with Authorization and Agent ID
    headers = {"Content-Type": "application/json"}
    if settings.xiaolei_auth_token:
        headers["Authorization"] = f"Bearer {settings.xiaolei_auth_token}"
        logger.debug("Using XiaoLei auth token for Gateway request")
    else:
        logger.warning("No XIAOLEI_AUTH_TOKEN configured - request may fail")
    
    # Add Agent ID for routing to specific agent (e.g., 博士小蕾)
    # OpenClaw uses x-openclaw-agent-id header for agent routing
    if settings.xiaolei_agent_id:
        headers["x-openclaw-agent-id"] = settings.xiaolei_agent_id
        logger.debug(f"Routing to agent: {settings.xiaolei_agent_id}")

    async def event_stream():
        timeout = httpx.Timeout(
            connect=settings.xiaolei_request_timeout,
            read=None,
            write=settings.xiaolei_request_timeout,
            pool=settings.xiaolei_request_timeout,
        )

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        detail = body.decode(errors="ignore").strip()
                        message = detail or f"XiaoLei API error (HTTP {response.status_code})"
                        logger.error(
                            "XiaoLei API error",
                            extra={"extra_fields": {"status_code": response.status_code, "detail": detail}},
                        )
                        yield _format_error(message)
                        return

                    async for chunk in response.aiter_raw():
                        if chunk:
                            yield chunk

        except httpx.RequestError as exc:
            logger.error("XiaoLei API request failed: %s", exc)
            yield _format_error("XiaoLei API unreachable")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("XiaoLei API stream error: %s", exc, exc_info=True)
            yield _format_error("XiaoLei API stream error")

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=_sse_headers())
