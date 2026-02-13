"""
Security utilities for LLM Provider Abstraction (B2.0).

This module provides structural protection against accidental
logging of sensitive values like API keys.
"""

from typing import Any


class SecretStr:
    """
    Wrapper for sensitive strings that prevents accidental logging.

    The secret value is never exposed in repr() or str(), only via
    get_secret_value() which must be called explicitly.

    Usage:
        key = SecretStr("sk-actual-key")
        print(key)  # Output: SecretStr('***')
        key.get_secret_value()  # Returns "sk-actual-key"
    """

    __slots__ = ("_secret_value",)

    def __init__(self, value: str):
        self._secret_value = value

    def get_secret_value(self) -> str:
        """Return the actual secret value. Use sparingly."""
        return self._secret_value

    def __repr__(self) -> str:
        return "SecretStr('***')"

    def __str__(self) -> str:
        return "***"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SecretStr):
            return self._secret_value == other._secret_value
        return False

    def __hash__(self) -> int:
        return hash(self._secret_value)

    def __bool__(self) -> bool:
        return bool(self._secret_value)

    def __len__(self) -> int:
        return len(self._secret_value)


def redact_headers(headers: dict) -> dict:
    """
    Return a copy of headers with sensitive values redacted.

    IMPORTANT: NEVER log raw headers from HTTP clients. Always use
    this function first.

    Args:
        headers: Dictionary of HTTP headers

    Returns:
        Copy of headers with sensitive values replaced by '***REDACTED***'
    """
    sensitive_keys = {
        "authorization",
        "x-api-key",
        "api-key",
        "bearer",
        "x-auth-token",
        "cookie",
        "set-cookie",
    }
    return {
        k: "***REDACTED***" if k.lower() in sensitive_keys else v
        for k, v in headers.items()
    }
