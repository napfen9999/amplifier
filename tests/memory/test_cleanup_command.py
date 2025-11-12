"""Tests for cleanup command"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from amplifier.memory.commands.cleanup_command import cleanup_extraction
from amplifier.memory.commands.cleanup_command import get_cleanup_recommendations
from amplifier.memory.state_tracker import ExtractionState
from amplifier.memory.state_tracker import TranscriptState
from amplifier.memory.state_tracker import save_extraction_state
from amplifier.memory.watchdog import ExtractionStatus


@pytest.fixture
def temp_data_dir(monkeypatch):
    """Create temporary data directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)

        # Patch module paths
        import amplifier.memory.state_tracker as state_module

        state_file = data_dir / ".extraction_state.json"
        monkeypatch.setattr(state_module, "STATE_FILE", state_file)

        yield data_dir


def test_cleanup_extraction_no_state(temp_data_dir):
    """Test cleanup when no state exists"""
    result = cleanup_extraction()

    assert result["success"] is True
    assert result["stopped"] is False


def test_cleanup_extraction_completed(temp_data_dir):
    """Test cleanup after successful completion"""
    # Create completed state
    state = ExtractionState(
        status="completed",
        started_at="2025-11-12T15:30:00",
        pid=None,
        transcripts=[TranscriptState(id="test", status="completed", memories=5)],
        last_update="2025-11-12T15:35:00",
    )

    save_extraction_state(state)

    # Cleanup should succeed
    result = cleanup_extraction()

    assert result["success"] is True
    assert result["stopped"] is False
    assert "cleaned up" in result["message"]


def test_cleanup_extraction_running_without_force(temp_data_dir):
    """Test cleanup refuses when extraction running"""
    # Mock running extraction
    with patch("amplifier.memory.commands.cleanup_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="running",
            pid=12345,
            started_at="2025-11-12T15:30:00",
            transcripts_total=3,
            transcripts_completed=1,
            memories_extracted=5,
        )

        result = cleanup_extraction(force=False)

    assert result["success"] is False
    assert "running" in result["message"]
    assert result["stopped"] is False


def test_cleanup_extraction_running_with_force(temp_data_dir):
    """Test cleanup stops extraction when forced"""
    # Create running state
    current_pid = os.getpid()

    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=current_pid,
        transcripts=[TranscriptState(id="test", status="in_progress")],
        last_update="2025-11-12T15:30:00",
    )

    save_extraction_state(state)

    # Mock stop_extraction and cleanup_extraction_state
    with (
        patch("amplifier.memory.commands.cleanup_command.stop_extraction") as mock_stop,
        patch("amplifier.memory.commands.cleanup_command.cleanup_extraction_state") as mock_cleanup,
    ):
        mock_stop.return_value = True
        mock_cleanup.return_value = True

        result = cleanup_extraction(force=True)

    assert result["success"] is True
    assert result["stopped"] is True
    assert "stopped" in result["message"]

    # Verify stop was called
    mock_stop.assert_called_once()
    mock_cleanup.assert_called_once()


def test_cleanup_extraction_force_stop_fails(temp_data_dir):
    """Test cleanup fails when stop fails"""
    # Mock running extraction
    with patch("amplifier.memory.commands.cleanup_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="running",
            pid=12345,
            started_at="2025-11-12T15:30:00",
            transcripts_total=1,
            transcripts_completed=0,
            memories_extracted=0,
        )

        # Mock stop to fail
        with patch("amplifier.memory.commands.cleanup_command.stop_extraction") as mock_stop:
            mock_stop.return_value = False

            result = cleanup_extraction(force=True)

    assert result["success"] is False
    assert "Failed to stop" in result["message"]
    assert result["stopped"] is False


def test_cleanup_extraction_stop_raises_error(temp_data_dir):
    """Test cleanup handles stop errors"""
    # Mock running extraction
    with patch("amplifier.memory.commands.cleanup_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="running",
            pid=12345,
            started_at="2025-11-12T15:30:00",
            transcripts_total=1,
            transcripts_completed=0,
            memories_extracted=0,
        )

        # Mock stop to raise error
        with patch("amplifier.memory.commands.cleanup_command.stop_extraction") as mock_stop:
            mock_stop.side_effect = RuntimeError("Stop failed")

            result = cleanup_extraction(force=True)

    assert result["success"] is False
    assert "Error stopping" in result["message"]
    assert result["stopped"] is False


