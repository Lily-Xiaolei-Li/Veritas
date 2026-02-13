"""
Configuration module for Agent B.

Loads configuration from environment variables with .env fallback.
Validates all settings on startup and provides typed access to configuration.
"""

import os
import warnings
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


# Allowed hosts for local LLM providers (SSRF prevention)
ALLOWED_LOCAL_HOSTS = frozenset({
    "localhost",
    "127.0.0.1",
    "::1",
    "host.docker.internal",  # Docker Desktop on Mac/Windows
})


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application Settings
    app_name: str = Field(default="Agent B", description="Application name")
    environment: Literal["development", "production", "test"] = Field(
        default="development",
        description="Runtime environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # API Settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API port")

    # XiaoLei API Settings (Step 2 - Chat Integration)
    xiaolei_api_base_url: str = Field(
        default="http://127.0.0.1:8768",
        description="XiaoLei API base URL (legacy)"
    )
    xiaolei_chat_path: str = Field(
        default="/chat",
        description="XiaoLei chat endpoint path"
    )
    xiaolei_request_timeout: int = Field(
        default=15,
        ge=1,
        le=300,
        description="XiaoLei API request timeout in seconds"
    )
    xiaolei_gateway_url: str = Field(
        default="http://localhost:18789",
        description="XiaoLei Gateway URL for chat completions"
    )
    xiaolei_auth_token: Optional[str] = Field(
        default=None,
        description="Authentication token for XiaoLei Gateway API"
    )
    xiaolei_agent_id: str = Field(
        default="phd",
        description="Agent ID for XiaoLei Gateway routing (e.g., 'phd' for 博士小蕾)"
    )

    # Database Settings
    database_url: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection string"
    )

    # Docker Settings
    min_disk_space_gb: float = Field(
        default=5.0,
        ge=0.1,
        description="Minimum required disk space in GB"
    )
    min_memory_gb: float = Field(
        default=4.0,
        ge=0.1,
        description="Minimum required memory in GB"
    )

    # Logging Settings
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Global log level"
    )
    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log output format"
    )
    log_file: Optional[Path] = Field(
        default=None,
        description="Path to log file (stdout only if not set)"
    )
    log_file_max_bytes: int = Field(
        default=10_485_760,  # 10MB
        ge=1024,
        description="Maximum log file size in bytes before rotation"
    )
    log_file_backup_count: int = Field(
        default=5,
        ge=1,
        description="Number of rotated log files to keep"
    )

    # Component-specific log levels
    log_level_database: Optional[str] = Field(
        default=None,
        description="Log level for database component"
    )
    log_level_docker: Optional[str] = Field(
        default=None,
        description="Log level for docker component"
    )
    log_level_api: Optional[str] = Field(
        default=None,
        description="Log level for API component"
    )

    # Authentication Settings (B0.0.4)
    auth_enabled: bool = Field(
        default=False,
        description="Enable authentication for protected endpoints"
    )
    session_secret_key: Optional[str] = Field(
        default=None,
        description="Secret key for JWT session tokens (required if auth_enabled=true)"
    )
    session_expire_hours: int = Field(
        default=24,
        ge=1,
        le=720,  # Max 30 days
        description="Session token expiration time in hours"
    )
    encryption_key: Optional[str] = Field(
        default=None,
        description="Encryption key for API keys at rest (required if using API key storage)"
    )

    # CORS Settings (Architecture A: separate frontend)
    cors_enabled: bool = Field(
        default=True,
        description="Enable CORS middleware"
    )
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3010",
            "http://localhost:3011",
            "http://localhost:3012",
            "http://localhost:8000",
            "http://localhost:8001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3010",
            "http://127.0.0.1:3011",
            "http://127.0.0.1:3012",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8001",
        ],
        description="Allowed CORS origins (comma-separated in env)"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )

    # Docker Execution Settings (B0.1)
    docker_timeout: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="Docker command execution timeout in seconds (default: 5 minutes)"
    )
    docker_network_enabled: bool = Field(
        default=False,
        description="Enable network access in Docker containers (default: disabled)"
    )
    docker_network_allowlist: list[str] = Field(
        default=[],
        description="Allowed networks for Docker containers (comma-separated in env)"
    )
    workspace_dir: str = Field(
        default="./workspace",
        description="Directory for workspace file mounting"
    )
    docker_memory_limit: str = Field(
        default="2g",
        description="Memory limit for Docker containers (e.g., '2g', '512m')"
    )
    docker_cpu_limit: float = Field(
        default=1.0,
        ge=0.1,
        le=16.0,
        description="CPU limit for Docker containers (number of cores)"
    )

    # Execution Safety Settings (B0.2)
    command_blocklist: list[str] = Field(
        default=["rm -rf /", "dd if=", ":(){ :|:& };:", "mkfs"],
        description="Dangerous command patterns that are always blocked (comma-separated in env)"
    )
    high_risk_patterns: list[str] = Field(
        default=["rm", "dd", "mkfs", "format"],
        description="High-risk command patterns that require approval (comma-separated in env)"
    )

    # File Watcher Settings (B1.2)
    file_watcher_enabled: bool = Field(
        default=True,
        description="Enable file system watching for workspace directory"
    )
    file_watcher_debounce_ms: int = Field(
        default=500,
        ge=100,
        le=5000,
        description="Debounce time for file change events in milliseconds"
    )
    file_watcher_ignore_patterns: list[str] = Field(
        default=[".git", "__pycache__", "*.pyc", "node_modules", ".DS_Store", "Thumbs.db"],
        description="File/directory patterns to ignore during watching (comma-separated in env)"
    )
    max_file_size_mb: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum file size to hash in MB (larger files indexed without hash)"
    )

    # Artifact Settings (B1.3)
    artifacts_dir: str = Field(
        default="./artifacts",
        description="Directory for artifact storage"
    )
    max_artifact_size_mb: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum artifact size in MB"
    )
    artifact_preview_max_kb: int = Field(
        default=2048,
        ge=10,
        le=10240,
        description="Maximum size for artifact preview in KB (default 2MB, max 10MB)"
    )

    # Metrics Settings (B7.2)
    metrics_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics endpoint"
    )
    metrics_token: Optional[str] = Field(
        default=None,
        description="Bearer token for /metrics endpoint authentication (required in production if not behind proxy)"
    )

    # LLM Provider Settings (B2.0)
    llm_default_provider: str = Field(
        default="gemini",
        description="Default LLM provider (gemini, openrouter, mock)"
    )
    llm_default_model: str = Field(
        default="gemini-1.5-flash",
        description="Default model for LLM requests"
    )
    llm_fallback_providers: list[str] = Field(
        default=[],
        description="Fallback provider chain in order (comma-separated in env)"
    )
    llm_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for LLM requests"
    )
    llm_retry_base_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Base delay between retries in seconds"
    )
    llm_request_timeout: int = Field(
        default=120,
        ge=10,
        le=600,
        description="LLM request timeout in seconds"
    )
    llm_cost_tracking_enabled: bool = Field(
        default=True,
        description="Enable LLM cost tracking to database"
    )
    llm_log_content: Literal["hash", "none"] = Field(
        default="hash",
        description="How to log LLM content: 'hash' (salted hash) or 'none'"
    )
    llm_log_hash_salt: str = Field(
        default="",
        description="Salt for content hashing. REQUIRED in production if llm_log_content='hash'"
    )
    llm_log_context_ids: bool = Field(
        default=False,
        description="Log run_id/session_id in LLM logs. Disable for high-cardinality concerns."
    )
    llm_credential_cache_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="TTL for cached provider credentials in seconds"
    )
    openrouter_http_referer: str = Field(
        default="http://localhost:3000",
        description="HTTP Referer header for OpenRouter API requests"
    )
    llm_fallback_on_content_filter: bool = Field(
        default=False,
        description="If True, fallback to next provider on content filter (DANGEROUS - bypasses safety)"
    )

    # Ollama / Local LLM Settings (B2.0)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL (localhost only by default for SSRF prevention)"
    )
    allow_cloud_fallback_from_local: bool = Field(
        default=False,
        description="If local provider fails, allow fallback to cloud. Has privacy implications."
    )

    # Multi-Brain Configuration (B2.2)
    # Brain 1 (Coordinator) - fast, can be local
    # Hardware auto-select deferred to B2.5
    brain_1_provider: str = Field(
        default="gemini",
        description="LLM provider for Brain 1 (Coordinator)"
    )
    brain_1_model: str = Field(
        default="gemini-2.0-flash",
        description="Model for Brain 1 (Coordinator) - should be fast"
    )

    # Brain 2 (Manager) - flagship cloud model
    brain_2_provider: str = Field(
        default="gemini",
        description="LLM provider for Brain 2 (Manager)"
    )
    brain_2_model: str = Field(
        default="gemini-1.5-pro",
        description="Model for Brain 2 (Manager) - flagship for complex reasoning"
    )

    # Collaboration thresholds
    max_deliberation_rounds: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum deliberation rounds before escalation"
    )

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_url_is_local(cls, v: str) -> str:
        """SSRF prevention: only allow local URLs by default."""
        parsed = urlparse(v)

        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"ollama_base_url must use http or https, got: {parsed.scheme}")

        hostname = parsed.hostname or ""
        if hostname not in ALLOWED_LOCAL_HOSTS:
            if not os.getenv("OLLAMA_ALLOW_NONLOCAL"):
                raise ValueError(
                    f"ollama_base_url must be localhost (got: {hostname}). "
                    f"Set OLLAMA_ALLOW_NONLOCAL=true to allow non-local URLs."
                )
        return v

    @field_validator("llm_fallback_providers", mode="before")
    @classmethod
    def parse_llm_fallback_providers(cls, v):
        """Parse LLM fallback providers from comma-separated string or list."""
        if isinstance(v, str):
            return [provider.strip() for provider in v.split(",") if provider.strip()]
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("docker_network_allowlist", mode="before")
    @classmethod
    def parse_network_allowlist(cls, v):
        """Parse network allowlist from comma-separated string or list."""
        if isinstance(v, str):
            return [network.strip() for network in v.split(",") if network.strip()]
        return v

    @field_validator("command_blocklist", mode="before")
    @classmethod
    def parse_command_blocklist(cls, v):
        """Parse command blocklist from comma-separated string or list."""
        if isinstance(v, str):
            return [cmd.strip() for cmd in v.split(",") if cmd.strip()]
        return v

    @field_validator("high_risk_patterns", mode="before")
    @classmethod
    def parse_high_risk_patterns(cls, v):
        """Parse high-risk patterns from comma-separated string or list."""
        if isinstance(v, str):
            return [pattern.strip() for pattern in v.split(",") if pattern.strip()]
        return v

    @field_validator("file_watcher_ignore_patterns", mode="before")
    @classmethod
    def parse_file_watcher_ignore_patterns(cls, v):
        """Parse file watcher ignore patterns from comma-separated string or list."""
        if isinstance(v, str):
            return [pattern.strip() for pattern in v.split(",") if pattern.strip()]
        return v

    @field_validator("session_secret_key", mode="after")
    @classmethod
    def validate_secret_key(cls, v, info):
        """Validate that secret key is set if auth is enabled."""
        if info.data.get("auth_enabled") and not v:
            raise ValueError(
                "session_secret_key is required when auth_enabled=true. "
                "Generate one with: openssl rand -hex 32"
            )
        return v

    @field_validator("encryption_key", mode="after")
    @classmethod
    def validate_encryption_key(cls, v):
        """Validate encryption key format if provided."""
        if v and len(v) < 32:
            raise ValueError(
                "encryption_key must be at least 32 characters. "
                "Generate one with: openssl rand -hex 32"
            )
        return v

    @field_validator("log_file", mode="before")
    @classmethod
    def validate_log_file(cls, v):
        """Convert string path to Path object and ensure parent directory exists."""
        if v is None or v == "":
            return None

        path = Path(v)

        # Create parent directory if it doesn't exist
        if path.parent and not path.parent.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Cannot create log directory {path.parent}: {e}")

        return path

    def get_component_log_level(self, component: str) -> str:
        """Get log level for a specific component, falling back to global level."""
        component_level = getattr(self, f"log_level_{component}", None)
        return component_level if component_level is not None else self.log_level


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance, loading if necessary."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def load_settings() -> Settings:
    """
    Load and validate settings from environment variables.

    Raises:
        ConfigurationError: If configuration is invalid or required values are missing
    """
    try:
        return Settings()
    except ValidationError as e:
        # Format validation errors into actionable messages
        errors = []
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            errors.append(f"  - {field}: {msg}")

        error_message = "Configuration validation failed:\n" + "\n".join(errors)
        raise ConfigurationError(error_message) from e
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}") from e


def reset_settings():
    """Reset the global settings instance (useful for testing)."""
    global _settings
    _settings = None


class ConfigurationError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""
    pass
