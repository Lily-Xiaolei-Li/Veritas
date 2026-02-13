"""
Tests for Consensus Detection (B2.2).

Tests intent-based structured consensus detection.
"""


from app.agent.consensus import check_consensus, merge_decisions, should_escalate
from app.agent.state import BrainDecision


class TestCheckConsensus:
    """Tests for check_consensus function."""

    def test_consensus_on_answer_only(self):
        """Should detect consensus when both brains agree on answer_only."""
        b1 = BrainDecision(
            decision="answer",
            intent="answer_only",
            summary="I think we should just answer",
        )
        b2 = BrainDecision(
            decision="answer",
            intent="answer_only",
            summary="Agreed, simple answer",
        )

        reached, reason = check_consensus(b1, b2)

        assert reached is True
        assert "consensus_on_answer_only" in reason

    def test_consensus_on_plan_only(self):
        """Should detect consensus when both agree on plan_only."""
        b1 = BrainDecision(
            decision="answer",
            intent="plan_only",
            plan_steps=["Step 1", "Step 2"],
            summary="Let's plan",
        )
        b2 = BrainDecision(
            decision="answer",
            intent="plan_only",
            plan_steps=["Step A", "Step B"],
            summary="Planning approach",
        )

        reached, reason = check_consensus(b1, b2)

        assert reached is True
        assert "consensus_on_plan_only" in reason

    def test_consensus_on_run_bash_matching_targets(self):
        """Should detect consensus on run_bash with overlapping targets."""
        b1 = BrainDecision(
            decision="use_tool",
            intent="run_bash",
            tool_name="bash",
            target_artifacts=["hello.py", "test.py"],
            summary="Create files",
        )
        b2 = BrainDecision(
            decision="use_tool",
            intent="run_bash",
            tool_name="bash",
            target_artifacts=["hello.py"],
            summary="Create hello.py",
        )

        reached, reason = check_consensus(b1, b2)

        assert reached is True
        assert "consensus_on_run_bash" in reason

    def test_no_consensus_decision_mismatch(self):
        """Should reject when decision types differ."""
        b1 = BrainDecision(
            decision="answer",
            intent="answer_only",
            summary="Answer directly",
        )
        b2 = BrainDecision(
            decision="use_tool",
            intent="run_bash",
            tool_name="bash",
            summary="Need to run tool",
        )

        reached, reason = check_consensus(b1, b2)

        assert reached is False
        assert "decision_mismatch" in reason

    def test_no_consensus_intent_mismatch(self):
        """Should reject when intents differ."""
        b1 = BrainDecision(
            decision="answer",
            intent="answer_only",
            summary="Just answer",
        )
        b2 = BrainDecision(
            decision="answer",
            intent="plan_only",
            summary="Need a plan",
        )

        reached, reason = check_consensus(b1, b2)

        assert reached is False
        assert "intent_mismatch" in reason

    def test_no_consensus_tool_name_mismatch(self):
        """Should reject run_bash when tool names differ."""
        b1 = BrainDecision(
            decision="use_tool",
            intent="run_bash",
            tool_name="bash",
            target_artifacts=["file.py"],
            summary="Use bash",
        )
        b2 = BrainDecision(
            decision="use_tool",
            intent="run_bash",
            tool_name="python",  # Different tool
            target_artifacts=["file.py"],
            summary="Use python",
        )

        reached, reason = check_consensus(b1, b2)

        assert reached is False
        assert "tool_name_mismatch" in reason

    def test_no_consensus_no_artifact_overlap(self):
        """Should reject run_bash when no target artifacts overlap."""
        b1 = BrainDecision(
            decision="use_tool",
            intent="run_bash",
            tool_name="bash",
            target_artifacts=["file1.py"],
            summary="Create file1",
        )
        b2 = BrainDecision(
            decision="use_tool",
            intent="run_bash",
            tool_name="bash",
            target_artifacts=["file2.py"],  # No overlap
            summary="Create file2",
        )

        reached, reason = check_consensus(b1, b2)

        assert reached is False
        assert "target_artifact_mismatch" in reason

    def test_consensus_on_ask_user(self):
        """Should detect consensus when both want to ask user."""
        b1 = BrainDecision(
            decision="ask_user",
            intent="ask_user",
            summary="Need clarification",
        )
        b2 = BrainDecision(
            decision="ask_user",
            intent="ask_user",
            summary="Also need to ask",
        )

        reached, reason = check_consensus(b1, b2)

        assert reached is True
        assert "consensus_on_ask_user" in reason


