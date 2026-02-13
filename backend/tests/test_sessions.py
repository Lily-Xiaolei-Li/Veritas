"""
Tests for session management API (B0.3).
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.routes.session_routes import (
    create_session,
    list_sessions,
    get_session_details,
    delete_session,
    SessionCreate,
)
from app.models import Session


class TestCreateSession:
    """Tests for creating sessions."""

    @pytest.mark.asyncio
    async def test_create_session_success(self):
        """Test successful session creation."""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()

        # Mock refresh to set datetime fields
        async def mock_refresh(obj):
            obj.created_at = datetime.now()
            obj.updated_at = datetime.now()
            obj.ended_at = None

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        # Mock current user
        mock_user = {"user_id": "user_123", "username": "testuser"}

        # Prepare session data
        session_data = SessionCreate(
            title="Test Session",
            mode="engineering",
            config={"key": "value"},
        )

        # Call endpoint
        result = await create_session(session_data, mock_db, mock_user)

        # Assertions
        assert result.title == "Test Session"
        assert result.mode == "engineering"
        assert result.status == "active"
        assert result.config == {"key": "value"}
        assert result.id is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_session_minimal_data(self):
        """Test creating session with minimal data."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit = AsyncMock()

        # Mock refresh to set datetime fields
        async def mock_refresh(obj):
            obj.created_at = datetime.now()
            obj.updated_at = datetime.now()
            obj.ended_at = None

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        session_data = SessionCreate(mode="creative")

        result = await create_session(session_data, mock_db, mock_user)

        assert result.title is None
        assert result.mode == "creative"
        assert result.status == "active"
        assert result.config is None

    @pytest.mark.asyncio
    async def test_create_session_database_error(self):
        """Test session creation with database error."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.commit.side_effect = Exception("Database error")
        mock_user = {"user_id": "user_123", "username": "testuser"}

        session_data = SessionCreate(mode="engineering")

        with pytest.raises(HTTPException) as exc_info:
            await create_session(session_data, mock_db, mock_user)

        assert exc_info.value.status_code == 500
        assert "Failed to create session" in exc_info.value.detail


class TestListSessions:
    """Tests for listing sessions."""

    @pytest.mark.asyncio
    async def test_list_sessions_success(self):
        """Test successful session listing."""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        # Mock sessions
        mock_sessions = [
            Session(
                id="session_1",
                title="Session 1",
                mode="engineering",
                status="active",
                config=None,
            ),
            Session(
                id="session_2",
                title="Session 2",
                mode="creative",
                status="active",
                config={"test": "data"},
            ),
        ]

        # Set datetime attributes
        from datetime import timezone
        now = datetime.now(timezone.utc)
        for s in mock_sessions:
            s.created_at = now
            s.updated_at = now
            s.ended_at = None

        # Mock query execution
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = mock_sessions
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Call endpoint
        result = await list_sessions(mock_db, mock_user)

        # Assertions
        assert len(result) == 2
        assert result[0].id == "session_1"
        assert result[0].title == "Session 1"
        assert result[1].id == "session_2"
        assert result[1].config == {"test": "data"}

    @pytest.mark.asyncio
    async def test_list_sessions_with_status_filter(self):
        """Test listing sessions with status filter."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        mock_sessions = [
            Session(
                id="session_1",
                title="Active Session",
                mode="engineering",
                status="active",
                config=None,
            ),
        ]

        from datetime import timezone
        now = datetime.now(timezone.utc)
        for s in mock_sessions:
            s.created_at = now
            s.updated_at = now
            s.ended_at = None

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = mock_sessions
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_sessions(mock_db, mock_user, status_filter="active")

        assert len(result) == 1
        assert result[0].status == "active"

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self):
        """Test listing sessions when none exist."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_sessions(mock_db, mock_user)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_list_sessions_with_pagination(self):
        """Test listing sessions with pagination."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_sessions(mock_db, mock_user, limit=10, offset=20)

        assert len(result) == 0
        mock_db.execute.assert_awaited_once()


class TestGetSessionDetails:
    """Tests for getting session details."""

    @pytest.mark.asyncio
    async def test_get_session_success(self):
        """Test successful session retrieval."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}
        session_id = "session_123"

        mock_session = Session(
            id=session_id,
            title="Test Session",
            mode="engineering",
            status="active",
            config={"key": "value"},
        )
        from datetime import timezone
        mock_session.created_at = datetime.now(timezone.utc)
        mock_session.updated_at = datetime.now(timezone.utc)
        mock_session.ended_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_session_details(session_id, mock_db, mock_user)

        assert result.id == session_id
        assert result.title == "Test Session"
        assert result.mode == "engineering"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self):
        """Test getting non-existent session."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_session_details("nonexistent", mock_db, mock_user)

        assert exc_info.value.status_code == 404
        assert "Session not found" in exc_info.value.detail


class TestDeleteSession:
    """Tests for deleting sessions."""

    @pytest.mark.asyncio
    async def test_delete_session_success(self):
        """Test successful session deletion."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}
        session_id = "session_123"

        mock_session = Session(
            id=session_id,
            title="Test Session",
            mode="engineering",
            status="active",
            config=None,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        result = await delete_session(session_id, mock_db, mock_user)

        assert result is None
        mock_db.delete.assert_awaited_once_with(mock_session)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self):
        """Test deleting non-existent session."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await delete_session("nonexistent", mock_db, mock_user)

        assert exc_info.value.status_code == 404
        assert "Session not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_session_database_error(self):
        """Test session deletion with database error."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = {"user_id": "user_123", "username": "testuser"}
        session_id = "session_123"

        mock_session = Session(
            id=session_id,
            title="Test Session",
            mode="engineering",
            status="active",
            config=None,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_session
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit.side_effect = Exception("Database error")

        with pytest.raises(HTTPException) as exc_info:
            await delete_session(session_id, mock_db, mock_user)

        assert exc_info.value.status_code == 500
        assert "Failed to delete session" in exc_info.value.detail


class TestSessionValidation:
    """Tests for session data validation."""

    def test_session_create_valid_modes(self):
        """Test SessionCreate with valid modes."""
        modes = ["engineering", "creative", "conservative"]
        for mode in modes:
            session_data = SessionCreate(mode=mode)
            assert session_data.mode == mode

    def test_session_create_with_title(self):
        """Test SessionCreate with title."""
        session_data = SessionCreate(title="My Session", mode="engineering")
        assert session_data.title == "My Session"

    def test_session_create_with_config(self):
        """Test SessionCreate with config."""
        config = {"setting1": "value1", "setting2": 123}
        session_data = SessionCreate(mode="engineering", config=config)
        assert session_data.config == config

    def test_session_create_defaults(self):
        """Test SessionCreate default values."""
        session_data = SessionCreate()
        assert session_data.mode == "engineering"
        assert session_data.title is None
        assert session_data.config is None
