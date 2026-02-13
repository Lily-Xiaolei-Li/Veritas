"""
LLM Provider Abstraction Layer (B2.0).

This module provides a unified interface for multiple LLM providers
with credential management, retry logic, cost tracking, and logging.

Usage:
    from app.llm.client import llm_complete
    from app.llm.types import LLMMessage, LLMOptions

    response = await llm_complete(
        messages=[LLMMessage(role="user", content="Hello")],
        options=LLMOptions(model="gemini-1.5-flash"),
        db_session=session,
    )
"""

from .types import (
    ProviderType,
    RequestStatus,
    ErrorType,
    LLMMessage,
    LLMOptions,
    TokenUsage,
    CostEstimate,
    LLMResponse,
    StreamChunk,
)
from .exceptions import (
    LLMError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMContentFilterError,
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMValidationError,
)
from .client import llm_complete

__all__ = [
    # Client API
    "llm_complete",
    # Types
    "ProviderType",
    "RequestStatus",
    "ErrorType",
    "LLMMessage",
    "LLMOptions",
    "TokenUsage",
    "CostEstimate",
    "LLMResponse",
    "StreamChunk",
    # Exceptions
    "LLMError",
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMConnectionError",
    "LLMTimeoutError",
    "LLMContentFilterError",
    "LLMModelNotFoundError",
    "LLMProviderUnavailableError",
    "LLMValidationError",
]
