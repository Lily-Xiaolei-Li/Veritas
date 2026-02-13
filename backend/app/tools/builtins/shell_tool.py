from __future__ import annotations

from typing import Any

from app.executor import (
    ApprovalRequiredError,
    ExecutionError,
    ValidationError,
    execute_command,
)
from app.tools.registry import register_tool
from app.tools.types import ToolResult, ToolSpec


@register_tool(
    ToolSpec(
        name="shell_exec",
        description="Execute a shell command locally with safety controls (workspace-scoped).",
        args_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string", "description": "Working directory (relative to workspace)"},
                "timeout": {"type": "integer", "minimum": 1, "maximum": 3600},
                "approval_token": {"type": "string", "description": "Required for high-risk commands"},
            },
            "required": ["command"],
        },
        risk_level="high",
        timeout_seconds=300,
        requires_approval=False,
    )
)
def shell_exec(args: dict[str, Any]) -> ToolResult:
    command = str(args.get("command") or "")
    cwd = args.get("cwd")
    timeout = args.get("timeout")
    approval_token = args.get("approval_token")

    try:
        r = execute_command(
            command,
            cwd=str(cwd) if cwd is not None else None,
            timeout=int(timeout) if timeout is not None else None,
            approval_token=str(approval_token) if approval_token is not None else None,
        )
        return ToolResult(
            success=(r.get("exit_code", 1) == 0),
            output={
                "stdout": r.get("stdout", ""),
                "stderr": r.get("stderr", ""),
                "exit_code": r.get("exit_code", 1),
                "execution_id": r.get("execution_id"),
                "cwd": r.get("cwd"),
            },
            error=None if r.get("exit_code", 1) == 0 else "Non-zero exit code",
        )

    except ApprovalRequiredError as e:
        return ToolResult(success=False, error=str(e))
    except ValidationError as e:
        return ToolResult(success=False, error=str(e))
    except ExecutionError as e:
        return ToolResult(success=False, error=str(e))
    except Exception as e:
        return ToolResult(success=False, error=f"{type(e).__name__}: {e}")
