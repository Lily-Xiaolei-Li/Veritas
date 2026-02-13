"""
Agent Event Emitter (B2.1 + B2.2).

Provides transport-agnostic event emission:
- All events go to asyncio.Queue for SSE streaming
- Selected events persist to database for history/forensics

Event Types:
- token: Streaming text chunk (queue only by default)
- token_chunk: Buffered tokens (optional DB persistence)
- tool_start: Tool invocation beginning (always persisted)
- tool_end: Tool invocation completed (always persisted)
- checkpoint_created: State checkpoint saved (always persisted)
- error: Error during processing (always persisted)
- done: Agent run completed (always persisted)
- run_terminated: User killed the run (always persisted)

B2.2 Multi-Brain Events:
- classification: Task complexity classification result
- brain_thinking: Full brain reasoning (events only, not state)
- deliberation_round: Deliberation round summary
- consensus_reached: Brains agreed on approach
- consensus_failed: Brains failed to agree
- escalation_required: Needs human intervention (distinct from done)
- state_truncated: State field was capped (observability)
"""

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models import Event as EventModel

logger = get_logger("events")

# Event types that ALWAYS persist to database
ALWAYS_PERSIST_EVENTS: Set[str] = {
    "tool_start",
    "tool_end",
    "checkpoint_created",
    "error",
    "done",
    "run_terminated",
    "run_resumed",
    # B2.2: Multi-brain events
    "classification",
    "brain_thinking",
    "deliberation_round",
    "consensus_reached",
    "consensus_failed",
    "escalation_required",
}

# Event types that are dropped when queue is full (low priority)
DROPPABLE_EVENTS: Set[str] = {
    "token",
    "token_chunk",
}

# Default queue size to prevent memory blowup
DEFAULT_QUEUE_SIZE = 2000

# Token buffering settings (when persistence enabled)
TOKEN_BUFFER_SIZE = 200  # characters
TOKEN_BUFFER_TIMEOUT = 1.0  # seconds


