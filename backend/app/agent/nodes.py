"""
LangGraph Node Implementations (B2.1 + B2.2).

Nodes for the agent graph:

B2.1 (original minimal graph):
- receive: Accept and validate user input
- process: Call LLM to generate response (default provider)
- respond: Finalize and emit response

B2.2 (multi-brain):
- classify_task: Classify task complexity and route
- process_b1: Solo mode processing by Brain 1
- deliberation: Multi-brain deliberation (B2 proposes, B1 reviews)
- check_consensus: Check if brains agreed and route
- tool_execute: Execute bash tools (B2.2b)

Each node:
- Checks cancellation before expensive operations
- Emits events via EventEmitter
- Updates state according to LangGraph conventions
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.llm.client import llm_complete
from app.llm.types import LLMMessage, LLMOptions

from .state import AgentState, AgentMessage, BrainDecision
from .events import EventEmitter
from .utils import cap_text, cap_list_items, extract_latest_user_message
from .prompts import (
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_USER_TEMPLATE,
    BRAIN1_SOLO_SYSTEM_PROMPT,
    BRAIN1_SOLO_USER_TEMPLATE,
    BRAIN1_CLARIFY_SYSTEM_PROMPT,
    BRAIN1_CLARIFY_USER_TEMPLATE,
    BRAIN2_DECISION_SYSTEM_PROMPT,
    BRAIN2_DECISION_USER_TEMPLATE,
    BRAIN1_REVIEW_SYSTEM_PROMPT,
    BRAIN1_REVIEW_USER_TEMPLATE,
    FINAL_RESPONSE_SYSTEM_PROMPT,
    FINAL_RESPONSE_USER_TEMPLATE,
)
from .brains import (
    call_brain_1,
    call_brain_2,
    call_brain_1_for_decision,
    call_brain_2_for_decision,
    parse_json_response,
    BrainCallError,
)
from .consensus import check_consensus, merge_decisions, should_escalate

logger = get_logger("nodes")


class NodeContext:
    """Context passed to all nodes for shared resources.

    Provides access to:
    - EventEmitter for SSE + DB events
    - Cancellation checking
    - Database session factory for LLM calls
    - Optional explicit LLM selection for this run
    """

    def __init__(
        self,
        emitter: EventEmitter,
        is_cancelled_fn,  # async callable returning bool
        session_factory=None,  # For LLM cost tracking
        run_id: str = None,
        session_id: str = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        llm_strict: bool = False,
    ):
        self.emitter = emitter
        self._is_cancelled = is_cancelled_fn
        self.session_factory = session_factory
        self.run_id = run_id
        self.session_id = session_id
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.llm_strict = llm_strict

    async def is_cancelled(self) -> bool:
        """Check if the run has been cancelled."""
        return await self._is_cancelled()

    async def check_cancellation(self, node_name: str) -> bool:
        """
        Check cancellation and emit termination event if cancelled.

        Returns True if cancelled (caller should abort).
        """
        if await self._is_cancelled():
            logger.info(f"Run cancelled at node {node_name}")
            await self.emitter.emit_run_terminated("user_requested")
            return True
        return False


async def receive_node(
    state: AgentState,
    context: NodeContext,
) -> Dict[str, Any]:
    """
    Receive node: Entry point for new messages.

    Validates the input state and prepares for processing.
    This is mostly a pass-through for the minimal graph.
    """
    if await context.check_cancellation("receive"):
        return {"error": "cancelled", "current_node": "receive"}

    logger.debug(f"Receive node processing run {state.get('run_id')}")

    # Validate we have messages
    messages = state.get("messages", [])
    if not messages:
        await context.emitter.emit_error("No messages in state", recoverable=False)
        return {"error": "no_messages", "current_node": "receive"}

    # Update current node
    return {"current_node": "process"}


async def process_node(
    state: AgentState,
    context: NodeContext,
) -> Dict[str, Any]:
    """
    Process node: Call LLM to generate a response.

    This node:
    - Converts agent messages to LLM format
    - Calls the LLM service
    - Streams tokens to the EventEmitter
    - Returns the complete response
    """
    if await context.check_cancellation("process"):
        return {"error": "cancelled", "current_node": "process"}

    run_id = state.get("run_id", "unknown")
    session_id = state.get("session_id", "unknown")

    logger.debug(f"Process node executing for run {run_id}")

    # Convert agent messages to LLM format
    messages = state.get("messages", [])
    llm_messages = []

    for msg in messages:
        if isinstance(msg, AgentMessage):
            llm_messages.append(LLMMessage(
                role=msg.role,
                content=msg.content,
            ))
        elif isinstance(msg, dict):
            llm_messages.append(LLMMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
            ))

    if not llm_messages:
        await context.emitter.emit_error("No messages to process", recoverable=False)
        return {"error": "no_messages", "current_node": "process"}

    try:
        # Check cancellation before LLM call
        if await context.check_cancellation("process"):
            return {"error": "cancelled", "current_node": "process"}

        # Configure LLM options
        from app.config import get_settings
        from app.llm.types import ProviderType

        settings = get_settings()

        # Allow explicit per-run model override
        model = (context.llm_model or "").strip() or settings.llm_default_model

        options = LLMOptions(
            model=model,
            temperature=0.7,
            max_tokens=2048,
            run_id=context.run_id,
            session_id=context.session_id,
        )

        preferred_provider = None
        if context.llm_provider:
            try:
                preferred_provider = ProviderType(str(context.llm_provider).strip())
            except Exception:
                preferred_provider = None

        # Import here to avoid circular dependency
        from app.database import get_database

        db = get_database()

        # Make LLM call
        # Note: llm_complete handles provider selection and fallback
        async with db.session() as llm_session:
            response = await llm_complete(
                messages=llm_messages,
                options=options,
                db_session=llm_session,
                session_factory=context.session_factory,
                preferred_provider=preferred_provider,
                strict_provider=bool(context.llm_strict),
            )

        # Check cancellation after LLM call
        if await context.check_cancellation("process"):
            return {"error": "cancelled", "current_node": "process"}

        # Stream the response content as tokens
        content = response.content or ""

        # Simulate streaming by chunking the response
        chunk_size = 25
        for i in range(0, len(content), chunk_size):
            # Check cancellation periodically during streaming
            if i > 0 and i % 100 == 0:
                if await context.check_cancellation("process"):
                    return {"error": "cancelled", "current_node": "process"}

            chunk = content[i:i + chunk_size]
            await context.emitter.emit_token(chunk)
            await asyncio.sleep(0.02)  # Small delay for natural streaming feel

        logger.debug(f"Process node completed for run {run_id}, response length: {len(content)}")

        # Return the new assistant message to add to state
        assistant_message = AgentMessage(
            role="assistant",
            content=content,
        )

        return {
            "messages": [assistant_message],
            "current_node": "respond",
            "partial_response": content,
        }

    except Exception as e:
        error_msg = f"LLM processing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await context.emitter.emit_error(error_msg, recoverable=True, error_type="llm_error")
        return {
            "error": error_msg,
            "error_recoverable": True,
            "current_node": "process",
        }


async def respond_node(
    state: AgentState,
    context: NodeContext,
) -> Dict[str, Any]:
    """
    Respond node: Finalize the response and complete the run.

    This node:
    - Emits the done event
    - Flushes any pending events
    - Marks the run as complete
    """
    if await context.check_cancellation("respond"):
        return {"error": "cancelled", "current_node": "respond"}

    run_id = state.get("run_id", "unknown")
    logger.debug(f"Respond node finalizing run {run_id}")

    # Get the final message ID (last assistant message)
    messages = state.get("messages", [])
    final_message_id = None
    for msg in reversed(messages):
        if isinstance(msg, AgentMessage) and msg.role == "assistant":
            final_message_id = msg.id
            break
        elif isinstance(msg, dict) and msg.get("role") == "assistant":
            final_message_id = msg.get("id")
            break

    # Emit done event
    await context.emitter.emit_done(final_message_id)

    # Flush all pending events
    await context.emitter.flush()

    logger.info(f"Run {run_id} completed successfully")

    return {"current_node": "end"}


# ============================================================================
# B2.2: Multi-Brain Nodes
# ============================================================================

async def classify_task_node(
    state: AgentState,
    context: NodeContext,
) -> Dict[str, Any]:
    """
    Classify task complexity and determine collaboration mode.

    Uses Brain 1 to classify:
    - simple + ONE_STEP_QA → solo mode
    - simple + AMBIGUOUS → solo mode with ask_user intent
    - complex + MULTI_STEP_PLAN → consensus mode
    - complex + TOOL_REQUIRED → consensus mode
    """
    if await context.check_cancellation("classify_task"):
        return {"error": "cancelled", "current_node": "classify_task"}

    run_id = state.get("run_id", "unknown")
    session_id = state.get("session_id", "unknown")

    logger.debug(f"Classify task node for run {run_id}")

    # Extract the latest user message (NOT messages[0])
    messages = state.get("messages", [])
    user_message = extract_latest_user_message(messages)

    if not user_message:
        await context.emitter.emit_error("No user message to classify", recoverable=False)
        return {"error": "no_message", "current_node": "classify_task"}

    # Cap the objective for state storage
    objective, was_truncated, orig_len = cap_text(user_message, 500)
    if was_truncated:
        await context.emitter.emit_state_truncated("current_objective", orig_len, 500)

    try:
        # Get database session for LLM call
        from app.database import get_database
        db = get_database()

        async with db.session() as db_session:
            # Call Brain 1 for classification
            user_prompt = CLASSIFICATION_USER_TEMPLATE.format(user_message=user_message)
            response = await call_brain_1(
                CLASSIFICATION_SYSTEM_PROMPT,
                user_prompt,
                db_session,
                run_id=run_id,
                session_id=session_id,
            )

        # Parse classification result
        classification = parse_json_response(response.content, "B1")

        complexity = classification.get("complexity", "complex")
        reason_code = classification.get("reason_code", "AMBIGUOUS")
        rationale = classification.get("rationale", "No rationale provided")

        # Determine collaboration mode based on classification
        if complexity == "simple":
            mode = "solo"
        else:
            mode = "consensus"

        # Get brain config for logging
        from app.config import get_settings
        settings = get_settings()

        # Emit classification event with brain info
        await context.emitter.emit_classification(
            complexity, mode, reason_code, rationale,
            brain_provider=settings.brain_1_provider,
            brain_model=settings.brain_1_model,
        )

        logger.info(
            f"Task classified",
            extra={
                "extra_fields": {
                    "run_id": run_id,
                    "complexity": complexity,
                    "mode": mode,
                    "reason_code": reason_code,
                }
            },
        )

        return {
            "current_objective": objective,
            "task_complexity": complexity,
            "collaboration_mode": mode,
            "classification_reason": reason_code,
            "current_node": "classify_task",
        }

    except BrainCallError as e:
        error_msg = f"Classification failed: {e}"
        logger.error(error_msg)
        await context.emitter.emit_error(error_msg, recoverable=True, error_type="brain_error")
        # Default to solo mode on classification error
        return {
            "current_objective": objective,
            "task_complexity": "simple",
            "collaboration_mode": "solo",
            "classification_reason": "AMBIGUOUS",
            "current_node": "classify_task",
        }
    except Exception as e:
        error_msg = f"Classification failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await context.emitter.emit_error(error_msg, recoverable=True, error_type="classification_error")
        return {
            "current_objective": objective,
            "task_complexity": "simple",
            "collaboration_mode": "solo",
            "classification_reason": "AMBIGUOUS",
            "current_node": "classify_task",
        }


async def process_b1_node(
    state: AgentState,
    context: NodeContext,
) -> Dict[str, Any]:
    """
    Solo mode processing by Brain 1.

    For simple tasks, B1 handles directly without deliberation.
    For AMBIGUOUS tasks, generates a clarifying question.
    """
    if await context.check_cancellation("process_b1"):
        return {"error": "cancelled", "current_node": "process_b1"}

    run_id = state.get("run_id", "unknown")
    session_id = state.get("session_id", "unknown")
    reason_code = state.get("classification_reason", "ONE_STEP_QA")
    objective = state.get("current_objective", "")

    logger.debug(f"Process B1 node for run {run_id}, reason: {reason_code}")

    # Get the user message
    messages = state.get("messages", [])
    user_message = extract_latest_user_message(messages)

    try:
        from app.database import get_database
        db = get_database()

        async with db.session() as db_session:
            if reason_code == "AMBIGUOUS":
                # Generate clarifying question
                user_prompt = BRAIN1_CLARIFY_USER_TEMPLATE.format(user_message=user_message)
                response = await call_brain_1(
                    BRAIN1_CLARIFY_SYSTEM_PROMPT,
                    user_prompt,
                    db_session,
                    run_id=run_id,
                    session_id=session_id,
                )
            else:
                # Direct answer
                user_prompt = BRAIN1_SOLO_USER_TEMPLATE.format(user_message=user_message)
                response = await call_brain_1(
                    BRAIN1_SOLO_SYSTEM_PROMPT,
                    user_prompt,
                    db_session,
                    run_id=run_id,
                    session_id=session_id,
                )

        content = response.content or ""

        # Stream the response
        chunk_size = 25
        for i in range(0, len(content), chunk_size):
            if i > 0 and i % 100 == 0:
                if await context.check_cancellation("process_b1"):
                    return {"error": "cancelled", "current_node": "process_b1"}

            chunk = content[i:i + chunk_size]
            await context.emitter.emit_token(chunk)
            await asyncio.sleep(0.02)

        # Create assistant message
        assistant_message = AgentMessage(
            role="assistant",
            content=content,
        )

        return {
            "messages": [assistant_message],
            "partial_response": content,
            "last_intent": "ask_user" if reason_code == "AMBIGUOUS" else "answer_only",
            "current_node": "respond",
        }

    except Exception as e:
        error_msg = f"B1 processing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await context.emitter.emit_error(error_msg, recoverable=True, error_type="brain_error")
        return {
            "error": error_msg,
            "error_recoverable": True,
            "current_node": "process_b1",
        }


async def deliberation_node(
    state: AgentState,
    context: NodeContext,
) -> Dict[str, Any]:
    """
    Multi-brain deliberation node.

    1. B2 (Manager) proposes a decision
    2. B1 (Coordinator) reviews and either agrees or disagrees
    3. Store summaries in state, full reasoning in events
    """
    if await context.check_cancellation("deliberation"):
        return {"error": "cancelled", "current_node": "deliberation"}

    run_id = state.get("run_id", "unknown")
    session_id = state.get("session_id", "unknown")
    objective = state.get("current_objective", "")
    round_num = state.get("deliberation_round", 0)
    max_rounds = state.get("max_deliberation_rounds", 3)

    logger.debug(f"Deliberation node for run {run_id}, round {round_num + 1}/{max_rounds}")

    # Build context from conversation
    messages = state.get("messages", [])
    context_summary = "\n".join([
        f"- {msg.content[:200]}..."
        for msg in messages[-3:]  # Last 3 messages for context
        if isinstance(msg, AgentMessage)
    ])

    try:
        from app.database import get_database
        from app.config import get_settings
        db = get_database()
        settings = get_settings()

        async with db.session() as db_session:
            # Step 1: B2 (Manager) proposes
            b2_user_prompt = BRAIN2_DECISION_USER_TEMPLATE.format(
                objective=objective,
                context=context_summary or "No previous context.",
            )

            b2_decision = await call_brain_2_for_decision(
                BRAIN2_DECISION_SYSTEM_PROMPT,
                b2_user_prompt,
                db_session,
                run_id=run_id,
                session_id=session_id,
            )

            # Emit B2 thinking event with model info
            await context.emitter.emit_brain_thinking(
                brain="B2",
                decision=b2_decision.to_dict(),
                full_reasoning=b2_decision.summary,
                brain_provider=settings.brain_2_provider,
                brain_model=settings.brain_2_model,
            )

            # Step 2: B1 (Coordinator) reviews
            b1_user_prompt = BRAIN1_REVIEW_USER_TEMPLATE.format(
                objective=objective,
                brain2_decision=json.dumps(b2_decision.to_dict(), indent=2),
            )

            b1_decision = await call_brain_1_for_decision(
                BRAIN1_REVIEW_SYSTEM_PROMPT,
                b1_user_prompt,
                db_session,
                run_id=run_id,
                session_id=session_id,
            )

            # Emit B1 thinking event with model info
            await context.emitter.emit_brain_thinking(
                brain="B1",
                decision=b1_decision.to_dict(),
                full_reasoning=b1_decision.summary,
                brain_provider=settings.brain_1_provider,
                brain_model=settings.brain_1_model,
            )

        # Cap summaries for state storage
        b1_summary, b1_truncated, b1_orig = cap_text(b1_decision.summary, 500)
        b2_summary, b2_truncated, b2_orig = cap_text(b2_decision.summary, 500)

        if b1_truncated:
            await context.emitter.emit_state_truncated("brain_1_summary", b1_orig, 500)
        if b2_truncated:
            await context.emitter.emit_state_truncated("brain_2_summary", b2_orig, 500)

        # Emit deliberation round event (1-based for display)
        await context.emitter.emit_deliberation_round(
            round_display=round_num + 1,
            max_rounds=max_rounds,
            b1_decision=b1_decision.to_dict(),
            b2_decision=b2_decision.to_dict(),
        )

        # Cap target artifacts
        merged_artifacts = list(set(b1_decision.target_artifacts) | set(b2_decision.target_artifacts))
        capped_artifacts, _ = cap_list_items(merged_artifacts, max_items=5, max_item_len=200)

        return {
            "brain_1_summary": b1_summary,
            "brain_2_summary": b2_summary,
            "last_intent": b1_decision.intent,
            "target_artifacts": capped_artifacts,
            "deliberation_round": round_num + 1,
            "current_node": "check_consensus",
            # Store decisions in node_metadata for consensus check
            "node_metadata": {
                "b1_decision": b1_decision.to_dict(),
                "b2_decision": b2_decision.to_dict(),
            },
        }

    except BrainCallError as e:
        error_msg = f"Deliberation failed: {e}"
        logger.error(error_msg)
        await context.emitter.emit_error(error_msg, recoverable=True, error_type="brain_error")
        # Escalate on brain error
        return {
            "escalation_required": True,
            "escalation_reason": "BRAIN_REQUESTED",
            "current_node": "check_consensus",
        }
    except Exception as e:
        error_msg = f"Deliberation failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await context.emitter.emit_error(error_msg, recoverable=True, error_type="deliberation_error")
        return {
            "escalation_required": True,
            "escalation_reason": "BRAIN_REQUESTED",
            "current_node": "check_consensus",
        }


async def check_consensus_node(
    state: AgentState,
    context: NodeContext,
) -> Dict[str, Any]:
    """
    Check if brains reached consensus and route accordingly.

    Routes to:
    - respond: If consensus reached or escalation required
    - deliberation: If no consensus and rounds remaining
    """
    if await context.check_cancellation("check_consensus"):
        return {"error": "cancelled", "current_node": "check_consensus"}

    run_id = state.get("run_id", "unknown")
    round_num = state.get("deliberation_round", 1)
    max_rounds = state.get("max_deliberation_rounds", 3)
    objective = state.get("current_objective", "")

    logger.debug(f"Check consensus for run {run_id}, round {round_num}/{max_rounds}")

    # Check if escalation was already requested
    if state.get("escalation_required"):
        reason = state.get("escalation_reason", "BRAIN_REQUESTED")
        await context.emitter.emit_escalation_required(
            objective=objective,
            rounds_attempted=round_num,
            b1_summary=state.get("brain_1_summary", ""),
            b2_summary=state.get("brain_2_summary", ""),
            reason=reason,
        )
        return {
            "consensus_reached": False,
            "current_node": "respond",
        }

    # Get decisions from node_metadata
    metadata = state.get("node_metadata", {})
    b1_data = metadata.get("b1_decision", {})
    b2_data = metadata.get("b2_decision", {})

    if not b1_data or not b2_data:
        # No decisions to check - escalate
        await context.emitter.emit_consensus_failed(round_num, "missing_decisions")
        return {
            "consensus_reached": False,
            "escalation_required": True,
            "escalation_reason": "BRAIN_REQUESTED",
            "current_node": "respond",
        }

    # Reconstruct decisions
    b1_decision = BrainDecision.from_dict(b1_data)
    b2_decision = BrainDecision.from_dict(b2_data)

    # Check for explicit escalation request
    escalate, escalate_reason = should_escalate(b1_decision, b2_decision)
    if escalate:
        await context.emitter.emit_escalation_required(
            objective=objective,
            rounds_attempted=round_num,
            b1_summary=state.get("brain_1_summary", ""),
            b2_summary=state.get("brain_2_summary", ""),
            reason=escalate_reason,
        )
        return {
            "consensus_reached": False,
            "escalation_required": True,
            "escalation_reason": escalate_reason,
            "current_node": "respond",
        }

    # Check consensus
    consensus_reached, consensus_reason = check_consensus(b1_decision, b2_decision)

    if consensus_reached:
        # Merge decisions and emit success
        merged = merge_decisions(b1_decision, b2_decision)
        await context.emitter.emit_consensus_reached(
            intent=merged.intent,
            tool_name=merged.tool_name,
            target_artifacts=merged.target_artifacts,
        )

        logger.info(f"Consensus reached for run {run_id}: {merged.intent}")

        return {
            "consensus_reached": True,
            "last_intent": merged.intent,
            "target_artifacts": merged.target_artifacts,
            "node_metadata": {
                **metadata,
                "merged_decision": merged.to_dict(),
            },
            "current_node": "respond" if merged.intent != "run_bash" else "tool_execute",
        }

    # No consensus - check if more rounds available
    if round_num < max_rounds:
        await context.emitter.emit_consensus_failed(round_num, consensus_reason)
        logger.info(f"No consensus after round {round_num}, continuing deliberation")
        return {
            "consensus_reached": False,
            "current_node": "deliberation",
        }

    # Max rounds reached - escalate
    await context.emitter.emit_consensus_failed(round_num, "max_rounds_reached")
    await context.emitter.emit_escalation_required(
        objective=objective,
        rounds_attempted=round_num,
        b1_summary=state.get("brain_1_summary", ""),
        b2_summary=state.get("brain_2_summary", ""),
        reason="MAX_ROUNDS",
    )

    return {
        "consensus_reached": False,
        "escalation_required": True,
        "escalation_reason": "MAX_ROUNDS",
        "current_node": "respond",
    }


async def tool_execute_node(
    state: AgentState,
    context: NodeContext,
) -> Dict[str, Any]:
    """
    Execute bash tool (B2.2b).

    Only bash commands are supported in B2.2b.
    Uses restrictive allowlist for safety.
    """
    if await context.check_cancellation("tool_execute"):
        return {"error": "cancelled", "current_node": "tool_execute"}

    run_id = state.get("run_id", "unknown")
    session_id = state.get("session_id", "unknown")

    logger.debug(f"Tool execute node for run {run_id}")

    # Get merged decision from metadata
    metadata = state.get("node_metadata", {})
    merged = metadata.get("merged_decision", {})

    if not merged or merged.get("intent") != "run_bash":
        # No tool to execute
        return {"current_node": "respond"}

    # Import tool validation
    from .tool_validation import validate_bash_command, build_bash_command_for_file_creation

    # For now, we'll generate a simple command based on the plan
    # In a real implementation, the LLM would provide the exact command
    plan_steps = merged.get("plan_steps", [])
    target_artifacts = merged.get("target_artifacts", [])

    # Simple example: if target is a .py file, create it
    if target_artifacts and target_artifacts[0].endswith(".py"):
        filename = target_artifacts[0]
        # Generate a simple Python file as demo
        content = '# Auto-generated file\nprint("Hello from Agent B!")\n'
        command = build_bash_command_for_file_creation(filename, content)
    else:
        # No valid command to execute
        await context.emitter.emit_error(
            "No valid bash command generated",
            recoverable=True,
            error_type="tool_error",
        )
        return {"current_node": "respond"}

    # Validate command
    is_valid, error_msg = validate_bash_command(command)
    if not is_valid:
        await context.emitter.emit_error(
            f"Command validation failed: {error_msg}",
            recoverable=True,
            error_type="validation_error",
        )
        return {"current_node": "respond"}

    # Generate tool call ID
    from uuid import uuid4
    tool_call_id = str(uuid4())

    # Emit tool start
    await context.emitter.emit_tool_start(
        tool_call_id=tool_call_id,
        tool_name="bash",
        input_preview=command[:200],
    )

    try:
        # Execute command using existing executor
        from app.executor import execute_command

        import time
        start_time = time.time()

        result = await execute_command(command)

        duration_ms = int((time.time() - start_time) * 1000)

        # Emit tool end
        await context.emitter.emit_tool_end(
            tool_call_id=tool_call_id,
            exit_code=result.exit_code if hasattr(result, 'exit_code') else 0,
            output_preview=str(result.stdout if hasattr(result, 'stdout') else result)[:500],
            duration_ms=duration_ms,
        )

        # Stream a response about the tool execution
        response_content = f"Created file: {target_artifacts[0]}" if target_artifacts else "Command executed."

        for i in range(0, len(response_content), 25):
            chunk = response_content[i:i + 25]
            await context.emitter.emit_token(chunk)
            await asyncio.sleep(0.02)

        assistant_message = AgentMessage(
            role="assistant",
            content=response_content,
        )

        return {
            "messages": [assistant_message],
            "partial_response": response_content,
            "current_node": "respond",
        }

    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)

        await context.emitter.emit_tool_end(
            tool_call_id=tool_call_id,
            exit_code=1,
            output_preview=error_msg[:500],
            duration_ms=0,
        )

        await context.emitter.emit_error(error_msg, recoverable=True, error_type="tool_error")

        return {
            "error": error_msg,
            "error_recoverable": True,
            "current_node": "respond",
        }


# Export node functions for graph registration
NODE_FUNCTIONS = {
    "receive": receive_node,
    "process": process_node,
    "respond": respond_node,
    # B2.2: Multi-brain nodes
    "classify_task": classify_task_node,
    "process_b1": process_b1_node,
    "deliberation": deliberation_node,
    "check_consensus": check_consensus_node,
    "tool_execute": tool_execute_node,
}
