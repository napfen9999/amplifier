"""Tests for terminal progress UI"""

from amplifier.memory.terminal_ui import ProgressState
from amplifier.memory.terminal_ui import TerminalUI


def test_progress_state_creation():
    """Test ProgressState dataclass creation"""
    state = ProgressState(
        total_transcripts=5,
        completed_transcripts=2,
        current_session_id="test123",
        current_stage="extraction",
        stage_progress=0.75,
        memories_extracted=10,
    )

    assert state.total_transcripts == 5
    assert state.completed_transcripts == 2
    assert state.current_session_id == "test123"
    assert state.current_stage == "extraction"
    assert state.stage_progress == 0.75
    assert state.memories_extracted == 10


def test_progress_state_defaults():
    """Test ProgressState default values"""
    state = ProgressState(
        total_transcripts=3,
        completed_transcripts=1,
    )

    assert state.current_session_id is None
    assert state.current_stage is None
    assert state.stage_progress == 0.0
    assert state.memories_extracted == 0


def test_terminal_ui_initialization():
    """Test TerminalUI initialization"""
    ui = TerminalUI(total_transcripts=5)

    assert ui.total_transcripts == 5
    assert ui._cursor_hidden is False


def test_terminal_ui_context_manager():
    """Test TerminalUI as context manager"""
    ui = TerminalUI(total_transcripts=3)

    # Not yet entered
    assert ui._cursor_hidden is False

    # Enter context
    ui.__enter__()
    assert ui._cursor_hidden is True

    # Exit context
    ui.__exit__()
    assert ui._cursor_hidden is False


def test_terminal_ui_with_statement():
    """Test TerminalUI with 'with' statement"""
    with TerminalUI(total_transcripts=3) as ui:
        assert ui._cursor_hidden is True
        assert ui.total_transcripts == 3

    # After exiting, cursor should be shown again
    # (we can't directly check this, but _cursor_hidden should be reset)


def test_render_progress_bar_empty():
    """Test progress bar rendering at 0%"""
    ui = TerminalUI(total_transcripts=1)
    bar = ui._render_progress_bar(0.0, width=10)

    assert bar == "[░░░░░░░░░░]"


def test_render_progress_bar_full():
    """Test progress bar rendering at 100%"""
    ui = TerminalUI(total_transcripts=1)
    bar = ui._render_progress_bar(1.0, width=10)

    assert bar == "[██████████]"


def test_render_progress_bar_half():
    """Test progress bar rendering at 50%"""
    ui = TerminalUI(total_transcripts=1)
    bar = ui._render_progress_bar(0.5, width=10)

    assert bar == "[█████░░░░░]"


def test_render_progress_bar_custom_width():
    """Test progress bar with different widths"""
    ui = TerminalUI(total_transcripts=1)

    bar_20 = ui._render_progress_bar(0.5, width=20)
    assert len(bar_20) == 22  # 20 + 2 for brackets

    bar_30 = ui._render_progress_bar(0.5, width=30)
    assert len(bar_30) == 32  # 30 + 2 for brackets


def test_render_progress_bar_partial_progress():
    """Test progress bar at various partial values"""
    ui = TerminalUI(total_transcripts=1)

    # 25% of 20 = 5 filled
    bar_25 = ui._render_progress_bar(0.25, width=20)
    assert bar_25.count("█") == 5
    assert bar_25.count("░") == 15

    # 75% of 20 = 15 filled
    bar_75 = ui._render_progress_bar(0.75, width=20)
    assert bar_75.count("█") == 15
    assert bar_75.count("░") == 5


def test_update_clears_previous_output(capsys):
    """Test that update method clears previous output"""
    ui = TerminalUI(total_transcripts=3)

    state = ProgressState(
        total_transcripts=3,
        completed_transcripts=1,
        current_session_id="test123",
        current_stage="extraction",
        stage_progress=0.5,
    )

    # Call update (should write ANSI escape codes to clear)
    ui.update(state)

    # Capture output
    captured = capsys.readouterr()

    # Should contain ANSI escape codes for clearing
    assert "\033[2K" in captured.out  # Clear line
    assert "\033[1A" in captured.out  # Move up


