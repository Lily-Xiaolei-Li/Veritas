"""
LLM request/response logging (B2.0).

Provides structured logging for LLM operations with:
- Salted content hashing (never logs raw content)
- Configurable context ID logging (high-cardinality concern)
- Best-effort (never blocks requests)

NEVER logs: actual content, API keys, headers
"""

import hashlib
from typing import List, Optional

from app.config import get_settings
from app.logging_config import get_logger

from .types import LLMMessage, LLMOptions, LLMResponse

logger = get_logger("llm")

# Track if we've warned about missing salt (warn once on startup)
_salt_warning_logged = False


def _get_validated_salt() -> Optional[str]:
    """
    Get hash salt, validating it's set in production.

    If empty and content_mode is 'hash', logs warning once and
    falls back to 'none' mode (no hashing).
    """
    global _salt_warning_logged
    settings = get_settings()

    salt = settings.llm_log_hash_salt
    if salt:
        return salt

    # Salt is empty
    if settings.llm_log_content == "hash" and not _salt_warning_logged:
        logger.warning(
            "LLM_LOG_HASH_SALT is empty but llm_log_content='hash'. "
            "Content hashing disabled to prevent predictable hashes. "
            "Set LLM_LOG_HASH_SALT to a random value in production."
        )
        _salt_warning_logged = True

    return None  # Fall back to no hashing


def _compute_content_hash(
    messages: List[LLMMessage],
    provider: str,
    model: str,
) -> Optional[str]:
    """
    Compute salted hash of request content.

    Hash includes: salt + provider + model + normalized messages
    Returns first 16 chars of SHA-256, or None if salt not configured.
    """
    salt = _get_validated_salt()
    if not salt:
        return None

    # Normalize: salt + provider + model + role:content pairs
    content_parts = [salt, provider, model]
    for m in messages:
        content_parts.append(f"{m.role}:{m.content}")

    combined = "|".join(content_parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def log_llm_request(
    provider: str,
    model: str,
    messages: List[LLMMessage],
    options: LLMOptions,
) -> None:
    """
    Log outgoing LLM request.

    NEVER logs: actual content, API keys, headers
    Context IDs (run_id, session_id) only logged if llm_log_context_ids=True
    to avoid high-cardinality issues in log aggregation systems.
    """
    settings = get_settings()
    content_mode = settings.llm_log_content

    log_data = {
        "provider": provider,
        "model": model,
        "message_count": len(messages),
        "total_chars": sum(len(m.content) for m in messages),
        "temperature": options.temperature,
        "max_tokens": options.max_tokens,
        "timeout_seconds": options.timeout_seconds,
    }

    # Context IDs only if configured (high-cardinality concern)
    if settings.llm_log_context_ids:
        if options.run_id:
            log_data["run_id"] = options.run_id
        if options.session_id:
            log_data["session_id"] = options.session_id

    # Add content hash if configured
    if content_mode == "hash":
        content_hash = _compute_content_hash(messages, provider, model)
        if content_hash:
            log_data["content_hash"] = content_hash

    logger.debug("LLM request", extra={"extra_fields": log_data})


def log_llm_response(response: LLMResponse) -> None:
    """
    Log incoming LLM response.

    Always logs: provider, model, tokens, cost, latency, status
    NEVER logs: response content
    """
    log_data = {
        "provider": response.provider.value,
        "model": response.model,
        "status": response.status.value,
        "input_tokens": response.tokens.input_tokens,
        "output_tokens": response.tokens.output_tokens,
        "total_tokens": response.tokens.total_tokens,
        "tokens_unavailable": response.tokens.usage_unavailable_reason,
        "cost_usd": (
            float(response.cost.total_cost_usd)
            if response.cost.total_cost_usd
            else None
        ),
        "cost_unavailable": response.cost.cost_unavailable_reason,
        "latency_ms": response.latency_ms,
        "total_latency_ms": response.total_latency_ms,
        "finish_reason": response.finish_reason,
    }

    if response.error_type:
        log_data["error_type"] = response.error_type.value

    if response.provider_request_id:
        log_data["provider_request_id"] = response.provider_request_id

    if response.attempted_providers and len(response.attempted_providers) > 1:
        log_data["attempted_providers"] = response.attempted_providers

    # Summary log line at INFO level
    cost_str = (
        f"${float(response.cost.total_cost_usd):.6f}"
        if response.cost.total_cost_usd
        else "unknown"
    )
    tokens_str = (
        str(response.tokens.total_tokens) if response.tokens.total_tokens else "unknown"
    )

    logger.info(
        f"LLM {response.status.value}: {response.model} - "
        f"{tokens_str} tokens - {cost_str} - {response.latency_ms}ms",
        extra={"extra_fields": log_data},
    )


def log_llm_error(
    provider: str,
    error_type: str,
    message: str,
    fallback_eligible: bool = False,
    retryable: bool = False,
) -> None:
    """
    Log LLM error with structured metadata.

    NEVER logs: request content, API keys
    """
    log_data = {
        "provider": provider,
        "error_type": error_type,
        "fallback_eligible": fallback_eligible,
        "retryable": retryable,
        # NEVER include: request content, exception details that may contain user input
    }

    logger.warning(
        f"LLM error ({provider}): {error_type}",
        extra={"extra_fields": log_data},
    )
