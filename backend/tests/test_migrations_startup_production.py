import os

import pytest
from fastapi.testclient import TestClient


def _set_env(**kwargs):
    for k, v in kwargs.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = str(v)


def test_startup_fails_in_production_when_migrations_fail(monkeypatch):
    """In production, a migration failure should prevent the app from starting."""

    # Import app, then force settings to production for this test.
    # (Avoid re-importing app.main which can cause global metric re-registration.)
    import app.main as main

    monkeypatch.setattr(main.settings, "environment", "production", raising=False)
    _set_env(DATABASE_URL="postgresql+asyncpg://dummy:dummy@127.0.0.1:5433/agent_b", AUTH_ENABLED="false")

    class FakeDB:
        is_configured = True

        async def initialize(self):
            return None

        async def dispose(self):
            return None

    # Force migrations to "fail"
    monkeypatch.setattr(main, "get_database", lambda: FakeDB())
    monkeypatch.setattr(main, "run_migrations", lambda: {"ok": False, "detail": "boom"})

    with pytest.raises(RuntimeError, match="Migrations failed"):
        with TestClient(main.app):
            pass
