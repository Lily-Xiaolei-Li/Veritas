"""
LangGraph State Machine (B2.1 + B2.2).

B2.1 Minimal Graph:
    receive -> process -> respond -> END

B2.2 Multi-Brain Graph:
    receive -> classify_task -> [solo: process_b1, consensus: deliberation]
    deliberation <-> check_consensus -> [consensus: tool_execute/respond, escalate: respond]

The graph uses PostgreSQL checkpoints for persistence and resumption.
"""

from typing import Any, Dict, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.logging_config import get_logger

from .state import AgentState
from .nodes import (
    receive_node,
    process_node,
    respond_node,
    classify_task_node,
    process_b1_node,
    deliberation_node,
    check_consensus_node,
    tool_execute_node,
    NodeContext,
)
from .checkpointer import get_checkpointer

logger = get_logger("graph")


def create_agent_graph(context: NodeContext) -> StateGraph:
    """
    Create the agent state machine graph.

    The minimal graph flow:
        receive -> process -> respond -> END

    Args:
        context: NodeContext with emitter and cancellation

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph with our state schema
    graph = StateGraph(AgentState)

    # Wrap node functions to include context
    async def wrapped_receive(state: AgentState) -> Dict[str, Any]:
        return await receive_node(state, context)

    async def wrapped_process(state: AgentState) -> Dict[str, Any]:
        return await process_node(state, context)

    async def wrapped_respond(state: AgentState) -> Dict[str, Any]:
        return await respond_node(state, context)

    # Add nodes
    graph.add_node("receive", wrapped_receive)
    graph.add_node("process", wrapped_process)
    graph.add_node("respond", wrapped_respond)

    # Define edges
    graph.set_entry_point("receive")
    graph.add_edge("receive", "process")
    graph.add_edge("process", "respond")
    graph.add_edge("respond", END)

    return graph


def create_multi_brain_graph(context: NodeContext) -> StateGraph:
    """
    Create the B2.2 multi-brain agent graph with conditional routing.

    Graph topology:
        receive -> classify_task
            |
            +-- solo (simple) --> process_b1 --> respond --> END
            |
            +-- consensus (complex) --> deliberation <--+
                                            |           |
                                       check_consensus -+ (loop if no consensus)
                                            |
                                       +----+----+
                                       |         |
                                  tool_execute  respond (escalation)
                                       |         |
                                    respond    END
                                       |
                                      END

    Args:
        context: NodeContext with emitter and cancellation

    Returns:
        StateGraph ready for compilation
    """
    graph = StateGraph(AgentState)

    # Wrap node functions to include context
    async def wrapped_receive(state: AgentState) -> Dict[str, Any]:
        return await receive_node(state, context)

    async def wrapped_classify_task(state: AgentState) -> Dict[str, Any]:
        return await classify_task_node(state, context)

    async def wrapped_process_b1(state: AgentState) -> Dict[str, Any]:
        return await process_b1_node(state, context)

    async def wrapped_deliberation(state: AgentState) -> Dict[str, Any]:
        return await deliberation_node(state, context)

    async def wrapped_check_consensus(state: AgentState) -> Dict[str, Any]:
        return await check_consensus_node(state, context)

    async def wrapped_tool_execute(state: AgentState) -> Dict[str, Any]:
        return await tool_execute_node(state, context)

    async def wrapped_respond(state: AgentState) -> Dict[str, Any]:
        return await respond_node(state, context)

    # Add all nodes
    graph.add_node("receive", wrapped_receive)
    graph.add_node("classify_task", wrapped_classify_task)
    graph.add_node("process_b1", wrapped_process_b1)
    graph.add_node("deliberation", wrapped_deliberation)
    graph.add_node("check_consensus", wrapped_check_consensus)
    graph.add_node("tool_execute", wrapped_tool_execute)
    graph.add_node("respond", wrapped_respond)

    # Entry point
    graph.set_entry_point("receive")

    # receive -> classify_task
    graph.add_edge("receive", "classify_task")

    # classify_task routes based on collaboration_mode
    def route_after_classification(state: AgentState) -> str:
        """Route based on classification result."""
        mode = state.get("collaboration_mode", "solo")
        if mode == "consensus":
            return "deliberation"
        return "process_b1"

    graph.add_conditional_edges(
        "classify_task",
        route_after_classification,
        {
            "process_b1": "process_b1",
            "deliberation": "deliberation",
        },
    )

    # process_b1 -> respond
    graph.add_edge("process_b1", "respond")

    # deliberation -> check_consensus
    graph.add_edge("deliberation", "check_consensus")

    # check_consensus routes based on consensus result
    def route_after_consensus(state: AgentState) -> str:
        """Route based on consensus check result."""
        # Check current_node set by the node
        current_node = state.get("current_node", "respond")

        if current_node == "deliberation":
            # Loop back for another round
            return "deliberation"
        elif current_node == "tool_execute":
            # Execute tool
            return "tool_execute"
        else:
            # Go to respond (consensus reached or escalation)
            return "respond"

    graph.add_conditional_edges(
        "check_consensus",
        route_after_consensus,
        {
            "deliberation": "deliberation",
            "tool_execute": "tool_execute",
            "respond": "respond",
        },
    )

    # tool_execute -> respond
    graph.add_edge("tool_execute", "respond")

    # respond -> END
    graph.add_edge("respond", END)

    return graph


def compile_graph_with_checkpointer(
    graph: StateGraph,
    checkpointer: Optional[AsyncPostgresSaver] = None,
):
    """
    Compile the graph with optional checkpoint persistence.

    Args:
        graph: The StateGraph to compile
        checkpointer: Optional checkpointer for persistence

    Returns:
        Compiled graph ready for ainvoke/astream
    """
    if checkpointer is None:
        checkpointer = get_checkpointer()

    if checkpointer is not None:
        logger.debug("Compiling graph with PostgreSQL checkpointer")
        return graph.compile(checkpointer=checkpointer)
    else:
        logger.warning("Compiling graph without checkpointer (no persistence)")
        return graph.compile()


async def run_agent(
    graph: StateGraph,
    initial_state: AgentState,
    run_id: str,
    checkpointer: Optional[AsyncPostgresSaver] = None,
    is_resume: bool = False,
) -> AgentState:
    """
    Execute the agent graph.

    Args:
        graph: Compiled StateGraph
        initial_state: Initial state (ignored if resuming)
        run_id: Run ID (used as thread_id for checkpoints)
        checkpointer: Optional checkpointer override
        is_resume: If True, resume from last checkpoint

    Returns:
        Final state after graph execution
    """
    # Compile with checkpointer
    compiled = compile_graph_with_checkpointer(graph, checkpointer)

    # LangGraph config uses thread_id for checkpoint identification
    config = {
        "configurable": {
            "thread_id": run_id,
        }
    }

    try:
        if is_resume:
            logger.info(f"Resuming run {run_id} from checkpoint")
            # When resuming, ainvoke with empty input continues from checkpoint
            # The state is loaded from the checkpointer automatically
            result = await compiled.ainvoke(None, config)
        else:
            logger.info(f"Starting new run {run_id}")
            result = await compiled.ainvoke(initial_state, config)

        return result

    except Exception as e:
        logger.error(f"Graph execution failed for run {run_id}: {e}", exc_info=True)
        raise


async def stream_agent(
    graph: StateGraph,
    initial_state: AgentState,
    run_id: str,
    checkpointer: Optional[AsyncPostgresSaver] = None,
    is_resume: bool = False,
):
    """
    Execute the agent graph with streaming state updates.

    Yields state updates as the graph progresses through nodes.

    Args:
        graph: Compiled StateGraph
        initial_state: Initial state (ignored if resuming)
        run_id: Run ID (used as thread_id for checkpoints)
        checkpointer: Optional checkpointer override
        is_resume: If True, resume from last checkpoint

    Yields:
        State updates from each node
    """
    # Compile with checkpointer
    compiled = compile_graph_with_checkpointer(graph, checkpointer)

    config = {
        "configurable": {
            "thread_id": run_id,
        }
    }

    try:
        if is_resume:
            logger.info(f"Streaming resumed run {run_id}")
            async for state_update in compiled.astream(None, config):
                yield state_update
        else:
            logger.info(f"Streaming new run {run_id}")
            async for state_update in compiled.astream(initial_state, config):
                yield state_update

    except Exception as e:
        logger.error(f"Graph streaming failed for run {run_id}: {e}", exc_info=True)
        raise
