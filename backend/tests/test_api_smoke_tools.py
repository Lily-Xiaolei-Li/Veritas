import os

import pytest
from fastapi.testclient import TestClient


def _set_env(**kwargs):
    for k, v in kwargs.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = str(v)


@pytest.fixture()
def client():
    # Import app lazily so env overrides can take effect per test.
    from app.main import app

    with TestClient(app) as c:
        yield c


def _reset_settings():
    from app.config import reset_settings

    reset_settings()


def test_tools_api_smoke_auth_enabled_requires_token(client):
    """When AUTH_ENABLED=true, /tools should require a Bearer token."""

    _set_env(AUTH_ENABLED="true", SESSION_SECRET_KEY="test-secret", DATABASE_URL="")
    _reset_settings()

    r = client.get("/api/v1/tools")
    assert r.status_code == 401


def test_tools_api_smoke_auth_enabled_allows_valid_token_and_execute(client):
    _set_env(AUTH_ENABLED="true", SESSION_SECRET_KEY="test-secret", DATABASE_URL="")
    _reset_settings()

    from app.auth import generate_session_token

    token = generate_session_token(user_id="u_test", username="tester")
    headers = {"Authorization": f"Bearer {token}"}

    # Tools discoverable
    r = client.get("/api/v1/tools", headers=headers)
    assert r.status_code == 200
    payload = r.json()
    names = {t["name"] for t in payload["tools"]}
    assert "file_read" in names
    assert "file_write" in names
    assert "shell_exec" in names
    assert "document_read" in names
    assert "document_write" in names

    # Execute a minimal file_write + file_read roundtrip
    path = "__smoke__/hello.txt"
    text = "hello from api smoke"

    w = client.post(
        "/api/v1/tools/execute",
        headers=headers,
        json={
            "tool_name": "file_write",
            "args": {"path": path, "text": text, "overwrite": True},
        },
    )
    assert w.status_code == 200
    assert w.json()["success"] is True

    rd = client.post(
        "/api/v1/tools/execute",
        headers=headers,
        json={
            "tool_name": "file_read",
            "args": {"path": path, "max_bytes": 200000},
        },
    )
    assert rd.status_code == 200
    j = rd.json()
    assert j["success"] is True
    assert j["output"]["text"].startswith(text)


def test_tools_api_smoke_auth_disabled_allows_no_token(client):
    """When AUTH_ENABLED=false, /tools should work without auth."""

    _set_env(AUTH_ENABLED="false", SESSION_SECRET_KEY=None, DATABASE_URL="")
    _reset_settings()

    r = client.get("/api/v1/tools")
    assert r.status_code == 200
