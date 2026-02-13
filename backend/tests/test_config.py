"""
Tests for configuration module.

Tests cover:
- Configuration loading from environment
- Validation of required fields
- Validation of field types and constraints
- Component-specific log level overrides
- Error handling for invalid configuration
"""

import pytest

from app.config import (
    ConfigurationError,
    Settings,
    get_settings,
    load_settings,
    reset_settings,
)


@pytest.fixture(autouse=True)
def reset_config():
    """Reset settings before and after each test."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def clean_env(monkeypatch):
    """Clear all Agent B environment variables and disable .env file loading."""
    env_vars = [
        "APP_NAME", "ENVIRONMENT", "DEBUG",
        "API_HOST", "API_PORT",
        "DATABASE_URL",
        "MIN_DISK_SPACE_GB", "MIN_MEMORY_GB",
        "LOG_LEVEL", "LOG_FORMAT", "LOG_FILE",
        "LOG_FILE_MAX_BYTES", "LOG_FILE_BACKUP_COUNT",
        "LOG_LEVEL_DATABASE", "LOG_LEVEL_DOCKER", "LOG_LEVEL_API",
        # Auth settings
        "AUTH_ENABLED", "SESSION_SECRET_KEY", "SESSION_EXPIRE_HOURS", "ENCRYPTION_KEY",
        # CORS settings
        "CORS_ENABLED", "CORS_ORIGINS", "CORS_ALLOW_CREDENTIALS",
        # Docker settings
        "DOCKER_TIMEOUT", "DOCKER_NETWORK_ENABLED", "DOCKER_NETWORK_ALLOWLIST",
        "WORKSPACE_DIR", "DOCKER_MEMORY_LIMIT", "DOCKER_CPU_LIMIT",
        # Execution settings
        "COMMAND_BLOCKLIST", "HIGH_RISK_PATTERNS",
        # File watcher settings
        "FILE_WATCHER_ENABLED", "FILE_WATCHER_DEBOUNCE_MS",
        "FILE_WATCHER_IGNORE_PATTERNS", "MAX_FILE_SIZE_MB",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)

    # Disable .env file loading by patching Settings.model_config
    from pydantic_settings import SettingsConfigDict

    # Create a new config dict without env_file
    new_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    monkeypatch.setattr(Settings, "model_config", new_config)


def test_default_settings(clean_env):
    """Test that settings load with defaults when no env vars are set."""
    settings = load_settings()

    assert settings.app_name == "Agent B"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.database_url is None
    assert settings.min_disk_space_gb == 5.0
    assert settings.min_memory_gb == 4.0
    assert settings.log_level == "INFO"
    assert settings.log_format == "json"
    assert settings.log_file is None


def test_environment_variable_override(clean_env, monkeypatch):
    """Test that environment variables override defaults."""
    monkeypatch.setenv("APP_NAME", "Test App")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "text")

    settings = load_settings()

    assert settings.app_name == "Test App"
    assert settings.environment == "production"
    assert settings.debug is True
    assert settings.api_port == 9000
    assert settings.log_level == "DEBUG"
    assert settings.log_format == "text"


def test_database_url_configuration(clean_env, monkeypatch):
    """Test database URL configuration."""
    db_url = "postgresql+asyncpg://user:pass@localhost:5432/testdb"
    monkeypatch.setenv("DATABASE_URL", db_url)

    settings = load_settings()

    assert settings.database_url == db_url


def test_invalid_api_port_too_low(clean_env, monkeypatch):
    """Test that API port validation rejects values below 1."""
    monkeypatch.setenv("API_PORT", "0")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert "api_port" in str(exc_info.value).lower()


def test_invalid_api_port_too_high(clean_env, monkeypatch):
    """Test that API port validation rejects values above 65535."""
    monkeypatch.setenv("API_PORT", "65536")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert "api_port" in str(exc_info.value).lower()


def test_invalid_environment(clean_env, monkeypatch):
    """Test that invalid environment value is rejected."""
    monkeypatch.setenv("ENVIRONMENT", "invalid")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert "environment" in str(exc_info.value).lower()


def test_invalid_log_level(clean_env, monkeypatch):
    """Test that invalid log level is rejected."""
    monkeypatch.setenv("LOG_LEVEL", "INVALID")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert "log_level" in str(exc_info.value).lower()


def test_invalid_log_format(clean_env, monkeypatch):
    """Test that invalid log format is rejected."""
    monkeypatch.setenv("LOG_FORMAT", "xml")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert "log_format" in str(exc_info.value).lower()


def test_log_file_path_creation(clean_env, monkeypatch, tmp_path):
    """Test that log file parent directory is created automatically."""
    log_file = tmp_path / "logs" / "test.log"
    monkeypatch.setenv("LOG_FILE", str(log_file))

    settings = load_settings()

    assert settings.log_file == log_file
    assert log_file.parent.exists()


def test_component_log_level_override(clean_env, monkeypatch):
    """Test component-specific log level overrides."""
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_LEVEL_DATABASE", "DEBUG")
    monkeypatch.setenv("LOG_LEVEL_DOCKER", "WARNING")

    settings = load_settings()

    assert settings.get_component_log_level("database") == "DEBUG"
    assert settings.get_component_log_level("docker") == "WARNING"
    assert settings.get_component_log_level("api") == "INFO"  # Falls back to global


def test_component_log_level_fallback(clean_env, monkeypatch):
    """Test that component log levels fall back to global level."""
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    settings = load_settings()

    assert settings.get_component_log_level("database") == "WARNING"
    assert settings.get_component_log_level("docker") == "WARNING"
    assert settings.get_component_log_level("api") == "WARNING"


def test_min_disk_space_validation(clean_env, monkeypatch):
    """Test that minimum disk space must be positive."""
    monkeypatch.setenv("MIN_DISK_SPACE_GB", "0")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert "min_disk_space_gb" in str(exc_info.value).lower()


def test_min_memory_validation(clean_env, monkeypatch):
    """Test that minimum memory must be positive."""
    monkeypatch.setenv("MIN_MEMORY_GB", "0")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert "min_memory_gb" in str(exc_info.value).lower()


def test_get_settings_singleton(clean_env):
    """Test that get_settings returns the same instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2


