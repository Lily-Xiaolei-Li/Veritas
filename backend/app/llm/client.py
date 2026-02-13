"""
Public API for LLM operations (B2.0).

This is the single entry point for other modules to use the LLM abstraction.
Keeps other modules from importing services/llm_service.py directly.

Usage:
    from app.llm.client import llm_complete
    from app.llm import LLMMessage, LLMOptions, ProviderType

    response = await llm_complete(
        messages=[
            LLMMessage(role="user", content="Hello"),
        ],
        options=LLMOptions(model="gemini-1.5-flash"),
        db_session=db_session,
        session_factory=session_factory,  # For cost tracking
    )
"""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .types import ProviderType, LLMMessage, LLMOptions, LLMResponse
from .logging import log_llm_request, log_llm_response


async def llm_complete(
    messages: List[LLMMessage],
    options: LLMOptions,
    db_session: AsyncSession,
    session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    preferred_provider: Optional[ProviderType] = None,
    strict_provider: bool = False,
) -> LLMResponse:
    """
    Complete a conversation with an LLM provider.

    This is the main entry point for LLM operations.

    Args:
        messages: Conversation history as list of LLMMessage
        options: Request options (model, temperature, etc.)
        db_session: Database session for credential lookup
        session_factory: Session factory for background cost tracking (optional)
        preferred_provider: Override default provider (optional)

    Returns:
        LLMResponse with content, tokens, cost, latency

    Raises:
        LLMAuthenticationError: Invalid or missing API key
        LLMRateLimitError: Rate limit exceeded (after max retries)
        LLMTimeoutError: Request timeout
        LLMContentFilterError: Content blocked by safety filters
        LLMModelNotFoundError: Model not available
        LLMProviderUnavailableError: All providers failed
        LLMValidationError: Invalid request parameters

    Example:
        from app.llm.client import llm_complete
        from app.llm import LLMMessage, LLMOptions

        response = await llm_complete(
            messages=[
                LLMMessage(role="system", content="You are a helpful assistant."),
                LLMMessage(role="user", content="Hello!"),
            ],
            options=LLMOptions(
                model="gemini-1.5-flash",
                temperature=0.7,
                max_tokens=1000,
            ),
            db_session=db_session,
            session_factory=async_session_factory,
        )

        print(response.content)
        print(f"Tokens: {response.tokens.total_tokens}")
        print(f"Cost: ${response.cost.total_cost_usd}")
    """
    from app.services.llm_service import get_llm_service
    from app.services.cost_tracker import schedule_usage_recording
    from app.config import get_settings

    settings = get_settings()
    service = get_llm_service()

    # Determine provider for logging
    log_provider = (
        preferred_provider.value if preferred_provider else settings.llm_default_provider
    )
    log_model = options.model or settings.llm_default_model

    # Log request (never blocks, best-effort)
    log_llm_request(
        provider=log_provider,
        model=log_model,
        messages=messages,
        options=options,
    )

    # Execute completion with retry and fallback
    response = await service.complete(
        messages=messages,
        options=options,
        db_session=db_session,
        preferred_provider=preferred_provider,
        strict_provider=strict_provider,
    )

    # Log response
    log_llm_response(response)

    # Schedule cost tracking (background, best-effort)
    if settings.llm_cost_tracking_enabled and session_factory:
        schedule_usage_recording(
            session_factory=session_factory,
            response=response,
            run_id=options.run_id,
            session_id=options.session_id,
        )

    return response
