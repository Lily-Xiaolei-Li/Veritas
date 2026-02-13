"""
Retry logic with exponential backoff for LLM requests (B2.0).

Provides a decorator for automatic retry with:
- Exponential backoff with jitter
- Respect for rate limit retry-after headers
- Separate tracking of per-call vs total latency
"""

import asyncio
import random
import time
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Optional

from .exceptions import LLMError, LLMRateLimitError
from app.logging_config import get_logger

logger = get_logger("llm.retry")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for retry with exponential backoff.

    Only retries if exception.retryable is True.
    Updates response.total_latency_ms to include all attempts.

    Usage:
        @with_retry(RetryConfig(max_attempts=5))
        async def my_llm_call():
            ...

    Args:
        config: Retry configuration (uses defaults if not provided)

    Returns:
        Decorated async function with retry behavior
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            total_start = time.perf_counter()
            total_retry_delay_ms = 0
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    response = await func(*args, **kwargs)

                    # Update total latency if retried.
                    # NOTE: The per-call latency_ms is a logical/provider-reported metric
                    # and may not match wall time in unit tests (which often stub calls).
                    # So we include accumulated retry delays and also fallback to wall time.
                    if attempt > 1:
                        wall_ms = int((time.perf_counter() - total_start) * 1000)
                        response.total_latency_ms = max(
                            int(getattr(response, "latency_ms", 0) or 0) + int(total_retry_delay_ms),
                            wall_ms,
                        )
                    return response

                except LLMError as e:
                    last_exception = e

                    # Check if we should retry
                    if not e.retryable or attempt == config.max_attempts:
                        raise

                    # Calculate backoff delay
                    delay = min(
                        config.base_delay_seconds
                        * (config.exponential_base ** (attempt - 1)),
                        config.max_delay_seconds,
                    )

                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay *= 0.5 + random.random()

                    # Respect rate limit retry-after if provided
                    if isinstance(e, LLMRateLimitError) and e.retry_after:
                        delay = max(delay, e.retry_after)

                    # Log retry attempt
                    # ONLY log provider + model + attempt, never request details
                    logger.warning(
                        f"LLM retry {attempt}/{config.max_attempts} after {delay:.2f}s",
                        extra={
                            "extra_fields": {
                                "provider": e.provider,
                                "attempt": attempt,
                                "delay_seconds": round(delay, 2),
                                "error_type": (
                                    e.error_type.value
                                    if hasattr(e, "error_type")
                                    else "unknown"
                                ),
                                # NEVER log: request, headers, api_key
                            }
                        },
                    )

                    total_retry_delay_ms += int(delay * 1000)
                    await asyncio.sleep(delay)

            # Should not reach here, but safety fallback
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


async def retry_with_fallback(
    primary_func: Callable,
    fallback_func: Callable,
    config: Optional[RetryConfig] = None,
):
    """
    Execute primary function with retry, then fallback on failure.

    This is a helper for manual fallback control. For automatic fallback,
    use the LLMProviderService.complete_with_fallback() method.

    Args:
        primary_func: Primary async function to try
        fallback_func: Fallback async function if primary fails
        config: Retry configuration

    Returns:
        Result from either primary or fallback function

    Raises:
        LLMError: If both primary and fallback fail
    """
    if config is None:
        config = RetryConfig()

    try:
        return await with_retry(config)(primary_func)()
    except LLMError as e:
        if e.fallback_eligible:
            logger.warning(
                f"Primary failed, trying fallback",
                extra={
                    "extra_fields": {
                        "provider": e.provider,
                        "error_type": e.error_type.value,
                    }
                },
            )
            return await fallback_func()
        raise
