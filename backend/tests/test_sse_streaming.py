"""
Tests for SSE streaming (B1.1 - Streaming Reasoning & Events).

Tests cover:
- SSE wire format compliance
- Event schema validation
- Endpoint behavior
- Sequence number monotonicity
"""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.routes.message_routes import (
    format_sse_event,
    format_sse_comment,
    stream_events,
    submit_message,
    MessageCreate,
)
from app.schemas.sse_events import (
    TokenEvent,
    ToolStartEvent,
    ToolEndEvent,
    ErrorEvent,
    DoneEvent,
)
from app.models import Session


class TestSSEFormat:
    """Test SSE wire format compliance."""

    def test_format_sse_event_with_id(self):
        """Event with ID must have correct line structure."""
        result = format_sse_event("token", {"content": "hi"}, event_id="123")
        lines = result.split("\n")

        assert lines[0] == "id: 123"
        assert lines[1] == "event: token"
        assert lines[2].startswith("data: ")
        assert lines[3] == ""  # Blank line terminates event

    def test_format_sse_event_without_id(self):
        """Event without ID should omit id line."""
        result = format_sse_event("done", {"run_id": "r1", "seq": 1})

        assert "id:" not in result
        assert "event: done" in result
        assert "data:" in result

    def test_format_sse_event_json_valid(self):
        """Data line must contain valid JSON."""
        data = {"run_id": "run-123", "seq": 1, "content": "test content"}
        result = format_sse_event("token", data, event_id="evt-1")

        # Find the data line
        data_line = [l for l in result.split("\n") if l.startswith("data:")][0]
        json_str = data_line[6:]  # Remove "data: " prefix

        parsed = json.loads(json_str)
        assert parsed["run_id"] == "run-123"
        assert parsed["seq"] == 1
        assert parsed["content"] == "test content"

    def test_format_sse_event_escapes_newlines(self):
        """JSON encoding should handle special characters."""
        data = {"content": "line1\nline2\ttabbed"}
        result = format_sse_event("token", data)

        # Find the data line
        data_line = [l for l in result.split("\n") if l.startswith("data:")][0]
        json_str = data_line[6:]

        # Should be valid JSON with escaped newlines
        parsed = json.loads(json_str)
        assert parsed["content"] == "line1\nline2\ttabbed"

    def test_format_sse_comment(self):
        """Comments should start with colon."""
        result = format_sse_comment("heartbeat")

        assert result == ": heartbeat\n\n"

    def test_format_sse_event_all_types(self):
        """Test formatting for all event types."""
        event_types = ["token", "tool_start", "tool_end", "error", "done"]

        for event_type in event_types:
            result = format_sse_event(event_type, {"test": True})
            assert f"event: {event_type}" in result
            assert "data:" in result


class TestSSEEventSchemas:
    """Test Pydantic event schemas."""

    def test_token_event_valid(self):
        """TokenEvent with valid data."""
        event = TokenEvent(run_id="run-123", seq=1, content="Hello")

        assert event.run_id == "run-123"
        assert event.seq == 1
        assert event.content == "Hello"

    def test_token_event_seq_must_be_positive(self):
        """TokenEvent seq must be >= 1."""
        with pytest.raises(Exception):  # Pydantic validation error
            TokenEvent(run_id="run-123", seq=0, content="Hello")

    def test_tool_start_event_valid(self):
        """ToolStartEvent with valid data."""
        event = ToolStartEvent(
            run_id="run-123",
            seq=5,
            tool_call_id="tc-456",
            tool_name="bash",
            input_preview="ls -la",
        )

        assert event.tool_name == "bash"
        assert event.tool_call_id == "tc-456"

    def test_tool_start_event_input_truncation(self):
        """ToolStartEvent input_preview should be max 200 chars."""
        long_input = "x" * 300

        with pytest.raises(Exception):  # Pydantic validation error
            ToolStartEvent(
                run_id="run-123",
                seq=1,
                tool_call_id="tc-1",
                tool_name="test",
                input_preview=long_input,
            )

    def test_tool_end_event_valid(self):
        """ToolEndEvent with valid data."""
        event = ToolEndEvent(
            run_id="run-123",
            seq=6,
            tool_call_id="tc-456",
            exit_code=0,
            output_preview="file1.txt\nfile2.txt",
            duration_ms=150,
        )

        assert event.exit_code == 0
        assert event.duration_ms == 150

    def test_tool_end_event_failure(self):
        """ToolEndEvent with non-zero exit code."""
        event = ToolEndEvent(
            run_id="run-123",
            seq=6,
            tool_call_id="tc-456",
            exit_code=1,
            output_preview="Error: file not found",
            duration_ms=50,
        )

        assert event.exit_code == 1

    def test_error_event_valid(self):
        """ErrorEvent with valid data."""
        event = ErrorEvent(
            run_id="run-123",
            seq=10,
            message="Connection timeout",
            recoverable=True,
        )

        assert event.message == "Connection timeout"
        assert event.recoverable is True

    def test_error_event_non_recoverable(self):
        """ErrorEvent with non-recoverable flag."""
        event = ErrorEvent(
            run_id="run-123",
            seq=10,
            message="Session not found",
            recoverable=False,
        )

        assert event.recoverable is False

    def test_done_event_valid(self):
        """DoneEvent with valid data."""
        event = DoneEvent(run_id="run-123", seq=15)

        assert event.run_id == "run-123"
        assert event.seq == 15


