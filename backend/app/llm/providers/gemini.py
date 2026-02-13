"""
Gemini LLM Provider implementation (B2.0).

Supports Gemini Flash and Pro models via the google-genai SDK.
Updated January 2026 to use new SDK (google-genai replaces google-generativeai).
"""

import asyncio
import hashlib
import time
from decimal import Decimal
from typing import AsyncIterator, Dict, List, Optional

from app.logging_config import get_logger

from ..base import LLMProvider
from ..exceptions import (
    LLMAuthenticationError,
    LLMContentFilterError,
    LLMError,
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from ..secrets import SecretStr
from ..types import (
    CostEstimate,
    ErrorType,
    LLMMessage,
    LLMOptions,
    LLMResponse,
    ProviderType,
    RequestStatus,
    StreamChunk,
    TokenUsage,
)

logger = get_logger("llm.gemini")


class GeminiProvider(LLMProvider):
    """
    Google Gemini LLM provider.

    Supports Gemini 2.0 and newer models via google-genai SDK.
    """

    provider_type = ProviderType.GEMINI

    # Pricing per 1K tokens (USD) - updated for current models
    # See: https://ai.google.dev/pricing
    MODEL_PRICING: Dict[str, Dict[str, Decimal]] = {
        "gemini-2.0-flash": {
            "input_per_1k": Decimal("0.0001"),
            "output_per_1k": Decimal("0.0004"),
        },
        "gemini-2.0-flash-lite": {
            "input_per_1k": Decimal("0.000075"),
            "output_per_1k": Decimal("0.0003"),
        },
        "gemini-2.5-flash": {
            "input_per_1k": Decimal("0.00015"),
            "output_per_1k": Decimal("0.0006"),
        },
        "gemini-2.5-pro": {
            "input_per_1k": Decimal("0.00125"),
            "output_per_1k": Decimal("0.005"),
        },
    }

    def __init__(self, api_key: SecretStr):
        """
        Initialize Gemini provider.

        Args:
            api_key: SecretStr wrapper (NEVER log the unwrapped value)
        """
        try:
            from google import genai

            # Create client with unwrapped key - never store or log the raw value
            self._client = genai.Client(api_key=api_key.get_secret_value())
        except ImportError:
            raise LLMProviderUnavailableError(
                "google-genai package not installed. "
                "Run: pip install google-genai",
                provider="gemini",
            )
        # NEVER store api_key as instance variable

    async def complete(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> LLMResponse:
        """Execute a completion request to Gemini."""
        start_time = time.perf_counter()

        try:
            # Convert messages to Gemini format
            contents = self._convert_messages(messages)

            # Build generation config
            config = {
                "temperature": options.temperature,
                "top_p": options.top_p,
            }
            if options.max_tokens is not None:
                config["max_output_tokens"] = options.max_tokens
            if options.stop_sequences:
                config["stop_sequences"] = options.stop_sequences

            # Run synchronous SDK call in thread pool to not block event loop
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self._client.models.generate_content(
                        model=options.model,
                        contents=contents,
                        config=config,
                    ),
                ),
                timeout=options.timeout_seconds,
            )

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Check for content filter using structured fields
            if self._check_content_filter(response):
                raise LLMContentFilterError(
                    "Content blocked by Gemini safety filters.",
                    provider="gemini",
                )

            # Extract tokens (may be None for some responses)
            tokens = self._extract_tokens(response)
            cost = self._calculate_cost(tokens, options.model)

            return LLMResponse(
                content=response.text,
                model=options.model,
                provider=self.provider_type,
                status=RequestStatus.SUCCESS,
                tokens=tokens,
                cost=cost,
                finish_reason=self._map_finish_reason(response),
                latency_ms=latency_ms,
                total_latency_ms=latency_ms,  # Updated by retry wrapper if retried
                provider_request_id=None,  # Gemini doesn't expose this
            )

        except asyncio.TimeoutError:
            raise LLMTimeoutError(
                f"Request timed out after {options.timeout_seconds}s",
                provider="gemini",
            )
        except LLMError:
            raise  # Re-raise our own errors
        except Exception as e:
            raise self._map_exception(e)

    async def stream(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream is not implemented for Gemini in B2.0.

        Raises NotImplementedError - use MockProvider for streaming tests.
        """
        raise NotImplementedError(
            "Streaming not implemented for Gemini in B2.0. "
            "Use MockProvider for streaming tests."
        )
        yield  # Make this a generator

    async def health_check(self) -> Dict[str, any]:
        """Check Gemini connectivity with a minimal request."""
        start = time.perf_counter()
        try:
            # Run synchronous SDK call in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents="Say 'ok'",
                    config={"max_output_tokens": 5},
                ),
            )
            return {
                "ok": True,
                "provider": "gemini",
                "latency_ms": int((time.perf_counter() - start) * 1000),
            }
        except Exception as e:
            return {
                "ok": False,
                "provider": "gemini",
                "error": str(e),
                "latency_ms": int((time.perf_counter() - start) * 1000),
            }

    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a Gemini model."""
        pricing = self.MODEL_PRICING.get(model)
        if pricing:
            return {
                "input_per_1k": float(pricing["input_per_1k"]),
                "output_per_1k": float(pricing["output_per_1k"]),
            }
        return {}

    def _convert_messages(self, messages: List[LLMMessage]) -> str:
        """
        Convert LLMMessage list to Gemini content format.

        For simple single-turn, we just concatenate messages.
        For multi-turn, the new SDK handles conversation differently.
        """
        parts = []
        for msg in messages:
            if msg.role == "system":
                parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                parts.append(msg.content)
            elif msg.role == "assistant":
                parts.append(f"Assistant: {msg.content}")

        return "\n\n".join(parts)

    def _map_exception(self, e: Exception) -> LLMError:
        """
        Map Gemini exceptions to our hierarchy.

        CRITICAL: Map by actual exception type/status, not string matching.
        """
        error_str = str(e).lower()

        # Check for common error patterns in the new SDK
        if "invalid api key" in error_str or "api key not valid" in error_str:
            return LLMAuthenticationError(
                "Invalid API key for Gemini. Verify the key in Settings.",
                provider="gemini",
            )

        if "permission denied" in error_str:
            return LLMAuthenticationError(
                "Permission denied. API key may lack required permissions.",
                provider="gemini",
            )

        if "rate limit" in error_str or "quota" in error_str or "resource exhausted" in error_str:
            return LLMRateLimitError(
                "Gemini rate limit exceeded. Retry with backoff.",
                provider="gemini",
                retry_after=60,
            )

        if "not found" in error_str:
            return LLMModelNotFoundError(
                f"Model not found: {e}",
                provider="gemini",
                model="unknown",
            )

        if "timeout" in error_str or "deadline" in error_str:
            return LLMTimeoutError(
                "Gemini request timed out.",
                provider="gemini",
            )

        if "unavailable" in error_str:
            return LLMProviderUnavailableError(
                "Gemini service temporarily unavailable.",
                provider="gemini",
            )

        # Unknown - wrap with reference hash for debugging
        error_hash = hashlib.sha256(str(e).encode()).hexdigest()[:8]
        logger.warning(f"Unknown Gemini error: {e}", extra={"extra_fields": {"error_hash": error_hash}})
        return LLMError(
            f"Unexpected Gemini error (ref: {error_hash}): {e}",
            provider="gemini",
            error_type=ErrorType.UNKNOWN,
            retryable=False,
            fallback_eligible=True,
        )

    def _check_content_filter(self, response) -> bool:
        """
        Check if response was blocked by content filter.

        Uses structured finish_reason and safety_ratings.
        """
        try:
            # Check candidate finish reason
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "finish_reason"):
                    reason = str(candidate.finish_reason).upper()
                    if "SAFETY" in reason:
                        return True

            # Check prompt feedback
            if hasattr(response, "prompt_feedback"):
                feedback = response.prompt_feedback
                if hasattr(feedback, "block_reason") and feedback.block_reason:
                    return True

            return False
        except Exception:
            return False

    def _extract_tokens(self, response) -> TokenUsage:
        """Extract token usage, returning None fields if unavailable."""
        try:
            usage = response.usage_metadata
            if usage:
                return TokenUsage(
                    input_tokens=getattr(usage, 'prompt_token_count', None),
                    output_tokens=getattr(usage, 'candidates_token_count', None),
                    total_tokens=getattr(usage, 'total_token_count', None),
                )
        except AttributeError:
            pass

        return TokenUsage(usage_unavailable_reason="provider_metadata_missing")

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

        # Quantize to avoid floating point drift
        return CostEstimate(
            input_cost_usd=input_cost.quantize(Decimal("0.00000001")),
            output_cost_usd=output_cost.quantize(Decimal("0.00000001")),
            total_cost_usd=total_cost.quantize(Decimal("0.00000001")),
        )

    def _map_finish_reason(self, response) -> Optional[str]:
        """Map Gemini finish reason to standard format."""
        try:
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "finish_reason"):
                    reason = str(candidate.finish_reason).upper()
                    # Map to standard names
                    if "STOP" in reason:
                        return "stop"
                    if "MAX" in reason or "LENGTH" in reason:
                        return "length"
                    if "SAFETY" in reason:
                        return "content_filter"
                    return reason.lower()
        except Exception:
            pass
        return None
