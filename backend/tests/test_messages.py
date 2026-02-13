"""
Tests for message and streaming API (B1.1 - Updated).

Note: SSE streaming tests are in test_sse_streaming.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, Session
from app.routes.message_routes import (
    MessageCreate,
    get_message_history,
    stream_events,
    submit_message,
)


class TestSubmitMessage:
    """Tests for submitting messages (B2.1 update - LangGraph integration)."""

    @pytest.mark.asyncio
    async def test_submit_message_success(self):
        """Test successful message submission returns user message and run_id."""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock refresh to set datetime fields
        async def mock_refresh(obj):
            from datetime import timezone
            obj.created_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        # Mock current user
        mock_user = {"user_id": "user_123", "username": "testuser"}

        # Mock session lookup
        session_id = "session_123"
        mock_session = Session(
            id=session_id,
            title="Test Session",
            mode="engineering",
            status="active",
            config=None,
        )
        from datetime import timezone
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Prepare message data
        message_data = MessageCreate(content="Hello, Agent B!")

        # Mock B2.1 dependencies
        with patch("app.services.run_registry.has_active_run", AsyncMock(return_value=False)), \
             patch("app.services.run_registry.set_active_run", AsyncMock()), \
             patch("app.services.agent_service.start_agent_run", AsyncMock()):

            # Call endpoint
            result = await submit_message(session_id, message_data, mock_db, mock_user)

        # Assertions (B2.1: user_message and run_id returned immediately)
        assert result.user_message.content == "Hello, Agent B!"
        assert result.user_message.role == "user"
        assert result.user_message.session_id == session_id

        # B2.1: run_id returned for tracking streamed response
        assert hasattr(result, 'run_id')
        assert result.run_id is not None

        # Verify database operations (B2.1: user message + run record stored)
        assert mock_db.add.call_count == 2  # User message + Run record
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_submit_message_session_not_found(self):
        """Test submitting message to non-existent session."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        # Mock session not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        message_data = MessageCreate(content="Hello")

        with pytest.raises(HTTPException) as exc_info:
            await submit_message("nonexistent", message_data, mock_db, mock_user)

        assert exc_info.value.status_code == 404
        assert "Session not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_submit_message_returns_run_id(self):
        """Test that submit message returns run_id for tracking streamed response."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock refresh to set datetime fields
        async def mock_refresh(obj):
            from datetime import timezone
            obj.created_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        session_id = "session_123"
        mock_session = Session(
            id=session_id,
            title="Test",
            mode="engineering",
            status="active",
            config=None,
        )
        from datetime import timezone
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

        # B2.1: run_id is a UUID string
        assert result.run_id is not None
        assert len(result.run_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_submit_message_database_error(self):
        """Test message submission with database error."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        # Mock session found
        session_id = "session_123"
        mock_session = Session(id=session_id, title="Test", mode="engineering", status="active", config=None)
        from datetime import timezone
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Database error on commit
        mock_db.commit.side_effect = Exception("Database error")
        mock_db.flush = AsyncMock()

        message_data = MessageCreate(content="Hello")

        # Mock B2.1 dependencies
        with patch("app.services.run_registry.has_active_run", AsyncMock(return_value=False)), \
             patch("app.services.run_registry.set_active_run", AsyncMock()), \
             patch("app.services.agent_service.start_agent_run", AsyncMock()):

            with pytest.raises(HTTPException) as exc_info:
                await submit_message(session_id, message_data, mock_db, mock_user)

        assert exc_info.value.status_code == 500
        assert "Failed to submit message" in exc_info.value.detail


class TestGetMessageHistory:
    """Tests for getting message history."""

    @pytest.mark.asyncio
    async def test_get_message_history_success(self):
        """Test successful message history retrieval."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}
        session_id = "session_123"

        # Mock session
        mock_session = Session(
            id=session_id,
            title="Test Session",
            mode="engineering",
            status="active",
            config=None,
        )
        from datetime import timezone
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        # Mock messages
        mock_messages = [
            Message(
                id="msg_1",
                session_id=session_id,
                role="user",
                content="Hello",
            ),
            Message(
                id="msg_2",
                session_id=session_id,
                role="assistant",
                content="[MOCK] Hello",
            ),
        ]

        from datetime import timezone
        now = datetime.now(timezone.utc)
        for msg in mock_messages:
            msg.created_at = now

        # Mock query execution - first for session, second for messages
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = mock_session

        message_result = MagicMock()
        message_result.scalars().all.return_value = mock_messages

        mock_db.execute = AsyncMock(side_effect=[session_result, message_result])

        # Call endpoint
        result = await get_message_history(session_id, mock_db, mock_user)

        # Assertions
        assert len(result) == 2
        assert result[0].role == "user"
        assert result[0].content == "Hello"
        assert result[1].role == "assistant"
        assert result[1].content == "[MOCK] Hello"

    @pytest.mark.asyncio
    async def test_get_message_history_session_not_found(self):
        """Test getting history for non-existent session."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_message_history("nonexistent", mock_db, mock_user)

        assert exc_info.value.status_code == 404
        assert "Session not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_message_history_empty(self):
        """Test getting empty message history."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}
        session_id = "session_123"

        # Mock session
        mock_session = Session(
            id=session_id,
            title="Test Session",
            mode="engineering",
            status="active",
            config=None,
        )
        from datetime import timezone
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = mock_session

        message_result = MagicMock()
        message_result.scalars().all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[session_result, message_result])

        result = await get_message_history(session_id, mock_db, mock_user)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_message_history_with_pagination(self):
        """Test getting message history with pagination."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}
        session_id = "session_123"

        mock_session = Session(
            id=session_id,
            title="Test",
            mode="engineering",
            status="active",
            config=None,
        )
        from datetime import timezone
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = mock_session

        message_result = MagicMock()
        message_result.scalars().all.return_value = []

        mock_db.execute = AsyncMock(side_effect=[session_result, message_result])

        result = await get_message_history(session_id, mock_db, mock_user, limit=10, offset=5)

        assert len(result) == 0
        # Verify execute was called twice (once for session, once for messages)
        assert mock_db.execute.await_count == 2


