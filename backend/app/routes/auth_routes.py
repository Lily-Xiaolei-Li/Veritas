"""
Authentication and API key management routes (B0.0.4).
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    TokenExpiredError,
    TokenInvalidError,
    extract_token_from_header,
    generate_session_token,
    validate_session_token,
)
from app.config import get_settings
from app.crypto import EncryptionError, encrypt_value, hash_password, verify_password
from app.database import get_session
from app.logging_config import get_logger
from app.models import APIKey, User

router = APIRouter()
logger = get_logger("auth")


# Request/Response Models

class APIKeyCreate(BaseModel):
    """Request model for creating an API key."""
    name: str = Field(..., min_length=1, max_length=255, description="Friendly name for the API key")
    provider: str = Field(..., min_length=1, max_length=50, description="Provider name (e.g., gemini, openai)")
    key: str = Field(..., min_length=1, description="The API key value")


class APIKeyResponse(BaseModel):
    """Response model for API key (without the actual key value)."""
    id: str
    name: str
    provider: str
    created_at: datetime
    last_used_at: Optional[datetime]
    is_active: bool


class LoginRequest(BaseModel):
    """Request model for user login."""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Response model for login."""
    token: str
    user_id: str
    username: str
    expires_in_hours: int


# Dependency: Get current user from token (only if auth enabled)
async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    settings = Depends(lambda: get_settings())
) -> Optional[dict]:
    """
    Extract current user from authorization header if auth is enabled.

    Returns:
        dict or None: User payload if authenticated, None if auth disabled or no token
    """
    # If auth is not enabled, skip authentication
    if not settings.auth_enabled:
        return None

    # Extract token from header
    token = extract_token_from_header(authorization)
    if not token:
        return None

    try:
        payload = validate_session_token(token)
        return payload
    except (TokenExpiredError, TokenInvalidError):
        return None


async def require_auth(
    authorization: Optional[str] = Header(None),
    settings = Depends(lambda: get_settings())
) -> dict:
    """
    Require authentication. Raises 401 if auth is enabled and token is missing/invalid.

    Returns:
        dict: User payload from token

    Raises:
        HTTPException: 401 if authentication fails
    """
    # If auth is not enabled, return a placeholder user
    if not settings.auth_enabled:
        return {"user_id": "system", "username": "system"}

    # Extract token
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token
    try:
        payload = validate_session_token(token)
        return payload
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


# API Key Management Endpoints

@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Create a new encrypted API key.

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        # Encrypt the API key
        encrypted_key = encrypt_value(key_data.key)

        # Create database record
        api_key = APIKey(
            id=str(uuid4()),
            name=key_data.name,
            provider=key_data.provider,
            encrypted_key=encrypted_key,
            is_active=True,
        )

        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)

        logger.info(
            f"API key created: {api_key.id} for provider {api_key.provider}",
            extra={"api_key_id": api_key.id, "provider": api_key.provider}
        )

        return APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            provider=api_key.provider,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            is_active=api_key.is_active,
        )

    except EncryptionError as e:
        logger.error(f"Encryption failed for API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to encrypt API key"
        )
    except Exception as e:
        logger.error(f"Failed to create API key: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
    provider: Optional[str] = None,
    active_only: bool = True,
):
    """
    List all stored API keys (metadata only, not the actual keys).

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        # Build query
        query = select(APIKey)

        if provider:
            query = query.where(APIKey.provider == provider)

        if active_only:
            query = query.where(APIKey.is_active == True)

        query = query.order_by(APIKey.created_at.desc())

        # Execute query
        result = await session.execute(query)
        api_keys = result.scalars().all()

        return [
            APIKeyResponse(
                id=key.id,
                name=key.name,
                provider=key.provider,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
                is_active=key.is_active,
            )
            for key in api_keys
        ]

    except Exception as e:
        logger.error(f"Failed to list API keys: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Delete an API key.

    Requires authentication if AUTH_ENABLED=true.
    """
    try:
        # Find the key
        result = await session.execute(
            select(APIKey).where(APIKey.id == key_id)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Delete the key
        await session.delete(api_key)
        await session.commit()

        logger.info(
            f"API key deleted: {key_id}",
            extra={"api_key_id": key_id}
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete API key: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API key"
        )


# Authentication Endpoints (for password-based auth)

@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
):
    """
    Authenticate a user and return a session token.

    Only available if AUTH_ENABLED=true.
    Returns 404 immediately if auth is disabled (no database needed).
    """
    settings = get_settings()

    # Check auth enabled FIRST, before any database access
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authentication not enabled"
        )
    
    # Only get database session if auth is enabled
    from app.database import get_database
    db = get_database()
    async with db.session() as session:
        try:
            # If no users exist yet, bootstrap a default admin account.
            # This is for local-first setup convenience.
            # NOTE: This does not bypass AUTH_ENABLED; that is still controlled by settings.
            if credentials.username == "admin" and credentials.password == "admin":
                existing = await session.execute(select(User.id).limit(1))
                any_user = existing.scalar_one_or_none()
                if not any_user:
                    user = User(
                        id=str(uuid4()),
                        username="admin",
                        password_hash=hash_password("admin"),
                        is_active=True,
                    )
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
                    logger.warning(
                        "Bootstrapped default admin user (admin/admin). Change this password.",
                        extra={"user_id": user.id, "username": user.username},
                    )

            # Find user
            result = await session.execute(
                select(User).where(User.username == credentials.username)
            )
            user = result.scalar_one_or_none()

            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password"
                )

            # Verify password
            if not verify_password(credentials.password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password"
                )

            # Update last login
            user.last_login_at = datetime.now(timezone.utc)
            await session.commit()

            # Generate token
            token = generate_session_token(user.id, user.username)

            logger.info(
                f"User logged in: {user.username}",
                extra={"user_id": user.id, "username": user.username}
            )

            return LoginResponse(
                token=token,
                user_id=user.id,
                username=user.username,
                expires_in_hours=settings.session_expire_hours,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed"
            )
