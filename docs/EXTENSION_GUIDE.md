# Extension Guide (Tools)

This repo implements a small tool registry (B1.8).

## 1) Where tools live
- Registry: `backend/app/tools/registry.py`
- Types/spec: `backend/app/tools/types.py`
- Built-ins: `backend/app/tools/builtins/`
- API: `backend/app/routes/tool_routes.py`

## 2) Add a new tool (example)
Create a module under `backend/app/tools/builtins/my_tool.py`:
```py
from typing import Any
from app.tools.registry import register_tool
from app.tools.types import ToolResult, ToolSpec

@register_tool(
  ToolSpec(
    name="my_tool",
    description="Does a thing.",
    args_schema={"type":"object","properties":{"x":{"type":"string"}},"required":["x"]},
    risk_level="low",
    timeout_seconds=30,
    requires_approval=False,
  )
)
def my_tool(args: dict[str, Any]) -> ToolResult:
  x = str(args.get("x") or "")
  return ToolResult(success=True, output={"echo": x})
```

Register it in `backend/app/tools/builtins/__init__.py`:
```py
from app.tools.builtins.my_tool import my_tool  # noqa: F401
```

## 3) Test it
- Add a unit test under `backend/tests/` calling `execute_tool("my_tool", {...})`.
- Optional: add an API smoke assertion using `/api/v1/tools/execute`.

## 4) UI visibility
Tool events are streamed via SSE as `tool_start` / `tool_end` (Console panel).
