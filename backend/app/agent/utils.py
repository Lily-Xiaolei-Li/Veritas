"""
Agent Utilities (B2.2).

Provides utility functions for state management and text processing.
"""

from typing import List, Tuple


def cap_text(text: str, max_len: int = 500) -> Tuple[str, bool, int]:
    """
    Truncate text to a maximum length.

    Returns a tuple of (capped_text, was_truncated, original_length).
    This is a SYNC function - caller emits event if truncation occurred.

    Args:
        text: The text to potentially truncate
        max_len: Maximum allowed length (default 500)

    Returns:
        Tuple of:
            - capped_text: The (possibly truncated) text
            - was_truncated: True if truncation occurred
            - original_length: Original length before truncation

    Example:
        capped, was_truncated, orig_len = cap_text(raw_text, 500)
        if was_truncated:
            await context.emitter.emit_state_truncated("field_name", orig_len, 500)
        return {"field_name": capped}
    """
    original_length = len(text)
    if original_length <= max_len:
        return text, False, original_length

    # Truncate with ellipsis
    capped = text[:max_len - 3] + "..."
    return capped, True, original_length


def cap_list_items(
    items: List[str],
    max_items: int = 5,
    max_item_len: int = 200,
) -> Tuple[List[str], bool]:
    """
    Cap a list of strings by both count and individual item length.

    Args:
        items: List of strings to cap
        max_items: Maximum number of items (default 5)
        max_item_len: Maximum length per item (default 200)

    Returns:
        Tuple of:
            - capped_items: The capped list
            - was_modified: True if any truncation/removal occurred
    """
    was_modified = False

    # Limit item count
    if len(items) > max_items:
        items = items[:max_items]
        was_modified = True

    # Limit each item's length
    capped_items = []
    for item in items:
        if len(item) > max_item_len:
            capped_items.append(item[:max_item_len - 3] + "...")
            was_modified = True
        else:
            capped_items.append(item)

    return capped_items, was_modified


def extract_latest_user_message(messages: list) -> str:
    """
    Extract the content of the latest user message from the message list.

    Args:
        messages: List of AgentMessage objects

    Returns:
        Content of the latest user message, or empty string if none found
    """
    for msg in reversed(messages):
        if hasattr(msg, 'role') and msg.role == "user":
            return msg.content
        elif isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
    return ""
