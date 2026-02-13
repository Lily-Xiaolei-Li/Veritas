"""Tests for local execution service (no Docker).

This repo enforces NO DOCKER.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import reset_settings
from app.executor import (
    ApprovalRequiredError,
    ValidationError,
    _prepare_workspace,
    cancel_execution,
    execute_command,
    get_execution_status,
    validate_command,
)


@pytest.fixture(autouse=True)
def reset_config():
    reset_settings()
    yield
    reset_settings()


def test_validate_blocks_blocklist():
    with pytest.raises(ValidationError):
        validate_command("rm -rf /")


def test_validate_high_risk_requires_approval():
    with pytest.raises(ApprovalRequiredError):
        validate_command("rm test.txt")


def test_validate_high_risk_with_approval_ok():
    is_high_risk, _ = validate_command("rm test.txt", approval_token="token_1234")
    assert is_high_risk is True


def test_prepare_workspace_writes_files(tmp_path: Path):
    ws = _prepare_workspace({"a.txt": "hello", "sub/b.txt": "world"}, workspace_path=str(tmp_path))
    assert (ws / "a.txt").read_text(encoding="utf-8") == "hello"
    assert (ws / "sub" / "b.txt").read_text(encoding="utf-8") == "world"


def test_execute_simple_command(tmp_path: Path):
    r = execute_command("echo hello", workspace_path=str(tmp_path))
    assert r["exit_code"] == 0
    assert "hello" in r["stdout"].lower()
    assert "execution_id" in r


def test_execute_timeout_and_cancel_status(tmp_path: Path):
    # Use a command that sleeps long enough to hit timeout.
    cmd = "python -c \"import time; time.sleep(5)\""
    r = execute_command(cmd, workspace_path=str(tmp_path), timeout=1)
    assert r["exit_code"] == 124


def test_cancel_unknown_execution_returns_false():
    assert cancel_execution("does-not-exist") is False


def test_get_execution_status_unknown():
    s = get_execution_status("does-not-exist")
    assert s["status"] == "not_found"
