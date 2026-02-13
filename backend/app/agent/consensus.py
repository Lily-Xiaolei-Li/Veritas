"""
Consensus Detection (B2.2).

Implements intent-based structured consensus detection for multi-brain deliberation.
Consensus is determined by matching decision, intent, and (for bash) tool/artifact overlap.
"""

from typing import Tuple

from app.logging_config import get_logger

from .state import BrainDecision

logger = get_logger("agent.consensus")


def check_consensus(b1: BrainDecision, b2: BrainDecision) -> Tuple[bool, str]:
    """
    Check if two brain decisions have reached consensus.

    Consensus rules (structured, not string-based):
    1. Decision type MUST match
    2. Intent MUST match
    3. If intent is "run_bash", tool_name must match AND targets must overlap

    Args:
        b1: Brain 1's decision
        b2: Brain 2's decision

    Returns:
        Tuple of (consensus_reached, reason)
        - If consensus: (True, "consensus_on_{intent}")
        - If no consensus: (False, "mismatch_{field}")
    """
    # Rule 1: Decision type MUST match
    if b1.decision != b2.decision:
        reason = f"decision_mismatch: B1={b1.decision}, B2={b2.decision}"
        logger.debug(f"No consensus: {reason}")
        return False, reason

    # Rule 2: Intent MUST match
    if b1.intent != b2.intent:
        reason = f"intent_mismatch: B1={b1.intent}, B2={b2.intent}"
        logger.debug(f"No consensus: {reason}")
        return False, reason

    # Rule 3: If bash tool, tool_name must match and targets must overlap
    if b1.intent == "run_bash":
        if b1.tool_name != b2.tool_name:
            reason = f"tool_name_mismatch: B1={b1.tool_name}, B2={b2.tool_name}"
            logger.debug(f"No consensus: {reason}")
            return False, reason

        # At least one target artifact in common
        b1_targets = set(b1.target_artifacts)
        b2_targets = set(b2.target_artifacts)
        overlap = b1_targets & b2_targets

        if not overlap:
            reason = f"target_artifact_mismatch: B1={b1_targets}, B2={b2_targets}"
            logger.debug(f"No consensus: {reason}")
            return False, reason

    # Consensus reached!
    reason = f"consensus_on_{b1.intent}"
    logger.info(f"Consensus reached: {reason}")
    return True, reason


def merge_decisions(b1: BrainDecision, b2: BrainDecision) -> BrainDecision:
    """
    Merge two consensus decisions into a final decision.

    When consensus is reached, create a merged decision that combines:
    - Decision/intent from either (they match)
    - Union of target_artifacts (capped at 5)
    - B2's plan_steps (flagship model's reasoning)
    - Union of key_risks (capped at 3)
    - Combined summary

    Args:
        b1: Brain 1's decision
        b2: Brain 2's decision

    Returns:
        Merged BrainDecision
    """
    # Use B2's plan (flagship reasoning) but merge artifacts and risks
    merged_artifacts = list(set(b1.target_artifacts) | set(b2.target_artifacts))[:5]
    merged_risks = list(set(b1.key_risks) | set(b2.key_risks))[:3]

    # Combine summaries
    combined_summary = f"B2: {b2.summary[:200]} | B1: {b1.summary[:200]}"
    if len(combined_summary) > 500:
        combined_summary = combined_summary[:497] + "..."

    return BrainDecision(
        decision=b1.decision,  # Same as b2.decision
        intent=b1.intent,  # Same as b2.intent
        tool_name=b1.tool_name,  # Same as b2.tool_name
        target_artifacts=merged_artifacts,
        plan_steps=b2.plan_steps,  # Use B2's plan
        key_risks=merged_risks,
        summary=combined_summary,
    )


def should_escalate(b1: BrainDecision, b2: BrainDecision) -> Tuple[bool, str]:
    """
    Check if either brain is requesting escalation.

    Args:
        b1: Brain 1's decision
        b2: Brain 2's decision

    Returns:
        Tuple of (should_escalate, reason)
    """
    if b1.intent == "escalate":
        return True, "BRAIN_REQUESTED"
    if b2.intent == "escalate":
        return True, "BRAIN_REQUESTED"
    return False, ""
