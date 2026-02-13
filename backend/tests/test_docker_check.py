import pytest

from app import health_checks


def test_resource_checks_structure(monkeypatch):
    # smoke: structure only
    r = health_checks.run_resource_checks()
    assert set(r.keys()) == {"ok", "checks"}
    assert isinstance(r["checks"], list)
    assert all("name" in c and "ok" in c and "detail" in c for c in r["checks"])


@pytest.mark.anyio
async def test_fastapi_health_endpoint(monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    # /health no longer depends on docker check payload; it should always return JSON.

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    # /health endpoint returns envelope with "healthy" or "degraded" status
    assert resp.json()["status"] in ("ok", "healthy", "degraded")


def test_disk_space_check_success(monkeypatch):
    """Test disk space check when sufficient space is available."""

    class MockStat:
        free = 10 * (1024**3)  # 10GB free

    def mock_disk_usage(path):
        return MockStat()

    import shutil
    monkeypatch.setattr(shutil, "disk_usage", mock_disk_usage)

    result = health_checks.check_disk_space()
    assert result["ok"] is True
    assert result["name"] == "disk_space"
    assert result["exit_code"] == 0
    assert result["remediation"] is None


def test_disk_space_check_failure(monkeypatch):
    """Test disk space check when insufficient space is available."""

    class MockStat:
        free = 2 * (1024**3)  # Only 2GB free (less than default 5GB requirement)

    def mock_disk_usage(path):
        return MockStat()

    import shutil
    monkeypatch.setattr(shutil, "disk_usage", mock_disk_usage)

    result = health_checks.check_disk_space()
    assert result["ok"] is False
    assert result["name"] == "disk_space"
    assert result["remediation"] is not None
    assert "Insufficient disk space" in result["remediation"]


def test_memory_check_success(monkeypatch):
    """Test memory check when sufficient memory is available."""

    class MockMemory:
        available = 8 * (1024**3)  # 8GB available

    def mock_virtual_memory():
        return MockMemory()

    # Mock psutil if not available
    if health_checks.psutil is None:
        from types import SimpleNamespace
        mock_psutil = SimpleNamespace(virtual_memory=mock_virtual_memory)
        monkeypatch.setattr(health_checks, "psutil", mock_psutil)
    else:
        monkeypatch.setattr(health_checks.psutil, "virtual_memory", mock_virtual_memory)

    result = health_checks.check_memory()
    assert result["ok"] is True
    assert result["name"] == "memory"
    assert result["exit_code"] == 0
    assert result["remediation"] is None


def test_memory_check_failure(monkeypatch):
    """Test memory check when insufficient memory is available."""

    class MockMemory:
        available = 2 * (1024**3)  # Only 2GB available (less than default 4GB requirement)

    def mock_virtual_memory():
        return MockMemory()

    # Mock psutil if not available
    if health_checks.psutil is None:
        from types import SimpleNamespace
        mock_psutil = SimpleNamespace(virtual_memory=mock_virtual_memory)
        monkeypatch.setattr(health_checks, "psutil", mock_psutil)
    else:
        monkeypatch.setattr(health_checks.psutil, "virtual_memory", mock_virtual_memory)

    result = health_checks.check_memory()
    assert result["ok"] is False
    assert result["name"] == "memory"
    assert result["remediation"] is not None
    assert "Insufficient memory" in result["remediation"]


def test_remediation_messages_present():
    """Test that all check functions include remediation field."""
    # This test ensures the structure is correct even with failures
    checks = [
        health_checks.check_disk_space(),
        health_checks.check_memory(),
    ]

    for check in checks:
        assert "remediation" in check, f"Check {check.get('name')} missing remediation field"
        # Remediation should be None for success, string for failure
        assert check["remediation"] is None or isinstance(check["remediation"], str)
