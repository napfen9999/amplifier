"""Tests for watchdog manager"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from amplifier.memory.state_tracker import ExtractionState
from amplifier.memory.state_tracker import TranscriptState
from amplifier.memory.state_tracker import save_extraction_state
from amplifier.memory.transcript_tracker import add_transcript_record
from amplifier.memory.watchdog import cleanup_extraction_state
from amplifier.memory.watchdog import get_extraction_status
from amplifier.memory.watchdog import start_extraction
from amplifier.memory.watchdog import stop_extraction


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


def test_get_extraction_status_idle(temp_data_dir):
    """Test status when no extraction has run"""
    data_dir, transcripts_dir = temp_data_dir

    status = get_extraction_status()

    assert status.status == "idle"
    assert status.pid is None
    assert status.started_at is None
    assert status.transcripts_total == 0


def test_get_extraction_status_running(temp_data_dir):
    """Test status when extraction is running"""
    data_dir, transcripts_dir = temp_data_dir

    # Create state with current process PID (we know it's running)
    current_pid = os.getpid()

    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=current_pid,
        transcripts=[
            TranscriptState(id="test1", status="completed", memories=5),
            TranscriptState(id="test2", status="in_progress"),
            TranscriptState(id="test3", status="pending"),
        ],
        last_update="2025-11-12T15:32:00",
    )

    save_extraction_state(state)

    status = get_extraction_status()

    assert status.status == "running"
    assert status.pid == current_pid
    assert status.started_at == "2025-11-12T15:30:00"
    assert status.transcripts_total == 3
    assert status.transcripts_completed == 1
    assert status.memories_extracted == 5


def test_get_extraction_status_completed(temp_data_dir):
    """Test status when extraction completed"""
    data_dir, transcripts_dir = temp_data_dir

    state = ExtractionState(
        status="completed",
        started_at="2025-11-12T15:30:00",
        pid=None,
        transcripts=[
            TranscriptState(id="test1", status="completed", memories=5),
            TranscriptState(id="test2", status="completed", memories=3),
        ],
        last_update="2025-11-12T15:35:00",
    )

    save_extraction_state(state)

    status = get_extraction_status()

    assert status.status == "completed"
    assert status.pid is None
    assert status.transcripts_total == 2
    assert status.transcripts_completed == 2
    assert status.memories_extracted == 8


def test_get_extraction_status_crashed(temp_data_dir):
    """Test status when process crashed"""
    data_dir, transcripts_dir = temp_data_dir

    # Create state with fake PID (process doesn't exist)
    fake_pid = 99999

    state = ExtractionState(
        status="running",  # Says running but process dead = crash
        started_at="2025-11-12T15:30:00",
        pid=fake_pid,
        transcripts=[
            TranscriptState(id="test1", status="completed", memories=5),
            TranscriptState(id="test2", status="in_progress"),
        ],
        last_update="2025-11-12T15:32:00",
    )

    save_extraction_state(state)

    status = get_extraction_status()

    assert status.status == "crashed"
    assert status.pid is None
    assert status.transcripts_total == 2
    assert status.transcripts_completed == 1


def test_start_extraction_no_transcripts(temp_data_dir):
    """Test starting extraction with no unprocessed transcripts"""
    data_dir, transcripts_dir = temp_data_dir

    # No transcripts added

    result = start_extraction(transcripts_dir)

    assert result is False


def test_start_extraction_already_running(temp_data_dir):
    """Test starting extraction when already running"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript
    transcript_path = transcripts_dir / "session_test.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')
    add_transcript_record("test", str(transcript_path))

    # Set state as running with current PID
    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=os.getpid(),
        transcripts=[TranscriptState(id="test", status="in_progress")],
        last_update="2025-11-12T15:30:00",
    )

    save_extraction_state(state)

    result = start_extraction(transcripts_dir)

    assert result is False