def test_render_with_triage_stage(capsys):
    """Test rendering with triage stage"""
    ui = TerminalUI(total_transcripts=3)

    state = ProgressState(
        total_transcripts=3,
        completed_transcripts=1,
        current_session_id="test123",
        current_stage="triage",
        stage_progress=0.0,
    )

    ui._render(state)
    captured = capsys.readouterr()

    assert "📝 Memory Extraction" in captured.out
    assert "[TRIAGE]" in captured.out
    assert "Identifying important ranges" in captured.out


def test_render_with_extraction_stage(capsys):
    """Test rendering with extraction stage"""
    ui = TerminalUI(total_transcripts=3)

    state = ProgressState(
        total_transcripts=3,
        completed_transcripts=1,
        current_session_id="test123",
        current_stage="extraction",
        stage_progress=0.85,
    )

    ui._render(state)
    captured = capsys.readouterr()

    assert "[EXTRACTION]" in captured.out
    assert "Processing messages" in captured.out
    assert "85%" in captured.out


def test_render_with_storage_stage(capsys):
    """Test rendering with storage stage"""
    ui = TerminalUI(total_transcripts=3)

    state = ProgressState(
        total_transcripts=3,
        completed_transcripts=1,
        current_session_id="test123",
        current_stage="storage",
        memories_extracted=15,
    )

    ui._render(state)
    captured = capsys.readouterr()

    assert "[STORAGE]" in captured.out
    assert "Saving memories" in captured.out
    assert "15 memories" in captured.out


def test_render_transcript_progress(capsys):
    """Test transcript progress rendering"""
    ui = TerminalUI(total_transcripts=5)

    state = ProgressState(
        total_transcripts=5,
        completed_transcripts=3,
    )

    ui._render(state)
    captured = capsys.readouterr()

    assert "Transcripts:" in captured.out
    assert "3/5" in captured.out


def test_render_current_session_id(capsys):
    """Test current session ID display"""
    ui = TerminalUI(total_transcripts=3)

    state = ProgressState(
        total_transcripts=3,
        completed_transcripts=1,
        current_session_id="test123",
    )

    ui._render(state)
    captured = capsys.readouterr()

    assert "Current: Processing transcript test123..." in captured.out


def test_render_long_session_id_truncated(capsys):
    """Test that long session IDs are truncated"""
    ui = TerminalUI(total_transcripts=3)

    long_session_id = "very_long_session_id_that_should_be_truncated"
    state = ProgressState(
        total_transcripts=3,
        completed_transcripts=1,
        current_session_id=long_session_id,
    )

    ui._render(state)
    captured = capsys.readouterr()

    # Should be truncated with "..."
    assert "very_long_se..." in captured.out


def test_render_no_current_session(capsys):
    """Test rendering when no current session"""
    ui = TerminalUI(total_transcripts=3)

    state = ProgressState(
        total_transcripts=3,
        completed_transcripts=0,
        current_session_id=None,
    )

    ui._render(state)
    captured = capsys.readouterr()

    assert "Current: Idle" in captured.out


def test_show_summary(capsys):
    """Test completion summary display"""
    ui = TerminalUI(total_transcripts=3)

    ui.show_summary(transcripts=3, memories=42, time="2m 15s")
    captured = capsys.readouterr()

    assert "✅ Extraction Complete" in captured.out
    assert "Transcripts processed: 3" in captured.out
    assert "Memories extracted: 42" in captured.out
    assert "Time taken: 2m 15s" in captured.out


def test_triage_complete_indicator(capsys):
    """Test triage complete indicator"""
    ui = TerminalUI(total_transcripts=3)

    state = ProgressState(
        total_transcripts=3,
        completed_transcripts=1,
        current_session_id="test123",
        current_stage="triage",
        stage_progress=1.0,  # Complete
    )

    ui._render(state)
    captured = capsys.readouterr()

    assert "✓ Triage complete" in captured.out


def test_zero_transcripts_progress():
    """Test progress calculation with zero transcripts"""
    ui = TerminalUI(total_transcripts=0)

    state = ProgressState(
        total_transcripts=0,
        completed_transcripts=0,
    )

    # Should not crash with division by zero
    ui._render(state)


def test_progress_state_stages():
    """Test all valid stage values"""
    valid_stages = ["triage", "extraction", "storage", None]

    for stage in valid_stages:
        state = ProgressState(
            total_transcripts=3,
            completed_transcripts=1,
            current_stage=stage,
        )

        assert state.current_stage == stage
