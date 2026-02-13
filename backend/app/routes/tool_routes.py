"""Tool Framework routes (B1.8).

Provides:
- GET /tools : list registered tools + schemas
- POST /tools/execute : execute a tool with args

Notes:
- This is the platform-level tool system (not the old B2.2b bash demo).
- No Docker dependency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

# ensure built-in tools are registered
import app.tools  # noqa: F401
from app.database import get_database
from app.logging_config import get_logger, redact_sensitive_data
from app.models import AuditLog
from app.routes.auth_routes import require_auth
from app.routes.message_routes import get_or_create_session_queue
from app.tools.registry import execute_tool, list_tools

router = APIRouter(prefix="/tools")
logger = get_logger("tools")


class ToolSpecResponse(BaseModel):
    name: str
    description: str
    args_schema: dict[str, Any]
    risk_level: str
    timeout_seconds: int
    requires_approval: bool


class ToolListResponse(BaseModel):
    tools: list[ToolSpecResponse]


class ToolExecuteRequest(BaseModel):
    tool_name: str = Field(..., min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None
    run_id: Optional[str] = None


class ToolExecuteResponse(BaseModel):
    success: bool
    output: Any = None
    error: Optional[str] = None
    tool_name: str
    tool_call_id: str
    started_at: str
    finished_at: str


@router.get("", response_model=ToolListResponse)
async def get_tools(current_user: dict = Depends(require_auth)):
    specs = list_tools()
    return ToolListResponse(
        tools=[
            ToolSpecResponse(
                name=s.name,
                description=s.description,
                args_schema=s.args_schema,
                risk_level=s.risk_level,
                timeout_seconds=s.timeout_seconds,
                requires_approval=s.requires_approval,
            )
            for s in specs
        ]
    )


@router.post("/execute", response_model=ToolExecuteResponse)
async def post_execute_tool(
    request: ToolExecuteRequest,
    current_user: dict = Depends(require_auth),
):
    started = datetime.now(timezone.utc)
    tool_call_id = str(uuid4())

    # SSE: tool_start (best-effort)
    try:
        if request.session_id:
            q = get_or_create_session_queue(request.session_id)
            q.put_nowait(
                (
                    "tool_start",
                    {
                        "tool_call_id": tool_call_id,
                        "tool_name": request.tool_name,
                        "input_preview": redact_sensitive_data(str(request.args))[:200],
                    },
                    None,
                )
            )
    except Exception:
        pass

    try:
        result = await execute_tool(request.tool_name, request.args)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    finished = datetime.now(timezone.utc)

    # SSE: tool_end (best-effort)
    try:
        if request.session_id:
            q = get_or_create_session_queue(request.session_id)
            duration_ms = int((finished - started).total_seconds() * 1000)
            out_preview = redact_sensitive_data(str(result.output if result.success else result.error))[:500]
            q.put_nowait(
                (
                    "tool_end",
                    {
                        "tool_call_id": tool_call_id,
                        "exit_code": 0 if result.success else 1,
                        "output_preview": out_preview,
                        "duration_ms": duration_ms,
                    },
                    None,
                )
            )
    except Exception:
        pass

    # audit log (best-effort) - avoid taking DB dependency for tool execution
    try:
        db = get_database()
        if db.is_configured:
            if not db._engine:
                await db.initialize()
            async with db.session() as s:
                entry = AuditLog(
                    id=str(uuid4()),
                    actor="user",
                    actor_id=current_user.get("user_id", "unknown"),
                    action="tool_execute",
                    resource=f"tool:{request.tool_name}",
                    session_id=request.session_id,
                    message=f"Tool executed: {request.tool_name}",
                    details={
                        "tool_name": request.tool_name,
                        "args": redact_sensitive_data(str(request.args))[:2000],
                        "run_id": request.run_id,
                        "success": result.success,
                    },
                    success=bool(result.success),
                )
                s.add(entry)
    except Exception:
        pass

    return ToolExecuteResponse(
        success=bool(result.success),
        output=result.output,
        error=result.error,
        tool_name=request.tool_name,
        tool_call_id=tool_call_id,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
    )
