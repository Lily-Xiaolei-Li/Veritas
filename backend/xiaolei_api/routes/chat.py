from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from config import get_settings
from models import ChatRequest, ChatEvent

router = APIRouter()
logger = logging.getLogger("xiaolei_api.chat")


def _model_dump(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=True)
    return model.dict(exclude_none=True)


def _format_sse(event: ChatEvent) -> str:
    payload = _model_dump(event)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class MockClawdbotClient:
    async def stream_chat(
        self,
        message: str,
        context: str | None,
        button_prompt: str | None,
    ) -> AsyncGenerator[ChatEvent, None]:
        parts = []
        if button_prompt:
            parts.append("Button prompt applied.")
        parts.append(f"Echo: {message}")
        if context:
            parts.append(f"Context: {context}")
        response_text = " ".join(parts)

        for token in response_text.split():
            yield ChatEvent(type="token", content=token)
            await asyncio.sleep(0)

        if button_prompt:
            artifact_text = (
                "This is a mocked artifact generated from the button prompt.\n"
                f"Prompt: {button_prompt}\n"
                f"Message: {message}\n"
            )
            yield ChatEvent(
                type="artifact",
                content=artifact_text,
                filename="button_result.md",
            )

        yield ChatEvent(type="done")


def _get_clawdbot_client() -> MockClawdbotClient:
    settings = get_settings()
    if settings.clawdbot_mode != "mock":
        logger.warning(
            "Clawdbot mode set to '%s' but only mock is implemented. Using mock.",
            settings.clawdbot_mode,
        )
    return MockClawdbotClient()


@router.post("/chat")
async def chat(request: ChatRequest):
    client = _get_clawdbot_client()

    async def event_stream():
        async for event in client.stream_chat(
            message=request.message,
            context=request.context,
            button_prompt=request.button_prompt,
        ):
            yield _format_sse(event)

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
