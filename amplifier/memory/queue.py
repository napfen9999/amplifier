"""Extraction queue management

JSONL-based queue for pending memory extractions. Decouples hook execution from
LLM-based extraction processing.
"""

import json
import logging
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

QUEUE_FILE = Path(".data/extraction_queue.jsonl")


@dataclass
class QueuedExtraction:
    """Item in extraction queue

    Attributes:
        session_id: Unique session identifier
        transcript_path: Path to JSONL transcript file
        timestamp: ISO8601 timestamp when queued
        hook_event: Hook event type ("Stop" or "SubagentStop")
        retries: Number of processing attempts
        last_error: Last error message if processing failed
    """

    session_id: str
    transcript_path: str
    timestamp: str
    hook_event: str
    retries: int = 0
    last_error: str | None = None


def queue_extraction(item: QueuedExtraction) -> None:
    """Append item to extraction queue

    Non-blocking operation that appends to JSONL file. Creates directory
    structure if needed.

    Args:
        item: Extraction item to queue
    """
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(QUEUE_FILE, "a") as f:
        f.write(json.dumps(asdict(item)) + "\n")

    logger.info(f"[QUEUE] Queued {item.session_id}")


def get_queued_items() -> list[QueuedExtraction]:
    """Read all pending items from queue

    Returns:
        List of queued extraction items (empty if no queue file)
    """
    if not QUEUE_FILE.exists():
        return []

    items = []
    with open(QUEUE_FILE) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                items.append(QueuedExtraction(**data))

    return items


def remove_from_queue(session_id: str) -> None:
    """Remove item from queue after processing

    Rewrites queue file excluding the specified session.

    Args:
        session_id: Session ID to remove
    """
    if not QUEUE_FILE.exists():
        return

    # Read all items except the one to remove
    remaining = []
    with open(QUEUE_FILE) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                if data.get("session_id") != session_id:
                    remaining.append(line)

    # Rewrite queue
    with open(QUEUE_FILE, "w") as f:
        f.writelines(remaining)

    logger.info(f"[QUEUE] Removed {session_id}")


def clear_queue() -> None:
    """Clear entire queue

    Deletes queue file. Used for testing and maintenance.
    """
    if QUEUE_FILE.exists():
        QUEUE_FILE.unlink()
    logger.info("[QUEUE] Cleared")
