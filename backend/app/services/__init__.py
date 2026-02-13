"""
Services package for Agent B.

Contains:
- run_registry: In-memory registry for tracking active runs (B1.4)
- termination_service: Kill switch termination logic (B1.4)
"""

from app.services.run_registry import (
    RunResources,
    RunRegistry,
    get_run_registry,
    set_active_run,
    get_active_run,
    get_run_resources,
    register_task,
    register_container,
    is_cancelled,
    mark_cancelled,
    clear_run,
)

from app.services.termination_service import (
    TerminationResult,
    terminate_session,
)

__all__ = [
    # run_registry
    "RunResources",
    "RunRegistry",
    "get_run_registry",
    "set_active_run",
    "get_active_run",
    "get_run_resources",
    "register_task",
    "register_container",
    "is_cancelled",
    "mark_cancelled",
    "clear_run",
    # termination_service
    "TerminationResult",
    "terminate_session",
]
