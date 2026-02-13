"""
Command execution routes for Agent B (B0.1, B0.2).

This repo enforces **NO DOCKER**. Commands run locally with safety controls.
"""

import time
from typing import Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.executor import (
    ApprovalRequiredError,
    ExecutionError,
    ValidationError,
    execute_command,
)
from app.logging_config import get_logger, redact_sensitive_data
from app.metrics import EXEC_COMMANDS_TOTAL, EXEC_DURATION_SECONDS, EXEC_RUNNING
from app.models import AuditLog
from app.routes.auth_routes import require_auth

router = APIRouter()
logger = get_logger("exec_routes")


# Request/Response Models

class ExecutionRequest(BaseModel):
    """Request model for command execution."""
    command: str = Field(..., min_length=1, description="Command to execute")
    files: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional files to create in workspace (filename -> content)"
    )
    workspace_path: Optional[str] = Field(
        default=None,
        description="Optional custom workspace path"
    )
    approval_token: Optional[str] = Field(
        default=None,
        description="Approval token for high-risk commands"
    )
    timeout: Optional[int] = Field(
        default=None,
        ge=1,
        le=3600,
        description="Optional custom timeout in seconds"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID for audit logging"
    )
    run_id: Optional[str] = Field(
        default=None,
        description="Optional run ID for kill switch tracking (B1.4)"
    )


class ExecutionResponse(BaseModel):
    """Response model for command execution."""
    execution_id: str
    stdout: str
    stderr: str
    exit_code: int
    is_high_risk: bool
    workspace_path: str
    approval_required: bool = False


class ExecutionErrorResponse(BaseModel):
    """Error response model."""
    error: str
    execution_id: Optional[str] = None
    approval_required: bool = False


# Endpoints

