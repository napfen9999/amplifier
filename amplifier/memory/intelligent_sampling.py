"""Intelligent two-pass extraction for large sessions

This module implements LLM-driven sampling that analyzes entire sessions
to identify important message ranges, then performs deep extraction only
from those ranges.

Approach:
- Pass 1 (Triage): Scan all messages to identify 3-5 important ranges
- Pass 2 (Extraction): Deep extraction from identified ranges only

Result: Intelligence of reading everything + efficiency of processing
only what matters.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Internal constants (not configurable - can be made configurable later if data shows need)
MAX_RANGES = 5  # Maximum ranges to identify in triage
TRIAGE_TIMEOUT = 30  # Timeout for triage pass (seconds)
FALLBACK_COUNT = 50  # Messages to process when triage fails


@dataclass
class MessageRange:
    """Range of important messages identified in triage pass"""

    start: int
    end: int
    reason: str  # Why this range is important (for logging/debugging)


async def two_pass_extraction(
    messages: list[dict],
    extractor: Any,  # MemoryExtractor instance
) -> dict:
    """Two-pass intelligent extraction from messages.

    Pass 1: Identify important message ranges using LLM triage
    Pass 2: Extract memories from those ranges only

    Args:
        messages: Full message list from session
        extractor: MemoryExtractor instance for LLM calls

    Returns:
        Extraction result with memories and metadata:
        {
            "memories": [...],
            "key_learnings": [...],
            "decisions_made": [...],
            "issues_solved": [...],
            "metadata": {
                "extraction_method": "two_pass_intelligent",
                "total_messages": int,
                "processed_messages": int,
                "coverage": float,
                "ranges_identified": int
            }
        }
    """
    total_messages = len(messages)
    logger.info(f"[TWO-PASS] Session: {total_messages} total messages")

    if not messages:
        raise RuntimeError("No messages provided for two-pass extraction")

    # Pass 1: Triage - Identify important ranges
    try:
        ranges = await _triage_pass(messages, extractor)
    except Exception as e:
        logger.warning(f"[TRIAGE] Failed with error: {e} - using fallback")
        ranges = []

    # Fallback: If triage produced no ranges, use last N messages
    if not ranges:
        logger.warning(f"[TRIAGE] No ranges identified - using fallback (last {FALLBACK_COUNT} messages)")
        fallback_start = max(0, total_messages - FALLBACK_COUNT)
        ranges = [MessageRange(start=fallback_start, end=total_messages, reason="fallback")]

    logger.info(f"[TRIAGE] Identified {len(ranges)} important ranges")
    logger.info(f"[TRIAGE] Ranges: {[(r.start, r.end, r.reason) for r in ranges]}")

    # Pass 2: Deep extraction from identified ranges
    result = await _extraction_pass(messages, ranges, extractor)

    # Calculate coverage
    processed_messages = sum(r.end - r.start for r in ranges)
    coverage = processed_messages / total_messages if total_messages > 0 else 0.0

    # Add metadata
    if "metadata" not in result:
        result["metadata"] = {}

    result["metadata"].update(
        {
            "extraction_method": "two_pass_intelligent",
            "total_messages": total_messages,
            "processed_messages": processed_messages,
            "coverage": coverage,
            "ranges_identified": len(ranges),
        }
    )

    logger.info(f"[TWO-PASS] Extracted {len(result.get('memories', []))} memories")
    logger.info(f"[TWO-PASS] Coverage: {coverage:.1%}")

    return result


async def _triage_pass(
    messages: list[dict],
    extractor: Any,
) -> list[MessageRange]:
    """Identify important message ranges using LLM triage.

    Args:
        messages: Full message list
        extractor: MemoryExtractor instance

    Returns:
        List of MessageRange objects identifying important sections

    Raises:
        TimeoutError: If triage exceeds timeout
        Exception: If triage fails for any reason
    """
    logger.info("[TRIAGE] Starting Pass 1: Identifying important ranges")

    # Format messages for triage (lightweight)
    formatted = _format_for_triage(messages)

    # Construct triage prompt
    total_messages = len(messages)
    prompt = f"""Analyze this conversation and identify the 3-5 most important message ranges.

Focus on:
- Important decisions made
- Problems solved
- Critical discussions
- Technical breakthroughs
- Key learnings

Return ONLY a JSON array of ranges (no explanations, no markdown):
[
  {{"start": 10, "end": 25, "reason": "Initial architecture decision"}},
  {{"start": 150, "end": 180, "reason": "Bug fix and solution discussion"}}
]

Rules:
- Start and end are 0-based message indices
- Each range should be 10-50 messages
- Maximum {MAX_RANGES} ranges
- Focus on quality over quantity
- Reason should be brief (5-10 words)

Conversation has {total_messages} messages.