def test_start_extraction_success(temp_data_dir):
    """Test successfully starting extraction"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript
    transcript_path = transcripts_dir / "session_test.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')
    add_transcript_record("test", str(transcript_path))

    # Use current PID (guaranteed to be running)
    current_pid = os.getpid()

    # Mock subprocess.Popen to avoid actually spawning
    with patch("amplifier.memory.watchdog.subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = current_pid
        mock_popen.return_value = mock_process

        result = start_extraction(transcripts_dir)

    assert result is True

    # Verify state was saved with PID
    status = get_extraction_status()
    assert status.status == "running"
    assert status.pid == current_pid


def test_start_extraction_process_dies_immediately(temp_data_dir):
    """Test starting extraction when process dies immediately"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript
    transcript_path = transcripts_dir / "session_test.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')
    add_transcript_record("test", str(transcript_path))

    # Mock subprocess.Popen
    with (
        patch("amplifier.memory.watchdog.subprocess.Popen") as mock_popen,
        patch("amplifier.memory.watchdog._is_process_running", return_value=False),
        pytest.raises(RuntimeError, match="died immediately"),
    ):
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        start_extraction(transcripts_dir)


def test_stop_extraction_not_running(temp_data_dir):
    """Test stopping when no extraction running"""
    data_dir, transcripts_dir = temp_data_dir

    result = stop_extraction()

    assert result is False


def test_stop_extraction_success(temp_data_dir):
    """Test successfully stopping extraction"""
    data_dir, transcripts_dir = temp_data_dir

    # Create state with current PID (we can signal ourselves)
    current_pid = os.getpid()

    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=current_pid,
        transcripts=[TranscriptState(id="test", status="in_progress")],
        last_update="2025-11-12T15:30:00",
    )

    save_extraction_state(state)

    # Mock os.kill to avoid actually killing
    with (
        patch("amplifier.memory.watchdog.os.kill") as mock_kill,
        patch("amplifier.memory.watchdog._is_process_running") as mock_running,
    ):
        mock_running.side_effect = [True, False]  # First call: running, second: stopped
        result = stop_extraction()

    assert result is True

    # Verify kill was called with SIGTERM
    mock_kill.assert_called_with(current_pid, 15)


def test_cleanup_extraction_state_while_running(temp_data_dir):
    """Test cleanup fails when extraction is running"""
    data_dir, transcripts_dir = temp_data_dir

    # Create state with current PID
    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=os.getpid(),
        transcripts=[TranscriptState(id="test", status="in_progress")],
        last_update="2025-11-12T15:30:00",
    )

    save_extraction_state(state)

    result = cleanup_extraction_state()

    assert result is False


def test_cleanup_extraction_state_success(temp_data_dir):
    """Test successful cleanup after completion"""
    data_dir, transcripts_dir = temp_data_dir

    # Create completed state
    state = ExtractionState(
        status="completed",
        started_at="2025-11-12T15:30:00",
        pid=None,
        transcripts=[TranscriptState(id="test", status="completed", memories=5)],
        last_update="2025-11-12T15:35:00",
    )

    save_extraction_state(state)

    result = cleanup_extraction_state()

    assert result is True

    # Verify state is gone
    status = get_extraction_status()
    assert status.status == "idle"


def test_is_process_running():
    """Test process running check"""
    from amplifier.memory.watchdog import _is_process_running

    # Current process should be running
    assert _is_process_running(os.getpid()) is True

    # Fake PID should not be running
    assert _is_process_running(99999) is False


def test_extraction_lifecycle(temp_data_dir):
    """Test complete extraction lifecycle"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript
    transcript_path = transcripts_dir / "session_test.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')
    add_transcript_record("test", str(transcript_path))

    # Start: idle
    status = get_extraction_status()
    assert status.status == "idle"

    # Mock subprocess and process checks
    with patch("amplifier.memory.watchdog.subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        with patch("amplifier.memory.watchdog._is_process_running", return_value=True):
            # Start extraction
            result = start_extraction(transcripts_dir)
            assert result is True

            # Check: running
            status = get_extraction_status()
            assert status.status == "running"
            assert status.pid == 12345

    # Simulate completion (set process as stopped)
    with patch("amplifier.memory.watchdog._is_process_running", return_value=False):
        state = ExtractionState(
            status="completed",
            started_at="2025-11-12T15:30:00",
            pid=None,
            transcripts=[TranscriptState(id="test", status="completed", memories=5)],
            last_update="2025-11-12T15:35:00",
        )

        save_extraction_state(state)

        # Check: completed
        status = get_extraction_status()
        assert status.status == "completed"

        # Cleanup
        result = cleanup_extraction_state()
        assert result is True

        # Check: idle again
        status = get_extraction_status()
        assert status.status == "idle"
