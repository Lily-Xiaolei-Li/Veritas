from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import get_settings
from app.tools.registry import register_tool
from app.tools.types import ToolResult, ToolSpec


def _resolve_in_workspace(rel_path: str) -> Path:
    settings = get_settings()
    ws = Path(settings.workspace_dir).resolve()
    ws.mkdir(parents=True, exist_ok=True)

    p = Path(rel_path)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("Path must be relative to workspace")

    full = (ws / p).resolve()
    if ws not in full.parents and full != ws:
        raise ValueError("Path escapes workspace")

    return full


@register_tool(
    ToolSpec(
        name="file_read",
        description="Read a text file from the workspace.",
        args_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative workspace path"},
                "max_bytes": {"type": "integer", "default": 200000},
            },
            "required": ["path"],
        },
        risk_level="low",
    )
)
def file_read(args: dict[str, Any]) -> ToolResult:
    try:
        path = str(args.get("path") or "")
        max_bytes = int(args.get("max_bytes") or 200000)
        full = _resolve_in_workspace(path)
        if not full.exists() or not full.is_file():
            return ToolResult(success=False, error=f"File not found: {path}")

        data = full.read_bytes()
        truncated = False
        if len(data) > max_bytes:
            data = data[:max_bytes]
            truncated = True

        # best-effort decode
        text = data.decode("utf-8", errors="replace")
        return ToolResult(success=True, output={"path": path, "text": text, "truncated": truncated})
    except Exception as e:
        return ToolResult(success=False, error=f"{type(e).__name__}: {e}")


@register_tool(
    ToolSpec(
        name="file_write",
        description="Write a text file to the workspace.",
        args_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative workspace path"},
                "text": {"type": "string"},
                "overwrite": {"type": "boolean", "default": True},
            },
            "required": ["path", "text"],
        },
        risk_level="medium",
    )
)
def file_write(args: dict[str, Any]) -> ToolResult:
    try:
        path = str(args.get("path") or "")
        text = str(args.get("text") or "")
        overwrite = bool(args.get("overwrite") if args.get("overwrite") is not None else True)

        full = _resolve_in_workspace(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        if full.exists() and not overwrite:
            return ToolResult(success=False, error=f"File exists and overwrite=false: {path}")

        full.write_text(text, encoding="utf-8")
        return ToolResult(success=True, output={"path": path, "bytes_written": len(text.encode('utf-8'))})
    except Exception as e:
        return ToolResult(success=False, error=f"{type(e).__name__}: {e}")
