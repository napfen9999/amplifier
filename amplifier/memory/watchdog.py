"""Watchdog manager for extraction worker subprocess

Manages extraction worker lifecycle:
- Spawns worker subprocess
- Monitors process health
- Detects crashes
- Reports status
- Handles cleanup

This provides process isolation and crash recovery for memory extraction.

Usage:
    from amplifier.memory.watchdog import start_extraction, get_extraction_status

    # Start extraction
    start_extraction(transcripts_dir)

    # Check status
    status = get_extraction_status()
    if status == "running":
        print("Extraction in progress")
    elif status == "completed":
        print("Extraction finished")
"""

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from amplifier.memory.extraction_logger import get_extraction_logger
from amplifier.memory.state_tracker import ExtractionState
from amplifier.memory.state_tracker import TranscriptState
from amplifier.memory.state_tracker import clear_extraction_state
from amplifier.memory.state_tracker import load_extraction_state
from amplifier.memory.state_tracker import save_extraction_state
from amplifier.memory.transcript_tracker import get_unprocessed_transcripts


@dataclass
class ExtractionStatus:
    """Status of extraction process

    Attributes:
        status: Current status (idle, running, completed, failed, crashed)
        pid: Process ID if running, None otherwise
        started_at: ISO8601 timestamp when started, None if not started
        transcripts_total: Total transcripts to process
        transcripts_completed: Number completed so far
        memories_extracted: Total memories extracted
    """

    status: str  # "idle" | "running" | "completed" | "failed" | "crashed"
    pid: int | None = None
    started_at: str | None = None
    transcripts_total: int = 0
    transcripts_completed: int = 0
    memories_extracted: int = 0


def get_extraction_status() -> ExtractionStatus:
    """Get current extraction status

    Checks extraction state and process health to determine:
    - idle: No extraction in progress
    - running: Extraction process running
    - completed: Extraction finished successfully
    - failed: Extraction finished with errors
    - crashed: Process died unexpectedly

    Returns:
        ExtractionStatus with current state
    """
    state = load_extraction_state()

    if state is None:
        # No state file = never run or cleaned up
        return ExtractionStatus(status="idle")

    # Check if process is still running
    if state.pid is not None:
        if _is_process_running(state.pid):
            # Process alive, calculate progress
            completed = sum(1 for t in state.transcripts if t.status == "completed")
            memories = sum(t.memories for t in state.transcripts)

            return ExtractionStatus(
                status="running",
                pid=state.pid,
                started_at=state.started_at,
                transcripts_total=len(state.transcripts),
                transcripts_completed=completed,
                memories_extracted=memories,
            )
        # Process died but state says running = crash
        if state.status == "running":
            return ExtractionStatus(
                status="crashed",
                pid=None,
                started_at=state.started_at,
                transcripts_total=len(state.transcripts),
                transcripts_completed=sum(1 for t in state.transcripts if t.status == "completed"),
                memories_extracted=sum(t.memories for t in state.transcripts),
            )

    # Process not running, check final status
    if state.status in ["completed", "completed_with_errors"]:
        completed = sum(1 for t in state.transcripts if t.status == "completed")
        memories = sum(t.memories for t in state.transcripts)

        status = "completed" if state.status == "completed" else "failed"

        return ExtractionStatus(
            status=status,
            pid=None,
            started_at=state.started_at,
            transcripts_total=len(state.transcripts),
            transcripts_completed=completed,
            memories_extracted=memories,
        )

    # Unknown state
    return ExtractionStatus(status="idle")


