"""Tests for extraction worker subprocess"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from amplifier.memory.extraction_worker import run_extraction_worker
from amplifier.memory.processor import ExtractionResult
from amplifier.memory.state_tracker import load_extraction_state
from amplifier.memory.transcript_tracker import add_transcript_record
from amplifier.memory.transcript_tracker import get_transcript_by_session


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


def test_run_extraction_worker_no_transcripts(temp_data_dir):
    """Test worker with no unprocessed transcripts"""
    data_dir, transcripts_dir = temp_data_dir

    # Run worker
    stats = run_extraction_worker(transcripts_dir)

    # Verify no work done
    assert stats["transcripts_processed"] == 0
    assert stats["memories_extracted"] == 0
    assert stats["errors"] == 0


def test_run_extraction_worker_single_transcript(temp_data_dir):
    """Test worker processing single transcript"""
    data_dir, transcripts_dir = temp_data_dir

    # Create a transcript file
    transcript_path = transcripts_dir / "session_test123.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')

    # Add to tracker
    add_transcript_record("test123", str(transcript_path))

    # Mock the processor
    with patch("amplifier.memory.extraction_worker.process_transcript") as mock_process:
        mock_process.return_value = ExtractionResult(session_id="test123", memories_extracted=5, success=True)

        # Mock time.sleep to speed up test
        with patch("amplifier.memory.extraction_worker.time.sleep"):
            # Run worker
            stats = run_extraction_worker(transcripts_dir)

    # Verify results
    assert stats["transcripts_processed"] == 1
    assert stats["memories_extracted"] == 5
    assert stats["errors"] == 0

    # Verify transcript marked as processed
    record = get_transcript_by_session("test123")
    assert record is not None
    assert record.processed is True
    assert record.memories_extracted == 5


def test_run_extraction_worker_multiple_transcripts(temp_data_dir):
    """Test worker processing multiple transcripts"""
    data_dir, transcripts_dir = temp_data_dir

    # Create multiple transcript files
    sessions = ["session1", "session2", "session3"]
    for session_id in sessions:
        transcript_path = transcripts_dir / f"session_{session_id}.jsonl"
        transcript_path.write_text('{"role": "user", "content": "test"}\n')
        add_transcript_record(session_id, str(transcript_path))

    # Mock the processor
    with patch("amplifier.memory.extraction_worker.process_transcript") as mock_process:
        # Return different memory counts for each
        mock_process.side_effect = [
            ExtractionResult(session_id="session1", memories_extracted=3, success=True),
            ExtractionResult(session_id="session2", memories_extracted=7, success=True),
            ExtractionResult(session_id="session3", memories_extracted=2, success=True),
        ]

        # Mock time.sleep
        with patch("amplifier.memory.extraction_worker.time.sleep"):
            # Run worker
            stats = run_extraction_worker(transcripts_dir)

    # Verify results
    assert stats["transcripts_processed"] == 3
    assert stats["memories_extracted"] == 12  # 3 + 7 + 2
    assert stats["errors"] == 0

    # Verify all transcripts marked as processed
    for session_id in sessions:
        record = get_transcript_by_session(session_id)
        assert record is not None
        assert record.processed is True


def test_run_extraction_worker_with_error(temp_data_dir):
    """Test worker handling processing error"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript file
    transcript_path = transcripts_dir / "session_error.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')
    add_transcript_record("error", str(transcript_path))

    # Mock processor to raise error
    with patch("amplifier.memory.extraction_worker.process_transcript") as mock_process:
        mock_process.side_effect = ValueError("Processing failed")

        # Mock time.sleep
        with patch("amplifier.memory.extraction_worker.time.sleep"):
            # Run worker
            stats = run_extraction_worker(transcripts_dir)

    # Verify error counted
    assert stats["transcripts_processed"] == 0
    assert stats["memories_extracted"] == 0
    assert stats["errors"] == 1

    # Verify transcript not marked as processed
    record = get_transcript_by_session("error")
    assert record is not None
    assert record.processed is False


