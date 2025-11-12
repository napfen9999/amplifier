"""Centralized transcript tracking system

Tracks which transcripts have been processed for memory extraction.
Provides single source of truth for transcript state.

Storage: .data/transcripts.json
"""

import fcntl
import json
import logging
import shutil
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Storage location relative to project root
TRANSCRIPTS_FILE = Path(".data/transcripts.json")


@dataclass
class TranscriptRecord:
    """Record of a transcript file

    Attributes:
        session_id: Unique identifier for Claude Code session
        transcript_path: Absolute path to JSONL transcript file
        created_at: When transcript file was created (ISO8601)
        processed: Whether extraction completed
        processed_at: When extraction completed (ISO8601), None if not processed
        memories_extracted: Count of memories extracted, 0 if not processed
    """

    session_id: str
    transcript_path: str
    created_at: str  # ISO8601
    processed: bool = False
    processed_at: str | None = None  # ISO8601
    memories_extracted: int = 0


def _ensure_tracking_file() -> None:
    """Create tracking file if doesn't exist"""
    if not TRANSCRIPTS_FILE.exists():
        TRANSCRIPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"version": "1.0", "transcripts": []}
        TRANSCRIPTS_FILE.write_text(json.dumps(data, indent=2) + "\n")
        logger.info(f"[TRANSCRIPT TRACKER] Created tracking file: {TRANSCRIPTS_FILE}")


def _read_with_lock() -> dict:
    """Read tracking file with file lock

    Returns:
        Dictionary containing version and transcripts list
    """
    _ensure_tracking_file()

    with open(TRANSCRIPTS_FILE) as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
        try:
            data = json.load(f)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock

    return data


def _write_with_lock(data: dict) -> None:
    """Write tracking file with file lock

    Args:
        data: Dictionary containing version and transcripts list
    """
    # Backup before writing
    if TRANSCRIPTS_FILE.exists():
        backup_path = TRANSCRIPTS_FILE.with_suffix(".json.backup")
        shutil.copy2(TRANSCRIPTS_FILE, backup_path)

    with open(TRANSCRIPTS_FILE, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
        try:
            json.dump(data, f, indent=2)
            f.write("\n")  # Ensure file ends with newline
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock


def load_transcripts() -> list[TranscriptRecord]:
    """Load all transcript records from storage

    Returns:
        List of TranscriptRecord objects
    """
    data = _read_with_lock()
    return [TranscriptRecord(**t) for t in data["transcripts"]]


def save_transcripts(records: list[TranscriptRecord]) -> None:
    """Save transcript records to storage

    Args:
        records: List of TranscriptRecord objects to save
    """
    data = {"version": "1.0", "transcripts": [asdict(r) for r in records]}
    _write_with_lock(data)


def add_transcript_record(session_id: str, transcript_path: str) -> None:
    """Add new transcript to tracking

    Creates record with processed=False. Skips if session_id already exists.

    Args:
        session_id: Unique identifier for Claude Code session
        transcript_path: Absolute path to JSONL transcript file
    """
    data = _read_with_lock()

    # Check for duplicate
    if any(t["session_id"] == session_id for t in data["transcripts"]):
        logger.warning(f"[TRANSCRIPT TRACKER] Transcript {session_id} already tracked")
        return

    # Add new record
    record = TranscriptRecord(
        session_id=session_id,
        transcript_path=transcript_path,
        created_at=datetime.now().isoformat(),
        processed=False,
        processed_at=None,
        memories_extracted=0,
    )

    data["transcripts"].append(asdict(record))
    _write_with_lock(data)

    logger.info(f"[TRANSCRIPT TRACKER] Added transcript: {session_id}")


def mark_transcript_processed(session_id: str, memories_count: int) -> None:
    """Mark transcript as processed with memory count

    Updates processed=True, processed_at=now, memories_extracted=count

    Args:
        session_id: Unique identifier for Claude Code session
        memories_count: Number of memories extracted from transcript
    """
    data = _read_with_lock()

    # Find and update record
    found = False
    for transcript in data["transcripts"]:
        if transcript["session_id"] == session_id:
            transcript["processed"] = True
            transcript["processed_at"] = datetime.now().isoformat()
            transcript["memories_extracted"] = memories_count
            found = True
            break

    if not found:
        logger.warning(f"[TRANSCRIPT TRACKER] Transcript {session_id} not found")
        return

    _write_with_lock(data)
    logger.info(f"[TRANSCRIPT TRACKER] Marked {session_id} as processed ({memories_count} memories)")


def get_unprocessed_transcripts() -> list[TranscriptRecord]:
    """Get all transcripts where processed=False

    Returns:
        List of TranscriptRecord objects not yet processed
    """
    transcripts = load_transcripts()
    return [t for t in transcripts if not t.processed]


def get_transcript_by_session(session_id: str) -> TranscriptRecord | None:
    """Get specific transcript record

    Args:
        session_id: Unique identifier for Claude Code session

    Returns:
        TranscriptRecord if found, None otherwise
    """
    transcripts = load_transcripts()
    for t in transcripts:
        if t.session_id == session_id:
            return t
    return None


def get_all_transcripts() -> list[TranscriptRecord]:
    """Get all transcript records

    Alias for load_transcripts() for consistency with documentation.

    Returns:
        List of all TranscriptRecord objects
    """
    return load_transcripts()
