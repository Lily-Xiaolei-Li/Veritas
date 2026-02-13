"""
OpenRouter LLM Provider implementation (B2.0).

Provides access to multiple LLM models via the OpenRouter API.
Uses OpenAI-compatible format.
"""

import asyncio
import hashlib
import time
from decimal import Decimal
from typing import AsyncIterator, Dict, List, Optional

import httpx

from ..base import LLMProvider
from ..exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMContentFilterError,
    LLMError,
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
)
from ..secrets import SecretStr
from ..types import (
    CostEstimate,
    LLMMessage,
    LLMOptions,
    LLMResponse,
    ProviderType,
    RequestStatus,
    StreamChunk,
    TokenUsage,
)
from app.logging_config import get_logger

logger = get_logger("llm.openrouter")


class OpenRouterProvider(LLMProvider):
    """
    OpenRouter LLM provider.

    Provides access to various models through the OpenRouter API.
    Uses OpenAI-compatible format.
    """

    provider_type = ProviderType.OPENROUTER
    BASE_URL = "https://openrouter.ai/api/v1"

    # Pricing per 1K tokens (USD) - common models only
    # Unknown models return None cost
    MODEL_PRICING: Dict[str, Dict[str, Decimal]] = {
        "anthropic/claude-3.5-sonnet": {
            "input_per_1k": Decimal("0.003"),
            "output_per_1k": Decimal("0.015"),
        },
        "anthropic/claude-3-opus": {
            "input_per_1k": Decimal("0.015"),
            "output_per_1k": Decimal("0.075"),
        },
        "openai/gpt-4o": {
            "input_per_1k": Decimal("0.005"),
            "output_per_1k": Decimal("0.015"),
        },
        "openai/gpt-4-turbo": {
            "input_per_1k": Decimal("0.01"),
            "output_per_1k": Decimal("0.03"),
        },
        "meta-llama/llama-3.1-70b-instruct": {
            "input_per_1k": Decimal("0.00035"),
            "output_per_1k": Decimal("0.0004"),
        },
        "meta-llama/llama-3.1-8b-instruct": {
            "input_per_1k": Decimal("0.00005"),
            "output_per_1k": Decimal("0.00005"),
        },
    }

    def __init__(
        self,
        api_key: SecretStr,
        http_referer: str = "http://localhost:3000",
        base_url: str | None = None,
        x_title: str | None = None,
    ):
        """
        Initialize OpenRouter provider.

        SECURITY: Never log self._client.headers - use redact_headers() if needed.

        Args:
            api_key: SecretStr wrapper (NEVER log the unwrapped value)
            http_referer: HTTP Referer header for OpenRouter API
        """
        self._client = httpx.AsyncClient(
            base_url=base_url or self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key.get_secret_value()}",
                "HTTP-Referer": http_referer,
                "X-Title": x_title or "Agent B Research",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(120.0, connect=10.0),
        )
        # NEVER store api_key or log headers

    async def complete(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> LLMResponse:
        """Execute a completion request to OpenRouter."""
        start_time = time.perf_counter()

        payload = {
            "model": options.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": options.temperature,
            "top_p": options.top_p,
        }
        if options.max_tokens is not None:
            payload["max_tokens"] = options.max_tokens
        if options.stop_sequences:
            payload["stop"] = options.stop_sequences

        try:
            response = await asyncio.wait_for(
                self._client.post("/chat/completions", json=payload),
                timeout=options.timeout_seconds,
            )
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            if response.status_code != 200:
                raise self._map_http_error(response)

            data = response.json()

            tokens = self._extract_tokens(data)
            cost = self._calculate_cost(tokens, options.model)

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=data.get("model", options.model),
                provider=self.provider_type,
                status=RequestStatus.SUCCESS,
                tokens=tokens,
                cost=cost,
                finish_reason=data["choices"][0].get("finish_reason"),
                latency_ms=latency_ms,
                total_latency_ms=latency_ms,
                provider_request_id=data.get("id"),
            )

        except asyncio.TimeoutError:
            raise LLMTimeoutError(
                f"Request timed out after {options.timeout_seconds}s",
                provider="openrouter",
            )
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"Failed to connect to OpenRouter: {e}",
                provider="openrouter",
            )
        except httpx.TimeoutException:
            raise LLMTimeoutError(
                "OpenRouter connection timed out",
                provider="openrouter",
            )
        except LLMError:
            raise  # Re-raise our own errors

    async def stream(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream is not implemented for OpenRouter in B2.0.

        Raises NotImplementedError - use MockProvider for streaming tests.
        """
        raise NotImplementedError(
            "Streaming not implemented for OpenRouter in B2.0. "
            "Use MockProvider for streaming tests."
        )
        yield  # Make this a generator

    async def health_check(self) -> Dict[str, any]:
        """Check OpenRouter connectivity."""
        start = time.perf_counter()
        try:
            # Use models endpoint as a lightweight health check
            response = await self._client.get("/models")
            latency_ms = int((time.perf_counter() - start) * 1000)

            if response.status_code == 200:
                return {"ok": True, "latency_ms": latency_ms}
            else:
                return {
                    "ok": False,
                    "error": f"HTTP {response.status_code}",
                    "latency_ms": latency_ms,
                }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "latency_ms": int((time.perf_counter() - start) * 1000),
            }

    async def close(self) -> None:
        """Close HTTP client. Call on shutdown to prevent connection leaks."""
        await self._client.aclose()

    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for an OpenRouter model."""
        pricing = self.MODEL_PRICING.get(model)
        if pricing:
            return {
                "input_per_1k": float(pricing["input_per_1k"]),
                "output_per_1k": float(pricing["output_per_1k"]),
            }
        return {}

    def _map_http_error(self, response: httpx.Response) -> LLMError:
        """
        Map HTTP status codes to exceptions.

        IMPORTANT: Correct mapping prevents incorrect fallback behavior.
        - 400/422 = validation error (no fallback - same bad request fails elsewhere)
        - 404 = model not found (fallback eligible)
        - 401/403 = auth (fallback eligible)
        - 5xx = provider unavailable (retryable + fallback eligible)
        """
        status = response.status_code

        # Log error safely - hash response body to avoid leaking user content
        # (providers sometimes echo prompts in error payloads)
        body_hash = hashlib.sha256(response.text.encode()).hexdigest()[:8]
        logger.warning(
            f"OpenRouter error: HTTP {status}",
            extra={
                "extra_fields": {
                    "status_code": status,
                    "response_body_hash": body_hash,
                    "response_length": len(response.text),
                    # NEVER: "response_body", "request_headers"
                }
            },
        )

        # Authentication errors (fallback eligible)
        if status == 401:
            return LLMAuthenticationError(
                "Invalid OpenRouter API key.",
                provider="openrouter",
            )
        if status == 403:
            return LLMAuthenticationError(
                "OpenRouter access forbidden. Check API key permissions.",
                provider="openrouter",
            )

        # Rate limiting (retryable + fallback eligible)
        if status == 429:
            retry_after = response.headers.get("Retry-After")
            return LLMRateLimitError(
                "OpenRouter rate limit exceeded.",
                provider="openrouter",
                retry_after=int(retry_after) if retry_after else None,
            )

        # Model not found (fallback eligible)
        if status == 404:
            return LLMModelNotFoundError(
                "Model not found on OpenRouter.",
                provider="openrouter",
                model="unknown",
            )

        # Validation errors (NO fallback - same bad request fails elsewhere)
        if status in (400, 422):
            return LLMValidationError(
                f"Invalid request to OpenRouter (HTTP {status}).",
                provider="openrouter",
            )

        # Server errors (retryable + fallback eligible)
        if status >= 500:
            return LLMProviderUnavailableError(
                f"OpenRouter server error: HTTP {status}",
                provider="openrouter",
            )

        # Check for content filter in response body (structured check)
        try:
            body = response.json()
            error_obj = body.get("error", {})
            error_code = error_obj.get("code", "").lower()
            if error_code in (
                "content_filter",
                "moderation",
                "content_policy_violation",
            ):
                return LLMContentFilterError(
                    "Content blocked by OpenRouter moderation.",
                    provider="openrouter",
                )
        except Exception:
            pass

        # Unknown 4xx - treat as validation (no fallback)
        if 400 <= status < 500:
            return LLMValidationError(
                f"OpenRouter client error: HTTP {status}",
                provider="openrouter",
            )

        # Fallback for truly unexpected cases
        return LLMProviderUnavailableError(
            f"OpenRouter error: HTTP {status}",
            provider="openrouter",
        )

    def _extract_tokens(self, data: dict) -> TokenUsage:
        """Extract token usage from response."""
        usage = data.get("usage", {})
        if not usage:
            return TokenUsage(usage_unavailable_reason="not_in_response")

        return TokenUsage(
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )

    def _calculate_cost(self, tokens: TokenUsage, model: str) -> CostEstimate:
        """Calculate cost using Decimal for precision."""
        if tokens.input_tokens is None or tokens.output_tokens is None:
            return CostEstimate(cost_unavailable_reason="tokens_unavailable")

        pricing = self.MODEL_PRICING.get(model)
        if not pricing:
            return CostEstimate(cost_unavailable_reason=f"pricing_unknown_for_{model}")

        input_cost = (Decimal(tokens.input_tokens) / 1000) * pricing["input_per_1k"]
        output_cost = (Decimal(tokens.output_tokens) / 1000) * pricing["output_per_1k"]
        total_cost = input_cost + output_cost

        return CostEstimate(
            input_cost_usd=input_cost.quantize(Decimal("0.00000001")),
            output_cost_usd=output_cost.quantize(Decimal("0.00000001")),
            total_cost_usd=total_cost.quantize(Decimal("0.00000001")),
        )