Messages (condensed format - role and brief content):
{formatted}
"""

    # Call LLM with timeout
    try:
        async with asyncio.timeout(TRIAGE_TIMEOUT):
            # Use extractor's Claude SDK connection
            response = await extractor._extract_with_claude_full(prompt, context=None)

            if not response:
                raise RuntimeError("Triage returned empty response")

            # Parse ranges from response
            # Response should be in the same format as extraction: {"memories": [...], ...}
            # But we need to extract just the ranges array
            # The LLM might return the array directly or in a wrapper
            ranges_data = response

            # If response is the full extraction format, look for a ranges key
            # Otherwise, try to find an array in the response
            if isinstance(ranges_data, dict):
                # Try common keys
                for key in ["ranges", "important_ranges", "message_ranges"]:
                    if key in ranges_data:
                        ranges_data = ranges_data[key]
                        break

            # Parse ranges
            ranges = []
            if isinstance(ranges_data, list):
                for item in ranges_data:
                    if isinstance(item, dict) and "start" in item and "end" in item:
                        ranges.append(
                            MessageRange(
                                start=item["start"],
                                end=item["end"],
                                reason=item.get("reason", "unknown"),
                            )
                        )

            if not ranges:
                logger.warning("[TRIAGE] No valid ranges parsed from response")

            return ranges

    except TimeoutError:
        logger.warning(f"[TRIAGE] Timeout after {TRIAGE_TIMEOUT} seconds")
        raise
    except Exception as e:
        logger.error(f"[TRIAGE] Error: {e}")
        raise


async def _extraction_pass(
    messages: list[dict],
    ranges: list[MessageRange],
    extractor: Any,
) -> dict:
    """Extract memories from identified ranges.

    Args:
        messages: Full message list
        ranges: List of MessageRange objects to extract from
        extractor: MemoryExtractor instance

    Returns:
        Extraction result dictionary with memories
    """
    total_range_messages = sum(r.end - r.start for r in ranges)
    logger.info(f"[EXTRACTION] Processing {total_range_messages} messages from {len(ranges)} ranges")

    # Format ranges for extraction (full content)
    formatted_ranges = []
    for r in ranges:
        range_text = _format_range(messages, r.start, r.end)
        formatted_ranges.append(f"## Range {r.start}-{r.end}: {r.reason}\n\n{range_text}")

    combined_text = "\n\n---\n\n".join(formatted_ranges)

    # Construct extraction prompt
    prompt = f"""Extract detailed memories from these important conversation sections.

Focus on:
- Technical decisions and rationale
- Problems solved and solutions
- Key learnings and insights
- Patterns identified
- User preferences

Return as JSON:
{{
  "memories": [
    {{
      "type": "learning|decision|issue_solved|pattern|preference",
      "content": "Concise memory content (1-2 sentences)",
      "importance": 0.0-1.0,
      "tags": ["tag1", "tag2"]
    }}
  ],
  "key_learnings": ["What was learned"],
  "decisions_made": ["Decisions made"],
  "issues_solved": ["Problems resolved"]
}}

Sections to extract from (with full context):

{combined_text}

Remember:
- Be specific and actionable
- Include technical details
- Capture "why" not just "what"
- Each memory should be useful in future conversations
"""

    # Use extractor's existing extraction method
    result = await extractor._extract_with_claude_full(prompt, context=None)

    if not result:
        raise RuntimeError("Extraction pass returned no results")

    logger.info(f"[EXTRACTION] Extracted {len(result.get('memories', []))} memories from ranges")
    return result


def _format_for_triage(messages: list[dict]) -> str:
    """Format messages for triage pass (lightweight).

    Args:
        messages: Message list

    Returns:
        Formatted string with role and brief content per message
    """
    formatted = []

    for idx, msg in enumerate(messages):
        # Handle Claude Code transcript format
        if "message" in msg and isinstance(msg["message"], dict):
            inner_message = msg["message"]
            role = inner_message.get("role", msg.get("type", "unknown"))
            content = inner_message.get("content", "")
        else:
            role = msg.get("role", msg.get("type", "unknown"))
            content = msg.get("content", "")

        # Skip non-conversation roles
        if role not in ["user", "assistant"]:
            continue

        # Handle content as list or string
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            content = " ".join(text_parts)
        elif not isinstance(content, str):
            content = str(content)

        if not content:
            continue

        # Truncate for triage (keep it lightweight)
        if len(content) > 100:
            content = content[:100] + "..."

        formatted.append(f"{idx}: {role.upper()}: {content}")

    return "\n".join(formatted)


def _format_range(messages: list[dict], start: int, end: int) -> str:
    """Format specific message range for extraction (full content).

    Args:
        messages: Full message list
        start: Start index (inclusive)
        end: End index (exclusive)

    Returns:
        Formatted string with full content from range
    """
    formatted = []
    range_messages = messages[start:end]

    for msg in range_messages:
        # Handle Claude Code transcript format
        if "message" in msg and isinstance(msg["message"], dict):
            inner_message = msg["message"]
            role = inner_message.get("role", msg.get("type", "unknown"))
            content = inner_message.get("content", "")
        else:
            role = msg.get("role", msg.get("type", "unknown"))
            content = msg.get("content", "")

        # Skip non-conversation roles
        if role not in ["user", "assistant"]:
            continue

        # Handle content as list or string
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            content = " ".join(text_parts)
        elif not isinstance(content, str):
            content = str(content)

        if not content:
            continue

        formatted.append(f"{role.upper()}: {content}")

    return "\n\n".join(formatted)
