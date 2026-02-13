"""
Abstract base class for LLM providers (B2.0).

All provider implementations must inherit from LLMProvider and
implement the required methods.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List

from .types import (
    LLMMessage,
    LLMOptions,
    LLMResponse,
    ProviderType,
    StreamChunk,
    TokenUsage,
    CostEstimate,
)


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Each provider implementation must:
    1. Set provider_type class attribute
    2. Implement complete() for non-streaming requests
    3. Implement stream() for streaming requests (optional in B2.0)
    4. Implement health_check() for connectivity verification
    """

    provider_type: ProviderType
    supports_streaming: bool = False  # Providers opt-in by setting True

    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> LLMResponse:
        """
        Send a completion request to the LLM.

        Args:
            messages: Conversation history
            options: Request options (model, temperature, etc.)

        Returns:
            LLMResponse with content, tokens, cost, latency

        Raises:
            LLMAuthenticationError: Invalid API key
            LLMRateLimitError: Rate limit exceeded
            LLMTimeoutError: Request timeout
            LLMContentFilterError: Content blocked by safety filter
            LLMModelNotFoundError: Model not available
            LLMProviderUnavailableError: Service unavailable
            LLMValidationError: Invalid request parameters
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream a completion response.

        Note: In B2.0, only MockProvider implements streaming.
        Real streaming is deferred to B2.1+.

        Args:
            messages: Conversation history
            options: Request options

        Yields:
            StreamChunk with content fragments
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, any]:
        """
        Check provider connectivity.

        Returns:
            Dict with:
            - "ok": bool - Whether provider is healthy
            - "latency_ms": int - Response time in milliseconds
            - "error": str (optional) - Error message if not ok
        """
        pass

    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """
        Get pricing for a model.

        Override in subclass to provide model-specific pricing.

        Args:
            model: Model identifier

        Returns:
            Dict with "input_per_1k" and "output_per_1k" in USD,
            or empty dict if pricing unknown.
        """
        return {}

    def estimate_cost(
        self,
        tokens: TokenUsage,
        model: str,
    ) -> CostEstimate:
        """
        Estimate cost based on token usage.

        Uses get_model_pricing() to calculate costs.
        Returns CostEstimate with unavailable reason if pricing unknown.

        Args:
            tokens: Token usage from response
            model: Model identifier

        Returns:
            CostEstimate with costs or unavailable reason
        """
        from decimal import Decimal

        if tokens.input_tokens is None or tokens.output_tokens is None:
            return CostEstimate(cost_unavailable_reason="tokens_unavailable")

        pricing = self.get_model_pricing(model)
        if not pricing:
            return CostEstimate(cost_unavailable_reason=f"pricing_unknown_for_{model}")

        input_cost = (Decimal(tokens.input_tokens) / 1000) * Decimal(
            str(pricing["input_per_1k"])
        )
        output_cost = (Decimal(tokens.output_tokens) / 1000) * Decimal(
            str(pricing["output_per_1k"])
        )
        total_cost = input_cost + output_cost

        return CostEstimate(
            input_cost_usd=input_cost.quantize(Decimal("0.00000001")),
            output_cost_usd=output_cost.quantize(Decimal("0.00000001")),
            total_cost_usd=total_cost.quantize(Decimal("0.00000001")),
        )
