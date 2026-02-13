"""
Agent runtime package for Agent B (B2.1 - LangGraph Runtime Integration).

This package contains the LangGraph-based agent implementation:
- state.py: AgentState schema with typed fields
- events.py: EventEmitter for SSE + DB persistence
- checkpointer.py: PostgreSQL checkpoint persistence
- reconciliation.py: Startup crash recovery
- nodes.py: Graph node implementations
- graph.py: LangGraph state machine definition
"""

from .state import AgentState, AgentMessage
from .events import EventEmitter, create_event_emitter
from .checkpointer import (
    initialize_checkpointer,
    shutdown_checkpointer,
    get_checkpointer,
)
from .reconciliation import reconcile_stale_runs
from .graph import create_agent_graph

__all__ = [
    "AgentState",
    "AgentMessage",
    "EventEmitter",
    "create_event_emitter",
    "initialize_checkpointer",
    "shutdown_checkpointer",
    "get_checkpointer",
    "reconcile_stale_runs",
    "create_agent_graph",
]