def test_get_cleanup_recommendations_idle(temp_data_dir):
    """Test recommendations when idle"""
    rec = get_cleanup_recommendations()

    assert rec["should_cleanup"] is False
    assert "No extraction state" in rec["reason"]
    assert len(rec["actions"]) == 0


def test_get_cleanup_recommendations_running(temp_data_dir):
    """Test recommendations when running"""
    # Mock running extraction
    with patch("amplifier.memory.commands.cleanup_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="running",
            pid=12345,
            started_at="2025-11-12T15:30:00",
            transcripts_total=3,
            transcripts_completed=1,
            memories_extracted=5,
        )

        rec = get_cleanup_recommendations()

    assert rec["should_cleanup"] is False
    assert "running" in rec["reason"]
    assert "Wait for extraction" in rec["actions"][0]


def test_get_cleanup_recommendations_completed(temp_data_dir):
    """Test recommendations when completed"""
    # Mock completed extraction
    with patch("amplifier.memory.commands.cleanup_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="completed",
            pid=None,
            started_at="2025-11-12T15:30:00",
            transcripts_total=3,
            transcripts_completed=3,
            memories_extracted=15,
        )

        rec = get_cleanup_recommendations()

    assert rec["should_cleanup"] is True
    assert "completed successfully" in rec["reason"]
    assert "cleanup_extraction()" in rec["actions"][0]


def test_get_cleanup_recommendations_failed(temp_data_dir):
    """Test recommendations when failed"""
    # Mock failed extraction
    with patch("amplifier.memory.commands.cleanup_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="failed",
            pid=None,
            started_at="2025-11-12T15:30:00",
            transcripts_total=3,
            transcripts_completed=2,
            memories_extracted=10,
        )

        rec = get_cleanup_recommendations()

    assert rec["should_cleanup"] is True
    assert "with errors" in rec["reason"]
    assert "Review logs" in rec["actions"][0]


def test_get_cleanup_recommendations_crashed(temp_data_dir):
    """Test recommendations when crashed"""
    # Mock crashed extraction
    with patch("amplifier.memory.commands.cleanup_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="crashed",
            pid=None,
            started_at="2025-11-12T15:30:00",
            transcripts_total=3,
            transcripts_completed=1,
            memories_extracted=5,
        )

        rec = get_cleanup_recommendations()

    assert rec["should_cleanup"] is True
    assert "crashed" in rec["reason"]
    assert "Review logs" in rec["actions"][0]
    assert "Investigate crash" in rec["actions"][2]


def test_cleanup_lifecycle(temp_data_dir):
    """Test complete cleanup lifecycle"""
    # Start with completed state
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

    # Get recommendations
    rec = get_cleanup_recommendations()
    assert rec["should_cleanup"] is True

    # Cleanup
    result = cleanup_extraction()
    assert result["success"] is True

    # Verify state gone
    rec = get_cleanup_recommendations()
    assert rec["should_cleanup"] is False
    assert "No extraction state" in rec["reason"]


def test_cleanup_with_crashed_state(temp_data_dir):
    """Test cleanup after crash"""
    # Create crashed state (process dead, status says running)
    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=99999,  # Fake PID
        transcripts=[
            TranscriptState(id="test", status="in_progress"),
        ],
        last_update="2025-11-12T15:32:00",
    )

    save_extraction_state(state)

    # Mock status as crashed
    with patch("amplifier.memory.commands.cleanup_command.get_extraction_status") as mock_status:
        mock_status.return_value = ExtractionStatus(
            status="crashed",
            pid=None,
            started_at="2025-11-12T15:30:00",
            transcripts_total=1,
            transcripts_completed=0,
            memories_extracted=0,
        )

        # Cleanup should succeed without force
        result = cleanup_extraction(force=False)

    assert result["success"] is True
    assert result["stopped"] is False
