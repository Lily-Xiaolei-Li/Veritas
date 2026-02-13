"""
Tests for Brain Provider Selection (B2.2).

Uses mocks to test brain call logic without hitting real LLMs.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.agent.brains import (
    parse_json_response,
    parse_brain_decision,
    BrainCallError,
    _extract_json_object,
    _repair_json_strings,
)
from app.agent.state import BrainDecision


class TestParseJsonResponse:
    """Tests for parse_json_response function."""

    def test_parse_valid_json(self):
        """Should parse valid JSON."""
        response = '{"key": "value", "number": 42}'
        result = parse_json_response(response, "B1")

        assert result == {"key": "value", "number": 42}

    def test_parse_json_with_whitespace(self):
        """Should handle leading/trailing whitespace."""
        response = '  \n{"key": "value"}\n  '
        result = parse_json_response(response, "B1")

        assert result == {"key": "value"}

    def test_parse_json_with_markdown_fences(self):
        """Should strip markdown code fences."""
        response = '```json\n{"key": "value"}\n```'
        result = parse_json_response(response, "B1")

        assert result == {"key": "value"}

    def test_parse_json_with_plain_fences(self):
        """Should strip plain markdown fences."""
        response = '```\n{"key": "value"}\n```'
        result = parse_json_response(response, "B1")

        assert result == {"key": "value"}

    def test_parse_invalid_json_raises_error(self):
        """Should raise BrainCallError for invalid JSON."""
        response = 'not valid json'

        with pytest.raises(BrainCallError) as exc_info:
            parse_json_response(response, "B1")

        assert "invalid JSON" in str(exc_info.value)
        assert exc_info.value.brain == "B1"

    def test_parse_incomplete_json_raises_error(self):
        """Should raise BrainCallError for incomplete JSON."""
        response = '{"key": "value"'

        with pytest.raises(BrainCallError) as exc_info:
            parse_json_response(response, "B2")

        assert "invalid JSON" in str(exc_info.value)
        assert exc_info.value.brain == "B2"


class TestParseBrainDecision:
    """Tests for parse_brain_decision function."""

    def test_parse_valid_decision(self):
        """Should parse valid BrainDecision JSON."""
        response = json.dumps({
            "decision": "answer",
            "intent": "answer_only",
            "tool_name": None,
            "target_artifacts": [],
            "plan_steps": ["Step 1"],
            "key_risks": [],
            "summary": "Test summary",
        })

        decision = parse_brain_decision(response, "B1")

        assert decision.decision == "answer"
        assert decision.intent == "answer_only"
        assert decision.tool_name is None
        assert decision.plan_steps == ["Step 1"]
        assert decision.summary == "Test summary"

    def test_parse_decision_with_markdown(self):
        """Should handle markdown-wrapped JSON."""
        response = '```json\n' + json.dumps({
            "decision": "use_tool",
            "intent": "run_bash",
            "tool_name": "bash",
            "target_artifacts": ["hello.py"],
            "plan_steps": [],
            "key_risks": [],
            "summary": "Create file",
        }) + '\n```'

        decision = parse_brain_decision(response, "B2")

        assert decision.decision == "use_tool"
        assert decision.intent == "run_bash"
        assert decision.tool_name == "bash"
        assert decision.target_artifacts == ["hello.py"]

    def test_parse_decision_missing_decision_field(self):
        """Should raise error when decision field is missing."""
        response = json.dumps({
            "intent": "answer_only",
            "summary": "Missing decision",
        })

        with pytest.raises(BrainCallError) as exc_info:
            parse_brain_decision(response, "B1")

        assert "missing 'decision'" in str(exc_info.value)

    def test_parse_decision_missing_intent_field(self):
        """Should raise error when intent field is missing."""
        response = json.dumps({
            "decision": "answer",
            "summary": "Missing intent",
        })

        with pytest.raises(BrainCallError) as exc_info:
            parse_brain_decision(response, "B2")

        assert "missing 'intent'" in str(exc_info.value)

    def test_parse_decision_caps_fields(self):
        """Should cap fields at their maximum lengths."""
        long_summary = "x" * 1000
        response = json.dumps({
            "decision": "answer",
            "intent": "answer_only",
            "target_artifacts": ["f1", "f2", "f3", "f4", "f5", "f6", "f7"],
            "plan_steps": ["s1", "s2", "s3", "s4", "s5", "s6", "s7"],
            "key_risks": ["r1", "r2", "r3", "r4", "r5"],
            "summary": long_summary,
        })

        decision = parse_brain_decision(response, "B1")

        assert len(decision.target_artifacts) <= 5
        assert len(decision.plan_steps) <= 5
        assert len(decision.key_risks) <= 3
        assert len(decision.summary) <= 500


class TestBrainDecisionDataclass:
    """Tests for BrainDecision dataclass methods."""

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        decision = BrainDecision(
            decision="answer",
            intent="answer_only",
            tool_name=None,
            target_artifacts=["file.py"],
            plan_steps=["Step 1"],
            key_risks=["Risk 1"],
            summary="Summary",
        )

        d = decision.to_dict()

        assert d["decision"] == "answer"
        assert d["intent"] == "answer_only"
        assert d["tool_name"] is None
        assert d["target_artifacts"] == ["file.py"]
        assert d["plan_steps"] == ["Step 1"]
        assert d["key_risks"] == ["Risk 1"]
        assert d["summary"] == "Summary"

    def test_from_dict(self):
        """Should create from dictionary correctly."""
        data = {
            "decision": "use_tool",
            "intent": "run_bash",
            "tool_name": "bash",
            "target_artifacts": ["hello.py"],
            "plan_steps": ["Create file"],
            "key_risks": [],
            "summary": "Create hello.py",
        }

        decision = BrainDecision.from_dict(data)

        assert decision.decision == "use_tool"
        assert decision.intent == "run_bash"
        assert decision.tool_name == "bash"
        assert decision.target_artifacts == ["hello.py"]

    def test_from_dict_with_defaults(self):
        """Should use defaults for missing fields."""
        data = {
            "decision": "escalate",
            "intent": "escalate",
        }

        decision = BrainDecision.from_dict(data)

        assert decision.decision == "escalate"
        assert decision.intent == "escalate"
        assert decision.tool_name is None
        assert decision.target_artifacts == []
        assert decision.plan_steps == []
        assert decision.summary == ""

    def test_from_dict_missing_required_uses_escalate(self):
        """Should default to escalate when fields missing."""
        data = {}

        decision = BrainDecision.from_dict(data)

        assert decision.decision == "escalate"
        assert decision.intent == "escalate"


class TestJsonExtraction:
    """Tests for JSON extraction helpers."""

    def test_extract_json_from_surrounding_text(self):
        """Should extract JSON object from text with surrounding content."""
        text = 'Here is the JSON: {"key": "value"} And some text after.'
        extracted, was_extracted = _extract_json_object(text)

        assert was_extracted is True
        assert extracted == '{"key": "value"}'

    def test_extract_nested_json(self):
        """Should extract full nested JSON object."""
        text = 'Result: {"outer": {"inner": "value"}} done'
        extracted, was_extracted = _extract_json_object(text)

        assert was_extracted is True
        assert extracted == '{"outer": {"inner": "value"}}'

    def test_extract_no_json(self):
        """Should return original text when no braces found."""
        text = 'no json here'
        extracted, was_extracted = _extract_json_object(text)

        assert was_extracted is False
        assert extracted == text

    def test_extract_invalid_brace_order(self):
        """Should return original when braces in wrong order."""
        text = '} something {'
        extracted, was_extracted = _extract_json_object(text)

        assert was_extracted is False


class TestJsonRepair:
    """Tests for JSON string repair."""

    def test_remove_trailing_comma_in_object(self):
        """Should remove trailing comma before closing brace."""
        text = '{"key": "value",}'
        repaired = _repair_json_strings(text)

        assert '{"key": "value"}' == repaired

    def test_remove_trailing_comma_in_array(self):
        """Should remove trailing comma before closing bracket."""
        text = '{"items": ["a", "b",]}'
        repaired = _repair_json_strings(text)

        assert repaired == '{"items": ["a", "b"]}'


class TestParseJsonResponseRobust:
    """Tests for robust JSON parsing with extraction and repair."""

    def test_parse_json_with_surrounding_text(self):
        """Should parse JSON even with surrounding text."""
        response = 'Here is my response: {"decision": "answer", "intent": "answer_only"} I hope that helps.'
        result = parse_json_response(response, "B1")

        assert result["decision"] == "answer"
        assert result["intent"] == "answer_only"

    def test_parse_json_with_trailing_comma(self):
        """Should handle JSON with trailing comma."""
        response = '{"decision": "answer", "intent": "answer_only",}'
        result = parse_json_response(response, "B1")

        assert result["decision"] == "answer"

    def test_parse_complex_json_with_text(self):
        """Should handle complex JSON extraction."""
        response = '''I'll analyze this request.
{"decision": "use_tool", "intent": "run_bash", "tool_name": "bash", "target_artifacts": ["test.py"], "plan_steps": ["Create file"], "key_risks": [], "summary": "Create test file"}
That's my decision.'''
        result = parse_json_response(response, "B2")

        assert result["decision"] == "use_tool"
        assert result["tool_name"] == "bash"
