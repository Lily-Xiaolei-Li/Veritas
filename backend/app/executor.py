"""Local execution service for Agent B (no Docker).

This repository enforces **NO DOCKER** to keep development/testing fast.

Security model (v1):
- command blocklist + high-risk approvals
- workspace-scoped working directory
- timeouts
- best-effort cancellation (terminate process)

NOTE: This is not a hardened sandbox. It is a practical local execution
facility with guardrails suitable for local-first use.
"""

from __future__ import annotations

import os
import secrets
import subprocess
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple
from uuid import uuid4

from .config import get_settings
from .logging_config import get_logger, redact_sensitive_data

logger = get_logger("executor")


class ExecutionError(Exception):
    """Raised when command execution fails."""


class ValidationError(Exception):
    """Raised when command validation fails."""


class ApprovalRequiredError(Exception):
    """Raised when a high-risk command requires approval."""


# In-memory registry of running processes
_RUNNING: dict[str, subprocess.Popen] = {}
_LOCK = threading.Lock()


def validate_command(command: str, approval_token: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Validate command against blocklist and high-risk patterns."""

    settings = get_settings()

    for blocked_pattern in settings.command_blocklist:
        if blocked_pattern in command:
            msg = f"Command contains blocked pattern: {blocked_pattern}"
            logger.warning(
                "Blocked command execution",
                extra={"command": redact_sensitive_data(command), "blocked_pattern": blocked_pattern},
            )
            raise ValidationError(msg)

    is_high_risk = False
    matched = []
    for risk_pattern in settings.high_risk_patterns:
        if risk_pattern in command:
            is_high_risk = True
            matched.append(risk_pattern)

    if is_high_risk:
        logger.info(
            "High-risk command detected",
            extra={"command": redact_sensitive_data(command), "patterns": matched},
        )
        if not approval_token or not _validate_approval_token(approval_token):
            raise ApprovalRequiredError(
                f"Command contains high-risk patterns {matched} and requires approval"
            )

    return is_high_risk, None


def _validate_approval_token(token: str) -> bool:
    return bool(token and len(token) >= 8)


def _prepare_workspace(
    files: Optional[Dict[str, str]],
    workspace_path: Optional[str] = None,
) -> Path:
    settings = get_settings()

    base = Path(workspace_path or settings.workspace_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)

    if files:
        for filename, content in files.items():
            # prevent path traversal
            safe = Path(filename)
            if safe.is_absolute() or ".." in safe.parts:
                raise ValidationError(f"Invalid filename: {filename}")
            target = (base / safe).resolve()
            if base not in target.parents and target != base:
                raise ValidationError(f"Invalid filename (outside workspace): {filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    return base


def execute_command(
    command: str,
    *,
    files: Optional[Dict[str, str]] = None,
    workspace_path: Optional[str] = None,
    cwd: Optional[str] = None,
    approval_token: Optional[str] = None,
    timeout: Optional[int] = None,
    on_container_start: Optional[callable] = None,  # legacy name, now execution_id
) -> dict:
    """Execute a command locally.

    Returns a dict matching the previous contract:
    {execution_id, stdout, stderr, exit_code, is_high_risk, workspace_path}
    """

    is_high_risk, _ = validate_command(command, approval_token=approval_token)

    ws = _prepare_workspace(files, workspace_path=workspace_path)

    # Optional working directory (relative to workspace)
    run_cwd = ws
    if cwd:
        safe = Path(cwd)
        if safe.is_absolute() or ".." in safe.parts:
            raise ValidationError(f"Invalid cwd: {cwd}")
        run_cwd = (ws / safe).resolve()
        if ws not in run_cwd.parents and run_cwd != ws:
            raise ValidationError(f"Invalid cwd (outside workspace): {cwd}")
        run_cwd.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    exec_timeout = timeout if timeout is not None else settings.docker_timeout  # legacy config key

    execution_id = str(uuid4())

    try:
        # Start process
        proc = subprocess.Popen(
            command,
            cwd=str(run_cwd),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        with _LOCK:
            _RUNNING[execution_id] = proc

        # notify legacy callback
        if on_container_start:
            try:
                on_container_start(execution_id)
            except Exception:
                pass

        try:
            out, err = proc.communicate(timeout=exec_timeout)
            code = proc.returncode or 0
        except subprocess.TimeoutExpired:
            err = f"Execution timed out after {exec_timeout}s"
            out = ""
            code = 124
            _terminate_process(proc)

        # redact and truncate before returning/logging
        out_r = redact_sensitive_data(out)
        err_r = redact_sensitive_data(err)

        def _truncate(s: str, limit: int) -> str:
            if s is None:
                return ""
            if len(s) <= limit:
                return s
            return s[:limit] + f"\n...<truncated {len(s) - limit} chars>"

        out_r = _truncate(out_r, 8000)
        err_r = _truncate(err_r, 8000)

        return {
            "execution_id": execution_id,
            "stdout": out_r,
            "stderr": err_r,
            "exit_code": int(code),
            "is_high_risk": is_high_risk,
            "workspace_path": str(ws),
            "cwd": str(run_cwd),
        }

    except (ValidationError, ApprovalRequiredError):
        raise
    except Exception as e:
        raise ExecutionError(str(e)) from e
    finally:
        with _LOCK:
            _RUNNING.pop(execution_id, None)


def _terminate_process(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
    except Exception:
        return

    try:
        proc.wait(timeout=2)
        return
    except Exception:
        pass

    try:
        proc.kill()
    except Exception:
        pass


def cancel_execution(execution_id: str) -> bool:
    """Cancel a running execution (best-effort)."""

    with _LOCK:
        proc = _RUNNING.get(execution_id)

    if not proc:
        return False

    _terminate_process(proc)
    return True


def get_execution_status(execution_id: str) -> dict:
    with _LOCK:
        proc = _RUNNING.get(execution_id)

    if not proc:
        return {"execution_id": execution_id, "status": "not_found"}

    code = proc.poll()
    if code is None:
        return {"execution_id": execution_id, "status": "running"}

    return {"execution_id": execution_id, "status": "exited", "exit_code": int(code)}