@router.post("/exec", response_model=ExecutionResponse, status_code=status.HTTP_200_OK)
async def execute(
    request_data: ExecutionRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_auth),
):
    """
    Execute a command locally (no Docker).

    Requires authentication if AUTH_ENABLED=true.

    Security features:
    - Network isolation by default
    - Resource limits (memory, CPU)
    - Timeout enforcement
    - Command validation and blocklist
    - High-risk command detection and approval
    - Output redaction
    - Audit logging

    Returns:
        ExecutionResponse with stdout, stderr, exit_code, and execution metadata

    Raises:
        HTTPException 400: If command is blocked or approval is required
        HTTPException 401: If authentication fails
        HTTPException 500: If execution fails
    """
    execution_id = None
    is_high_risk = False
    exec_start_time = None

    # Get client IP for audit logging
    client_ip = http_request.client.host if http_request.client else None

    # Container tracking callback for kill switch (B1.4)
    def on_container_start(container_id: str) -> None:
        if request_data.run_id:
            import asyncio

            from app.services import run_registry

            # Register container with run_registry
            # Note: This is called from sync code, so we need to handle async carefully
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule the coroutine to run in the existing loop
                    asyncio.create_task(
                        run_registry.register_container(request_data.run_id, container_id)
                    )
                else:
                    loop.run_until_complete(
                        run_registry.register_container(request_data.run_id, container_id)
                    )
            except Exception as e:
                logger.warning(f"Failed to register container for kill switch: {e}")

    try:
        # Track running executions (B7.2)
        EXEC_RUNNING.inc()
        exec_start_time = time.perf_counter()

        # Execute command
        result = execute_command(
            command=request_data.command,
            files=request_data.files,
            workspace_path=request_data.workspace_path,
            approval_token=request_data.approval_token,
            timeout=request_data.timeout,
            run_id=request_data.run_id,
            on_container_start=on_container_start if request_data.run_id else None,
        )

        # Record execution duration (B7.2)
        exec_duration = time.perf_counter() - exec_start_time
        EXEC_DURATION_SECONDS.observe(exec_duration)
        EXEC_COMMANDS_TOTAL.labels(status="success").inc()

        execution_id = result["execution_id"]
        is_high_risk = result["is_high_risk"]

        # Log successful execution to audit_log
        audit_entry = AuditLog(
            id=str(uuid4()),
            actor="user",
            actor_id=current_user.get("user_id", "unknown"),
            action="command_execution",
            resource=f"execution:{execution_id}",
            session_id=request_data.session_id,
            ip_address=client_ip,
            message=f"Command executed: {redact_sensitive_data(request_data.command[:100])}",
            details={
                "execution_id": execution_id,
                "exit_code": result["exit_code"],
                "is_high_risk": is_high_risk,
                "approval_provided": bool(request_data.approval_token),
                "timeout": request_data.timeout,
            },
            success=True,
        )
        session.add(audit_entry)
        await session.commit()

        logger.info(
            f"Command execution successful: {execution_id}",
            extra={
                "execution_id": execution_id,
                "user_id": current_user.get("user_id"),
                "exit_code": result["exit_code"],
                "is_high_risk": is_high_risk,
            }
        )

        return ExecutionResponse(
            execution_id=result["execution_id"],
            stdout=result["stdout"],
            stderr=result["stderr"],
            exit_code=result["exit_code"],
            is_high_risk=result["is_high_risk"],
            workspace_path=result["workspace_path"],
            approval_required=False,
        )

    except ValidationError as e:
        # Command blocked by validation - NO duration recorded (B7.2)
        EXEC_COMMANDS_TOTAL.labels(status="blocked").inc()

        logger.warning(
            f"Command validation failed: {e}",
            extra={
                "command": redact_sensitive_data(request_data.command),
                "user_id": current_user.get("user_id"),
            }
        )

        # Log failed execution to audit_log
        audit_entry = AuditLog(
            id=str(uuid4()),
            actor="user",
            actor_id=current_user.get("user_id", "unknown"),
            action="command_execution_blocked",
            resource=f"command:{redact_sensitive_data(request_data.command[:100])}",
            session_id=request_data.session_id,
            ip_address=client_ip,
            message=f"Command blocked: {str(e)}",
            details={
                "error": str(e),
                "command": redact_sensitive_data(request_data.command),
            },
            success=False,
        )
        session.add(audit_entry)
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except ApprovalRequiredError as e:
        # High-risk command requires approval - NO duration recorded (B7.2)
        EXEC_COMMANDS_TOTAL.labels(status="approval_required").inc()

        logger.warning(
            f"Approval required: {e}",
            extra={
                "command": redact_sensitive_data(request_data.command),
                "user_id": current_user.get("user_id"),
            }
        )

        # Log approval requirement to audit_log
        audit_entry = AuditLog(
            id=str(uuid4()),
            actor="user",
            actor_id=current_user.get("user_id", "unknown"),
            action="command_execution_approval_required",
            resource=f"command:{redact_sensitive_data(request_data.command[:100])}",
            session_id=request_data.session_id,
            ip_address=client_ip,
            message=f"High-risk command requires approval: {str(e)}",
            details={
                "error": str(e),
                "command": redact_sensitive_data(request_data.command),
                "approval_provided": bool(request_data.approval_token),
            },
            success=False,
        )
        session.add(audit_entry)
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": str(e),
                "approval_required": True,
            }
        )

    except ExecutionError as e:
        # Execution failed - record duration if we got to execution (B7.2)
        EXEC_COMMANDS_TOTAL.labels(status="failure").inc()
        if exec_start_time is not None:
            exec_duration = time.perf_counter() - exec_start_time
            EXEC_DURATION_SECONDS.observe(exec_duration)

        logger.error(
            f"Command execution failed: {e}",
            extra={
                "execution_id": execution_id,
                "command": redact_sensitive_data(request_data.command),
                "user_id": current_user.get("user_id"),
            }
        )

        # Log failed execution to audit_log
        audit_entry = AuditLog(
            id=str(uuid4()),
            actor="user",
            actor_id=current_user.get("user_id", "unknown"),
            action="command_execution_failed",
            resource=f"execution:{execution_id}" if execution_id else "unknown",
            session_id=request_data.session_id,
            ip_address=client_ip,
            message=f"Command execution failed: {str(e)}",
            details={
                "execution_id": execution_id,
                "error": str(e),
                "command": redact_sensitive_data(request_data.command),
            },
            success=False,
        )
        session.add(audit_entry)
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        # Unexpected error - record duration if we got to execution (B7.2)
        EXEC_COMMANDS_TOTAL.labels(status="failure").inc()
        if exec_start_time is not None:
            exec_duration = time.perf_counter() - exec_start_time
            EXEC_DURATION_SECONDS.observe(exec_duration)

        logger.error(
            f"Unexpected error during command execution: {e}",
            exc_info=True,
            extra={
                "execution_id": execution_id,
                "command": redact_sensitive_data(request_data.command),
                "user_id": current_user.get("user_id"),
            }
        )

        # Log unexpected error to audit_log
        audit_entry = AuditLog(
            id=str(uuid4()),
            actor="user",
            actor_id=current_user.get("user_id", "unknown"),
            action="command_execution_error",
            resource=f"execution:{execution_id}" if execution_id else "unknown",
            session_id=request_data.session_id,
            ip_address=client_ip,
            message=f"Unexpected error during command execution: {str(e)}",
            details={
                "execution_id": execution_id,
                "error": str(e),
                "command": redact_sensitive_data(request_data.command),
            },
            success=False,
        )
        session.add(audit_entry)
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    finally:
        # Always decrement running counter (B7.2)
        EXEC_RUNNING.dec()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint for execution service.

    Does not require authentication.
    """
    # No Docker dependency: execution health is "healthy" if server is up.
    return {
        "status": "healthy",
        "execution": {"ok": True, "detail": "Local execution enabled"},
    }
