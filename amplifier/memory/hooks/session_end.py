"""SessionEnd hook integration for memory extraction

Connects the exit command to Claude Code's SessionEnd hook.
Triggers memory extraction when sessions end.

This module will be called by the SessionEnd hook to handle
transcript registration and extraction triggering.

Usage:
    # In SessionEnd hook:
    from amplifier.memory.hooks.session_end import handle_session_end

    result = handle_session_end(session_id, transcript_path)
"""

from pathlib import Path

from amplifier.memory.commands.exit_command import handle_exit
from amplifier.memory.extraction_logger import get_extraction_logger


def handle_session_end(session_id: str, transcript_path: str | Path) -> dict[str, bool | str]:
    """Handle SessionEnd hook event

    Registers transcript and starts extraction.

    Args:
        session_id: Claude Code session ID
        transcript_path: Path to transcript JSONL file (string or Path)

    Returns:
        Dict with:
        - success: Whether operation succeeded
        - message: Human-readable status message
        - extraction_started: Whether extraction was started
    """
    logger = get_extraction_logger()

    logger.info(f"SessionEnd hook: session_id={session_id}")

    # Convert to Path if string
    if isinstance(transcript_path, str):
        transcript_path = Path(transcript_path)

    # Delegate to exit command
    return handle_exit(session_id, transcript_path)


def get_hook_status() -> dict[str, str]:
    """Get hook integration status for debugging

    Returns:
        Dict with:
        - hook_name: Name of this hook
        - integration_status: Whether integration is active
        - description: What this hook does
    """
    return {
        "hook_name": "SessionEnd",
        "integration_status": "active",
        "description": "Triggers memory extraction when Claude Code sessions end",
    }
