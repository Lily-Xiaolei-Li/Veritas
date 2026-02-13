"""
SSE Event Schemas (B1.4 - Kill Switch)

Pydantic models for all Server-Sent Event types. These define the contract
between backend streaming and frontend consumption.

Event Types:
- token: Streaming text content (chunked, not char-by-char)
- tool_start: Tool invocation beginning
- tool_end: Tool invocation completed
- error: Error during processing
- done: Stream completed
- run_terminated: Run was terminated via kill switch (B1.4)
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TerminationReason(str, Enum):
    """Reason for run termination."""
    USER_CANCEL = "user_cancel"
    TIMEOUT = "timeout"
    ERROR = "error"
    SYSTEM = "system"


class CancelStatus(str, Enum):
    """Status of cancellation operation."""
    TASK_CANCELLED = "task_cancelled"
    CONTAINER_STOPPED = "container_stopped"
    CONTAINER_KILLED = "container_killed"
    ALREADY_STOPPED = "already_stopped"
    NONE = "none"


class TokenEvent(BaseModel):
    """
    Streaming text token event.

    Sent during agent reasoning to stream text content in chunks.
    Frontend should append content to display.
    """
    run_id: str = Field(..., description="Unique identifier for this run/execution")
    seq: int = Field(..., ge=1, description="Monotonically increasing sequence number per run")
    content: str = Field(..., description="Text chunk to append (typically 20-30 chars)")


class ToolStartEvent(BaseModel):
    """
    Tool invocation start event.

    Sent when agent begins executing a tool. Frontend should show
    "running" indicator in console panel.
    """
    run_id: str = Field(..., description="Unique identifier for this run/execution")
    seq: int = Field(..., ge=1, description="Monotonically increasing sequence number per run")
    tool_call_id: str = Field(..., description="Unique identifier for this tool invocation")
    tool_name: str = Field(..., description="Name of the tool being executed")
    input_preview: str = Field(
        ...,
        max_length=200,
        description="Truncated preview of tool input (max 200 chars)"
    )


class ToolEndEvent(BaseModel):
    """
    Tool invocation end event.

    Sent when tool execution completes. Frontend should update
    status from "running" to "completed" or "failed".
    """
    run_id: str = Field(..., description="Unique identifier for this run/execution")
    seq: int = Field(..., ge=1, description="Monotonically increasing sequence number per run")
    tool_call_id: str = Field(..., description="Unique identifier for this tool invocation")
    exit_code: int = Field(..., description="Tool exit code (0 = success)")
    output_preview: str = Field(
        ...,
        max_length=500,
        description="Truncated preview of tool output (max 500 chars)"
    )
    duration_ms: int = Field(..., ge=0, description="Execution duration in milliseconds")


class ErrorEvent(BaseModel):
    """
    Error event.

    Sent when an error occurs during processing. Frontend should
    display in console panel with red styling.
    """
    run_id: str = Field(..., description="Unique identifier for this run/execution")
    seq: int = Field(..., ge=1, description="Monotonically increasing sequence number per run")
    message: str = Field(..., description="Human-readable error message")
    recoverable: bool = Field(
        ...,
        description="Whether the error is recoverable (hint to UI for retry behavior)"
    )


class DoneEvent(BaseModel):
    """
    Stream completion event.

    Sent when agent processing completes. Frontend should finalize
    streaming message and clear streaming indicator.
    """
    run_id: str = Field(..., description="Unique identifier for this run/execution")
    seq: int = Field(..., ge=1, description="Final sequence number for this run")


class RunTerminatedEvent(BaseModel):
    """
    Run termination event (B1.4 - Kill Switch).

    Sent when a run is terminated via kill switch or system action.
    Frontend should:
    - Clear streaming state
    - Mark any running tools as failed
    - Show termination banner with reason
    """
    run_id: str = Field(..., description="Unique identifier for the terminated run")
    session_id: str = Field(..., description="Session the run belonged to")
    terminated_at: datetime = Field(..., description="Timestamp of termination")
    reason: TerminationReason = Field(..., description="Why the run was terminated")
    cancel_status: CancelStatus = Field(
        ...,
        description="What was cancelled (task, container, etc.)"
    )
    latency_ms: float = Field(
        ...,
        ge=0,
        description="Time from termination request to completion in milliseconds"
    )
    message: Optional[str] = Field(
        None,
        description="Human-readable message about the termination"
    )
