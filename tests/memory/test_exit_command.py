"""Tests for exit command"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from amplifier.memory.commands.exit_command import get_exit_command_status
from amplifier.memory.commands.exit_command import handle_exit
from amplifier.memory.state_tracker import ExtractionState
from amplifier.memory.state_tracker import TranscriptState
from amplifier.memory.state_tracker import save_extraction_state
from amplifier.memory.transcript_tracker import get_transcript_by_session
from amplifier.memory.watchdog import ExtractionStatus


@pytest.fixture
def temp_data_dir(monkeypatch):
    """Create temporary data directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        transcripts_dir = data_dir / "transcripts"
        transcripts_dir.mkdir()

        # Patch module paths
        import amplifier.memory.state_tracker as state_module
        import amplifier.memory.transcript_tracker as tracker_module

        state_file = data_dir / ".extraction_state.json"
        tracker_file = data_dir / "transcripts.json"

        monkeypatch.setattr(state_module, "STATE_FILE", state_file)
        monkeypatch.setattr(tracker_module, "TRANSCRIPTS_FILE", tracker_file)

        yield data_dir, transcripts_dir


def test_handle_exit_transcript_not_found(temp_data_dir):
    """Test exit when transcript file doesn't exist"""
    data_dir, transcripts_dir = temp_data_dir

    # Non-existent transcript
    transcript_path = transcripts_dir / "session_nonexistent.jsonl"

    result = handle_exit("nonexistent", transcript_path)

    assert result["success"] is False
    assert "not found" in result["message"]
    assert result["extraction_started"] is False


def test_handle_exit_first_session(temp_data_dir):
    """Test exit with first session (starts extraction)"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript
    transcript_path = transcripts_dir / "session_first.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')

    # Mock start_extraction
    with patch("amplifier.memory.commands.exit_command.start_extraction") as mock_start:
        mock_start.return_value = True

        result = handle_exit("first", transcript_path)

    assert result["success"] is True
    assert result["extraction_started"] is True
    assert "started" in result["message"]

    # Verify transcript registered
    record = get_transcript_by_session("first")
    assert record is not None
    assert record.session_id == "first"
    assert record.processed is False


def test_handle_exit_extraction_already_running(temp_data_dir):
    """Test exit when extraction already running"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript
    transcript_path = transcripts_dir / "session_second.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')

    # Mock extraction as running
    with patch("amplifier.memory.commands.exit_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="running",
            pid=12345,
            started_at="2025-11-12T15:30:00",
            transcripts_total=2,
            transcripts_completed=1,
            memories_extracted=5,
        )

        result = handle_exit("second", transcript_path)

    assert result["success"] is True
    assert result["extraction_started"] is False
    assert "already in progress" in result["message"]

    # Verify transcript still registered
    record = get_transcript_by_session("second")
    assert record is not None


def test_handle_exit_start_extraction_fails(temp_data_dir):
    """Test exit when start_extraction raises error"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript
    transcript_path = transcripts_dir / "session_fail.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')

    # Mock start_extraction to raise error
    with patch("amplifier.memory.commands.exit_command.start_extraction") as mock_start:
        mock_start.side_effect = RuntimeError("Worker failed to start")

        result = handle_exit("fail", transcript_path)

    assert result["success"] is False
    assert "failed to start extraction" in result["message"]
    assert result["extraction_started"] is False

    # Verify transcript was registered anyway
    record = get_transcript_by_session("fail")
    assert record is not None


def test_handle_exit_register_transcript_fails(temp_data_dir):
    """Test exit when transcript registration fails"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript
    transcript_path = transcripts_dir / "session_reg_fail.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')

    # Mock add_transcript_record to raise error
    with patch("amplifier.memory.commands.exit_command.add_transcript_record") as mock_add:
        mock_add.side_effect = ValueError("Registration failed")

        result = handle_exit("reg_fail", transcript_path)

    assert result["success"] is False
    assert "Failed to register" in result["message"]
    assert result["extraction_started"] is False


def test_get_exit_command_status_idle(temp_data_dir):
    """Test status when idle"""
    data_dir, transcripts_dir = temp_data_dir

    status = get_exit_command_status()

    assert status["status"] == "idle"
    assert "No extraction" in status["message"]
    assert "transcripts_total" not in status


