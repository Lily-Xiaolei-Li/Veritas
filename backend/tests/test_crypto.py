"""
Tests for cryptography utilities (B0.0.4).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings
from app.crypto import (
    EncryptionError,
    decrypt_value,
    encrypt_value,
    hash_password,
    verify_password,
)


@pytest.fixture
def mock_settings():
    """Mock settings with encryption key."""
    settings = MagicMock(spec=Settings)
    settings.encryption_key = "test_encryption_key_at_least_32_chars_long"
    return settings


def test_encrypt_decrypt_roundtrip(mock_settings):
    """Test that encryption and decryption work correctly."""
    with patch("app.crypto.get_settings", return_value=mock_settings):
        plaintext = "my_secret_api_key"

        # Encrypt
        encrypted = encrypt_value(plaintext)

        # Should be different from plaintext
        assert encrypted != plaintext

        # Decrypt
        decrypted = decrypt_value(encrypted)

        # Should match original
        assert decrypted == plaintext


def test_encrypt_empty_value_raises_error(mock_settings):
    """Test that encrypting empty value raises error."""
    with patch("app.crypto.get_settings", return_value=mock_settings):
        with pytest.raises(EncryptionError, match="Cannot encrypt empty value"):
            encrypt_value("")


def test_decrypt_empty_value_raises_error(mock_settings):
    """Test that decrypting empty value raises error."""
    with patch("app.crypto.get_settings", return_value=mock_settings):
        with pytest.raises(EncryptionError, match="Cannot decrypt empty value"):
            decrypt_value("")


def test_decrypt_invalid_token_raises_error(mock_settings):
    """Test that decrypting invalid token raises error."""
    with patch("app.crypto.get_settings", return_value=mock_settings):
        with pytest.raises(EncryptionError, match="Decryption failed"):
            decrypt_value("invalid_base64_token")


def test_encrypt_without_key_raises_error():
    """Test that encryption without configured key raises error."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.encryption_key = None

    with patch("app.crypto.get_settings", return_value=mock_settings):
        with pytest.raises(EncryptionError, match="ENCRYPTION_KEY not configured"):
            encrypt_value("test")


def test_decrypt_with_wrong_key_raises_error():
    """Test that decryption with wrong key raises error."""
    # Encrypt with one key
    settings1 = MagicMock(spec=Settings)
    settings1.encryption_key = "key_one_32_characters_long_yes"

    with patch("app.crypto.get_settings", return_value=settings1):
        encrypted = encrypt_value("secret")

    # Try to decrypt with different key
    settings2 = MagicMock(spec=Settings)
    settings2.encryption_key = "key_two_32_characters_long_yes"

    with patch("app.crypto.get_settings", return_value=settings2):
        with pytest.raises(EncryptionError, match="Invalid token or wrong encryption key"):
            decrypt_value(encrypted)


def test_hash_password():
    """Test password hashing."""
    password = "my_secure_password"

    hashed = hash_password(password)

    # Hash should be different from password
    assert hashed != password

    # Hash should have bcrypt format
    assert hashed.startswith("$2b$")


def test_hash_empty_password_raises_error():
    """Test that hashing empty password raises error."""
    with pytest.raises(ValueError, match="Password cannot be empty"):
        hash_password("")


def test_verify_password_correct():
    """Test password verification with correct password."""
    password = "my_secure_password"
    hashed = hash_password(password)

    # Correct password should verify
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test password verification with incorrect password."""
    password = "my_secure_password"
    hashed = hash_password(password)

    # Incorrect password should not verify
    assert verify_password("wrong_password", hashed) is False


def test_verify_password_empty_returns_false():
    """Test that verifying empty password returns False."""
    assert verify_password("", "hash") is False
    assert verify_password("password", "") is False


def test_verify_password_invalid_hash_returns_false():
    """Test that verifying with invalid hash returns False."""
    assert verify_password("password", "not_a_valid_bcrypt_hash") is False
