"""
Tests for Agent Utilities (B2.2).

Tests cap_text, cap_list_items, and extract_latest_user_message.
"""

import pytest

from app.agent.utils import cap_text, cap_list_items, extract_latest_user_message
from app.agent.state import AgentMessage


class TestCapText:
    """Tests for cap_text function."""

    def test_cap_text_short_text_unchanged(self):
        """Short text should pass through unchanged."""
        text = "Hello world"
        capped, was_truncated, orig_len = cap_text(text, 500)

        assert capped == "Hello world"
        assert was_truncated is False
        assert orig_len == 11

    def test_cap_text_exact_length_unchanged(self):
        """Text exactly at max length should pass through."""
        text = "x" * 500
        capped, was_truncated, orig_len = cap_text(text, 500)

        assert capped == text
        assert was_truncated is False
        assert orig_len == 500

    def test_cap_text_long_text_truncated(self):
        """Long text should be truncated with ellipsis."""
        text = "x" * 600
        capped, was_truncated, orig_len = cap_text(text, 500)

        assert len(capped) == 500
        assert capped.endswith("...")
        assert was_truncated is True
        assert orig_len == 600

    def test_cap_text_custom_max_length(self):
        """Custom max length should be respected."""
        text = "Hello world, this is a test"
        capped, was_truncated, orig_len = cap_text(text, 10)

        assert len(capped) == 10
        assert capped == "Hello w..."
        assert was_truncated is True
        assert orig_len == 27

    def test_cap_text_empty_string(self):
        """Empty string should pass through."""
        text = ""
        capped, was_truncated, orig_len = cap_text(text, 500)

        assert capped == ""
        assert was_truncated is False
        assert orig_len == 0


class TestCapListItems:
    """Tests for cap_list_items function."""

    def test_cap_list_items_under_limits(self):
        """List under limits should pass through unchanged."""
        items = ["item1", "item2", "item3"]
        capped, was_modified = cap_list_items(items, max_items=5, max_item_len=200)

        assert capped == items
        assert was_modified is False

    def test_cap_list_items_too_many_items(self):
        """List with too many items should be truncated."""
        items = ["item1", "item2", "item3", "item4", "item5", "item6"]
        capped, was_modified = cap_list_items(items, max_items=3, max_item_len=200)

        assert len(capped) == 3
        assert capped == ["item1", "item2", "item3"]
        assert was_modified is True

    def test_cap_list_items_long_item(self):
        """Items over max length should be truncated."""
        items = ["short", "x" * 300]
        capped, was_modified = cap_list_items(items, max_items=5, max_item_len=100)

        assert len(capped) == 2
        assert capped[0] == "short"
        assert len(capped[1]) == 100
        assert capped[1].endswith("...")
        assert was_modified is True

    def test_cap_list_items_empty_list(self):
        """Empty list should pass through."""
        items = []
        capped, was_modified = cap_list_items(items, max_items=5, max_item_len=200)

        assert capped == []
        assert was_modified is False

    def test_cap_list_items_both_limits_exceeded(self):
        """Both item count and length limits should be enforced."""
        items = ["x" * 300 for _ in range(10)]
        capped, was_modified = cap_list_items(items, max_items=3, max_item_len=50)

        assert len(capped) == 3
        for item in capped:
            assert len(item) == 50
            assert item.endswith("...")
        assert was_modified is True


class TestExtractLatestUserMessage:
    """Tests for extract_latest_user_message function."""

    def test_extract_from_agent_messages(self):
        """Should extract content from AgentMessage objects."""
        messages = [
            AgentMessage(role="user", content="First message"),
            AgentMessage(role="assistant", content="Response"),
            AgentMessage(role="user", content="Second message"),
        ]

        result = extract_latest_user_message(messages)
        assert result == "Second message"

    def test_extract_from_dict_messages(self):
        """Should extract content from dict messages."""
        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Latest"},
        ]

        result = extract_latest_user_message(messages)
        assert result == "Latest"

    def test_extract_no_user_messages(self):
        """Should return empty string if no user messages."""
        messages = [
            AgentMessage(role="assistant", content="Response"),
            AgentMessage(role="system", content="System"),
        ]

        result = extract_latest_user_message(messages)
        assert result == ""

    def test_extract_empty_list(self):
        """Should return empty string for empty list."""
        result = extract_latest_user_message([])
        assert result == ""

    def test_extract_mixed_message_types(self):
        """Should handle mixed AgentMessage and dict."""
        messages = [
            {"role": "user", "content": "Dict message"},
            AgentMessage(role="user", content="AgentMessage"),
        ]

        result = extract_latest_user_message(messages)
        assert result == "AgentMessage"
