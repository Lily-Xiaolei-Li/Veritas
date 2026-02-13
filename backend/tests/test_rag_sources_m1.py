import os

import pytest
from fastapi.testclient import TestClient


def _set_env(**kwargs):
    for k, v in kwargs.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = str(v)


def _reset_settings():
    from app.config import reset_settings

    reset_settings()


def test_rag_sources_returns_503_when_db_not_configured():
    """This test must be isolated from other tests that import app.main.

    app.main loads .env on import (without overriding env). If app.main was already
    imported earlier in the test run, we need to force a fresh import so our env
    overrides take effect.
    """

    # IMPORTANT: set env BEFORE using the DB singleton.
    _set_env(DATABASE_URL="", AUTH_ENABLED="false")
    _reset_settings()

    # Reset global DB singleton to make it pick up env changes.
    import app.database as dbmod

    dbmod._db = None

    from app.main import app

    with TestClient(app) as client:
        r = client.get("/api/v1/rag/sources")
        assert r.status_code == 503
        assert "Database not configured" in r.text