class TestMergeDecisions:
    """Tests for merge_decisions function."""

    def test_merge_basic_decisions(self):
        """Should merge two agreeing decisions."""
        b1 = BrainDecision(
            decision="answer",
            intent="answer_only",
            plan_steps=["B1 step 1"],
            key_risks=["B1 risk"],
            summary="B1 summary",
        )
        b2 = BrainDecision(
            decision="answer",
            intent="answer_only",
            plan_steps=["B2 step 1", "B2 step 2"],
            key_risks=["B2 risk"],
            summary="B2 summary",
        )

        merged = merge_decisions(b1, b2)

        assert merged.decision == "answer"
        assert merged.intent == "answer_only"
        # Should use B2's plan
        assert merged.plan_steps == ["B2 step 1", "B2 step 2"]
        # Should merge risks
        assert "B1 risk" in merged.key_risks or "B2 risk" in merged.key_risks
        # Summary should combine both
        assert "B1" in merged.summary and "B2" in merged.summary

    def test_merge_artifacts(self):
        """Should union target artifacts."""
        b1 = BrainDecision(
            decision="use_tool",
            intent="run_bash",
            tool_name="bash",
            target_artifacts=["file1.py", "file2.py"],
            summary="B1",
        )
        b2 = BrainDecision(
            decision="use_tool",
            intent="run_bash",
            tool_name="bash",
            target_artifacts=["file2.py", "file3.py"],
            summary="B2",
        )

        merged = merge_decisions(b1, b2)

        assert len(merged.target_artifacts) == 3
        assert "file1.py" in merged.target_artifacts
        assert "file2.py" in merged.target_artifacts
        assert "file3.py" in merged.target_artifacts

    def test_merge_caps_artifacts(self):
        """Should cap merged artifacts at 5."""
        b1 = BrainDecision(
            decision="use_tool",
            intent="run_bash",
            tool_name="bash",
            target_artifacts=["f1.py", "f2.py", "f3.py"],
            summary="B1",
        )
        b2 = BrainDecision(
            decision="use_tool",
            intent="run_bash",
            tool_name="bash",
            target_artifacts=["f4.py", "f5.py", "f6.py"],
            summary="B2",
        )

        merged = merge_decisions(b1, b2)

        assert len(merged.target_artifacts) <= 5


class TestShouldEscalate:
    """Tests for should_escalate function."""

    def test_escalate_when_b1_requests(self):
        """Should escalate when B1 requests it."""
        b1 = BrainDecision(
            decision="escalate",
            intent="escalate",
            summary="Safety concern",
        )
        b2 = BrainDecision(
            decision="answer",
            intent="answer_only",
            summary="Normal answer",
        )

        should, reason = should_escalate(b1, b2)

        assert should is True
        assert reason == "BRAIN_REQUESTED"

    def test_escalate_when_b2_requests(self):
        """Should escalate when B2 requests it."""
        b1 = BrainDecision(
            decision="answer",
            intent="answer_only",
            summary="Normal answer",
        )
        b2 = BrainDecision(
            decision="escalate",
            intent="escalate",
            summary="Need human review",
        )

        should, reason = should_escalate(b1, b2)

        assert should is True
        assert reason == "BRAIN_REQUESTED"

    def test_no_escalate_when_neither_requests(self):
        """Should not escalate when neither brain requests it."""
        b1 = BrainDecision(
            decision="answer",
            intent="answer_only",
            summary="Answer",
        )
        b2 = BrainDecision(
            decision="answer",
            intent="answer_only",
            summary="Also answer",
        )

        should, reason = should_escalate(b1, b2)

        assert should is False
        assert reason == ""