def start_extraction(transcripts_dir: Path) -> bool:
    """Start extraction worker subprocess

    Spawns extraction worker as subprocess with:
    - Process isolation (crashes don't affect main process)
    - PID tracking for monitoring
    - Initial state persistence

    Args:
        transcripts_dir: Directory containing transcript files

    Returns:
        True if started successfully, False if already running

    Raises:
        RuntimeError: If worker fails to start
    """
    logger = get_extraction_logger()

    # Check if already running
    current_status = get_extraction_status()
    if current_status.status == "running":
        logger.warning(f"Extraction already running (PID: {current_status.pid})")
        return False

    # Get unprocessed transcripts
    unprocessed = get_unprocessed_transcripts()
    if len(unprocessed) == 0:
        logger.info("No unprocessed transcripts to extract")
        return False

    logger.info(f"Starting extraction for {len(unprocessed)} transcripts")

    # Initialize state
    transcript_states = [TranscriptState(id=t.session_id, status="pending") for t in unprocessed]

    initial_state = ExtractionState(
        status="running",
        started_at=datetime.now().isoformat(),
        pid=None,  # Will be set after spawn
        transcripts=transcript_states,
        last_update=datetime.now().isoformat(),
    )

    save_extraction_state(initial_state)

    # Spawn worker subprocess
    try:
        # Use current Python interpreter
        python_exe = sys.executable

        # Build command
        cmd = [
            python_exe,
            "-m",
            "amplifier.memory.extraction_worker",
            "--transcripts-dir",
            str(transcripts_dir),
        ]

        # Spawn subprocess (detached from parent)
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,  # Detach from parent
        )

        # Update state with PID
        state = load_extraction_state()
        if state:
            state.pid = process.pid
            save_extraction_state(state)

        logger.info(f"Extraction worker started (PID: {process.pid})")

        # Brief wait to ensure it started
        time.sleep(0.5)

        # Verify it's running
        if not _is_process_running(process.pid):
            raise RuntimeError("Worker process died immediately after start")

        return True

    except Exception as e:
        logger.error(f"Failed to start extraction worker: {e}", exc_info=True)
        raise RuntimeError(f"Failed to start extraction: {e}")


def stop_extraction() -> bool:
    """Stop running extraction process

    Gracefully terminates extraction worker if running.

    Returns:
        True if stopped, False if not running

    Raises:
        RuntimeError: If failed to stop process
    """
    logger = get_extraction_logger()

    status = get_extraction_status()

    if status.status != "running":
        logger.info("No extraction process running")
        return False

    if status.pid is None:
        logger.warning("Status says running but no PID found")
        return False

    logger.info(f"Stopping extraction process (PID: {status.pid})")

    try:
        # Try graceful termination
        os.kill(status.pid, 15)  # SIGTERM

        # Wait up to 5 seconds
        for _ in range(50):
            if not _is_process_running(status.pid):
                logger.info("Extraction process stopped gracefully")
                break
            time.sleep(0.1)
        else:
            # Force kill if still running
            logger.warning("Process didn't stop gracefully, forcing kill")
            os.kill(status.pid, 9)  # SIGKILL

        # Update state
        state = load_extraction_state()
        if state:
            state.status = "cancelled"
            state.pid = None
            save_extraction_state(state)

        return True

    except ProcessLookupError:
        # Process already dead
        logger.info("Process already stopped")
        return True

    except Exception as e:
        logger.error(f"Failed to stop extraction: {e}", exc_info=True)
        raise RuntimeError(f"Failed to stop extraction: {e}")


def cleanup_extraction_state() -> bool:
    """Clean up extraction state after completion

    Removes state file. Only call after extraction is complete or crashed.

    Returns:
        True if cleaned up, False if extraction still running

    Raises:
        RuntimeError: If cleanup fails
    """
    logger = get_extraction_logger()

    status = get_extraction_status()

    if status.status == "running":
        logger.warning("Cannot cleanup while extraction is running")
        return False

    logger.info("Cleaning up extraction state")

    try:
        clear_extraction_state()
        return True

    except Exception as e:
        logger.error(f"Failed to cleanup extraction state: {e}", exc_info=True)
        raise RuntimeError(f"Failed to cleanup: {e}")


def _is_process_running(pid: int) -> bool:
    """Check if process is running

    Args:
        pid: Process ID to check

    Returns:
        True if process is running, False otherwise
    """
    try:
        # Send signal 0 (no-op, just checks existence)
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        # Process doesn't exist
        return False
    except PermissionError:
        # Process exists but we can't signal it
        return True
    except Exception:
        # Unknown error, assume not running
        return False
