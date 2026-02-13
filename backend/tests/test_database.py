"""
Tests for database configuration and models.

Note: These tests verify the database setup without requiring
a live PostgreSQL instance.
"""

import pytest

from app import models
from app.database import Base, Database, DatabaseConfig


def test_database_config_default(monkeypatch):
    """When DATABASE_URL is not set, DatabaseConfig should fall back to the local default."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config = DatabaseConfig()
    assert config.is_configured
    assert config.database_url
    assert config.database_url.startswith("postgresql+asyncpg://")


def test_database_config_configured(monkeypatch):
    """Test DatabaseConfig when DATABASE_URL is set."""
    test_url = "postgresql+asyncpg://user:pass@localhost:5432/test"
    monkeypatch.setenv("DATABASE_URL", test_url)
    config = DatabaseConfig()
    assert config.is_configured
    assert config.database_url == test_url


def test_database_config_pool_settings(monkeypatch):
    """Test database pool configuration from environment."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    monkeypatch.setenv("DB_POOL_SIZE", "10")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "20")

    config = DatabaseConfig()
    assert config.pool_size == 10
    assert config.max_overflow == 20


@pytest.mark.asyncio
async def test_database_initialize_with_default_url(monkeypatch):
    """Initializing with the default DATABASE_URL should succeed (engine created)."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db = Database(DatabaseConfig())
    assert db.is_configured
    await db.initialize()
    await db.dispose()


def test_database_models_exist():
    """Test that all required models are defined."""
    # Verify models are registered with Base
    assert hasattr(models, "Session")
    assert hasattr(models, "Run")
    assert hasattr(models, "Event")
    assert hasattr(models, "AuditLog")

    # Verify models inherit from Base
    assert issubclass(models.Session, Base)
    assert issubclass(models.Run, Base)
    assert issubclass(models.Event, Base)
    assert issubclass(models.AuditLog, Base)


def test_session_model_attributes():
    """Test Session model has required attributes."""
    session = models.Session
    assert hasattr(session, "id")
    assert hasattr(session, "created_at")
    assert hasattr(session, "updated_at")
    assert hasattr(session, "ended_at")
    assert hasattr(session, "title")
    assert hasattr(session, "mode")
    assert hasattr(session, "status")
    assert hasattr(session, "config")


def test_run_model_attributes():
    """Test Run model has required attributes."""
    run = models.Run
    assert hasattr(run, "id")
    assert hasattr(run, "session_id")
    assert hasattr(run, "created_at")
    assert hasattr(run, "started_at")
    assert hasattr(run, "completed_at")
    assert hasattr(run, "task")
    assert hasattr(run, "status")
    assert hasattr(run, "result")
    assert hasattr(run, "error")
    assert hasattr(run, "escalated")
    assert hasattr(run, "escalation_reason")
    assert hasattr(run, "brain_used")
    assert hasattr(run, "run_metadata")


def test_event_model_attributes():
    """Test Event model has required attributes."""
    event = models.Event
    assert hasattr(event, "id")
    assert hasattr(event, "run_id")
    assert hasattr(event, "session_id")
    assert hasattr(event, "created_at")
    assert hasattr(event, "event_type")
    assert hasattr(event, "component")
    assert hasattr(event, "message")
    assert hasattr(event, "data")
    assert hasattr(event, "severity")


def test_audit_log_model_attributes():
    """Test AuditLog model has required attributes."""
    audit_log = models.AuditLog
    assert hasattr(audit_log, "id")
    assert hasattr(audit_log, "created_at")
    assert hasattr(audit_log, "actor")
    assert hasattr(audit_log, "actor_id")
    assert hasattr(audit_log, "action")
    assert hasattr(audit_log, "resource")
    assert hasattr(audit_log, "session_id")
    assert hasattr(audit_log, "ip_address")
    assert hasattr(audit_log, "message")
    assert hasattr(audit_log, "details")
    assert hasattr(audit_log, "success")


@pytest.mark.asyncio
async def test_database_health_check_not_initialized(monkeypatch):
    """With default URL, health_check should report not initialized before initialize()."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db = Database(DatabaseConfig())
    health = await db.health_check()

    assert health["ok"] is False
    assert "not initialized" in health["detail"].lower()
    assert health["remediation"] is not None


# (duplicate test removed; covered by test_database_health_check_not_initialized above)
