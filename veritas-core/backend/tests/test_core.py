"""
Veritas Core Integration Tests
"""
import pytest
from fastapi.testclient import TestClient

# Test that core can be imported
def test_imports():
    from app.main import app
    from app.plugins import PluginManager
    from app.config import *  # noqa
    assert app is not None
    assert PluginManager is not None

# Test health endpoint
def test_health_endpoint():
    from app.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

# Test plugins endpoint
def test_plugins_endpoint():
    from app.main import app
    client = TestClient(app)
    response = client.get("/api/v1/plugins")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
