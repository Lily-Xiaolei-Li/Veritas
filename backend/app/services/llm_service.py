"""
LLM Provider Service (B2.0).

Central service for LLM provider management with:
- Lazy initialization with TTL-based credential caching
- Automatic retry and fallback
- Provider lifecycle management (shutdown hook)
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.base import LLMProvider
from app.llm.types import (
    ProviderType,
    LLMMessage,
    LLMOptions,
    LLMResponse,
    ErrorType,
)
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.openrouter import OpenRouterProvider
from app.llm.providers.ollama import OllamaProvider
from app.llm.providers.mock import MockProvider
from app.llm.exceptions import (
    LLMError,
    LLMAuthenticationError,
    LLMProviderUnavailableError,
)
from app.llm.secrets import SecretStr
from app.llm.retry import with_retry, RetryConfig
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger("llm.service")


# Provider classification for fallback policy
LOCAL_PROVIDERS = {ProviderType.OLLAMA, ProviderType.MOCK}
CLOUD_PROVIDERS = {ProviderType.GEMINI, ProviderType.OPENROUTER}


def is_local_provider(ptype: ProviderType) -> bool:
    """Check if provider runs locally (no network/cloud dependency)."""
    return ptype in LOCAL_PROVIDERS


def is_cloud_provider(ptype: ProviderType) -> bool:
    """Check if provider requires cloud/network access."""
    return ptype in CLOUD_PROVIDERS


class CachedProvider:
    """Provider instance with cache metadata."""

    def __init__(self, provider: LLMProvider, cached_at: datetime):
        self.provider = provider
        self.cached_at = cached_at


class LLMProviderService:
    """
    Central service for LLM provider management.

    Uses lazy initialization with TTL-based caching.
    Credentials are fetched fresh when cache expires.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._cache: Dict[ProviderType, CachedProvider] = {}
        self._settings = get_settings()

    async def _get_or_create_provider(
        self,
        provider_type: ProviderType,
        db_session: AsyncSession,
    ) -> LLMProvider:
        """Get provider from cache or create new with fresh credentials."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            cache_ttl = self._settings.llm_credential_cache_seconds

            # Check cache validity
            cached = self._cache.get(provider_type)
            if cached:
                age = (now - cached.cached_at).total_seconds()
                if age < cache_ttl:
                    return cached.provider
                else:
                    # Cache expired, close old provider if it has close()
                    try:
                        if hasattr(cached.provider, "close"):
                            await cached.provider.close()
                    except Exception as e:
                        logger.warning(f"Error closing expired provider: {e}")

            # Mock provider doesn't need credentials
            if provider_type == ProviderType.MOCK:
                provider = MockProvider()
                self._cache[provider_type] = CachedProvider(provider, now)
                return provider

            # Ollama: credentials optional (for future auth needs like reverse proxy)
            if provider_type == ProviderType.OLLAMA:
                from app.services.credential_manager import get_api_key_for_provider

                # Try to get optional auth token
                api_key = await get_api_key_for_provider("ollama", db_session)
                auth_token = SecretStr(api_key) if api_key else None

                provider = OllamaProvider(
                    base_url=self._settings.ollama_base_url,
                    timeout_seconds=self._settings.llm_request_timeout,
                    auth_token=auth_token,
                )
                self._cache[provider_type] = CachedProvider(provider, now)
                logger.debug(
                    f"Created and cached Ollama provider",
                    extra={"extra_fields": {"base_url": self._settings.ollama_base_url}},
                )
                return provider

            # Fetch credentials/config for cloud providers
            api_key: Optional[str] = None
            base_url: Optional[str] = None
            title: Optional[str] = None

            if provider_type == ProviderType.OPENROUTER:
                # Phase 2: provider config stored in DB (plaintext, no encryption)
                from app.models import LLMProviderConfig
                from sqlalchemy import select

                row = await db_session.execute(
                    select(LLMProviderConfig).where(LLMProviderConfig.provider == "openrouter")
                )
                cfg = row.scalar_one_or_none()
                data = cfg.config_data if cfg and isinstance(cfg.config_data, dict) else {}

                api_key = data.get("apiKey") or None
                base_url = data.get("baseUrl") or None
                title = data.get("xTitle") or data.get("title") or None

            if not api_key:
                # Fall back to legacy env/db encrypted key flow for now (until fully removed)
                from app.services.credential_manager import get_api_key_for_provider

                api_key = await get_api_key_for_provider(provider_type.value, db_session)

            if not api_key:
                raise LLMAuthenticationError(
                    f"No API key configured for {provider_type.value}. "
                    f"Add one in Settings > API Keys.",
                    provider=provider_type.value,
                )

            # Create provider with SecretStr wrapper
            secret_key = SecretStr(api_key)

            if provider_type == ProviderType.GEMINI:
                provider = GeminiProvider(secret_key)
            elif provider_type == ProviderType.OPENROUTER:
                provider = OpenRouterProvider(
                    secret_key,
                    http_referer=self._settings.openrouter_http_referer,
                    base_url=base_url,
                    x_title=title,
                )
            else:
                raise ValueError(f"Unknown provider: {provider_type}")

            # Cache provider
            self._cache[provider_type] = CachedProvider(provider, now)
            logger.debug(
                f"Created and cached provider: {provider_type.value}",
                extra={"extra_fields": {"provider": provider_type.value}},
            )
            return provider

    async def refresh_provider(self, provider_type: ProviderType) -> None:
        """
        Force refresh of a provider (e.g., after key rotation).

        Removes the provider from cache so next request fetches fresh credentials.
        """
        async with self._lock:
            if provider_type in self._cache:
                # Close if provider has close()
                try:
                    provider = self._cache[provider_type].provider
                    if hasattr(provider, "close"):
                        await provider.close()
                except Exception as e:
                    logger.warning(f"Error closing provider during refresh: {e}")

                del self._cache[provider_type]
                logger.info(
                    f"Refreshed provider: {provider_type.value}",
                    extra={"extra_fields": {"provider": provider_type.value}},
                )

    async def complete(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
        db_session: AsyncSession,
        preferred_provider: Optional[ProviderType] = None,
        strict_provider: bool = False,
    ) -> LLMResponse:
        """
        Execute completion with retry and fallback.

        Fallback eligibility is determined by exception type.
        ContentFilterError does NOT fallback by default.

        Args:
            messages: Conversation history
            options: Request options
            db_session: Database session for credential lookup
            preferred_provider: Override default provider

        Returns:
            LLMResponse with content, tokens, cost, latency

        Raises:
            LLMError: If all providers fail
        """
        settings = self._settings
        attempted_providers: List[str] = []

        # Build provider chain
        providers_to_try: List[ProviderType] = []

        if preferred_provider:
            providers_to_try.append(preferred_provider)

        # If caller explicitly requested a provider and wants strict behavior,
        # do not add defaults/fallbacks.
        if not (strict_provider and preferred_provider):
            # Add default provider if not already in list
            try:
                default = ProviderType(settings.llm_default_provider)
                if default not in providers_to_try:
                    providers_to_try.append(default)
            except ValueError:
                logger.warning(f"Unknown default provider: {settings.llm_default_provider}")

            # Add fallback providers
            for fallback in settings.llm_fallback_providers:
                try:
                    ptype = ProviderType(fallback)
                    if ptype not in providers_to_try:
                        providers_to_try.append(ptype)
                except ValueError:
                    logger.warning(f"Unknown fallback provider: {fallback}")

        last_error: Optional[LLMError] = None

        for provider_type in providers_to_try:
            attempted_providers.append(provider_type.value)

            try:
                provider = await self._get_or_create_provider(provider_type, db_session)

                # Apply retry decorator dynamically
                # Stage 12: dev fast-fail mode
                import os

                fast_fail = os.getenv("LLM_DEV_FAST_FAIL", "").lower() in {"1", "true", "yes"}
                retry_config = RetryConfig(
                    max_attempts=(1 if fast_fail else settings.llm_max_retries),
                    base_delay_seconds=(0.2 if fast_fail else settings.llm_retry_base_delay),
                )

                @with_retry(retry_config)
                async def do_complete():
                    return await provider.complete(messages, options)

                response = await do_complete()
                response.attempted_providers = attempted_providers
                return response

            except LLMError as e:
                last_error = e
                logger.warning(
                    f"Provider {provider_type.value} failed",
                    extra={
                        "extra_fields": {
                            "provider": provider_type.value,
                            "error_type": e.error_type.value,
                            "fallback_eligible": e.fallback_eligible,
                            "retryable": e.retryable,
                        }
                    },
                )

                # Check fallback eligibility
                if not e.fallback_eligible:
                    # Special case: allow content filter fallback if explicitly enabled
                    if (
                        e.error_type == ErrorType.CONTENT_FILTER
                        and settings.llm_fallback_on_content_filter
                    ):
                        logger.warning(
                            "Content filter fallback enabled - trying next provider "
                            "(DANGEROUS: bypasses safety filters)"
                        )
                        continue
                    # Not fallback eligible, re-raise
                    raise

                # Enforce local→cloud fallback policy (privacy protection)
                current_idx = providers_to_try.index(provider_type)
                if current_idx + 1 < len(providers_to_try):
                    next_provider = providers_to_try[current_idx + 1]

                    if is_local_provider(provider_type) and is_cloud_provider(next_provider):
                        if not settings.allow_cloud_fallback_from_local:
                            raise LLMProviderUnavailableError(
                                f"Local provider '{provider_type.value}' unavailable. "
                                f"Cloud fallback disabled by policy (privacy protection). "
                                f"Set ALLOW_CLOUD_FALLBACK_FROM_LOCAL=true to override.",
                                provider=provider_type.value,
                            )
                        else:
                            logger.warning(
                                f"Falling back from local ({provider_type.value}) to cloud "
                                f"({next_provider.value}) - privacy policy override enabled"
                            )

                # Fallback eligible, try next provider
                continue

        # All providers failed
        raise LLMProviderUnavailableError(
            f"All providers failed. Last error: {last_error}. "
            f"Tried: {attempted_providers}",
            provider="fallback_chain",
        )

    async def health_check_all(
        self, db_session: AsyncSession
    ) -> Dict[str, Dict[str, any]]:
        """
        Health check all configured providers.

        Returns dict of provider name to health status.
        """
        results = {}

        providers = [ProviderType.GEMINI, ProviderType.OPENROUTER, ProviderType.OLLAMA, ProviderType.MOCK]
        for ptype in providers:
            try:
                provider = await self._get_or_create_provider(ptype, db_session)
                results[ptype.value] = await provider.health_check()
            except Exception as e:
                results[ptype.value] = {"ok": False, "error": str(e)}

        return results

    async def shutdown(self) -> None:
        """
        Clean up provider resources.

        Call this in FastAPI lifespan shutdown to prevent connection leaks.
        """
        async with self._lock:
            for ptype, cached in list(self._cache.items()):
                try:
                    provider = cached.provider
                    if hasattr(provider, "close"):
                        await provider.close()
                        logger.debug(f"Closed provider: {ptype.value}")
                except Exception as e:
                    logger.warning(f"Error closing provider {ptype.value}: {e}")

            self._cache.clear()
            logger.info("LLM provider service shutdown complete")


# Global singleton
_llm_service: Optional[LLMProviderService] = None


def get_llm_service() -> LLMProviderService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMProviderService()
    return _llm_service


async def shutdown_llm_service() -> None:
    """Shutdown hook for FastAPI lifespan."""
    global _llm_service
    if _llm_service is not None:
        await _llm_service.shutdown()
        _llm_service = None
