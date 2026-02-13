"""
Cost tracking service for LLM usage (B2.0).

Records LLM API usage to database for cost tracking and observability.
Uses best-effort async recording - never blocks the main request.

IMPORTANT: Uses session_factory (not session instance) to avoid
AsyncSession lifecycle issues with background tasks.
"""

import asyncio
import json
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.llm.types import LLMResponse
from app.logging_config import get_logger
from app.models import LLMUsage

logger = get_logger("llm.cost_tracker")


def to_cents(d: Optional[Decimal]) -> Optional[int]:
    """
    Convert Decimal USD to integer cents with explicit ROUND_HALF_UP rounding.

    Args:
        d: Decimal value in USD (e.g., Decimal("0.0015"))

    Returns:
        Integer cents or None if input is None
    """
    if d is None:
        return None
    # Multiply by 100 and round using ROUND_HALF_UP for predictable behavior
    cents = (d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)


async def record_llm_usage(
    session_factory: async_sessionmaker[AsyncSession],
    response: LLMResponse,
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
    request_type: str = "complete",
) -> Optional[str]:
    """
    Record LLM usage to database.

    BEST-EFFORT: Never blocks or fails the main request.
    Returns usage ID or None on failure.

    IMPORTANT: Takes session_factory, NOT a session instance.
    Background tasks must create their own session to avoid
    lifecycle issues with the request-scoped session.

    Args:
        session_factory: Async session factory to create new DB session
        response: LLM response with tokens, cost, latency
        run_id: Optional run context
        session_id: Optional session context
        request_type: Type of request (complete, stream)

    Returns:
        Usage record ID or None if recording failed
    """
    try:
        async with session_factory() as db_session:
            usage = LLMUsage(
                id=str(uuid4()),
                run_id=run_id,
                session_id=session_id,
                provider=response.provider.value,
                model=response.model,
                request_type=request_type,
                status=response.status.value,
                error_type=response.error_type.value if response.error_type else None,
                input_tokens=response.tokens.input_tokens,
                output_tokens=response.tokens.output_tokens,
                total_tokens=response.tokens.total_tokens,
                tokens_unavailable_reason=response.tokens.usage_unavailable_reason,
                input_cost_cents=to_cents(response.cost.input_cost_usd),
                output_cost_cents=to_cents(response.cost.output_cost_usd),
                total_cost_cents=to_cents(response.cost.total_cost_usd),
                cost_unavailable_reason=response.cost.cost_unavailable_reason,
                latency_ms=response.latency_ms,
                total_latency_ms=response.total_latency_ms,
                provider_request_id=response.provider_request_id,
                finish_reason=response.finish_reason,
                # JSON encode attempted_providers list
                attempted_providers=(
                    json.dumps(response.attempted_providers)
                    if response.attempted_providers
                    else None
                ),
            )

            db_session.add(usage)
            await db_session.commit()

            logger.debug(
                f"Recorded LLM usage: {usage.id}",
                extra={
                    "extra_fields": {
                        "usage_id": usage.id,
                        "provider": response.provider.value,
                        "model": response.model,
                        "total_cost_cents": usage.total_cost_cents,
                    }
                },
            )
            return usage.id

    except Exception as e:
        # NEVER fail the main request due to logging
        logger.error(
            f"Failed to record LLM usage (non-blocking): {e}",
            extra={
                "extra_fields": {
                    "provider": response.provider.value,
                    "error": str(e),
                }
            },
        )
        return None


def schedule_usage_recording(
    session_factory: async_sessionmaker[AsyncSession],
    response: LLMResponse,
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
    request_type: str = "complete",
) -> None:
    """
    Schedule usage recording as a background task.

    CRITICAL: Pass session_factory (not session) to avoid AsyncSession
    lifecycle issues. Background task creates its own session.

    Args:
        session_factory: Async session factory for creating DB session
        response: LLM response to record
        run_id: Optional run context
        session_id: Optional session context
        request_type: Type of request (complete, stream)
    """
    asyncio.create_task(
        record_llm_usage(
            session_factory=session_factory,
            response=response,
            run_id=run_id,
            session_id=session_id,
            request_type=request_type,
        )
    )