def test_run_extraction_worker_continues_after_error(temp_data_dir):
    """Test worker continues processing after error"""
    data_dir, transcripts_dir = temp_data_dir

    # Create multiple transcript files
    for i in range(1, 4):
        transcript_path = transcripts_dir / f"session_test{i}.jsonl"
        transcript_path.write_text('{"role": "user", "content": "test"}\n')
        add_transcript_record(f"test{i}", str(transcript_path))

    # Mock processor: error on second, success on others
    with patch("amplifier.memory.extraction_worker.process_transcript") as mock_process:
        mock_process.side_effect = [
            ExtractionResult(session_id="test1", memories_extracted=3, success=True),
            ValueError("Processing failed"),  # Error on second
            ExtractionResult(session_id="test3", memories_extracted=2, success=True),
        ]

        # Mock time.sleep
        with patch("amplifier.memory.extraction_worker.time.sleep"):
            # Run worker
            stats = run_extraction_worker(transcripts_dir)

    # Verify results: 2 succeeded, 1 failed
    assert stats["transcripts_processed"] == 2
    assert stats["memories_extracted"] == 5  # 3 + 2
    assert stats["errors"] == 1

    # Verify only successful transcripts marked as processed
    test1 = get_transcript_by_session("test1")
    assert test1 is not None
    assert test1.processed is True

    test2 = get_transcript_by_session("test2")
    assert test2 is not None
    assert test2.processed is False

    test3 = get_transcript_by_session("test3")
    assert test3 is not None
    assert test3.processed is True


def test_run_extraction_worker_updates_state(temp_data_dir):
    """Test worker updates extraction state"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript
    transcript_path = transcripts_dir / "session_state.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')
    add_transcript_record("state", str(transcript_path))

    # Mock processor
    with patch("amplifier.memory.extraction_worker.process_transcript") as mock_process:
        mock_process.return_value = ExtractionResult(session_id="state", memories_extracted=5, success=True)

        # Mock time.sleep
        with patch("amplifier.memory.extraction_worker.time.sleep"):
            # Run worker
            run_extraction_worker(transcripts_dir)

    # Verify final state
    state = load_extraction_state()
    assert state is not None
    assert state.status == "completed"
    assert state.pid is None

    # Verify transcript state
    transcript_state = next(t for t in state.transcripts if t.id == "state")
    assert transcript_state.status == "completed"
    assert transcript_state.memories == 5


def test_run_extraction_worker_terminal_ui_integration(temp_data_dir):
    """Test worker integrates with terminal UI"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript
    transcript_path = transcripts_dir / "session_ui.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')
    add_transcript_record("ui", str(transcript_path))

    # Mock processor
    with patch("amplifier.memory.extraction_worker.process_transcript") as mock_process:
        mock_process.return_value = ExtractionResult(session_id="ui", memories_extracted=3, success=True)

        # Mock TerminalUI to track calls
        with patch("amplifier.memory.extraction_worker.TerminalUI") as mock_ui:
            mock_ui_instance = MagicMock()
            mock_ui.return_value.__enter__.return_value = mock_ui_instance

            # Mock time.sleep
            with patch("amplifier.memory.extraction_worker.time.sleep"):
                # Run worker
                run_extraction_worker(transcripts_dir)

    # Verify UI was used
    mock_ui.assert_called_once_with(total_transcripts=1)

    # Verify update() was called multiple times
    assert mock_ui_instance.update.call_count > 0

    # Verify show_summary() was called
    mock_ui_instance.show_summary.assert_called_once()


def test_run_extraction_worker_logging(temp_data_dir):
    """Test worker logs extraction activity"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript
    transcript_path = transcripts_dir / "session_log.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')
    add_transcript_record("log", str(transcript_path))

    # Mock processor
    with patch("amplifier.memory.extraction_worker.process_transcript") as mock_process:
        mock_process.return_value = ExtractionResult(session_id="log", memories_extracted=1, success=True)

        # Mock logger to capture calls
        with patch("amplifier.memory.extraction_worker.get_extraction_logger") as mock_logger:
            logger_instance = MagicMock()
            mock_logger.return_value = logger_instance

            # Mock time.sleep
            with patch("amplifier.memory.extraction_worker.time.sleep"):
                # Run worker
                run_extraction_worker(transcripts_dir)

    # Verify logging calls
    assert logger_instance.info.call_count > 0

    # Verify specific log messages
    log_calls = [call[0][0] for call in logger_instance.info.call_args_list]
    assert any("Starting extraction" in msg for msg in log_calls)
    assert any("Complete" in msg for msg in log_calls)


def test_run_extraction_worker_duration_tracking(temp_data_dir):
    """Test worker tracks duration accurately"""
    data_dir, transcripts_dir = temp_data_dir

    # Create transcript
    transcript_path = transcripts_dir / "session_time.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')
    add_transcript_record("time", str(transcript_path))

    # Mock processor
    with patch("amplifier.memory.extraction_worker.process_transcript") as mock_process:
        mock_process.return_value = ExtractionResult(session_id="time", memories_extracted=1, success=True)

        # Mock time.sleep (don't actually sleep)
        with patch("amplifier.memory.extraction_worker.time.sleep"):
            # Run worker
            stats = run_extraction_worker(transcripts_dir)

    # Verify duration is present and reasonable
    assert "duration_seconds" in stats
    assert stats["duration_seconds"] >= 0
    assert stats["duration_seconds"] < 5  # Should be fast with mocked sleep
