"""
Tests for logging configuration module.

Tests cover:
- Sensitive data redaction
- JSON and text formatting
- Request ID propagation
- Logger creation
- Log level configuration
"""

import json
import logging

from app.config import Settings
from app.logging_config import (
    JSONFormatter,
    TextFormatter,
    clear_request_id,
    get_logger,
    get_request_id,
    redact_sensitive_data,
    set_request_id,
    setup_logging,
)


def test_redact_aws_api_key():
    """Test that AWS API keys are redacted."""
    text = "My key is AKIAIOSFODNN7EXAMPLE and it's secret"
    redacted = redact_sensitive_data(text)

    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "[REDACTED_AWS_KEY]" in redacted


def test_redact_openai_api_key():
    """Test that OpenAI API keys are redacted."""
    text = "sk-1234567890abcdefghijklmnopqrstuv"
    redacted = redact_sensitive_data(text)

    assert "sk-1234567890abcdefghijklmnopqrstuv" not in redacted
    assert "[REDACTED_OPENAI_KEY]" in redacted


def test_redact_google_api_key():
    """Test that Google API keys are redacted."""
    text = "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
    redacted = redact_sensitive_data(text)

    assert "AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI" not in redacted
    assert "[REDACTED_GOOGLE_KEY]" in redacted


def test_redact_github_token():
    """Test that GitHub tokens are redacted."""
    text = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    redacted = redact_sensitive_data(text)

    assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "[REDACTED_GITHUB_TOKEN]" in redacted


def test_redact_generic_api_key():
    """Test that generic API key patterns are redacted."""
    text = 'api_key: "my_secret_key_12345"'
    redacted = redact_sensitive_data(text)

    assert "my_secret_key_12345" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_password():
    """Test that password patterns are redacted."""
    text = 'password: "SecurePass123"'
    redacted = redact_sensitive_data(text)

    assert "SecurePass123" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_database_url():
    """Test that database credentials in URLs are redacted."""
    text = "postgresql://user:secretpass@localhost:5432/db"
    redacted = redact_sensitive_data(text)

    assert "secretpass" not in redacted
    assert "[REDACTED]" in redacted
    assert "postgresql://" in redacted


def test_redact_multiple_secrets():
    """Test that multiple secrets in same string are all redacted."""
    text = "My AWS key is AKIAIOSFODNN7EXAMPLE and OpenAI key is sk-abcdefghijklmnopqrstuvwxyz123456"
    redacted = redact_sensitive_data(text)

    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in redacted
    assert "[REDACTED_AWS_KEY]" in redacted
    assert "[REDACTED_OPENAI_KEY]" in redacted


def test_redact_non_string():
    """Test that non-string values are converted and redacted."""
    redacted = redact_sensitive_data(12345)
    assert redacted == "12345"


def test_json_formatter_basic():
    """Test that JSONFormatter produces valid JSON."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test.component",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["component"] == "test.component"
    assert parsed["message"] == "Test message"
    assert "timestamp" in parsed


def test_json_formatter_with_request_id():
    """Test that JSONFormatter includes request ID when set."""
    formatter = JSONFormatter()
    set_request_id("test-request-123")

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["request_id"] == "test-request-123"

    clear_request_id()


def test_json_formatter_redacts_secrets():
    """Test that JSONFormatter redacts sensitive data."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="API key is AKIAIOSFODNN7EXAMPLE",
        args=(),
        exc_info=None
    )

    output = formatter.format(record)
    parsed = json.loads(output)

    assert "AKIAIOSFODNN7EXAMPLE" not in parsed["message"]
    assert "[REDACTED_AWS_KEY]" in parsed["message"]


def test_text_formatter_basic():
    """Test that TextFormatter produces readable text."""
    formatter = TextFormatter()
    record = logging.LogRecord(
        name="test.component",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )

    output = formatter.format(record)

    assert "[INFO]" in output
    assert "test.component" in output
    assert "Test message" in output


def test_text_formatter_with_request_id():
    """Test that TextFormatter includes request ID when set."""
    formatter = TextFormatter()
    set_request_id("test-request-456")

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )

    output = formatter.format(record)

    assert "request_id=test-request-456" in output

    clear_request_id()


def test_text_formatter_redacts_secrets():
    """Test that TextFormatter redacts sensitive data."""
    formatter = TextFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="API key is AKIAIOSFODNN7EXAMPLE",
        args=(),
        exc_info=None
    )

    output = formatter.format(record)

    assert "AKIAIOSFODNN7EXAMPLE" not in output
    assert "[REDACTED_AWS_KEY]" in output


def test_setup_logging_json_format(tmp_path):
    """Test that setup_logging configures JSON logging."""
    settings = Settings(
        log_level="INFO",
        log_format="json",
        log_file=None
    )

    setup_logging(settings)

    # Get root logger and check handler
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO
    assert len(root_logger.handlers) > 0

    # Check that handler uses JSONFormatter
    handler = root_logger.handlers[0]
    assert isinstance(handler.formatter, JSONFormatter)


def test_setup_logging_text_format(tmp_path):
    """Test that setup_logging configures text logging."""
    settings = Settings(
        log_level="DEBUG",
        log_format="text",
        log_file=None
    )

    setup_logging(settings)

    # Get root logger and check handler
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG

    # Check that handler uses TextFormatter
    handler = root_logger.handlers[0]
    assert isinstance(handler.formatter, TextFormatter)


def test_setup_logging_with_file(tmp_path):
    """Test that setup_logging creates file handler when log_file is set."""
    log_file = tmp_path / "test.log"
    settings = Settings(
        log_level="INFO",
        log_format="json",
        log_file=log_file
    )

    setup_logging(settings)

    # Should have both stdout and file handlers
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) >= 2


def test_get_logger_namespace():
    """Test that get_logger adds agent_b namespace."""
    logger = get_logger("test")

    assert logger.name == "agent_b.test"


def test_get_logger_existing_namespace():
    """Test that get_logger preserves existing namespace."""
    logger = get_logger("agent_b.test")

    assert logger.name == "agent_b.test"


def test_request_id_context():
    """Test request ID context management."""
    # Initially no request ID
    assert get_request_id() is None

    # Set request ID
    set_request_id("test-123")
    assert get_request_id() == "test-123"

    # Clear request ID
    clear_request_id()
    assert get_request_id() is None


def test_component_log_levels(tmp_path):
    """Test that component-specific log levels are configured."""
    settings = Settings(
        log_level="INFO",
        log_level_database="DEBUG",
        log_format="json"
    )

    setup_logging(settings)

    # Check component loggers
    db_logger = logging.getLogger("agent_b.database")
    api_logger = logging.getLogger("agent_b.api")

    assert db_logger.level == logging.DEBUG
    assert api_logger.level == logging.INFO
