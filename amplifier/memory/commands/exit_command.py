"""Exit command for memory extraction

User-facing command to trigger memory extraction on session exit.
Registers transcripts for processing and starts extraction worker.

Usage:
    from amplifier.memory.commands.exit_command import handle_exit

    # In SessionEnd hook:
    handle_exit(session_id, transcript_path)
"""

from pathlib import Path

from amplifier.memory.extraction_logger import get_extraction_logger
from amplifier.memory.transcript_tracker import add_transcript_record
from amplifier.memory.watchdog import get_extraction_status
from amplifier.memory.watchdog import start_extraction


def handle_exit(session_id: str, transcript_path: Path) -> dict[str, bool | str]:
    """Handle session exit with memory extraction

    Registers transcript and starts extraction if not already running.

    Args:
        session_id: Claude Code session ID
        transcript_path: Path to transcript JSONL file

    Returns:
        Dict with:
        - success: Whether operation succeeded
        - message: Human-readable status message
        - extraction_started: Whether extraction was started (vs already running)
    """
    logger = get_extraction_logger()

    logger.info(f"Exit command: session_id={session_id}, transcript={transcript_path}")

    # Validate transcript exists
    if not transcript_path.exists():
        logger.error(f"Transcript not found: {transcript_path}")
        return {
            "success": False,
            "message": f"Transcript file not found: {transcript_path}",
            "extraction_started": False,
        }

    # Register transcript
    try:
        add_transcript_record(session_id, str(transcript_path))
        logger.info(f"Registered transcript: {session_id}")
    except Exception as e:
        logger.error(f"Failed to register transcript: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to register transcript: {e}",
            "extraction_started": False,
        }

    # Check if extraction already running
    status = get_extraction_status()

    if status.status == "running":
        logger.info("Extraction already running, transcript queued")
        return {
            "success": True,
            "message": f"Transcript registered. Extraction already in progress (PID: {status.pid})",
            "extraction_started": False,
        }

    # Start extraction
    try:
        transcripts_dir = transcript_path.parent
        started = start_extraction(transcripts_dir)

        if started:
            logger.info("Extraction started")
            return {
                "success": True,
                "message": "Transcript registered and extraction started",
                "extraction_started": True,
            }
        # Should not happen (start_extraction returns False only if already running)
        logger.warning("Extraction not started (unexpected)")
        return {
            "success": True,
            "message": "Transcript registered",
            "extraction_started": False,
        }

    except Exception as e:
        logger.error(f"Failed to start extraction: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Transcript registered but failed to start extraction: {e}",
            "extraction_started": False,
        }


def get_exit_command_status() -> dict[str, str | int]:
    """Get current extraction status for display

    Returns:
        Dict with:
        - status: Current status string
        - message: Human-readable message
        - transcripts_total: Total transcripts (if running/completed)
        - transcripts_completed: Completed transcripts (if running/completed)
        - memories_extracted: Total memories extracted (if running/completed)
    """
    status = get_extraction_status()

    if status.status == "idle":
        return {
            "status": "idle",
            "message": "No extraction in progress",
        }

    if status.status == "running":
        return {
            "status": "running",
            "message": f"Extraction in progress: {status.transcripts_completed}/{status.transcripts_total} transcripts",
            "transcripts_total": status.transcripts_total,
            "transcripts_completed": status.transcripts_completed,
            "memories_extracted": status.memories_extracted,
        }

    if status.status == "completed":
        return {
            "status": "completed",
            "message": f"Extraction complete: {status.transcripts_completed} transcripts, {status.memories_extracted} memories",
            "transcripts_total": status.transcripts_total,
            "transcripts_completed": status.transcripts_completed,
            "memories_extracted": status.memories_extracted,
        }

    if status.status == "failed":
        return {
            "status": "failed",
            "message": f"Extraction failed: {status.transcripts_completed}/{status.transcripts_total} transcripts completed",
            "transcripts_total": status.transcripts_total,
            "transcripts_completed": status.transcripts_completed,
            "memories_extracted": status.memories_extracted,
        }

    if status.status == "crashed":
        return {
            "status": "crashed",
            "message": f"Extraction crashed: {status.transcripts_completed}/{status.transcripts_total} transcripts completed before crash",
            "transcripts_total": status.transcripts_total,
            "transcripts_completed": status.transcripts_completed,
            "memories_extracted": status.memories_extracted,
        }

    return {
        "status": "unknown",
        "message": f"Unknown status: {status.status}",
    }
