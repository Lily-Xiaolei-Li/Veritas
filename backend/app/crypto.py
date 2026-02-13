"""
Cryptography utilities for Agent B.

Provides encryption/decryption for sensitive data like API keys stored at rest.
Uses Fernet (symmetric encryption) with a configurable encryption key.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""
    pass


def _get_fernet() -> Fernet:
    """
    Get a Fernet instance using the configured encryption key.

    Returns:
        Fernet: Configured encryption instance

    Raises:
        EncryptionError: If encryption key is not configured
    """
    settings = get_settings()

    if not settings.encryption_key:
        raise EncryptionError(
            "ENCRYPTION_KEY not configured. Set it in environment variables. "
            "Generate with: openssl rand -hex 32"
        )

    # Derive a Fernet-compatible key from the encryption key
    # Fernet requires a 32-byte base64-encoded key
    key_bytes = hashlib.sha256(settings.encryption_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)

    return Fernet(fernet_key)


def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a plaintext value for storage.

    Args:
        plaintext: The value to encrypt

    Returns:
        str: Base64-encoded encrypted value

    Raises:
        EncryptionError: If encryption fails
    """
    if not plaintext:
        raise EncryptionError("Cannot encrypt empty value")

    try:
        fernet = _get_fernet()
        encrypted_bytes = fernet.encrypt(plaintext.encode())
        return encrypted_bytes.decode()
    except Exception as e:
        raise EncryptionError(f"Encryption failed: {e}") from e


def decrypt_value(encrypted: str) -> str:
    """
    Decrypt an encrypted value.

    Args:
        encrypted: Base64-encoded encrypted value

    Returns:
        str: Decrypted plaintext value

    Raises:
        EncryptionError: If decryption fails or value is invalid
    """
    if not encrypted:
        raise EncryptionError("Cannot decrypt empty value")

    try:
        fernet = _get_fernet()
        decrypted_bytes = fernet.decrypt(encrypted.encode())
        return decrypted_bytes.decode()
    except InvalidToken:
        raise EncryptionError(
            "Decryption failed: Invalid token or wrong encryption key"
        )
    except Exception as e:
        raise EncryptionError(f"Decryption failed: {e}") from e


def hash_password(password: str) -> str:
    """
    Hash a password for storage.

    Uses bcrypt for secure password hashing.

    Args:
        password: Plaintext password

    Returns:
        str: Hashed password
    """
    import bcrypt

    if not password:
        raise ValueError("Password cannot be empty")

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against a stored hash.

    Args:
        password: Plaintext password to verify
        hashed: Stored password hash

    Returns:
        bool: True if password matches, False otherwise
    """
    import bcrypt

    if not password or not hashed:
        return False

    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False
