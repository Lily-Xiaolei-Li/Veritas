"""
Agent State Schema (B2.1 + B2.2).

Defines the strongly-typed state for the LangGraph agent.
Uses Annotated types for proper state mutation (add operator for messages).

B2.2 additions: Multi-brain routing fields (small state, rich events principle).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict
from uuid import uuid4


# ============================================================================
# B2.2 Type Definitions
# ============================================================================

# Classification reason codes (anchored criteria)
ClassificationReason = Literal[
    "ONE_STEP_QA",       # Simple question, direct answer
    "MULTI_STEP_PLAN",   # Needs planning
    "TOOL_REQUIRED",     # Needs bash execution
    "AMBIGUOUS",         # Unclear, ask user
]

# Collaboration modes (B2.2 only implements solo and consensus)
CollaborationMode = Literal["solo", "consensus"]

# Task complexity
TaskComplexity = Literal["simple", "complex"]

# Intent types for structured consensus
IntentType = Literal["answer_only", "plan_only", "run_bash", "ask_user", "escalate"]

# Decision types
DecisionType = Literal["answer", "use_tool", "ask_user", "escalate"]

# Escalation reasons
EscalationReason = Literal["MAX_ROUNDS", "BRAIN_REQUESTED"]


@dataclass
class AgentMessage:
    """
    Message in the agent conversation.

    Represents both user and assistant messages with optional tool calls.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    role: Literal["user", "assistant", "system", "tool"] = "user"
    content: str = ""
    name: Optional[str] = None  # For tool messages
    tool_call_id: Optional[str] = None  # For tool response messages
    tool_calls: Optional[List[Dict[str, Any]]] = None  # For assistant tool requests
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_llm_format(self) -> Dict[str, Any]:
        """Convert to format expected by LLM providers."""
        msg: Dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }
        if self.name:
            msg["name"] = self.name
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        return msg


@dataclass
class ToolCall:
    """Represents a pending tool call from the LLM."""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """Result from a tool execution."""
    tool_call_id: str
    tool_name: str
    output: str
    exit_code: int = 0
    duration_ms: int = 0
    error: Optional[str] = None


@dataclass
class BrainDecision:
    """
    Structured decision from a brain (B2.2).

    Used for intent-based consensus detection.
    Only decision, intent, tool_name, and target_artifacts are used for matching.
    Other fields are for display/logging only.
    """
    # Consensus-determining fields
    decision: DecisionType  # "answer", "use_tool", "ask_user", "escalate"
    intent: IntentType  # "answer_only", "plan_only", "run_bash", "ask_user", "escalate"
    tool_name: Optional[str] = None  # Only for intent == "run_bash"
    target_artifacts: List[str] = field(default_factory=list)  # Max 5 items

    # Display fields (NOT used for consensus matching)
    plan_steps: List[str] = field(default_factory=list)  # Max 5 steps
    key_risks: List[str] = field(default_factory=list)  # Max 3 risks
    summary: str = ""  # Max 500 chars for state storage

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "decision": self.decision,
            "intent": self.intent,
            "tool_name": self.tool_name,
            "target_artifacts": self.target_artifacts,
            "plan_steps": self.plan_steps,
            "key_risks": self.key_risks,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrainDecision":
        """Create from dictionary (JSON parsing)."""
        return cls(
            decision=data.get("decision", "escalate"),
            intent=data.get("intent", "escalate"),
            tool_name=data.get("tool_name"),
            target_artifacts=data.get("target_artifacts", [])[:5],  # Enforce max 5
            plan_steps=data.get("plan_steps", [])[:5],  # Enforce max 5
            key_risks=data.get("key_risks", [])[:3],  # Enforce max 3
            summary=data.get("summary", "")[:500],  # Enforce max 500 chars
        )


def add_messages(left: List[AgentMessage], right: List[AgentMessage]) -> List[AgentMessage]:
    """
    Reducer function for messages - appends new messages to existing list.

    Used with Annotated type to define how message updates are merged.
    """
    return left + right


class AgentState(TypedDict, total=False):
    """
    LangGraph state for Agent B.

    All fields are optional (total=False) to support partial updates.
    The messages field uses a reducer to append new messages.

    B2.2 Design Principle: State = Routing, Events = History.
    State fields are bounded and drive graph transitions.
    Full transcripts go to events, not state.
    """
    # Core conversation state - uses add reducer for proper accumulation
    messages: Annotated[List[AgentMessage], add_messages]

    # Run context
    run_id: str
    session_id: str

    # Graph execution tracking
    current_node: Optional[str]
    node_metadata: Optional[Dict[str, Any]]

    # Tool execution state
    pending_tool_calls: Optional[List[ToolCall]]
    tool_results: Optional[List[ToolResult]]

    # Error tracking
    error: Optional[str]
    error_recoverable: Optional[bool]

    # Response accumulation (for streaming)
    partial_response: Optional[str]

    # Checkpoint metadata
    checkpoint_count: Optional[int]

    # ========================================================================
    # B2.2: Multi-Brain Routing Fields (all bounded)
    # ========================================================================

    # Classification results
    collaboration_mode: Optional[CollaborationMode]  # "solo" or "consensus"
    task_complexity: Optional[TaskComplexity]  # "simple" or "complex"
    current_objective: Optional[str]  # Max 500 chars, enforced by cap_text()
    classification_reason: Optional[ClassificationReason]

    # Deliberation routing (NOT transcripts - those go to events)
    deliberation_round: Optional[int]  # Default 0, internal 0-based
    max_deliberation_rounds: Optional[int]  # Default 3

    # Consensus routing (structured, not free-text)
    last_intent: Optional[IntentType]
    consensus_reached: Optional[bool]
    escalation_required: Optional[bool]
    escalation_reason: Optional[EscalationReason]

    # Position summaries (HARD CAPPED via cap_text())
    brain_1_summary: Optional[str]  # Max 500 chars
    brain_2_summary: Optional[str]  # Max 500 chars

    # Tool execution state (B2.2b)
    target_artifacts: Optional[List[str]]  # Max 5 items, each max 200 chars


def create_initial_state(
    run_id: str,
    session_id: str,
    user_message: str,
    system_context: Optional[str] = None,
    max_deliberation_rounds: int = 3,
) -> AgentState:
    """
    Create the initial agent state for a new run.

    Args:
        run_id: Unique identifier for this run
        session_id: Session this run belongs to
        user_message: The user's input message
        max_deliberation_rounds: Max rounds before escalation (default 3)

    Returns:
        Initial AgentState ready for graph execution
    """
    messages: List[AgentMessage] = []
    if system_context:
        messages.append(AgentMessage(role="system", content=system_context))
    messages.append(AgentMessage(role="user", content=user_message))

    return AgentState(
        messages=messages,
        run_id=run_id,
        session_id=session_id,
        current_node="receive",
        node_metadata={},
        pending_tool_calls=None,
        tool_results=None,
        error=None,
        error_recoverable=None,
        partial_response=None,
        checkpoint_count=0,
        # B2.2: Multi-brain routing fields
        collaboration_mode=None,
        task_complexity=None,
        current_objective=None,
        classification_reason=None,
        deliberation_round=0,
        max_deliberation_rounds=max_deliberation_rounds,
        last_intent=None,
        consensus_reached=None,
        escalation_required=None,
        escalation_reason=None,
        brain_1_summary=None,
        brain_2_summary=None,
        target_artifacts=None,
    )
