"""
Structured logging configuration for Agent B.

Provides JSON and text logging with:
- Request ID propagation
- Sensitive value redaction
- Per-component log levels
- File rotation support
"""

import contextvars
import json
import logging
import logging.handlers
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import Settings


# Context variable for request ID
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)


# Patterns for sensitive data redaction
SENSITIVE_PATTERNS = [
    # API Keys
    (re.compile(r'AKIA[0-9A-Z]{16}'), '[REDACTED_AWS_KEY]'),
    (re.compile(r'sk-[a-zA-Z0-9]{32,}'), '[REDACTED_OPENAI_KEY]'),
    (re.compile(r'AIza[0-9A-Za-z-_]{35}'), '[REDACTED_GOOGLE_KEY]'),

    # Tokens
    (re.compile(r'ghp_[a-zA-Z0-9]{36}'), '[REDACTED_GITHUB_TOKEN]'),
    (re.compile(r'gho_[a-zA-Z0-9]{36}'), '[REDACTED_GITHUB_OAUTH]'),

    # Generic patterns
    (re.compile(r'api[_-]?key["\s:=]+["\']?([a-zA-Z0-9_-]{16,})["\']?', re.IGNORECASE),
     r'api_key: [REDACTED]'),
    (re.compile(r'token["\s:=]+["\']?([a-zA-Z0-9_-]{16,})["\']?', re.IGNORECASE),
     r'token: [REDACTED]'),
    (re.compile(r'password["\s:=]+["\']?([^\s"\']{6,})["\']?', re.IGNORECASE),
     r'password: [REDACTED]'),
    (re.compile(r'secret["\s:=]+["\']?([a-zA-Z0-9_-]{16,})["\']?', re.IGNORECASE),
     r'secret: [REDACTED]'),

    # Database URLs with credentials
    (re.compile(r'postgresql://([^:]+):([^@]+)@'), 'postgresql://[USER]:[REDACTED]@'),
    (re.compile(r'mysql://([^:]+):([^@]+)@'), 'mysql://[USER]:[REDACTED]@'),
]


def redact_sensitive_data(text: str) -> str:
    """Redact sensitive information from log messages."""
    if not isinstance(text, str):
        text = str(text)

    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)

    return text


class JSONFormatter(logging.Formatter):
    """Format log records as JSON with structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Build base log entry
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": redact_sensitive_data(record.getMessage()),
        }

        # Add request ID if present
        request_id = request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id

        # Add extra fields
        if hasattr(record, "extra_fields"):
            for key, value in record.extra_fields.items():
                log_entry[key] = redact_sensitive_data(str(value))

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = redact_sensitive_data(
                self.formatException(record.exc_info)
            )

        return json.dumps(log_entry)


class TextFormatter(logging.Formatter):
    """Format log records as human-readable text with sensitive data redaction."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as text with redaction."""
        # Redact the message
        original_msg = record.msg
        record.msg = redact_sensitive_data(str(record.msg))

        # Format the record
        formatted = super().format(record)

        # Restore original message (in case the record is reused)
        record.msg = original_msg

        # Add request ID if present
        request_id = request_id_var.get()
        if request_id:
            formatted = f"{formatted} [request_id={request_id}]"

        return redact_sensitive_data(formatted)


class ExtraFieldsAdapter(logging.LoggerAdapter):
    """Logger adapter that supports extra fields in log calls."""

    def process(self, msg, kwargs):
        """Process log call, extracting extra fields."""
        extra_fields = kwargs.pop("extra_fields", {})
        if not hasattr(kwargs.get("extra", {}), "__dict__"):
            kwargs["extra"] = type("Extra", (), {})()
        kwargs["extra"].extra_fields = extra_fields
        return msg, kwargs


def setup_logging(settings: Settings) -> None:
    """
    Configure logging based on settings.

    Args:
        settings: Application settings
    """
    # Determine formatter
    if settings.log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

    # Remove existing handlers (and close them to avoid ResourceWarning in tests)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass

    # Add stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    # Add file handler if configured
    if settings.log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.log_file,
            maxBytes=settings.log_file_max_bytes,
            backupCount=settings.log_file_backup_count,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Configure component-specific loggers
    for component in ["database", "api"]:
        logger = logging.getLogger(f"agent_b.{component}")
        logger.setLevel(settings.get_component_log_level(component))

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given component name.

    Notes:
    - We keep component loggers at NOTSET by default so they inherit the root
      level/handlers (important for pytest caplog and consistent configuration).
    """
    # Prefix with agent_b namespace
    if not name.startswith("agent_b."):
        name = f"agent_b.{name}"

    logger = logging.getLogger(name)
    logger.propagate = True
    # Ensure default inheritance unless explicitly overridden elsewhere.
    logger.setLevel(logging.NOTSET)
    return logger


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context."""
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Get the request ID for the current context."""
    return request_id_var.get()


def clear_request_id() -> None:
    """Clear the request ID for the current context."""
    request_id_var.set(None)
