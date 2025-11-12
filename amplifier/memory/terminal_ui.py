"""ASCII-based terminal progress UI

Renders extraction progress using pure ASCII (no external dependencies).
Provides progress bars, stage indicators, and completion summaries.

Usage:
    with TerminalUI(total_transcripts=3) as ui:
        state = ProgressState(...)
        ui.update(state)
        ui.show_summary(3, 42, "2m 15s")
"""

import sys
from dataclasses import dataclass


@dataclass
class ProgressState:
    """Current progress state

    Attributes:
        total_transcripts: Total number of transcripts to process
        completed_transcripts: Number of transcripts completed
        current_session_id: Session ID currently being processed, None if none
        current_stage: Current stage ("triage", "extraction", "storage"), None if none
        stage_progress: Progress within current stage (0.0 to 1.0)
        memories_extracted: Total memories extracted so far
    """

    total_transcripts: int
    completed_transcripts: int
    current_session_id: str | None = None
    current_stage: str | None = None  # "triage" | "extraction" | "storage"
    stage_progress: float = 0.0  # 0.0 to 1.0
    memories_extracted: int = 0


class TerminalUI:
    """ASCII progress UI renderer

    Context manager for terminal UI with cursor management.
    """

    def __init__(self, total_transcripts: int):
        """Initialize terminal UI

        Args:
            total_transcripts: Total number of transcripts to process
        """
        self.total_transcripts = total_transcripts
        self._cursor_hidden = False

    def __enter__(self):
        """Setup terminal (hide cursor)"""
        # Hide cursor for cleaner UI
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
        self._cursor_hidden = True
        return self

    def __exit__(self, *args):
        """Cleanup terminal (show cursor)"""
        # Show cursor again
        if self._cursor_hidden:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()
            self._cursor_hidden = False

    def update(self, state: ProgressState) -> None:
        """Update progress display

        Clears previous output and renders current state.

        Args:
            state: Current progress state
        """
        # Clear previous output (move cursor up and clear lines)
        # We'll render about 8 lines, so clear that many
        sys.stdout.write("\033[2K")  # Clear current line
        for _ in range(7):
            sys.stdout.write("\033[1A\033[2K")  # Move up and clear

        # Render updated display
        self._render(state)
        sys.stdout.flush()

    def _render(self, state: ProgressState) -> None:
        """Render progress display

        Args:
            state: Current progress state
        """
        print()
        print("📝 Memory Extraction")
        print()

        # Transcripts progress bar
        transcript_progress = (
            state.completed_transcripts / state.total_transcripts if state.total_transcripts > 0 else 0
        )
        transcript_bar = self._render_progress_bar(transcript_progress, width=20)
        print(f"Transcripts: {transcript_bar} {state.completed_transcripts}/{state.total_transcripts}")

        # Current transcript
        if state.current_session_id:
            # Truncate session ID for display
            session_display = (
                state.current_session_id[:12] + "..."
                if len(state.current_session_id) > 15
                else state.current_session_id
            )
            print(f"Current: Processing transcript {session_display}...")
        else:
            print("Current: Idle")

        print()

        # Stage indicator
        if state.current_stage == "triage":
            print("[TRIAGE]     Identifying important ranges...")
            if state.stage_progress >= 1.0:
                print("             ✓ Triage complete")
        elif state.current_stage == "extraction":
            print("[EXTRACTION] Processing messages...")
            progress_bar = self._render_progress_bar(state.stage_progress, width=30)
            percentage = int(state.stage_progress * 100)
            print(f"             {progress_bar} {percentage}%")
        elif state.current_stage == "storage":
            print("[STORAGE]    Saving memories...")
            print(f"             ✓ Saved {state.memories_extracted} memories")
        else:
            print()

    def _render_progress_bar(self, progress: float, width: int = 20) -> str:
        """Render ASCII progress bar

        Args:
            progress: Progress (0.0 to 1.0)
            width: Width of progress bar in characters

        Returns:
            ASCII progress bar string like "[████░░░]"
        """
        filled = int(progress * width)
        empty = width - filled

        bar = "[" + ("█" * filled) + ("░" * empty) + "]"
        return bar

    def show_summary(self, transcripts: int, memories: int, time: str) -> None:
        """Show completion summary

        Args:
            transcripts: Number of transcripts processed
            memories: Total memories extracted
            time: Time taken (formatted string like "2m 15s")
        """
        # Clear current display
        sys.stdout.write("\033[2K")
        for _ in range(7):
            sys.stdout.write("\033[1A\033[2K")

        # Show summary
        print()
        print("✅ Extraction Complete")
        print()
        print(f"Transcripts processed: {transcripts}")
        print(f"Memories extracted: {memories}")
        print(f"Time taken: {time}")
        print()

        sys.stdout.flush()
