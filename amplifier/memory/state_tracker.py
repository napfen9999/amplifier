"""Extraction state tracking for crash recovery

Tracks extraction progress to enable resuming after crashes or cancellations.
Provides state persistence for watchdog manager.

Storage: .data/memories/.extraction_state.json
"""

import json
import logging
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Storage location
STATE_FILE = Path(".data/memories/.extraction_state.json")


@dataclass
class TranscriptState:
    """State of individual transcript in extraction

    Attributes:
        id: Session ID of transcript
        status: Current status ("pending", "in_progress", "completed")
        memories: Count of memories extracted, 0 if not completed
        completed_at: When processing completed (ISO8601), None if not completed
    """

    id: str
    status: str  # "pending" | "in_progress" | "completed"
    memories: int = 0
    completed_at: str | None = None


@dataclass
class ExtractionState:
    """Overall extraction state

    Attributes:
        status: Overall status ("running", "completed", "failed", "cancelled")
        started_at: When extraction started (ISO8601)
        pid: Process ID of extraction worker, None if not running
        transcripts: List of transcript states
        last_update: When state was last updated (ISO8601)
    """

    status: str  # "running" | "completed" | "failed" | "cancelled"
    started_at: str  # ISO8601
    pid: int | None
    transcripts: list[TranscriptState]
    last_update: str  # ISO8601


def save_extraction_state(state: ExtractionState) -> Path:
    """Save state to storage

    Creates backup before writing for safety.

    Args:
        state: ExtractionState object to save

    Returns:
        Path to saved state file
    """
    # Ensure directory exists
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Create backup if file exists
    if STATE_FILE.exists():
        backup_path = STATE_FILE.with_suffix(".json.backup")
        STATE_FILE.rename(backup_path)

    # Update last_update timestamp
    state.last_update = datetime.now().isoformat()

    # Write state
    with open(STATE_FILE, "w") as f:
        json.dump(asdict(state), f, indent=2)
        f.write("\n")  # Ensure file ends with newline

    logger.info(f"[STATE TRACKER] Saved extraction state: {state.status}")
    return STATE_FILE


def load_extraction_state() -> ExtractionState | None:
    """Load state if exists

    Returns:
        ExtractionState if file exists, None otherwise
    """
    if not STATE_FILE.exists():
        return None

    try:
        with open(STATE_FILE) as f:
            data = json.load(f)

        # Convert transcript dicts to TranscriptState objects
        transcripts = [TranscriptState(**t) for t in data["transcripts"]]

        # Create ExtractionState
        state = ExtractionState(
            status=data["status"],
            started_at=data["started_at"],
            pid=data["pid"],
            transcripts=transcripts,
            last_update=data["last_update"],
        )

        logger.info(f"[STATE TRACKER] Loaded extraction state: {state.status}")
        return state

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"[STATE TRACKER] Failed to load state: {e}")
        return None


def clear_extraction_state() -> None:
    """Delete state file after successful completion

    Safe to call even if file doesn't exist.
    """
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        logger.info("[STATE TRACKER] Cleared extraction state")

        # Also remove backup if exists
        backup_path = STATE_FILE.with_suffix(".json.backup")
        if backup_path.exists():
            backup_path.unlink()


def update_transcript_progress(session_id: str, status: str, memories: int = 0) -> None:
    """Update specific transcript status in state

    Loads current state, updates transcript, saves back.
    Creates new state if none exists.

    Args:
        session_id: Session ID of transcript to update
        status: New status ("pending", "in_progress", "completed")
        memories: Memory count (only used for completed status)
    """
    # Load current state
    state = load_extraction_state()

    if state is None:
        logger.warning(f"[STATE TRACKER] No state to update for {session_id}")
        return

    # Find and update transcript
    found = False
    for transcript in state.transcripts:
        if transcript.id == session_id:
            transcript.status = status
            transcript.memories = memories
            if status == "completed":
                transcript.completed_at = datetime.now().isoformat()
            found = True
            break

    if not found:
        logger.warning(f"[STATE TRACKER] Transcript {session_id} not found in state")
        return

    # Save updated state
    save_extraction_state(state)
    logger.info(f"[STATE TRACKER] Updated {session_id}: {status}")