def test_get_exit_command_status_running(temp_data_dir):
    """Test status when running"""
    data_dir, transcripts_dir = temp_data_dir

    # Create running state
    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=12345,
        transcripts=[
            TranscriptState(id="test1", status="completed", memories=5),
            TranscriptState(id="test2", status="in_progress"),
            TranscriptState(id="test3", status="pending"),
        ],
        last_update="2025-11-12T15:32:00",
    )

    save_extraction_state(state)

    # Mock process as running
    with patch("amplifier.memory.commands.exit_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="running",
            pid=12345,
            started_at="2025-11-12T15:30:00",
            transcripts_total=3,
            transcripts_completed=1,
            memories_extracted=5,
        )

        status = get_exit_command_status()

    assert status["status"] == "running"
    assert "in progress" in status["message"]
    assert status["transcripts_total"] == 3
    assert status["transcripts_completed"] == 1
    assert status["memories_extracted"] == 5


def test_get_exit_command_status_completed(temp_data_dir):
    """Test status when completed"""
    data_dir, transcripts_dir = temp_data_dir

    # Mock completed status
    with patch("amplifier.memory.commands.exit_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="completed",
            pid=None,
            started_at="2025-11-12T15:30:00",
            transcripts_total=3,
            transcripts_completed=3,
            memories_extracted=15,
        )

        status = get_exit_command_status()

    assert status["status"] == "completed"
    assert "complete" in status["message"]
    assert status["transcripts_completed"] == 3
    assert status["memories_extracted"] == 15


def test_get_exit_command_status_failed(temp_data_dir):
    """Test status when failed"""
    data_dir, transcripts_dir = temp_data_dir

    # Mock failed status
    with patch("amplifier.memory.commands.exit_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="failed",
            pid=None,
            started_at="2025-11-12T15:30:00",
            transcripts_total=3,
            transcripts_completed=2,
            memories_extracted=10,
        )

        status = get_exit_command_status()

    assert status["status"] == "failed"
    assert "failed" in status["message"]
    assert status["transcripts_completed"] == 2
    assert status["transcripts_total"] == 3


def test_get_exit_command_status_crashed(temp_data_dir):
    """Test status when crashed"""
    data_dir, transcripts_dir = temp_data_dir

    # Mock crashed status
    with patch("amplifier.memory.commands.exit_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="crashed",
            pid=None,
            started_at="2025-11-12T15:30:00",
            transcripts_total=3,
            transcripts_completed=1,
            memories_extracted=5,
        )

        status = get_exit_command_status()

    assert status["status"] == "crashed"
    assert "crashed" in status["message"]
    assert status["transcripts_completed"] == 1


def test_handle_exit_multiple_sessions_sequence(temp_data_dir):
    """Test handling multiple session exits in sequence"""
    data_dir, transcripts_dir = temp_data_dir

    # Create multiple transcripts
    for i in range(1, 4):
        transcript_path = transcripts_dir / f"session_multi{i}.jsonl"
        transcript_path.write_text('{"role": "user", "content": "test"}\n')

    # Mock extraction status progression
    call_count = [0]

    def mock_status_progression():
        call_count[0] += 1
        if call_count[0] == 1:
            # First call: idle
            return ExtractionStatus(status="idle")
        # Subsequent calls: running
        return ExtractionStatus(
            status="running",
            pid=12345,
            started_at="2025-11-12T15:30:00",
            transcripts_total=3,
            transcripts_completed=0,
            memories_extracted=0,
        )

    with (
        patch("amplifier.memory.commands.exit_command.get_extraction_status", side_effect=mock_status_progression),
        patch("amplifier.memory.commands.exit_command.start_extraction", return_value=True),
    ):
        # First session: starts extraction
        result1 = handle_exit("multi1", transcripts_dir / "session_multi1.jsonl")
        assert result1["extraction_started"] is True

        # Subsequent sessions: extraction already running
        result2 = handle_exit("multi2", transcripts_dir / "session_multi2.jsonl")
        assert result2["extraction_started"] is False

        result3 = handle_exit("multi3", transcripts_dir / "session_multi3.jsonl")
        assert result3["extraction_started"] is False

    # Verify all registered
    assert get_transcript_by_session("multi1") is not None
    assert get_transcript_by_session("multi2") is not None
    assert get_transcript_by_session("multi3") is not None