def test_reset_settings(clean_env):
    """Test that reset_settings clears the singleton."""
    settings1 = get_settings()
    reset_settings()
    settings2 = get_settings()

    # Should be different instances after reset
    assert settings1 is not settings2


def test_case_insensitive_env_vars(clean_env, monkeypatch):
    """Test that environment variable names are case-insensitive."""
    monkeypatch.setenv("log_level", "DEBUG")  # lowercase var name, uppercase value
    monkeypatch.setenv("API_PORT", "9000")    # uppercase var name

    settings = load_settings()

    assert settings.log_level == "DEBUG"
    assert settings.api_port == 9000


def test_log_file_rotation_settings(clean_env, monkeypatch, tmp_path):
    """Test log file rotation configuration."""
    log_file = tmp_path / "test.log"
    monkeypatch.setenv("LOG_FILE", str(log_file))
    monkeypatch.setenv("LOG_FILE_MAX_BYTES", "5242880")  # 5MB
    monkeypatch.setenv("LOG_FILE_BACKUP_COUNT", "10")

    settings = load_settings()

    assert settings.log_file == log_file
    assert settings.log_file_max_bytes == 5242880
    assert settings.log_file_backup_count == 10


def test_invalid_log_file_max_bytes(clean_env, monkeypatch, tmp_path):
    """Test that log file max bytes must be >= 1024."""
    log_file = tmp_path / "test.log"
    monkeypatch.setenv("LOG_FILE", str(log_file))
    monkeypatch.setenv("LOG_FILE_MAX_BYTES", "100")  # Too small

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert "log_file_max_bytes" in str(exc_info.value).lower()


def test_invalid_log_file_backup_count(clean_env, monkeypatch, tmp_path):
    """Test that log file backup count must be >= 1."""
    log_file = tmp_path / "test.log"
    monkeypatch.setenv("LOG_FILE", str(log_file))
    monkeypatch.setenv("LOG_FILE_BACKUP_COUNT", "0")

    with pytest.raises(ConfigurationError) as exc_info:
        load_settings()

    assert "log_file_backup_count" in str(exc_info.value).lower()
