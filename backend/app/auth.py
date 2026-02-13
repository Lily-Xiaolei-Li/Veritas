"""
Authentication and authorization utilities for Agent B.

Provides JWT session token generation and validation,
user authentication, and authorization helpers.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app.config import get_settings


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired."""
    pass


class TokenInvalidError(AuthenticationError):
    """Raised when a token is invalid or malformed."""
    pass


def generate_session_token(user_id: str, username: str) -> str:
    """
    Generate a JWT session token for a user.

    Args:
        user_id: Unique user identifier
        username: Username

    Returns:
        str: JWT token string

    Raises:
        AuthenticationError: If token generation fails
    """
    settings = get_settings()

    if not settings.session_secret_key:
        raise AuthenticationError(
            "SESSION_SECRET_KEY not configured. Required for authentication."
        )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=settings.session_expire_hours)

    payload = {
        "user_id": user_id,
        "username": username,
        "iat": now,
        "exp": expires_at,
        "type": "session",
    }

    try:
        token = jwt.encode(
            payload,
            settings.session_secret_key,
            algorithm="HS256"
        )
        return token
    except Exception as e:
        raise AuthenticationError(f"Failed to generate token: {e}") from e


def validate_session_token(token: str) -> dict:
    """
    Validate a JWT session token and return its payload.

    Args:
        token: JWT token string

    Returns:
        dict: Token payload containing user_id, username, etc.

    Raises:
        TokenExpiredError: If token has expired
        TokenInvalidError: If token is invalid or malformed
    """
    settings = get_settings()

    if not settings.session_secret_key:
        raise AuthenticationError(
            "SESSION_SECRET_KEY not configured. Required for authentication."
        )

    try:
        payload = jwt.decode(
            token,
            settings.session_secret_key,
            algorithms=["HS256"]
        )

        # Verify token type
        if payload.get("type") != "session":
            raise TokenInvalidError("Invalid token type")

        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise TokenInvalidError(f"Invalid token: {e}") from e
    except Exception as e:
        raise TokenInvalidError(f"Token validation failed: {e}") from e


def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Supports "Bearer <token>" format.

    Args:
        authorization: Authorization header value

    Returns:
        str or None: Extracted token, or None if not found
    """
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def get_current_user_id_from_token(token: str) -> str:
    """
    Extract user ID from a validated token.

    Args:
        token: JWT token string

    Returns:
        str: User ID

    Raises:
        AuthenticationError: If token is invalid
    """
    payload = validate_session_token(token)
    user_id = payload.get("user_id")

    if not user_id:
        raise TokenInvalidError("Token missing user_id")

    return user_id
