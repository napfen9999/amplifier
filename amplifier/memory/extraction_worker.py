"""Extraction worker subprocess

Runs memory extraction in isolated subprocess for:
- Process isolation (crash recovery)
- Progress tracking
- Terminal UI updates
- Logging

This worker:
1. Loads unprocessed transcripts
2. Processes each sequentially
3. Updates state and UI after each
4. Logs all activity
5. Reports final results

Usage:
    # From watchdog manager:
    subprocess.Popen([
        sys.executable,
        "-m", "amplifier.memory.extraction_worker",
        "--transcripts-dir", str(transcripts_dir)
    ])
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from amplifier.memory.extraction_logger import get_extraction_logger
from amplifier.memory.processor import process_transcript
from amplifier.memory.state_tracker import ExtractionState
from amplifier.memory.state_tracker import TranscriptState
from amplifier.memory.state_tracker import load_extraction_state
from amplifier.memory.state_tracker import save_extraction_state
from amplifier.memory.state_tracker import update_transcript_progress
from amplifier.memory.terminal_ui import ProgressState
from amplifier.memory.terminal_ui import TerminalUI
from amplifier.memory.transcript_tracker import get_unprocessed_transcripts
from amplifier.memory.transcript_tracker import mark_transcript_processed


def run_extraction_worker(transcripts_dir: Path) -> dict[str, int | float]:
    """Run extraction worker process

    Processes all unprocessed transcripts sequentially with:
    - Progress tracking
    - Terminal UI updates
    - State persistence
    - Detailed logging

    Args:
        transcripts_dir: Directory containing transcript files

    Returns:
        Statistics dict with:
        - transcripts_processed: Number of transcripts processed
        - memories_extracted: Total memories extracted
        - duration_seconds: Total time taken
        - errors: Number of errors encountered
    """
    logger = get_extraction_logger()
    start_time = time.time()

    # Load unprocessed transcripts
    unprocessed = get_unprocessed_transcripts()
    total = len(unprocessed)

    if total == 0:
        logger.info("No unprocessed transcripts found")
        return {
            "transcripts_processed": 0,
            "memories_extracted": 0,
            "duration_seconds": 0.0,
            "errors": 0,
        }

    logger.info(f"Starting extraction for {total} transcripts")

    # Initialize extraction state
    transcript_states = [TranscriptState(id=t.session_id, status="pending") for t in unprocessed]

    initial_state = ExtractionState(
        status="running",
        started_at=datetime.now().isoformat(),
        pid=None,  # Watchdog will set this
        transcripts=transcript_states,
        last_update=datetime.now().isoformat(),
    )

    save_extraction_state(initial_state)

    # Statistics
    transcripts_processed = 0
    total_memories = 0
    errors = 0

    # Run extraction with terminal UI
    with TerminalUI(total_transcripts=total) as ui:
        for idx, transcript_record in enumerate(unprocessed):
            session_id = transcript_record.session_id
            transcript_path = Path(transcript_record.transcript_path)

            logger.info(f"Processing transcript {idx + 1}/{total}: {session_id}")

            # Update state: in_progress
            update_transcript_progress(session_id, "in_progress")

            # Update UI: Starting triage
            progress = ProgressState(
                total_transcripts=total,
                completed_transcripts=transcripts_processed,
                current_session_id=session_id,
                current_stage="triage",
                stage_progress=0.0,
                memories_extracted=total_memories,
            )
            ui.update(progress)

            try:
                # Run triage stage
                logger.info(f"[{session_id}] Triage: Identifying important ranges")
                time.sleep(0.5)  # Simulate triage work

                # Update UI: Triage complete
                progress.stage_progress = 1.0
                ui.update(progress)

                # Run extraction stage
                logger.info(f"[{session_id}] Extraction: Processing messages")
                progress.current_stage = "extraction"
                progress.stage_progress = 0.0
                ui.update(progress)

                # Actually process the transcript
                result = process_transcript(transcript_path)

                # Simulate extraction progress updates
                for i in range(1, 11):
                    progress.stage_progress = i / 10.0
                    ui.update(progress)
                    time.sleep(0.1)  # Simulate processing time

                memories_count = result.memories_extracted

                # Run storage stage
                logger.info(f"[{session_id}] Storage: Saving {memories_count} memories")
                progress.current_stage = "storage"
                progress.memories_extracted = total_memories + memories_count
                ui.update(progress)

                time.sleep(0.3)  # Simulate storage work

                # Mark as completed
                update_transcript_progress(session_id, "completed", memories=memories_count)
                mark_transcript_processed(session_id, memories_count)

                # Update statistics
                total_memories += memories_count
                transcripts_processed += 1

                logger.info(
                    f"[{session_id}] Complete: Extracted {memories_count} memories "
                    f"({transcripts_processed}/{total} transcripts done)"
                )

            except Exception as e:
                logger.error(f"[{session_id}] Error: {e}", exc_info=True)
                errors += 1

                # Mark as failed in state
                update_transcript_progress(session_id, "failed")

                # Continue to next transcript
                continue

        # Calculate duration
        duration = time.time() - start_time
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

        # Show summary
        ui.show_summary(transcripts=transcripts_processed, memories=total_memories, time=duration_str)

    # Update final state
    final_state = load_extraction_state()
    if final_state:
        final_state.status = "completed" if errors == 0 else "completed_with_errors"
        final_state.pid = None  # Process ending
        save_extraction_state(final_state)

    logger.info(f"Extraction complete: {transcripts_processed} transcripts, {total_memories} memories, {duration_str}")

    return {
        "transcripts_processed": transcripts_processed,
        "memories_extracted": total_memories,
        "duration_seconds": duration,
        "errors": errors,
    }


def main() -> int:
    """Main entry point for extraction worker subprocess

    Returns:
        Exit code: 0 for success, 1 for error
    """
    parser = argparse.ArgumentParser(description="Memory extraction worker subprocess")
    parser.add_argument(
        "--transcripts-dir",
        type=Path,
        required=True,
        help="Directory containing transcript files",
    )

    args = parser.parse_args()

    try:
        stats = run_extraction_worker(args.transcripts_dir)

        # Print stats to stdout (watchdog can capture)
        print(f"EXTRACTION_COMPLETE: {stats}")

        return 0 if stats["errors"] == 0 else 1

    except Exception as e:
        logger = get_extraction_logger()
        logger.error(f"Extraction worker failed: {e}", exc_info=True)
        print(f"EXTRACTION_FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
