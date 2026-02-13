"""
Tests for authentication utilities (B0.0.4).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest

from app.auth import (
    AuthenticationError,
    TokenExpiredError,
    TokenInvalidError,
    extract_token_from_header,
    generate_session_token,
    get_current_user_id_from_token,
    validate_session_token,
)
from app.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings with session secret."""
    settings = MagicMock(spec=Settings)
    settings.session_secret_key = "test_secret_key_at_least_32_chars_long"
    settings.session_expire_hours = 24
    return settings


def test_generate_session_token(mock_settings):
    """Test session token generation."""
    with patch("app.auth.get_settings", return_value=mock_settings):
        token = generate_session_token("user123", "testuser")

        # Token should be a string
        assert isinstance(token, str)

        # Token should be decodable
        payload = jwt.decode(
            token,
            mock_settings.session_secret_key,
            algorithms=["HS256"]
        )

        # Check payload contents
        assert payload["user_id"] == "user123"
        assert payload["username"] == "testuser"
        assert payload["type"] == "session"
        assert "exp" in payload
        assert "iat" in payload


def test_generate_token_without_secret_raises_error():
    """Test that generating token without secret raises error."""
    settings = MagicMock(spec=Settings)
    settings.session_secret_key = None

    with patch("app.auth.get_settings", return_value=settings):
        with pytest.raises(AuthenticationError, match="SESSION_SECRET_KEY not configured"):
            generate_session_token("user123", "testuser")


def test_validate_session_token(mock_settings):
    """Test session token validation."""
    with patch("app.auth.get_settings", return_value=mock_settings):
        # Generate token
        token = generate_session_token("user123", "testuser")

        # Validate token
        payload = validate_session_token(token)

        # Check payload
        assert payload["user_id"] == "user123"
        assert payload["username"] == "testuser"


def test_validate_expired_token_raises_error(mock_settings):
    """Test that expired token raises TokenExpiredError."""
    with patch("app.auth.get_settings", return_value=mock_settings):
        # Generate expired token
        now = datetime.now(timezone.utc)
        expired_payload = {
            "user_id": "user123",
            "username": "testuser",
            "iat": now - timedelta(hours=25),
            "exp": now - timedelta(hours=1),
            "type": "session",
        }
        expired_token = jwt.encode(
            expired_payload,
            mock_settings.session_secret_key,
            algorithm="HS256"
        )

        # Should raise TokenExpiredError
        with pytest.raises(TokenExpiredError, match="Token has expired"):
            validate_session_token(expired_token)


def test_validate_invalid_token_raises_error(mock_settings):
    """Test that invalid token raises TokenInvalidError."""
    with patch("app.auth.get_settings", return_value=mock_settings):
        with pytest.raises(TokenInvalidError, match="Invalid token"):
            validate_session_token("not_a_valid_jwt_token")


def test_validate_token_with_wrong_secret_raises_error(mock_settings):
    """Test that token signed with wrong secret raises error."""
    # Generate token with one secret
    token = jwt.encode(
        {"user_id": "user123", "type": "session"},
        "wrong_secret_key",
        algorithm="HS256"
    )

    # Try to validate with different secret
    with patch("app.auth.get_settings", return_value=mock_settings):
        with pytest.raises(TokenInvalidError):
            validate_session_token(token)


def test_validate_token_wrong_type_raises_error(mock_settings):
    """Test that token with wrong type raises error."""
    # Generate token with wrong type
    payload = {
        "user_id": "user123",
        "type": "refresh",  # Wrong type
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(
        payload,
        mock_settings.session_secret_key,
        algorithm="HS256"
    )

    with patch("app.auth.get_settings", return_value=mock_settings):
        with pytest.raises(TokenInvalidError, match="Invalid token type"):
            validate_session_token(token)


def test_extract_token_from_header():
    """Test extracting token from Authorization header."""
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"

    # Valid Bearer token
    assert extract_token_from_header(f"Bearer {token}") == token

    # Case insensitive
    assert extract_token_from_header(f"bearer {token}") == token


def test_extract_token_from_invalid_header_returns_none():
    """Test that invalid Authorization header returns None."""
    assert extract_token_from_header(None) is None
    assert extract_token_from_header("") is None
    assert extract_token_from_header("NoBearer token") is None
    assert extract_token_from_header("Bearer") is None  # Missing token


def test_get_current_user_id_from_token(mock_settings):
    """Test extracting user ID from token."""
    with patch("app.auth.get_settings", return_value=mock_settings):
        token = generate_session_token("user123", "testuser")

        user_id = get_current_user_id_from_token(token)

        assert user_id == "user123"


def test_get_user_id_from_token_without_user_id_raises_error(mock_settings):
    """Test that token without user_id raises error."""
    # Generate token without user_id
    payload = {
        "username": "testuser",
        "type": "session",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(
        payload,
        mock_settings.session_secret_key,
        algorithm="HS256"
    )

    with patch("app.auth.get_settings", return_value=mock_settings):
        with pytest.raises(TokenInvalidError, match="Token missing user_id"):
            get_current_user_id_from_token(token)
