"""
Tests for LLM retry logic (B2.0).
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.llm.retry import RetryConfig, with_retry
from app.llm.exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMValidationError,
)
from app.llm.types import (
    LLMResponse,
    RequestStatus,
    ProviderType,
    TokenUsage,
    CostEstimate,
)


def make_success_response(latency_ms: int = 100) -> LLMResponse:
    """Create a successful mock response."""
    return LLMResponse(
        content="Test response",
        model="test-model",
        provider=ProviderType.MOCK,
        status=RequestStatus.SUCCESS,
        tokens=TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15),
        cost=CostEstimate(),
        finish_reason="stop",
        latency_ms=latency_ms,
        total_latency_ms=latency_ms,
    )


class TestRetryConfig:
    """Test RetryConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay_seconds == 1.0
        assert config.max_delay_seconds == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay_seconds=0.5,
            max_delay_seconds=30.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_attempts == 5
        assert config.base_delay_seconds == 0.5


class TestWithRetry:
    """Test with_retry decorator."""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """Successful call should not retry."""
        call_count = 0

        @with_retry()
        async def succeed():
            nonlocal call_count
            call_count += 1
            return make_success_response()

        result = await succeed()

        assert call_count == 1
        assert result.status == RequestStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_retryable_error_retries(self):
        """Retryable error should trigger retry."""
        call_count = 0
        config = RetryConfig(max_attempts=3, base_delay_seconds=0.01, jitter=False)

        @with_retry(config)
        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise LLMRateLimitError("Rate limited", provider="test")
            return make_success_response()

        result = await fail_then_succeed()

        assert call_count == 2
        assert result.status == RequestStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_non_retryable_error_no_retry(self):
        """Non-retryable error should not retry."""
        call_count = 0

        @with_retry()
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise LLMAuthenticationError("Bad key", provider="test")

        with pytest.raises(LLMAuthenticationError):
            await always_fail()

        assert call_count == 1  # No retry for auth errors

    @pytest.mark.asyncio
    async def test_validation_error_no_retry(self):
        """Validation error should not retry."""
        call_count = 0

        @with_retry()
        async def validation_fail():
            nonlocal call_count
            call_count += 1
            raise LLMValidationError("Bad request", provider="test")

        with pytest.raises(LLMValidationError):
            await validation_fail()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_max_attempts_exhausted(self):
        """Should raise after max attempts exhausted."""
        call_count = 0
        config = RetryConfig(max_attempts=3, base_delay_seconds=0.01, jitter=False)

        @with_retry(config)
        async def always_timeout():
            nonlocal call_count
            call_count += 1
            raise LLMTimeoutError("Timeout", provider="test")

        with pytest.raises(LLMTimeoutError):
            await always_timeout()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_total_latency_updated_on_retry(self):
        """total_latency_ms should include retry delays."""
        call_count = 0
        config = RetryConfig(max_attempts=3, base_delay_seconds=0.05, jitter=False)

        @with_retry(config)
        async def fail_once():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise LLMRateLimitError("Rate limited", provider="test")
            return make_success_response(latency_ms=50)

        result = await fail_once()

        # total_latency should be greater than per-call latency due to retry
        assert result.total_latency_ms > result.latency_ms

    @pytest.mark.asyncio
    async def test_respects_retry_after_header(self):
        """Should respect retry_after from rate limit error."""
        config = RetryConfig(max_attempts=2, base_delay_seconds=0.01, jitter=False)
        sleep_times = []

        @with_retry(config)
        async def rate_limited():
            if len(sleep_times) == 0:
                raise LLMRateLimitError("Rate limited", provider="test", retry_after=1)
            return make_success_response()

        with patch("asyncio.sleep") as mock_sleep:
            async def track_sleep(delay):
                sleep_times.append(delay)

            mock_sleep.side_effect = track_sleep
            await rate_limited()

        # Should have waited at least 1 second (the retry_after value)
        assert len(sleep_times) == 1
        assert sleep_times[0] >= 1.0


class TestExceptionFlags:
    """Test exception retryable and fallback_eligible flags."""

    def test_auth_error_flags(self):
        """Auth error should be fallback eligible but not retryable."""
        err = LLMAuthenticationError("Bad key", provider="test")

        assert err.retryable is False
        assert err.fallback_eligible is True

    def test_rate_limit_flags(self):
        """Rate limit should be retryable and fallback eligible."""
        err = LLMRateLimitError("Limited", provider="test")

        assert err.retryable is True
        assert err.fallback_eligible is True

    def test_timeout_flags(self):
        """Timeout should be retryable and fallback eligible."""
        err = LLMTimeoutError("Timeout", provider="test")

        assert err.retryable is True
        assert err.fallback_eligible is True

    def test_validation_error_flags(self):
        """Validation error should not be retryable or fallback eligible."""
        err = LLMValidationError("Bad params", provider="test")

        assert err.retryable is False
        assert err.fallback_eligible is False

    def test_content_filter_flags(self):
        """Content filter should NOT be fallback eligible (safety)."""
        from app.llm.exceptions import LLMContentFilterError

        err = LLMContentFilterError("Blocked", provider="test")

        assert err.retryable is False
        assert err.fallback_eligible is False  # CRITICAL - don't bypass safety
