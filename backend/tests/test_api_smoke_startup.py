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


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_startup_health_smoke_no_db_required(client):
    """Minimal smoke: app imports and serves /health without DB configured."""

    _set_env(DATABASE_URL="", AUTH_ENABLED="false")
    _reset_settings()

    r = client.get("/api/v1/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "healthy"
    assert j.get("execution", {}).get("ok") is True