@dataclass
class EventEmitter:
    """
    Emits agent events to queue (SSE) and optionally to database.

    Usage:
        emitter = EventEmitter(queue, db_session, run_id, session_id)
        await emitter.emit_token("Hello")
        await emitter.emit_tool_start(tool_call_id, "bash", "ls -la")
        await emitter.flush()  # Call at node boundaries and in finally
    """
    queue: asyncio.Queue
    db_session: AsyncSession
    run_id: str
    session_id: str

    # Internal state
    _seq: int = field(default=0, init=False)
    _pending_events: List[EventModel] = field(default_factory=list, init=False)
    _token_buffer: str = field(default="", init=False)
    _last_token_time: Optional[float] = field(default=None, init=False)
    _persist_tokens: bool = field(default=False, init=False)

    def __post_init__(self):
        # Check if token persistence is enabled
        self._persist_tokens = os.getenv("EVENT_TOKEN_PERSIST", "").lower() == "true"

    def _next_seq(self) -> int:
        """Get next sequence number."""
        self._seq += 1
        return self._seq

    def _make_event_id(self) -> str:
        """Generate SSE event ID."""
        return f"{self.run_id}-{self._seq}"

    async def _emit_to_queue(
        self,
        event_type: str,
        data: Dict[str, Any],
        event_id: Optional[str] = None,
    ) -> bool:
        """
        Emit event to the SSE queue.

        Returns True if emitted, False if dropped (queue full).
        """
        try:
            # Try to put without blocking
            self.queue.put_nowait((event_type, data, event_id or self._make_event_id()))
            return True
        except asyncio.QueueFull:
            # Drop low-priority events, log high-priority drops
            if event_type in DROPPABLE_EVENTS:
                logger.debug(f"Dropped {event_type} event (queue full)")
            else:
                logger.warning(f"Queue full, forcing {event_type} event")
                # For important events, wait a bit then try again
                try:
                    await asyncio.wait_for(
                        self.queue.put((event_type, data, event_id or self._make_event_id())),
                        timeout=0.5,
                    )
                    return True
                except asyncio.TimeoutError:
                    logger.error(f"Failed to emit {event_type} event after timeout")
            return False

    def _add_db_event(
        self,
        event_type: str,
        component: str,
        message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        severity: str = "info",
    ) -> None:
        """Add event to pending DB writes (committed on flush)."""
        event = EventModel(
            id=str(uuid4()),
            run_id=self.run_id,
            session_id=self.session_id,
            event_type=event_type,
            component=component,
            message=message,
            data=data,
            severity=severity,
        )
        self._pending_events.append(event)

    async def emit_token(self, content: str, seq: Optional[int] = None) -> None:
        """
        Emit a streaming token.

        Tokens always go to queue for SSE.
        If EVENT_TOKEN_PERSIST=true, tokens are buffered and persisted periodically.
        """
        if seq is None:
            seq = self._next_seq()

        # Always emit to queue
        await self._emit_to_queue("token", {
            "run_id": self.run_id,
            "seq": seq,
            "content": content,
        })

        # Buffer for optional DB persistence
        if self._persist_tokens:
            self._token_buffer += content
            current_time = asyncio.get_event_loop().time()

            if self._last_token_time is None:
                self._last_token_time = current_time

            # Flush buffer if size or time threshold reached
            if (len(self._token_buffer) >= TOKEN_BUFFER_SIZE or
                    current_time - self._last_token_time >= TOKEN_BUFFER_TIMEOUT):
                await self._flush_token_buffer()

    async def _flush_token_buffer(self) -> None:
        """Flush accumulated tokens to DB as token_chunk event."""
        if not self._token_buffer:
            return

        self._add_db_event(
            event_type="token_chunk",
            component="respond",
            message=None,
            data={"content": self._token_buffer, "char_count": len(self._token_buffer)},
            severity="debug",
        )

        self._token_buffer = ""
        self._last_token_time = asyncio.get_event_loop().time()

    async def emit_tool_start(
        self,
        tool_call_id: str,
        tool_name: str,
        input_preview: str,
    ) -> None:
        """Emit tool invocation start event."""
        seq = self._next_seq()

        await self._emit_to_queue("tool_start", {
            "run_id": self.run_id,
            "seq": seq,
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "input_preview": input_preview,
        })

        self._add_db_event(
            event_type="tool_start",
            component="tool_execute",
            message=f"Tool {tool_name} started",
            data={
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "input_preview": input_preview[:500],  # Truncate for storage
            },
        )

    async def emit_tool_end(
        self,
        tool_call_id: str,
        exit_code: int,
        output_preview: str,
        duration_ms: int,
    ) -> None:
        """Emit tool invocation completion event."""
        seq = self._next_seq()

        await self._emit_to_queue("tool_end", {
            "run_id": self.run_id,
            "seq": seq,
            "tool_call_id": tool_call_id,
            "exit_code": exit_code,
            "output_preview": output_preview,
            "duration_ms": duration_ms,
        })

        self._add_db_event(
            event_type="tool_end",
            component="tool_execute",
            message=f"Tool completed with exit code {exit_code}",
            data={
                "tool_call_id": tool_call_id,
                "exit_code": exit_code,
                "output_preview": output_preview[:500],
                "duration_ms": duration_ms,
            },
            severity="info" if exit_code == 0 else "warning",
        )

    async def emit_checkpoint_created(self, checkpoint_id: str, node: str) -> None:
        """Emit checkpoint creation event."""
        seq = self._next_seq()

        await self._emit_to_queue("checkpoint_created", {
            "run_id": self.run_id,
            "seq": seq,
            "checkpoint_id": checkpoint_id,
            "node": node,
        })

        self._add_db_event(
            event_type="checkpoint_created",
            component=node,
            message=f"Checkpoint created at node {node}",
            data={"checkpoint_id": checkpoint_id},
        )

    async def emit_error(
        self,
        message: str,
        recoverable: bool = True,
        error_type: Optional[str] = None,
    ) -> None:
        """Emit error event."""
        seq = self._next_seq()

        await self._emit_to_queue("error", {
            "run_id": self.run_id,
            "seq": seq,
            "message": message,
            "recoverable": recoverable,
        })

        self._add_db_event(
            event_type="error",
            component="agent",
            message=message,
            data={"recoverable": recoverable, "error_type": error_type},
            severity="error",
        )

    async def emit_done(self, final_message_id: Optional[str] = None) -> None:
        """Emit run completion event."""
        seq = self._next_seq()

        await self._emit_to_queue("done", {
            "run_id": self.run_id,
            "seq": seq,
            "final_message_id": final_message_id,
        })

        self._add_db_event(
            event_type="done",
            component="agent",
            message="Run completed successfully",
            data={"final_message_id": final_message_id},
        )

    async def emit_run_terminated(self, reason: str = "user_requested") -> None:
        """Emit run termination event (kill switch)."""
        seq = self._next_seq()

        await self._emit_to_queue("run_terminated", {
            "run_id": self.run_id,
            "seq": seq,
            "reason": reason,
        })

        self._add_db_event(
            event_type="run_terminated",
            component="agent",
            message=f"Run terminated: {reason}",
            data={"reason": reason},
            severity="warning",
        )

    async def emit_run_resumed(self, from_checkpoint: str) -> None:
        """Emit run resumed event."""
        seq = self._next_seq()

        await self._emit_to_queue("run_resumed", {
            "run_id": self.run_id,
            "seq": seq,
            "from_checkpoint": from_checkpoint,
        })

        self._add_db_event(
            event_type="run_resumed",
            component="agent",
            message="Run resumed from checkpoint",
            data={"from_checkpoint": from_checkpoint},
        )

    # ========================================================================
    # B2.2: Multi-Brain Events
    # ========================================================================

    async def emit_classification(
        self,
        complexity: str,
        mode: str,
        reason_code: str,
        rationale: str,
        brain_provider: str = "",
        brain_model: str = "",
    ) -> None:
        """
        Emit task classification event.

        Args:
            complexity: "simple" or "complex"
            mode: "solo" or "consensus"
            reason_code: ONE_STEP_QA, MULTI_STEP_PLAN, TOOL_REQUIRED, or AMBIGUOUS
            rationale: Full reasoning (stored in events, not state)
            brain_provider: Provider used for classification (e.g., "gemini")
            brain_model: Model used for classification (e.g., "gemini-2.0-flash")
        """
        seq = self._next_seq()

        await self._emit_to_queue("classification", {
            "run_id": self.run_id,
            "seq": seq,
            "complexity": complexity,
            "mode": mode,
            "reason_code": reason_code,
            "rationale": rationale,
            "brain_provider": brain_provider,
            "brain_model": brain_model,
        })

        self._add_db_event(
            event_type="classification",
            component="classify_task",
            message=f"Task classified: {complexity}/{mode} ({reason_code}) via {brain_provider}/{brain_model}",
            data={
                "complexity": complexity,
                "mode": mode,
                "reason_code": reason_code,
                "rationale": rationale,
                "brain_provider": brain_provider,
                "brain_model": brain_model,
            },
        )

        # Log visibly for debugging
        logger.info(
            f"[CLASSIFICATION] {complexity}/{mode} ({reason_code}) via B1={brain_provider}/{brain_model}",
            extra={
                "extra_fields": {
                    "complexity": complexity,
                    "mode": mode,
                    "reason_code": reason_code,
                    "brain_provider": brain_provider,
                    "brain_model": brain_model,
                }
            },
        )

    async def emit_brain_thinking(
        self,
        brain: str,
        decision: Dict[str, Any],
        full_reasoning: str,
        brain_provider: str = "",
        brain_model: str = "",
    ) -> None:
        """
        Emit brain thinking event (full reasoning preserved in events).

        Args:
            brain: "B1" or "B2"
            decision: BrainDecision as dict
            full_reasoning: Full reasoning text (NOT stored in state)
            brain_provider: Provider used (e.g., "gemini")
            brain_model: Model used (e.g., "gemini-2.5-flash")
        """
        seq = self._next_seq()

        await self._emit_to_queue("brain_thinking", {
            "run_id": self.run_id,
            "seq": seq,
            "brain": brain,
            "decision": decision,
            "brain_provider": brain_provider,
            "brain_model": brain_model,
        })

        self._add_db_event(
            event_type="brain_thinking",
            component=f"deliberation_{brain.lower()}",
            message=f"{brain} thinking via {brain_provider}/{brain_model}",
            data={
                "brain": brain,
                "decision": decision,
                "full_reasoning": full_reasoning[:2000],  # Cap for storage
                "brain_provider": brain_provider,
                "brain_model": brain_model,
            },
        )

        # Log visibly for debugging
        logger.info(
            f"[{brain} THINKING] intent={decision.get('intent')} decision={decision.get('decision')} via {brain_provider}/{brain_model}",
        )

    async def emit_deliberation_round(
        self,
        round_display: int,
        max_rounds: int,
        b1_decision: Dict[str, Any],
        b2_decision: Dict[str, Any],
    ) -> None:
        """
        Emit deliberation round event.

        Args:
            round_display: 1-based round number for humans
            max_rounds: Maximum rounds before escalation
            b1_decision: Brain 1's decision as dict
            b2_decision: Brain 2's decision as dict
        """
        seq = self._next_seq()

        await self._emit_to_queue("deliberation_round", {
            "run_id": self.run_id,
            "seq": seq,
            "round_display": round_display,
            "max_rounds": max_rounds,
            "b1_decision": b1_decision,
            "b2_decision": b2_decision,
        })

        self._add_db_event(
            event_type="deliberation_round",
            component="deliberation",
            message=f"Deliberation round {round_display}/{max_rounds}",
            data={
                "round_display": round_display,
                "max_rounds": max_rounds,
                "b1_decision": b1_decision,
                "b2_decision": b2_decision,
            },
        )

        # Log visibly for debugging
        logger.info(
            f"[DELIBERATION] Round {round_display}/{max_rounds} - "
            f"B1:{b1_decision.get('intent')} B2:{b2_decision.get('intent')}",
        )

    async def emit_consensus_reached(
        self,
        intent: str,
        tool_name: Optional[str],
        target_artifacts: List[str],
    ) -> None:
        """
        Emit consensus reached event.

        Args:
            intent: Agreed intent (answer_only, plan_only, run_bash, etc.)
            tool_name: Tool name if applicable
            target_artifacts: Target files if applicable
        """
        seq = self._next_seq()

        await self._emit_to_queue("consensus_reached", {
            "run_id": self.run_id,
            "seq": seq,
            "intent": intent,
            "tool_name": tool_name,
            "target_artifacts": target_artifacts,
        })

        self._add_db_event(
            event_type="consensus_reached",
            component="check_consensus",
            message=f"Consensus reached: {intent}",
            data={
                "intent": intent,
                "tool_name": tool_name,
                "target_artifacts": target_artifacts,
            },
        )

        # Log visibly for debugging
        logger.info(
            f"[CONSENSUS REACHED] intent={intent} tool={tool_name} artifacts={target_artifacts}",
        )

    async def emit_consensus_failed(self, rounds: int, reason: str) -> None:
        """
        Emit consensus failed event.

        Args:
            rounds: Number of rounds attempted
            reason: Why consensus failed
        """
        seq = self._next_seq()

        await self._emit_to_queue("consensus_failed", {
            "run_id": self.run_id,
            "seq": seq,
            "rounds": rounds,
            "reason": reason,
        })

        self._add_db_event(
            event_type="consensus_failed",
            component="check_consensus",
            message=f"Consensus failed after {rounds} rounds: {reason}",
            data={"rounds": rounds, "reason": reason},
            severity="warning",
        )

        # Log visibly for debugging
        logger.warning(
            f"[CONSENSUS FAILED] after {rounds} rounds: {reason}",
        )

    async def emit_escalation_required(
        self,
        objective: str,
        rounds_attempted: int,
        b1_summary: str,
        b2_summary: str,
        reason: str,
    ) -> None:
        """
        Emit escalation required event (DISTINCT from done).

        This indicates the run needs human intervention - UI must show
        "needs human decision" rather than normal completion.

        Args:
            objective: Current objective (capped)
            rounds_attempted: Number of deliberation rounds
            b1_summary: Brain 1's last position summary
            b2_summary: Brain 2's last position summary
            reason: "MAX_ROUNDS" or "BRAIN_REQUESTED"
        """
        seq = self._next_seq()

        await self._emit_to_queue("escalation_required", {
            "run_id": self.run_id,
            "seq": seq,
            "objective": objective,
            "rounds_attempted": rounds_attempted,
            "b1_summary": b1_summary,
            "b2_summary": b2_summary,
            "reason": reason,
        })

        self._add_db_event(
            event_type="escalation_required",
            component="escalation",
            message=f"Escalation required: {reason}",
            data={
                "objective": objective,
                "rounds_attempted": rounds_attempted,
                "b1_summary": b1_summary,
                "b2_summary": b2_summary,
                "reason": reason,
            },
            severity="warning",
        )

    async def emit_state_truncated(
        self,
        field_name: str,
        original_length: int,
        capped_length: int,
    ) -> None:
        """
        Emit state truncation event (for observability).

        Args:
            field_name: Name of the field that was truncated
            original_length: Original text length
            capped_length: Length after truncation
        """
        seq = self._next_seq()

        # Only emit to queue (not persisted by default)
        await self._emit_to_queue("state_truncated", {
            "run_id": self.run_id,
            "seq": seq,
            "field_name": field_name,
            "original_length": original_length,
            "capped_length": capped_length,
        })

        logger.debug(
            "State field truncated",
            extra={
                "extra_fields": {
                    "field_name": field_name,
                    "original_length": original_length,
                    "capped_length": capped_length,
                }
            },
        )

    async def flush(self) -> None:
        """
        Flush pending events to database.

        Call at node boundaries and in finally blocks.
        """
        # Flush any remaining token buffer
        if self._persist_tokens and self._token_buffer:
            await self._flush_token_buffer()

        # Commit pending DB events
        if self._pending_events:
            try:
                for event in self._pending_events:
                    self.db_session.add(event)
                await self.db_session.commit()
                logger.debug(f"Flushed {len(self._pending_events)} events to database")
            except Exception as e:
                logger.error(f"Failed to flush events to database: {e}", exc_info=True)
                await self.db_session.rollback()
            finally:
                self._pending_events.clear()


def create_bounded_queue(maxsize: int = DEFAULT_QUEUE_SIZE) -> asyncio.Queue:
    """Create a bounded queue for SSE events."""
    return asyncio.Queue(maxsize=maxsize)


def create_event_emitter(
    queue: asyncio.Queue,
    db_session: AsyncSession,
    run_id: str,
    session_id: str,
) -> EventEmitter:
    """Factory function to create an EventEmitter."""
    return EventEmitter(
        queue=queue,
        db_session=db_session,
        run_id=run_id,
        session_id=session_id,
    )
