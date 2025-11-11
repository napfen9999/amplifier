"""Message filtering for memory extraction

Removes sidechain messages (internal Claude Code operations) from conversation
transcripts to improve extraction quality.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def filter_sidechain_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove sidechain messages from conversation

    Sidechain messages are internal Claude Code operations (warmup, tool execution,
    subagent coordination) that aren't part of the main user-assistant conversation.

    Args:
        messages: Full message list from transcript

    Returns:
        Filtered messages (main conversation only)
    """
    filtered = []

    for msg in messages:
        # Check for top-level sidechain marker
        if msg.get("isSidechain", False):
            continue

        # Check nested sidechain marker (message.message.isSidechain)
        if isinstance(msg.get("message"), dict) and msg["message"].get("isSidechain", False):
            continue

        filtered.append(msg)

    removed = len(messages) - len(filtered)
    logger.info(f"[FILTER] {len(messages)} → {len(filtered)} messages (removed {removed} sidechain)")

    return filtered


def is_subagent_message(msg: dict[str, Any]) -> bool:
    """Check if message is from subagent (not main conversation)

    Args:
        msg: Message to check

    Returns:
        True if message is from subagent
    """
    content = str(msg.get("content", ""))

    subagent_markers = [
        "Task tool call",
        "I'll use the Task tool",
        "Let me launch",
        "[SUBAGENT]",
    ]

    return any(marker in content for marker in subagent_markers)
