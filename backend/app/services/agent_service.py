"""
Agent Service (B2.1 - LangGraph Runtime Integration).

Orchestrates agent execution in background tasks with proper lifecycle:
- Creates its own database session (never uses request-scoped session)
- Manages run status transitions
- Handles cancellation and cleanup
- Coordinates with RunRegistry for active run tracking

Critical: Background tasks must create their own AsyncSession.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Any, Dict
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.database import get_database
from app.models import Run, Message, AuditLog, Artifact
from app.agent.state import AgentState, AgentMessage, create_initial_state
from app.agent.graph import create_multi_brain_graph, run_agent
from app.agent.events import EventEmitter, create_bounded_queue
from app.agent.nodes import NodeContext
from app.agent.checkpointer import get_checkpointer
from app.services.run_registry import (
    get_run_registry,
    set_active_run,
    clear_run,
    is_cancelled,
    register_task,
)

logger = get_logger("agent_service")

# Status values for runs (B2.1 canonical values)
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_TERMINATED = "terminated"
STATUS_INTERRUPTED = "interrupted"

# Statuses that allow resume
RESUMABLE_STATUSES = {STATUS_TERMINATED, STATUS_FAILED, STATUS_INTERRUPTED}


async def _build_workspace_context(
    db_session: AsyncSession,
    session_id: str,
    run_id: str,
    context_cfg: Optional[dict],
) -> str:
    """Build a lightweight, safe context header for the run.

    Goal: make artifacts "visible" by default (names + ids), and make focused
    artifacts easy for the model to use (include short previews).

    This is NOT full RAG yet; it is a pragmatic MVP that avoids token blowups.
    """
    from app.artifact_service import get_artifact_preview

    cfg = context_cfg or {}
    focused_ids: List[str] = list(cfg.get("focused_artifact_ids") or [])
    focus_mode = (cfg.get("focus_mode") or "prefer").lower()
    artifact_scope = (cfg.get("artifact_scope") or "session").lower()

    # Load artifacts (default: current session only)
    q = select(Artifact).where(Artifact.is_deleted == False)  # noqa: E712
    if artifact_scope == "all_sessions":
        # NOTE: no user scoping in DB yet; "all_sessions" means all artifacts.
        q = q
    else:
        q = q.where(Artifact.session_id == session_id)

    q = q.order_by(Artifact.created_at.desc()).limit(80)
    result = await db_session.execute(q)
    artifacts: List[Artifact] = list(result.scalars().all())

    id_to_artifact = {a.id: a for a in artifacts}

    focused: List[Artifact] = [id_to_artifact[i] for i in focused_ids if i in id_to_artifact]

    # Build catalog lines (cap to keep system prompt small)
    catalog = artifacts
    if focus_mode == "only":
        catalog = focused

    catalog_lines: List[str] = []
    for a in catalog[:50]:
        catalog_lines.append(f"- {a.display_name} (id: {a.id})")

    # Focused previews (small excerpts)
    focused_blocks: List[str] = []
    for a in focused[:5]:
        try:
            preview = get_artifact_preview(a)
            text = (preview.get("text") or "")
            text = text[:6000]
            if text:
                focused_blocks.append(
                    "\n".join(
                        [
                            f"[FOCUSED ARTIFACT PREVIEW] {a.display_name} (id: {a.id})",
                            "---",
                            text,
                            "---",
                        ]
                    )
                )
        except Exception:
            continue

    # Check for edit target (B1.7 - Edit Toggle)
    edit_target_id: Optional[str] = cfg.get("edit_target_artifact_id")
    edit_target_selections: List[dict] = cfg.get("edit_target_selections") or []
    edit_target_artifact: Optional[Artifact] = None
    edit_target_content: str = ""

    logger.info(f"[_build_workspace_context] edit_target_id={edit_target_id}, selections_count={len(edit_target_selections)}")

    if edit_target_id and edit_target_id in id_to_artifact:
        edit_target_artifact = id_to_artifact[edit_target_id]
        try:
            preview = get_artifact_preview(edit_target_artifact)
            edit_target_content = preview.get("text") or ""
        except Exception:
            pass

    parts: List[str] = []
    parts.append("You are working inside a workspace with user-provided documents (Artifacts).")
    parts.append("You may reference them by name/id. If you need a document's details and it isn't previewed here, ask the user to focus it (pin it) or provide the relevant excerpt.")
    parts.append("")

    # Edit mode instructions (B1.7)
    if edit_target_artifact:
        parts.append("[EDIT MODE ACTIVE]")
        parts.append(f"The user has set '{edit_target_artifact.display_name}' (id: {edit_target_artifact.id}) as the EDIT TARGET.")
        parts.append("Your response should UPDATE this artifact, not create a new one.")
        parts.append("")
        parts.append("OUTPUT FORMAT FOR EDIT MODE:")
        parts.append('Reply with a JSON object: {"type":"artifact_update","artifact_id":"<target_id>","content":"<updated full content>"}')
        parts.append("The content should be the COMPLETE updated artifact (not just the changes).")
        if edit_target_selections:
            parts.append("")
            parts.append("SPECIFIC SECTIONS TO EDIT:")
            for sel in edit_target_selections[:5]:
                parts.append(f"  - Lines {sel.get('startLine')}-{sel.get('endLine')}: {sel.get('text', '')[:100]}...")
            parts.append("Focus your changes on these sections while keeping the rest of the document intact.")
        parts.append("")
        parts.append(f"[CURRENT CONTENT OF '{edit_target_artifact.display_name}']")
        parts.append("---")
        parts.append(edit_target_content[:15000])  # Limit to avoid token blowup
        parts.append("---")
        parts.append("")
    else:
        parts.append("[OUTPUT FORMAT]")
        parts.append("Normally reply with plain text.")
        parts.append("If you want to create an Artifact (a file) as your output, reply with ONLY a single JSON object in this exact envelope format (no markdown fences):")
        parts.append('{"type":"artifact","content":"<file contents>","artifact_meta":{"filename":"analysis.md","display_name":"Analysis Results"}}')
        parts.append("If you reply with this envelope, the system will save it as an Artifact and show it in the Artifacts panel.")

    if focus_mode == "only":
        parts.append("Mode: ONLY use focused artifacts. If none are focused, ask the user to focus the relevant documents.")
    else:
        parts.append("Mode: Prefer focused artifacts; otherwise use other artifacts as needed.")

    parts.append("")
    parts.append("[ARTIFACT CATALOG]")
    parts.append("\n".join(catalog_lines) if catalog_lines else "(no artifacts available)")

    if focused_blocks:
        parts.append("")
        parts.append("\n".join(focused_blocks))

    return "\n".join(parts)


async def execute_agent_run(
    run_id: str,
    session_id: str,
    user_message: str,
    event_queue: asyncio.Queue,
    is_resume: bool = False,
) -> None:
    """
    Execute an agent run in a background task.

    CRITICAL: This function creates its own database session.
    Never pass a request-scoped session to background tasks.

    Args:
        run_id: Unique run identifier
        session_id: Session this run belongs to
        user_message: User's input message (ignored if resuming)
        event_queue: Queue for SSE events
        is_resume: If True, resume from last checkpoint
    """
    db = get_database()

    # Track if we need to clear the active run in finally
    should_clear_run = True

    try:
        # Create our own session for the entire background task
        async with db.session() as db_session:
            # Update run status to running
            await _update_run_status(
                db_session,
                run_id,
                STATUS_RUNNING,
                session_id=session_id,
                event_queue=event_queue,
            )

            # Create event emitter
            emitter = EventEmitter(
                queue=event_queue,
                db_session=db_session,
                run_id=run_id,
                session_id=session_id,
            )

            # Create cancellation check function
            async def check_cancelled() -> bool:
                return await is_cancelled(run_id)

            # Load run metadata (context + llm selection)
            run_result = await db_session.execute(select(Run).where(Run.id == run_id))
            run = run_result.scalar_one_or_none()
            context_cfg = (run.run_metadata or {}).get("context") if run else {}
            llm_cfg = (run.run_metadata or {}).get("llm") if run else {}

            # DEBUG: Log edit target config
            edit_target_id = context_cfg.get("edit_target_artifact_id") if context_cfg else None
            logger.info(f"[execute_agent_run] run_id={run_id}, edit_target_artifact_id={edit_target_id}")

            # Create node context
            context = NodeContext(
                emitter=emitter,
                is_cancelled_fn=check_cancelled,
                session_factory=None,  # Could add for cost tracking
                run_id=run_id,
                session_id=session_id,
                llm_provider=(llm_cfg or {}).get("provider"),
                llm_model=(llm_cfg or {}).get("model"),
                llm_strict=bool((llm_cfg or {}).get("strict")),
            )

            # Create the multi-brain graph (B2.2)
            graph = create_multi_brain_graph(context)

            system_context = await _build_workspace_context(
                db_session=db_session,
                session_id=session_id,
                run_id=run_id,
                context_cfg=context_cfg,
            )

            # Create initial state (only used for new runs)
            initial_state = create_initial_state(
                run_id=run_id,
                session_id=session_id,
                user_message=user_message,
                system_context=system_context,
            )

            try:
                if is_resume:
                    await emitter.emit_run_resumed(run_id)

                # Get checkpointer
                checkpointer = get_checkpointer()

                # Execute the graph
                final_state = await run_agent(
                    graph=graph,
                    initial_state=initial_state,
                    run_id=run_id,
                    checkpointer=checkpointer,
                    is_resume=is_resume,
                )

                # Check if run was cancelled
                if await check_cancelled():
                    await _update_run_status(
                        db_session,
                        run_id,
                        STATUS_TERMINATED,
                        session_id=session_id,
                        event_queue=event_queue,
                    )
                    logger.info(f"Run {run_id} terminated by user")
                elif final_state.get("error"):
                    error = final_state.get("error")
                    if error == "cancelled":
                        await _update_run_status(
                            db_session,
                            run_id,
                            STATUS_TERMINATED,
                            session_id=session_id,
                            event_queue=event_queue,
                        )
                    else:
                        await _update_run_status(
                            db_session,
                            run_id,
                            STATUS_FAILED,
                            error=str(error),
                            session_id=session_id,
                            event_queue=event_queue,
                        )
                else:
                    # Store the assistant output (message and/or artifact)
                    await _store_assistant_output(
                        db_session=db_session,
                        session_id=session_id,
                        run_id=run_id,
                        final_state=final_state,
                        event_queue=event_queue,
                    )
                    await _update_run_status(
                        db_session,
                        run_id,
                        STATUS_COMPLETED,
                        session_id=session_id,
                        event_queue=event_queue,
                    )
                    logger.info(f"Run {run_id} completed successfully")

            except asyncio.CancelledError:
                logger.info(f"Run {run_id} cancelled via task cancellation")
                await emitter.emit_run_terminated("task_cancelled")
                await emitter.flush()
                await _update_run_status(
                    db_session,
                    run_id,
                    STATUS_TERMINATED,
                    session_id=session_id,
                    event_queue=event_queue,
                )
                raise

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Run {run_id} failed with error: {error_msg}", exc_info=True)
                await emitter.emit_error(error_msg, recoverable=True)
                await emitter.flush()
                await _update_run_status(
                    db_session,
                    run_id,
                    STATUS_FAILED,
                    error=error_msg,
                    session_id=session_id,
                    event_queue=event_queue,
                )

            finally:
                # Always flush events
                await emitter.flush()

    except Exception as e:
        logger.error(f"Agent service error for run {run_id}: {e}", exc_info=True)
        # Try to update status even on outer exception
        try:
            async with db.session() as error_session:
                await _update_run_status(
                    error_session,
                    run_id,
                    STATUS_FAILED,
                    error=str(e),
                    session_id=session_id,
                    event_queue=event_queue,
                )
        except Exception as inner_e:
            logger.error(f"Failed to update run status: {inner_e}")

    finally:
        # Always clear the active run
        if should_clear_run:
            await clear_run(run_id)
            logger.debug(f"Cleared active run {run_id}")


async def start_agent_run(
    run_id: str,
    session_id: str,
    user_message: str,
    event_queue: asyncio.Queue,
    is_resume: bool = False,
) -> asyncio.Task:
    """
    Start an agent run as a background task.

    This is the main entry point for starting runs from message_routes.

    Args:
        run_id: Unique run identifier
        session_id: Session this run belongs to
        user_message: User's input message
        event_queue: Queue for SSE events
        is_resume: If True, resume from last checkpoint

    Returns:
        The asyncio.Task running the agent
    """
    # Create the task
    task = asyncio.create_task(
        execute_agent_run(
            run_id=run_id,
            session_id=session_id,
            user_message=user_message,
            event_queue=event_queue,
            is_resume=is_resume,
        ),
        name=f"agent_run_{run_id}",
    )

    # Register task with run registry for cancellation support
    await register_task(run_id, task)

    logger.info(
        f"Started agent run {run_id} for session {session_id} "
        f"(resume={is_resume})"
    )

    return task


async def can_resume_run(db_session: AsyncSession, run_id: str) -> tuple[bool, str]:
    """
    Check if a run can be resumed.

    Args:
        db_session: Database session
        run_id: Run to check

    Returns:
        Tuple of (can_resume, reason)
    """
    from app.agent.checkpointer import has_checkpoint

    # Get run status
    result = await db_session.execute(
        select(Run).where(Run.id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        return False, "Run not found"

    if run.status not in RESUMABLE_STATUSES:
        return False, f"Run status '{run.status}' is not resumable"

    # Check if checkpoint exists
    has_cp = await has_checkpoint(run_id)
    if not has_cp:
        return False, "No checkpoint found for this run"

    return True, "Run can be resumed"


async def _update_run_status(
    db_session: AsyncSession,
    run_id: str,
    status: str,
    error: Optional[str] = None,
    *,
    session_id: Optional[str] = None,
    event_queue: Optional[asyncio.Queue] = None,
) -> None:
    """Update run status in database.

    Stage 10: optionally emits a lightweight SSE event `run_state_changed`.
    """
    update_data = {
        "status": status,
    }

    if status == STATUS_RUNNING:
        update_data["started_at"] = datetime.now(timezone.utc)
    elif status in {STATUS_COMPLETED, STATUS_FAILED, STATUS_TERMINATED}:
        update_data["completed_at"] = datetime.now(timezone.utc)

    if error:
        update_data["error"] = error

    await db_session.execute(
        update(Run).where(Run.id == run_id).values(**update_data)
    )
    await db_session.commit()

    # Stage 10: SSE notify
    if event_queue is not None and session_id is not None:
        try:
            event_queue.put_nowait((
                "run_state_changed",
                {
                    "run_id": run_id,
                    "session_id": session_id,
                    "status": status,
                    "error": error,
                },
                None,
            ))
        except Exception:
            # Never fail run updates due to SSE issues
            logger.debug("Failed to emit run_state_changed (ignored)")

    logger.debug(f"Updated run {run_id} status to {status}")


async def _store_assistant_output(
    *,
    db_session: AsyncSession,
    session_id: str,
    run_id: str,
    final_state: AgentState,
    event_queue: Optional[asyncio.Queue] = None,
) -> None:
    """Store the assistant's output.

    Supports two output types:
    1) Plain assistant message (stored to messages)
    2) Structured artifact envelope (creates Artifact + emits artifact_created SSE)

    Artifact envelope format (JSON):
      {
        "type": "artifact",
        "content": "<file contents>",
        "artifact_meta": {
          "filename": "analysis.md",
          "display_name": "Analysis Results"
        }
      }

    If parsing fails, falls back to storing the raw content as an assistant message.
    """

    messages = final_state.get("messages", [])

    # Find the last assistant message
    assistant_content: Optional[str] = None
    for msg in reversed(messages):
        if isinstance(msg, AgentMessage) and msg.role == "assistant":
            assistant_content = msg.content
            break
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            assistant_content = str(msg.get("content", ""))
            break

    if not assistant_content:
        return

    raw = assistant_content.strip()

    # DEBUG: Log raw assistant content for troubleshooting
    logger.info(f"[_store_assistant_output] Raw content (first 500 chars): {raw[:500]}")

    # Try parse structured envelope
    parsed: Optional[dict] = None
    if raw.startswith("{") and raw.endswith("}"):
        try:
            import json

            parsed = json.loads(raw)
            logger.info(f"[_store_assistant_output] Parsed as JSON, type={parsed.get('type')}")
        except Exception as e:
            logger.warning(f"[_store_assistant_output] JSON parse failed: {e}")
            parsed = None
    else:
        logger.info(f"[_store_assistant_output] Not JSON (starts with '{raw[:20] if raw else 'empty'}')")

    # Handle artifact update (B1.7 - Edit Toggle)
    if isinstance(parsed, dict) and (parsed.get("type") == "artifact_update"):
        try:
            artifact_id = parsed.get("artifact_id")
            new_content = parsed.get("content")

            if not artifact_id or not isinstance(new_content, str):
                logger.warning("Invalid artifact_update envelope, falling back to message")
            else:
                # Update the artifact content
                result = await db_session.execute(
                    select(Artifact).where(Artifact.id == artifact_id)
                )
                artifact = result.scalar_one_or_none()

                if artifact:
                    # Update content
                    artifact.content = new_content.encode("utf-8")
                    artifact.size_bytes = len(artifact.content)
                    await db_session.commit()
                    await db_session.refresh(artifact)

                    # Emit SSE artifact_updated (best-effort)
                    try:
                        if event_queue is not None:
                            from app.routes.artifact_routes import artifact_to_response
                            resp = artifact_to_response(artifact)
                            event_queue.put_nowait(("artifact_updated", {"artifact": resp.model_dump()}, None))
                    except Exception:
                        pass

                    # Store a message for Chat/History
                    msg_text = f"Updated artifact: {artifact.display_name}"
                    db_session.add(
                        Message(
                            id=str(uuid4()),
                            session_id=session_id,
                            role="assistant",
                            content=msg_text,
                        )
                    )
                    await db_session.commit()
                    logger.debug(f"Updated artifact {artifact_id} for session {session_id}")
                    return
                else:
                    logger.warning(f"Artifact {artifact_id} not found for update")

        except Exception as e:
            logger.error(f"Failed to update artifact: {e}", exc_info=True)

    # Handle artifact creation
    if isinstance(parsed, dict) and (parsed.get("type") == "artifact"):
        try:
            from app.artifact_service import create_artifact_internal
            from app.routes.artifact_routes import artifact_to_response

            artifact_meta = parsed.get("artifact_meta") or {}
            if not isinstance(artifact_meta, dict):
                artifact_meta = {}

            filename = (artifact_meta.get("filename") or artifact_meta.get("display_name") or "artifact.txt")
            if not isinstance(filename, str) or not filename.strip():
                filename = "artifact.txt"

            display_name = artifact_meta.get("display_name")
            if isinstance(display_name, str) and display_name.strip():
                # Preserve display_name separately
                artifact_meta = {**artifact_meta, "display_name": display_name}

            content = parsed.get("content")
            if not isinstance(content, str):
                content = str(content) if content is not None else ""

            artifact = await create_artifact_internal(
                db_session=db_session,
                run_id=run_id,
                session_id=session_id,
                filename=filename,
                content=content.encode("utf-8"),
                artifact_type="file",
                artifact_meta=artifact_meta,
            )

            # Emit SSE artifact_created (best-effort)
            try:
                if event_queue is not None:
                    resp = artifact_to_response(artifact)
                    event_queue.put_nowait(("artifact_created", {"artifact": resp.model_dump()}, None))
            except Exception:
                pass

            # Store a lightweight assistant message for Chat/History
            msg_text = f"Created artifact: {artifact.display_name}"
            db_session.add(
                Message(
                    id=str(uuid4()),
                    session_id=session_id,
                    role="assistant",
                    content=msg_text,
                )
            )
            await db_session.commit()
            logger.debug(f"Stored assistant artifact + message for session {session_id}")
            return

        except Exception as e:
            # Fall through to raw message storage
            logger.error(f"Failed to persist artifact envelope: {e}", exc_info=True)

    # Default: store raw content as assistant message
    db_session.add(
        Message(
            id=str(uuid4()),
            session_id=session_id,
            role="assistant",
            content=assistant_content,
        )
    )
    await db_session.commit()
    logger.debug(f"Stored assistant message for session {session_id}")


async def create_audit_log(
    db_session: AsyncSession,
    action: str,
    resource: str,
    message: str,
    session_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Create an audit log entry."""
    audit = AuditLog(
        id=str(uuid4()),
        actor="system",
        action=action,
        resource=resource,
        message=message,
        session_id=session_id,
        details=details,
        success=True,
    )
    db_session.add(audit)
    await db_session.commit()
