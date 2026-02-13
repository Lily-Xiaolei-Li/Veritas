from cli import health


def test_cli_ready(monkeypatch, capsys):
    def fake_payload():
        return {
            "status": "ok",
            "docker": {"ok": True, "checks": []},
            "resources": {"ok": True, "checks": []},
        }

    monkeypatch.setattr(health, "as_health_payload", fake_payload)
    exit_code = health.main([])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "READY" in captured.out
    assert "ALL CHECKS PASSED" in captured.out


def test_cli_not_ready(monkeypatch, capsys):
    def fake_payload():
        return {
            "status": "degraded",
            "docker": {
                "ok": False,
                "checks": [
                    {"name": "daemon_reachable", "ok": False, "detail": "mock down", "remediation": "Start Docker"},
                    {"name": "user_permissions", "ok": True, "detail": "ok", "remediation": None},
                ],
            },
            "resources": {
                "ok": True,
                "checks": [
                    {"name": "disk_space", "ok": True, "detail": "10GB available", "remediation": None},
                    {"name": "memory", "ok": True, "detail": "8GB available", "remediation": None},
                ],
            },
        }

    monkeypatch.setattr(health, "as_health_payload", fake_payload)
    exit_code = health.main([])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "NOT READY" in captured.out
    assert "daemon_reachable" in captured.out


def test_cli_resource_failure(monkeypatch, capsys):
    """Test CLI output when resource checks fail."""

    def fake_payload():
        return {
            "status": "degraded",
            "docker": {"ok": True, "checks": []},
            "resources": {
                "ok": False,
                "checks": [
                    {
                        "name": "disk_space",
                        "ok": False,
                        "detail": "2GB available",
                        "remediation": "Free up disk space",
                    },
                    {"name": "memory", "ok": True, "detail": "8GB available", "remediation": None},
                ],
            },
        }

    monkeypatch.setattr(health, "as_health_payload", fake_payload)
    exit_code = health.main([])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "NOT READY" in captured.out
    assert "disk_space" in captured.out
    assert "REMEDIATION" in captured.out