class TestStreamEvents:
    """Tests for SSE stream endpoint (B1.1 update).

    Note: More comprehensive SSE tests are in test_sse_streaming.py
    """

    @pytest.mark.asyncio
    async def test_stream_events_session_not_found(self):
        """Test streaming to non-existent session returns error event."""
        mock_db = AsyncMock(spec=AsyncSession)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        # B1.1: Returns StreamingResponse with error event instead of HTTP 404
        response = await stream_events("nonexistent", token=None, db_session=mock_db)

        from fastapi.responses import StreamingResponse
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"

    @pytest.mark.asyncio
    async def test_stream_events_returns_streaming_response(self):
        """Test that stream endpoint returns StreamingResponse."""
        mock_db = AsyncMock(spec=AsyncSession)
        session_id = "session_123"

        # Mock session
        mock_session = Session(
            id=session_id,
            title="Test",
            mode="engineering",
            status="active",
            config=None,
        )
        from datetime import timezone
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Call endpoint
        response = await stream_events(session_id, token=None, db_session=mock_db)

        # Verify response is a StreamingResponse
        from fastapi.responses import StreamingResponse
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"

    @pytest.mark.asyncio
    async def test_stream_events_headers(self):
        """Test the SSE endpoint returns correct headers."""
        mock_db = AsyncMock(spec=AsyncSession)
        session_id = "session_123"

        mock_session = Session(
            id=session_id,
            title="Test",
            mode="engineering",
            status="active",
            config=None,
        )
        from datetime import timezone
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await stream_events(session_id, token=None, db_session=mock_db)

        # Verify response headers
        assert "no-cache" in response.headers.get("cache-control", "")
        assert response.headers["connection"] == "keep-alive"


class TestMessageValidation:
    """Tests for message data validation."""

    def test_message_create_valid(self):
        """Test MessageCreate with valid content."""
        message = MessageCreate(content="Hello, world!")
        assert message.content == "Hello, world!"

    def test_message_create_empty_fails(self):
        """Test that empty content fails validation."""
        with pytest.raises(Exception):  # Pydantic validation error
            MessageCreate(content="")

    def test_message_create_with_special_characters(self):
        """Test MessageCreate with special characters."""
        content = "Hello! @#$%^&*() 你好"
        message = MessageCreate(content=content)
        assert message.content == content

    def test_message_create_with_newlines(self):
        """Test MessageCreate with newlines."""
        content = "Line 1\nLine 2\nLine 3"
        message = MessageCreate(content=content)
        assert message.content == content


class TestMockAgentBehavior:
    """Tests for agent behavior (B2.1 update - LangGraph streaming).

    Note: Agent response is now streamed via SSE, not returned immediately.
    These tests verify the user message is stored correctly.
    """

    @pytest.mark.asyncio
    async def test_multiple_messages_store_correctly(self):
        """Test that multiple user messages are stored correctly."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock refresh to set datetime fields
        async def mock_refresh(obj):
            from datetime import timezone
            obj.created_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        session_id = "session_123"
        mock_session = Session(
            id=session_id,
            title="Test",
            mode="engineering",
            status="active",
            config=None,
        )
        from datetime import timezone
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        test_messages = [
            "Hello",
            "How are you?",
            "What is 2+2?",
            "Tell me a joke",
        ]

        # Mock B2.1 dependencies
        with patch("app.services.run_registry.has_active_run", AsyncMock(return_value=False)), \
             patch("app.services.run_registry.set_active_run", AsyncMock()), \
             patch("app.services.agent_service.start_agent_run", AsyncMock()):

            for test_msg in test_messages:
                message_data = MessageCreate(content=test_msg)
                result = await submit_message(session_id, message_data, mock_db, mock_user)

                # Verify user message stored correctly
                assert result.user_message.content == test_msg
                assert result.user_message.role == "user"

    @pytest.mark.asyncio
    async def test_submit_stores_user_message(self):
        """Test that user message is stored in database immediately."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        # Mock refresh to set datetime fields
        async def mock_refresh(obj):
            from datetime import timezone
            obj.created_at = datetime.now(timezone.utc)

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        session_id = "session_123"
        mock_session = Session(
            id=session_id,
            title="Test",
            mode="engineering",
            status="active",
            config=None,
        )
        from datetime import timezone
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        message_data = MessageCreate(content="Test")

        # Mock B2.1 dependencies
        with patch("app.services.run_registry.has_active_run", AsyncMock(return_value=False)), \
             patch("app.services.run_registry.set_active_run", AsyncMock()), \
             patch("app.services.agent_service.start_agent_run", AsyncMock()):

            result = await submit_message(session_id, message_data, mock_db, mock_user)

        # B2.1: User message + Run record stored immediately (assistant via SSE)
        assert mock_db.add.call_count == 2  # User message + Run record
        assert result.user_message.role == "user"
        assert result.user_message.content == "Test"
