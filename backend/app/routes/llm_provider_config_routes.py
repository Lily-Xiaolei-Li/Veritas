"""LLM provider config routes (Phase 2).

Goal: Replace the overkill encrypted API key flow with a simple provider-config
store in the backend DB.

Security model:
- Still requires auth when AUTH_ENABLED=true (same as other settings endpoints)
- When auth is disabled, this is effectively local-machine security.

NOTE: This stores API keys in plaintext in the DB (per user request).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import LLMProviderConfig
from app.routes.auth_routes import require_auth

router = APIRouter()


class ProviderConfigResponse(BaseModel):
    provider: str
    config: Dict[str, Any]


class ProviderConfigUpdateRequest(BaseModel):
    # Full config payload. If apiKey omitted, we keep existing apiKey.
    config: Dict[str, Any] = Field(default_factory=dict)
    # Optional apiKey convenience field (UI can send apiKey separately).
    apiKey: Optional[str] = Field(default=None, description="Optional provider API key")


@router.get("/llm/providers/{provider}/config", response_model=ProviderConfigResponse)
async def get_provider_config(
    provider: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    row = await db_session.execute(
        select(LLMProviderConfig).where(LLMProviderConfig.provider == provider)
    )
    cfg = row.scalar_one_or_none()

    if not cfg:
        # Return an empty skeleton so the UI can render.
        return ProviderConfigResponse(provider=provider, config={"provider": provider})

    return ProviderConfigResponse(provider=provider, config=cfg.config_data or {"provider": provider})


@router.put("/llm/providers/{provider}/config", response_model=ProviderConfigResponse)
async def upsert_provider_config(
    provider: str,
    body: ProviderConfigUpdateRequest,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    row = await db_session.execute(
        select(LLMProviderConfig).where(LLMProviderConfig.provider == provider)
    )
    cfg = row.scalar_one_or_none()

    next_cfg: Dict[str, Any] = dict(body.config or {})
    # Normalize provider field
    next_cfg.setdefault("provider", provider)

    # If apiKey is provided explicitly, set it. Otherwise preserve existing.
    if body.apiKey is not None:
        next_cfg["apiKey"] = body.apiKey
    elif cfg and isinstance(cfg.config_data, dict) and "apiKey" in cfg.config_data and "apiKey" not in next_cfg:
        next_cfg["apiKey"] = cfg.config_data.get("apiKey")

    if cfg:
        cfg.config_data = next_cfg
    else:
        cfg = LLMProviderConfig(provider=provider, config_data=next_cfg)
        db_session.add(cfg)

    await db_session.commit()
    await db_session.refresh(cfg)

    return ProviderConfigResponse(provider=provider, config=cfg.config_data or {"provider": provider})
