"""
Message and streaming API routes (B2.1 - LangGraph Runtime Integration).

Provides:
- POST /sessions/{id}/messages - Submit message and trigger agent run
- GET /sessions/{id}/messages - Get message history
- GET /sessions/{id}/stream - Persistent SSE connection for real-time events

B2.1 Changes:
- Replaced mock agent with LangGraph runtime
- Added 409 Conflict for one active run per session
- Uses bounded queues to prevent memory blowup
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.events import DEFAULT_QUEUE_SIZE, create_bounded_queue
from app.database import get_session
from app.logging_config import get_logger
from app.metrics import (
    MESSAGES_TOTAL,
    SSE_CONNECTIONS_ACTIVE,
    SSE_CONNECTIONS_TOTAL,
)
from app.models import Message, Run, Session
from app.routes.auth_routes import require_auth
from app.schemas.sse_events import ErrorEvent

router = APIRouter()
logger = get_logger("messages")


# =============================================================================
# SSE Infrastructure
# =============================================================================

# In-memory event queues for each session
# Uses bounded queues to prevent memory blowup when UI disconnects
_session_event_queues: Dict[str, asyncio.Queue] = {}


def get_or_create_session_queue(session_id: str) -> asyncio.Queue:
    """Get or create a bounded queue for a session."""
    if session_id not in _session_event_queues:
        _session_event_queues[session_id] = create_bounded_queue(DEFAULT_QUEUE_SIZE)
    return _session_event_queues[session_id]


def get_session_event_queues() -> Dict[str, asyncio.Queue]:
    """
    Get reference to session event queues.

    Used by file_watcher to broadcast file events to all active SSE sessions.

    Returns:
        Dictionary mapping session_id to asyncio.Queue
    """
    return _session_event_queues


def format_sse_event(
    event_type: str,
    data: dict,
    event_id: Optional[str] = None,
) -> str:
    """
    Format an SSE event with proper wire format.

    SSE format:
        id: {event_id}       (optional)
        event: {event_type}
        data: {json}

        (blank line terminates event)

    Args:
        event_type: The event type (token, tool_start, tool_end, error, done)
        data: The event data as a dictionary (will be JSON serialized)
        event_id: Optional event ID for replay support

    Returns:
        Properly formatted SSE event string
    """
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type}")
    lines.append(f"data: {json.dumps(data)}")
    lines.append("")  # Blank line terminates event
    lines.append("")  # Extra blank for safety
    return "\n".join(lines)


def format_sse_comment(comment: str) -> str:
    """Format an SSE comment (used for heartbeats)."""
    return f": {comment}\n\n"



# Note: Mock agent removed in B2.1 - replaced by LangGraph runtime in agent_service.py


# =============================================================================
# Request/Response Models
# =============================================================================


class EditTargetSelection(BaseModel):
    """A selected section within an artifact for editing."""
    artifactId: str
    startLine: int
    endLine: int
    text: str


class MessageCreate(BaseModel):
    """Request model for creating a message."""

    content: str = Field(..., min_length=1, description="Message content")

    # LLM selection (explicit user choice)
    llm_provider: Optional[str] = Field(
        default=None,
        description="Optional explicit provider (gemini|openrouter|ollama|mock)",
    )
    llm_model: Optional[str] = Field(default=None, description="Optional model override")
    llm_strict: bool = Field(
        default=False,
        description="If true and llm_provider is set, do not use default/fallback providers.",
    )

    # Context / knowledge-source config (Stage 14: workspace context)
    focused_artifact_ids: List[str] = Field(default_factory=list)
    focus_mode: str = Field(default="prefer")  # prefer|only
    artifact_scope: str = Field(default="session")  # session|all_sessions
    external_sources: Optional[dict] = Field(default=None)

    # Edit target (B1.7) - AI output should update this artifact
    edit_target_artifact_id: Optional[str] = Field(
        default=None,
        description="Artifact ID to be updated by AI output (edit mode)",
    )
    edit_target_selections: List[EditTargetSelection] = Field(
        default_factory=list,
        description="Specific sections within the artifact to edit",
    )


class MessageResponse(BaseModel):
    """Response model for message."""

    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime


class MessageSubmitResponse(BaseModel):
    """Response model for message submission."""

    user_message: MessageResponse
    run_id: str = Field(..., description="ID of the triggered agent run")


# =============================================================================
# Message Endpoints
# =============================================================================


@router.post(
    "/sessions/{session_id}/messages",
    response_model=MessageSubmitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_message(
    session_id: str,
    message_data: MessageCreate,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Submit a message to a session and trigger agent processing.

    The agent response will be streamed via the SSE endpoint.
    This endpoint returns immediately after storing the user message.

    Returns 409 Conflict if a run is already active for this session.
    Requires authentication if AUTH_ENABLED=true.
    """
    from app.services import run_registry
    from app.services.agent_service import start_agent_run

    try:
        # Verify session exists
        result = await db_session.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}. Create a session first via POST /api/v1/sessions",
            )

        # Check for active run (B2.1: one active run per session)
        if await run_registry.has_active_run(session_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A run is already active for this session. Wait for it to complete or terminate it first.",
            )

        # Create user message
        user_message = Message(
            id=str(uuid4()),
            session_id=session_id,
            role="user",
            content=message_data.content,
        )

        # Generate run ID for this agent execution
        run_id = str(uuid4())

        # Create run record (B2.1: persist run to database)
        run = Run(
            id=run_id,
            session_id=session_id,
            task=message_data.content[:500],  # Truncate for storage
            status="pending",
            run_metadata={
                "context": {
                    "focused_artifact_ids": message_data.focused_artifact_ids[:20],
                    "focus_mode": message_data.focus_mode,
                    "artifact_scope": message_data.artifact_scope,
                    "external_sources": message_data.external_sources or {},
                    # Edit target (B1.7)
                    "edit_target_artifact_id": message_data.edit_target_artifact_id,
                    "edit_target_selections": [
                        s.model_dump() for s in message_data.edit_target_selections
                    ] if message_data.edit_target_selections else [],
                },
                "llm": {
                    "provider": (message_data.llm_provider or "").strip() or None,
                    "model": (message_data.llm_model or "").strip() or None,
                    "strict": bool(message_data.llm_strict),
                },
            },
        )

        db_session.add(user_message)
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(user_message)

        # Increment message counter (B7.2)
        MESSAGES_TOTAL.labels(role="user").inc()

        # Register run with registry BEFORE starting task (B2.1)
        await run_registry.set_active_run(session_id, run_id)

        logger.info(
            f"Message submitted to session {session_id}, starting run {run_id}",
            extra={
                "session_id": session_id,
                "user_id": current_user.get("user_id"),
                "message_id": user_message.id,
                "run_id": run_id,
            },
        )

        # Get or create session queue for SSE
        event_queue = get_or_create_session_queue(session_id)

        # Start LangGraph agent in background (B2.1)
        await start_agent_run(
            run_id=run_id,
            session_id=session_id,
            user_message=message_data.content,
            event_queue=event_queue,
            is_resume=False,
        )

        return MessageSubmitResponse(
            user_message=MessageResponse(
                id=user_message.id,
                session_id=user_message.session_id,
                role=user_message.role,
                content=user_message.content,
                created_at=user_message.created_at,
            ),
            run_id=run_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit message: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit message: {str(e)}",
        )


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_message_history(
    session_id: str,
    db_session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
    limit: int = 100,
    offset: int = 0,
):
    """
    Get message history for a session.

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        # Verify session exists
        result = await db_session.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {session_id}",
            )

        # Get messages
        query = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await db_session.execute(query)
        messages = result.scalars().all()

        return [
            MessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in messages
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}",
        )


# =============================================================================
# SSE Streaming Endpoint
# =============================================================================


@router.get("/sessions/{session_id}/stream")
async def stream_events(
    session_id: str,
    token: Optional[str] = Query(None, description="Auth token (stubbed for B1.1)"),
    db_session: AsyncSession = Depends(get_session),
):
    """
    Persistent SSE connection for real-time agent events.

    Connect to this endpoint when opening a session. Events will be streamed
    as the agent processes messages:

    Event Types:
    - token: Text content chunk (append to display)
    - tool_start: Tool invocation beginning
    - tool_end: Tool invocation completed
    - error: Error during processing
    - done: Agent run completed

    Query Parameters:
        token: Auth token (optional, stubbed for B1.1)

    Returns:
        text/event-stream: SSE stream of agent events
    """
    # Verify session exists
    result = await db_session.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        # Can't use HTTP error after SSE starts, so return error event then close
        async def error_stream():
            error = ErrorEvent(
                run_id="init",
                seq=1,
                message=f"Session not found: {session_id}",
                recoverable=False,
            )
            yield format_sse_event("error", error.model_dump())

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers=_sse_headers(),
        )

    # Auth token validation (stubbed for B1.1)
    # In production: if settings.auth_enabled and not validate_token(token): ...
    if token:
        logger.debug(f"SSE connection with token for session {session_id}")

    logger.info(f"SSE connection opened for session {session_id}")

    # Track SSE connection metrics (B7.2)
    SSE_CONNECTIONS_TOTAL.inc()
    SSE_CONNECTIONS_ACTIVE.inc()

    async def event_generator():
        """Generate SSE events from the session queue."""
        queue = get_or_create_session_queue(session_id)
        heartbeat_interval = 30  # seconds
        last_heartbeat = asyncio.get_event_loop().time()

        try:
            # Send initial connection event
            yield format_sse_comment("connected")

            while True:
                try:
                    # Wait for events with timeout for heartbeat
                    current_time = asyncio.get_event_loop().time()
                    timeout = max(0.1, heartbeat_interval - (current_time - last_heartbeat))

                    try:
                        event_type, data, event_id = await asyncio.wait_for(
                            queue.get(),
                            timeout=timeout,
                        )

                        # Handle internal message storage event
                        if event_type == "_store_message":
                            await _store_assistant_message(
                                data["session_id"],
                                data["content"],
                            )
                            continue

                        # Send the event
                        yield format_sse_event(event_type, data, event_id)

                    except asyncio.TimeoutError:
                        # Send heartbeat
                        current_time = asyncio.get_event_loop().time()
                        if current_time - last_heartbeat >= heartbeat_interval:
                            yield format_sse_comment("heartbeat")
                            last_heartbeat = current_time

                except asyncio.CancelledError:
                    logger.info(f"SSE connection cancelled for session {session_id}")
                    break

        except Exception as e:
            logger.error(f"SSE stream error for session {session_id}: {e}", exc_info=True)
            error = ErrorEvent(
                run_id="stream",
                seq=1,
                message=f"Stream error: {str(e)}",
                recoverable=True,
            )
            yield format_sse_event("error", error.model_dump())

        finally:
            # Decrement active SSE connections (B7.2)
            SSE_CONNECTIONS_ACTIVE.dec()
            logger.info(f"SSE connection closed for session {session_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


def _sse_headers() -> dict:
    """Return standard SSE headers."""
    return {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Disable nginx buffering
    }


async def _store_assistant_message(session_id: str, content: str) -> None:
    """Store the complete assistant message after streaming."""
    try:
        from app.database import get_database

        db = get_database()
        async with db.session() as new_session:
            assistant_message = Message(
                id=str(uuid4()),
                session_id=session_id,
                role="assistant",
                content=content,
            )
            new_session.add(assistant_message)
            await new_session.commit()

            # Increment message counter (B7.2)
            MESSAGES_TOTAL.labels(role="assistant").inc()

            logger.debug(f"Stored assistant message for session {session_id}")
    except Exception as e:
        logger.error(f"Failed to store assistant message: {e}", exc_info=True)