class TestSSEStreamEndpoint:
    """Test SSE endpoint behavior."""

    @pytest.mark.asyncio
    async def test_stream_session_not_found(self):
        """Stream endpoint returns error event for non-existent session."""
        mock_db = AsyncMock(spec=AsyncSession)

        # Mock session not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await stream_events("nonexistent", token=None, db_session=mock_db)

        # Should return StreamingResponse (not HTTP error)
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"

    @pytest.mark.asyncio
    async def test_stream_returns_correct_headers(self):
        """Stream endpoint returns correct SSE headers."""
        mock_db = AsyncMock(spec=AsyncSession)
        session_id = "session-123"

        # Mock session found
        mock_session = Session(
            id=session_id,
            title="Test",
            mode="engineering",
            status="active",
            config=None,
        )
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await stream_events(session_id, token=None, db_session=mock_db)

        assert response.media_type == "text/event-stream"
        assert "no-cache" in response.headers.get("cache-control", "")
        assert response.headers.get("connection") == "keep-alive"
        assert response.headers.get("x-accel-buffering") == "no"

    @pytest.mark.asyncio
    async def test_stream_with_token_parameter(self):
        """Stream endpoint accepts token query parameter."""
        mock_db = AsyncMock(spec=AsyncSession)
        session_id = "session-123"

        mock_session = Session(
            id=session_id,
            title="Test",
            mode="engineering",
            status="active",
            config=None,
        )
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Should not raise even with token (stubbed for B1.1)
        response = await stream_events(session_id, token="test-token", db_session=mock_db)

        assert isinstance(response, StreamingResponse)


class TestMessageSubmitWithStreaming:
    """Test message submission triggers streaming events (B2.1 - LangGraph)."""

    @pytest.mark.asyncio
    async def test_submit_message_returns_run_id(self):
        """Submit message returns run_id for tracking."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        async def mock_refresh(obj):
            obj.created_at = datetime.now(timezone.utc)
        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        mock_user = {"user_id": "user_123", "username": "testuser"}
        session_id = "session-123"

        mock_session = Session(
            id=session_id,
            title="Test",
            mode="engineering",
            status="active",
            config=None,
        )
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        message_data = MessageCreate(content="Hello")

        # Mock B2.1 dependencies
        with patch("app.services.run_registry.has_active_run", AsyncMock(return_value=False)), \
             patch("app.services.run_registry.set_active_run", AsyncMock()), \
             patch("app.services.agent_service.start_agent_run", AsyncMock()):

            result = await submit_message(session_id, message_data, mock_db, mock_user)

        # Should include run_id
        assert hasattr(result, 'run_id')
        assert result.run_id is not None
        assert len(result.run_id) > 0

    @pytest.mark.asyncio
    async def test_submit_message_stores_user_message(self):
        """Submit message stores user message and run in database."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        async def mock_refresh(obj):
            obj.created_at = datetime.now(timezone.utc)
        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        mock_user = {"user_id": "user_123", "username": "testuser"}
        session_id = "session-123"

        mock_session = Session(
            id=session_id,
            title="Test",
            mode="engineering",
            status="active",
            config=None,
        )
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        message_data = MessageCreate(content="Test message")

        # Mock B2.1 dependencies
        with patch("app.services.run_registry.has_active_run", AsyncMock(return_value=False)), \
             patch("app.services.run_registry.set_active_run", AsyncMock()), \
             patch("app.services.agent_service.start_agent_run", AsyncMock()):

            result = await submit_message(session_id, message_data, mock_db, mock_user)

        # B2.1: User message + Run record stored
        assert mock_db.add.call_count == 2  # User message + Run record
        assert result.user_message.content == "Test message"
        assert result.user_message.role == "user"


class TestEventSequenceNumbers:
    """Test event sequence number behavior."""

    def test_sequence_numbers_in_formatted_events(self):
        """Formatted events preserve sequence numbers."""
        events = []
        run_id = "run-test"

        for seq in range(1, 6):
            data = TokenEvent(run_id=run_id, seq=seq, content=f"chunk{seq}").model_dump()
            event_str = format_sse_event("token", data, f"{run_id}-{seq}")
            events.append(event_str)

        # Parse and verify sequences
        sequences = []
        for event_str in events:
            data_line = [l for l in event_str.split("\n") if l.startswith("data:")][0]
            parsed = json.loads(data_line[6:])
            sequences.append(parsed["seq"])

        assert sequences == [1, 2, 3, 4, 5]
        assert sequences == sorted(sequences), "Sequence numbers must be monotonic"

    def test_event_id_format(self):
        """Event IDs follow run_id-seq format."""
        run_id = "run-abc123"
        seq = 42

        event_str = format_sse_event(
            "token",
            TokenEvent(run_id=run_id, seq=seq, content="test").model_dump(),
            event_id=f"{run_id}-{seq}"
        )

        # Parse event ID
        id_line = [l for l in event_str.split("\n") if l.startswith("id:")][0]
        event_id = id_line[4:]  # Remove "id: " prefix

        assert event_id == "run-abc123-42"
