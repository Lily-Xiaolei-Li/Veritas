"""
Core types for LLM Provider Abstraction (B2.0).

This module defines the data structures used throughout the LLM layer.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class ProviderType(str, Enum):
    """Supported LLM providers."""

    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    MOCK = "mock"


class RequestStatus(str, Enum):
    """Status of an LLM request."""

    SUCCESS = "success"
    ERROR = "error"


class ErrorType(str, Enum):
    """Categorized error types for LLM operations."""

    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    CONTENT_FILTER = "content_filter"
    MODEL_NOT_FOUND = "model_not_found"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class LLMMessage:
    """A message in the conversation."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMOptions:
    """Options for LLM requests."""

    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    stop_sequences: List[str] = field(default_factory=list)
    timeout_seconds: int = 120
    # Metadata for logging/tracking
    run_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class TokenUsage:
    """
    Token usage for a request.

    Fields are Optional because not all providers return this data.
    """

    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    usage_unavailable_reason: Optional[str] = None  # e.g., "streaming", "provider_unsupported"


@dataclass
class CostEstimate:
    """
    Cost estimate for a request.

    Fields are Optional because pricing may be unknown for some models.
    Uses Decimal to avoid floating-point precision issues.
    """

    input_cost_usd: Optional[Decimal] = None
    output_cost_usd: Optional[Decimal] = None
    total_cost_usd: Optional[Decimal] = None
    cost_unavailable_reason: Optional[str] = None  # e.g., "pricing_unknown", "tokens_unavailable"
    cost_source: Optional[str] = None  # "api_pricing" | "local" | "custom"


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    provider: ProviderType
    status: RequestStatus
    tokens: TokenUsage
    cost: CostEstimate
    finish_reason: Optional[str]  # "stop", "length", "content_filter", None
    latency_ms: int  # Measured around provider call only (excludes retries)
    total_latency_ms: int  # Includes all retry attempts
    provider_request_id: Optional[str] = None
    error_type: Optional[ErrorType] = None
    attempted_providers: List[str] = field(default_factory=list)  # For fallback tracking
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """A chunk from a streaming response (MockProvider only in B2.0)."""

    content: str
    finish_reason: Optional[str] = None
