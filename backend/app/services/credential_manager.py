"""
Credential manager for LLM providers (B2.0).

Retrieves and decrypts API keys from the database.
Selects the most recent active key for each provider.

B2.2: Falls back to environment variables for quick testing.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import EncryptionError, decrypt_value
from app.llm.exceptions import LLMAuthenticationError
from app.logging_config import get_logger
from app.models import APIKey

logger = get_logger("llm.credentials")


# Environment variable names for each provider (fallback for testing)
ENV_VAR_NAMES = {
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ollama": "OLLAMA_API_KEY",
}


async def get_api_key_for_provider(
    provider: str,
    db_session: AsyncSession,
) -> Optional[str]:
    """
    Retrieve and decrypt the most recent active API key for a provider.

    Priority (B2.2 - env var first for dev convenience):
    1. Environment variable (for testing/development)
    2. Database (encrypted api_keys table)

    Args:
        provider: Provider name (e.g., "gemini", "openrouter")
        db_session: Database session

    Returns:
        Decrypted API key string, or None if no key found

    Raises:
        LLMAuthenticationError: If decryption fails (key may be corrupted)
    """
    # B2.2: Check environment variable FIRST for dev convenience
    env_var = ENV_VAR_NAMES.get(provider)
    if env_var:
        env_key = os.getenv(env_var)
        if env_key:
            logger.debug(
                f"Using API key from environment variable: {env_var}",
                extra={"extra_fields": {"provider": provider}},
            )
            return env_key

    # Query for most recent active key in database
    result = await db_session.execute(
        select(APIKey)
        .where(APIKey.provider == provider)
        .where(APIKey.is_active == True)
        .order_by(APIKey.created_at.desc())
        .limit(1)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        logger.debug(f"No active API key for provider: {provider}")
        return None

    # Update last_used_at
    api_key.last_used_at = datetime.now(timezone.utc)
    await db_session.commit()

    # Decrypt - treat failure as auth error (don't retry with bad key)
    try:
        decrypted = decrypt_value(api_key.encrypted_key)
        logger.debug(
            f"Retrieved API key for provider: {provider}",
            extra={
                "extra_fields": {
                    "provider": provider,
                    "key_id": api_key.id,
                    # NEVER log the key itself
                }
            },
        )
        return decrypted
    except EncryptionError as e:
        logger.error(
            f"Failed to decrypt API key for {provider}",
            extra={
                "extra_fields": {
                    "provider": provider,
                    "key_id": api_key.id,
                    "error": str(e),
                }
            },
        )
        raise LLMAuthenticationError(
            f"Failed to decrypt API key for {provider}. "
            f"Key may be corrupted or encryption key changed.",
            provider=provider,
        )
