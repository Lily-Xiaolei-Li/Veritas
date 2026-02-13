"""
Tests for LLM cost tracking (B2.0).
"""

from decimal import Decimal
import pytest

from app.services.cost_tracker import to_cents


class TestToCents:
    """Test USD to cents conversion."""

    def test_simple_conversion(self):
        """Test basic dollar to cents conversion."""
        assert to_cents(Decimal("1.00")) == 100
        assert to_cents(Decimal("0.50")) == 50
        assert to_cents(Decimal("10.00")) == 1000

    def test_fractional_cents(self):
        """Test values with fractional cents are rounded correctly."""
        # ROUND_HALF_UP: 0.5 and above rounds up
        assert to_cents(Decimal("0.015")) == 2  # 1.5 cents -> 2
        assert to_cents(Decimal("0.014")) == 1  # 1.4 cents -> 1
        assert to_cents(Decimal("0.005")) == 1  # 0.5 cents -> 1
        assert to_cents(Decimal("0.004")) == 0  # 0.4 cents -> 0

    def test_small_values(self):
        """Test very small values (common in LLM pricing)."""
        # $0.00001875 per 1k tokens (Gemini Flash input)
        # For 1000 tokens: $0.00001875 = 0.001875 cents
        assert to_cents(Decimal("0.00001875")) == 0  # Less than 0.5 cent

        # For 100,000 tokens: $0.001875 = 0.1875 cents
        assert to_cents(Decimal("0.001875")) == 0

        # For 1,000,000 tokens: $0.01875 = 1.875 cents -> 2
        assert to_cents(Decimal("0.01875")) == 2

    def test_none_input(self):
        """Test None input returns None."""
        assert to_cents(None) is None

    def test_zero(self):
        """Test zero value."""
        assert to_cents(Decimal("0")) == 0
        assert to_cents(Decimal("0.00")) == 0

    def test_large_values(self):
        """Test larger dollar amounts."""
        assert to_cents(Decimal("100.00")) == 10000
        assert to_cents(Decimal("999.99")) == 99999
        assert to_cents(Decimal("1000.00")) == 100000

    def test_precision_maintained(self):
        """Test that Decimal precision is handled correctly."""
        # Very precise value
        value = Decimal("0.123456789")
        result = to_cents(value)

        # Should round 12.3456789 cents to 12 cents
        assert result == 12


class TestCostTrackerIntegration:
    """Integration tests for cost tracking (require database mocking)."""

    def test_response_with_unknown_pricing_records_null(self):
        """Unknown model pricing should record null cost fields."""
        from app.llm.types import (
            LLMResponse,
            RequestStatus,
            ProviderType,
            TokenUsage,
            CostEstimate,
        )

        # Response with tokens but unknown pricing
        response = LLMResponse(
            content="Test",
            model="unknown-model-xyz",
            provider=ProviderType.GEMINI,
            status=RequestStatus.SUCCESS,
            tokens=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
            cost=CostEstimate(cost_unavailable_reason="pricing_unknown_for_unknown-model-xyz"),
            finish_reason="stop",
            latency_ms=100,
            total_latency_ms=100,
        )

        # Cost fields should be None
        assert response.cost.total_cost_usd is None
        assert response.cost.cost_unavailable_reason is not None
        # Tokens should still be present
        assert response.tokens.total_tokens == 150

    def test_response_with_unavailable_tokens_records_null(self):
        """Missing token info should record null token fields."""
        from app.llm.types import (
            LLMResponse,
            RequestStatus,
            ProviderType,
            TokenUsage,
            CostEstimate,
        )

        response = LLMResponse(
            content="Test",
            model="gemini-1.5-flash",
            provider=ProviderType.GEMINI,
            status=RequestStatus.SUCCESS,
            tokens=TokenUsage(usage_unavailable_reason="streaming_response"),
            cost=CostEstimate(cost_unavailable_reason="tokens_unavailable"),
            finish_reason="stop",
            latency_ms=100,
            total_latency_ms=100,
        )

        assert response.tokens.input_tokens is None
        assert response.tokens.output_tokens is None
        assert response.tokens.usage_unavailable_reason == "streaming_response"
        assert response.cost.cost_unavailable_reason == "tokens_unavailable"
