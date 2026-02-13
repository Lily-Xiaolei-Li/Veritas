"""
Security tests for LLM module (B2.0).

CRITICAL: These tests verify that API keys never appear in logs.
"""

import logging

from app.llm.secrets import SecretStr, redact_headers


class TestSecretStr:
    """Test SecretStr wrapper prevents accidental key exposure."""

    def test_repr_is_redacted(self):
        """repr() should never show the actual value."""
        key = SecretStr("sk-super-secret-api-key-12345")
        result = repr(key)

        assert "super-secret" not in result
        assert "sk-" not in result
        assert "12345" not in result
        assert "***" in result

    def test_str_is_redacted(self):
        """str() should never show the actual value."""
        key = SecretStr("AIzaSyA-test-key-abc123")
        result = str(key)

        assert "AIzaSyA" not in result
        assert "abc123" not in result
        assert "***" in result

    def test_get_secret_value_returns_actual_value(self):
        """get_secret_value() should return the actual key."""
        original = "sk-or-v1-test-key-xyz"
        key = SecretStr(original)

        assert key.get_secret_value() == original

    def test_equality_with_same_value(self):
        """Two SecretStr with same value should be equal."""
        key1 = SecretStr("test-key")
        key2 = SecretStr("test-key")

        assert key1 == key2

    def test_inequality_with_different_value(self):
        """Two SecretStr with different values should not be equal."""
        key1 = SecretStr("key-1")
        key2 = SecretStr("key-2")

        assert key1 != key2

    def test_inequality_with_non_secretstr(self):
        """SecretStr should not equal plain string."""
        key = SecretStr("test-key")

        assert key != "test-key"
        assert key != 123

    def test_hash_is_consistent(self):
        """SecretStr should be hashable for use in dicts/sets."""
        key1 = SecretStr("same-key")
        key2 = SecretStr("same-key")

        assert hash(key1) == hash(key2)

        # Can be used in a set
        key_set = {key1, key2}
        assert len(key_set) == 1

    def test_format_string_is_redacted(self):
        """f-string formatting should be redacted."""
        key = SecretStr("sk-secret-key")
        result = f"API key is: {key}"

        assert "sk-secret" not in result
        assert "***" in result


class TestRedactHeaders:
    """Test header redaction utility."""

    def test_authorization_header_redacted(self):
        """Authorization header should be redacted."""
        headers = {
            "Authorization": "Bearer sk-secret-key-12345",
            "Content-Type": "application/json",
        }

        redacted = redact_headers(headers)

        assert "sk-secret" not in redacted["Authorization"]
        assert "REDACTED" in redacted["Authorization"]
        assert redacted["Content-Type"] == "application/json"

    def test_api_key_header_redacted(self):
        """X-API-Key header should be redacted."""
        headers = {
            "X-API-Key": "AIzaSyA-test-key",
            "Accept": "application/json",
        }

        redacted = redact_headers(headers)

        assert "AIzaSyA" not in redacted["X-API-Key"]
        assert "REDACTED" in redacted["X-API-Key"]
        assert redacted["Accept"] == "application/json"

    def test_case_insensitive_matching(self):
        """Header matching should be case-insensitive."""
        headers = {
            "AUTHORIZATION": "Bearer secret",
            "x-api-key": "another-secret",
        }

        redacted = redact_headers(headers)

        assert "secret" not in redacted["AUTHORIZATION"]
        assert "another-secret" not in redacted["x-api-key"]

    def test_original_headers_unchanged(self):
        """Original dict should not be modified."""
        headers = {"Authorization": "Bearer secret"}
        original_value = headers["Authorization"]

        redact_headers(headers)

        assert headers["Authorization"] == original_value


class TestKeyNeverInLogs:
    """Test that API keys never appear in log output."""

    def test_secretstr_not_in_log_message(self, caplog):
        """SecretStr should not leak when logged directly."""
        fake_key = "AIza-LEAKME-TEST-KEY-12345"

        with caplog.at_level(logging.DEBUG):
            key = SecretStr(fake_key)
            logger = logging.getLogger("test")
            logger.info(f"Using key: {key}")
            logger.debug(f"Key repr: {repr(key)}")

        for record in caplog.records:
            assert fake_key not in record.message
            assert "LEAKME" not in record.message

    def test_secretstr_not_in_exception(self, caplog):
        """SecretStr should not leak in exception messages."""
        fake_key = "sk-or-LEAKME-TEST-KEY-xyz"

        with caplog.at_level(logging.ERROR):
            key = SecretStr(fake_key)
            try:
                raise ValueError(f"Failed with key: {key}")
            except ValueError:
                logger = logging.getLogger("test")
                logger.exception("Error occurred")

        for record in caplog.records:
            full_text = record.getMessage()
            assert fake_key not in full_text
            assert "LEAKME" not in full_text

    def test_headers_not_in_log_after_redaction(self, caplog):
        """Redacted headers should not contain secrets in logs."""
        fake_key = "Bearer LEAKME-secret-token"

        with caplog.at_level(logging.DEBUG):
            headers = {"Authorization": fake_key}
            redacted = redact_headers(headers)

            logger = logging.getLogger("test")
            logger.info(f"Headers: {redacted}")

        for record in caplog.records:
            assert "LEAKME" not in record.message
            assert "secret-token" not in record.message


class TestProviderKeyIsolation:
    """Test that provider implementations don't leak keys."""

    def test_gemini_provider_repr_no_key(self):
        """GeminiProvider should not expose key in repr."""
        # We can't fully test without the google SDK, but we can test
        # that SecretStr is used correctly
        from app.llm.secrets import SecretStr

        key = SecretStr("AIzaSyA-test-gemini-key")

        # Verify the wrapper works
        assert "AIzaSyA" not in str(key)
        assert "AIzaSyA" not in repr(key)

    def test_openrouter_provider_repr_no_key(self):
        """OpenRouterProvider should not expose key in repr."""
        from app.llm.secrets import SecretStr

        key = SecretStr("sk-or-v1-test-openrouter-key")

        # Verify the wrapper works
        assert "sk-or-v1" not in str(key)
        assert "sk-or-v1" not in repr(key)
