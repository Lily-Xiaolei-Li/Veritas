"""LLM utility routes (Stage 12 - Real LLM dev mode).

Provides a quick 'test provider' endpoint so the UI can validate that an API key
works and the provider is reachable.

Security: requires auth when AUTH_ENABLED=true (same as other APIs).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.routes.auth_routes import require_auth
from app.llm.types import ProviderType, LLMMessage, LLMOptions
from app.services.llm_service import get_llm_service
from app.config import get_settings

router = APIRouter()


class LLMTestRequest(BaseModel):
    provider: str = Field(..., description="Provider name (gemini|openrouter|ollama|mock)")
    model: str | None = Field(default=None, description="Optional model override")


class LLMTestResponse(BaseModel):
    ok: bool
    provider: str
    model: str
    latency_ms: int | None = None
    error: str | None = None


@router.post("/llm/test", response_model=LLMTestResponse)
async def test_llm_provider(
    req: LLMTestRequest,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """Quickly test that a provider works with current credentials.

    Designed for development: short prompt, small output, short timeout.
    """

    settings = get_settings()

    try:
        provider_type = ProviderType(req.provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}")

    model = req.model or settings.llm_default_model

    service = get_llm_service()

    messages = [
        LLMMessage(role="system", content="You are a health-check bot. Reply with 'ok'."),
        LLMMessage(role="user", content="ok"),
    ]

    options = LLMOptions(
        model=model,
        temperature=0.0,
        max_tokens=8,
        timeout_seconds=10,
    )

    try:
        resp = await service.complete(
            messages=messages,
            options=options,
            db_session=db_session,
            preferred_provider=provider_type,
        )
        return LLMTestResponse(
            ok=True,
            provider=resp.provider.value,
            model=resp.model,
            latency_ms=resp.total_latency_ms,
        )
    except Exception as e:
        return LLMTestResponse(ok=False, provider=provider_type.value, model=model, error=str(e))
