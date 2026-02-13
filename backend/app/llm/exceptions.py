"""
Exception hierarchy for LLM Provider Abstraction (B2.0).

Each exception type has explicit retry and fallback eligibility flags.
This prevents incorrect behavior like bypassing safety filters or
retrying requests that will always fail.
"""

from typing import Optional

from .types import ErrorType


class LLMError(Exception):
    """
    Base exception for all LLM errors.

    Attributes:
        provider: Name of the provider that raised the error
        error_type: Categorized error type
        retryable: Whether this error can be retried with backoff
        fallback_eligible: Whether to try the next provider in the chain
    """

    def __init__(
        self,
        message: str,
        provider: str,
        error_type: ErrorType,
        retryable: bool = False,
        fallback_eligible: bool = False,
    ):
        self.provider = provider
        self.error_type = error_type
        self.retryable = retryable
        self.fallback_eligible = fallback_eligible
        super().__init__(message)


class LLMAuthenticationError(LLMError):
    """
    API key invalid or missing.

    Not retryable (same key will always fail).
    Fallback eligible (try another provider with valid key).
    """

    def __init__(self, message: str, provider: str):
        super().__init__(
            message,
            provider,
            error_type=ErrorType.AUTH,
            retryable=False,
            fallback_eligible=True,
        )


class LLMRateLimitError(LLMError):
    """
    Rate limit exceeded.

    Retryable with backoff (respects retry_after if provided).
    Fallback eligible after max retries.
    """

    def __init__(
        self, message: str, provider: str, retry_after: Optional[int] = None
    ):
        self.retry_after = retry_after
        super().__init__(
            message,
            provider,
            error_type=ErrorType.RATE_LIMIT,
            retryable=True,
            fallback_eligible=True,
        )


class LLMConnectionError(LLMError):
    """
    Network/connection error.

    Retryable (transient network issues).
    Fallback eligible.
    """

    def __init__(self, message: str, provider: str):
        super().__init__(
            message,
            provider,
            error_type=ErrorType.CONNECTION,
            retryable=True,
            fallback_eligible=True,
        )


class LLMTimeoutError(LLMError):
    """
    Request timeout.

    Retryable (server may have been temporarily slow).
    Fallback eligible.
    """

    def __init__(self, message: str, provider: str):
        super().__init__(
            message,
            provider,
            error_type=ErrorType.TIMEOUT,
            retryable=True,
            fallback_eligible=True,
        )


class LLMContentFilterError(LLMError):
    """
    Content blocked by safety filters.

    CRITICAL: NOT fallback eligible by default.
    Bypassing safety filters by trying another provider defeats the
    purpose of the filter. The llm_fallback_on_content_filter config
    can override this, but it's dangerous.
    """

    def __init__(self, message: str, provider: str):
        super().__init__(
            message,
            provider,
            error_type=ErrorType.CONTENT_FILTER,
            retryable=False,
            fallback_eligible=False,  # CRITICAL: Don't bypass safety
        )


class LLMModelNotFoundError(LLMError):
    """
    Requested model not available.

    Not retryable (model won't appear).
    Fallback eligible (another provider may have the model).
    """

    def __init__(self, message: str, provider: str, model: str):
        self.model = model
        super().__init__(
            message,
            provider,
            error_type=ErrorType.MODEL_NOT_FOUND,
            retryable=False,
            fallback_eligible=True,
        )


class LLMProviderUnavailableError(LLMError):
    """
    Provider service unavailable.

    Retryable (service may come back).
    Fallback eligible.
    """

    def __init__(self, message: str, provider: str):
        super().__init__(
            message,
            provider,
            error_type=ErrorType.PROVIDER_UNAVAILABLE,
            retryable=True,
            fallback_eligible=True,
        )


class LLMValidationError(LLMError):
    """
    Request validation failed (bad parameters).

    NOT retryable (same bad request will always fail).
    NOT fallback eligible (same bad request fails on all providers).
    """

    def __init__(self, message: str, provider: str):
        super().__init__(
            message,
            provider,
            error_type=ErrorType.VALIDATION,
            retryable=False,
            fallback_eligible=False,
        )
