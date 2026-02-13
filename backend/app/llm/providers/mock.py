"""
Mock LLM Provider for testing (B2.0).

This is the only provider with streaming implemented in B2.0.
Use for development and testing without real API calls.
"""

import asyncio
from typing import AsyncIterator, Dict, List

from ..base import LLMProvider
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


class MockProvider(LLMProvider):
    """
    Mock LLM provider for development and testing.

    Features:
    - No API calls required
    - Simulates realistic latency
    - Only provider with streaming in B2.0
    - Free (cost = 0)
    """

    provider_type = ProviderType.MOCK

    def __init__(self, latency_ms: int = 100):
        """
        Initialize mock provider.

        Args:
            latency_ms: Simulated latency in milliseconds (default: 100)
        """
        self._latency_ms = latency_ms

    async def complete(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> LLMResponse:
        """Execute a mock completion request."""
        await asyncio.sleep(self._latency_ms / 1000)

        last_content = messages[-1].content if messages else ""

        # Generate mock response
        response_content = f"[MOCK] Echo: {last_content[:100]}"

        # Estimate tokens (rough approximation)
        input_tokens = sum(len(m.content.split()) for m in messages)
        output_tokens = len(response_content.split())

        return LLMResponse(
            content=response_content,
            model="mock-v1",
            provider=self.provider_type,
            status=RequestStatus.SUCCESS,
            tokens=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
            cost=CostEstimate(),  # Free - no cost fields set
            finish_reason="stop",
            latency_ms=self._latency_ms,
            total_latency_ms=self._latency_ms,
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream a mock completion response.

        This is the only provider with streaming implemented in B2.0.
        """
        last_content = messages[-1].content if messages else ""
        content = f"[MOCK] Streaming echo: {last_content[:50]}"

        words = content.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.05)  # 50ms between tokens

            is_last = i == len(words) - 1
            yield StreamChunk(
                content=word + " ",
                finish_reason="stop" if is_last else None,
            )

    async def health_check(self) -> Dict[str, any]:
        """Mock health check - always healthy."""
        return {"ok": True, "latency_ms": 0}

    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """Mock pricing - always free."""
        return {"input_per_1k": 0.0, "output_per_1k": 0.0}
