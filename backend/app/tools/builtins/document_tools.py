from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import get_settings
from app.services.document_processing_service import (
    convert_file_to_artifact_payloads,
    generate_docx_bytes,
    generate_xlsx_bytes,
)
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
        name="document_read",
        description="Extract text/data from a document in the workspace (docx/xlsx/csv/pdf/txt/md/json).",
        args_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative workspace path"},
                "max_bytes": {"type": "integer", "default": 200000},
            },
            "required": ["path"],
        },
        risk_level="low",
        timeout_seconds=60,
    )
)
def document_read(args: dict[str, Any]) -> ToolResult:
    try:
        rel_path = str(args.get("path") or "")
        max_bytes = int(args.get("max_bytes") or 200000)

        full = _resolve_in_workspace(rel_path)
        if not full.exists() or not full.is_file():
            return ToolResult(success=False, error=f"File not found: {rel_path}")

        payloads = convert_file_to_artifact_payloads(str(full), imported_via="tool:document_read")

        outputs: list[dict[str, Any]] = []
        for p in payloads:
            content = p.get("content") or b""
            if not isinstance(content, (bytes, bytearray)):
                content = str(content).encode("utf-8")

            truncated = False
            if len(content) > max_bytes:
                content = content[:max_bytes]
                truncated = True

            text = bytes(content).decode("utf-8", errors="replace")
            meta = dict(p.get("artifact_meta") or {})
            # avoid leaking absolute paths in tool output
            meta.pop("source_path", None)

            outputs.append(
                {
                    "filename": p.get("filename"),
                    "text": text,
                    "truncated": truncated,
                    "meta": meta,
                }
            )

        return ToolResult(success=True, output={"path": rel_path, "outputs": outputs})
    except Exception as e:
        return ToolResult(success=False, error=f"{type(e).__name__}: {e}")


@register_tool(
    ToolSpec(
        name="document_write",
        description="Generate a document (docx/xlsx) into the workspace.",
        args_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative workspace path (will add extension if missing)"},
                "format": {"type": "string", "enum": ["docx", "xlsx"], "description": "Document format"},
                "text": {"type": "string", "description": "For docx: plain text content"},
                "sheets": {
                    "type": "array",
                    "description": "For xlsx: sheet payloads [{name, headers, rows}]",
                },
                "overwrite": {"type": "boolean", "default": True},
            },
            "required": ["path", "format"],
        },
        risk_level="medium",
        timeout_seconds=60,
    )
)
def document_write(args: dict[str, Any]) -> ToolResult:
    try:
        rel_path = str(args.get("path") or "")
        fmt = str(args.get("format") or "").lower()
        overwrite = bool(args.get("overwrite") if args.get("overwrite") is not None else True)

        if fmt not in {"docx", "xlsx"}:
            return ToolResult(success=False, error="format must be one of: docx, xlsx")

        if fmt == "docx" and not rel_path.lower().endswith(".docx"):
            rel_path = f"{rel_path}.docx"
        if fmt == "xlsx" and not rel_path.lower().endswith(".xlsx"):
            rel_path = f"{rel_path}.xlsx"

        full = _resolve_in_workspace(rel_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        if full.exists() and not overwrite:
            return ToolResult(success=False, error=f"File exists and overwrite=false: {rel_path}")

        if fmt == "docx":
            text = str(args.get("text") or "")
            data = generate_docx_bytes(text)
        else:
            sheets = args.get("sheets") or []
            if not isinstance(sheets, list):
                return ToolResult(success=False, error="sheets must be an array")
            data = generate_xlsx_bytes(sheets=sheets)

        full.write_bytes(data)
        return ToolResult(
            success=True,
            output={"path": rel_path, "bytes_written": len(data), "format": fmt},
        )
    except Exception as e:
        return ToolResult(success=False, error=f"{type(e).__name__}: {e}")
