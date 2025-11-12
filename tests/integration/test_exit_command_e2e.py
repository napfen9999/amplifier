"""End-to-end integration tests for exit-command memory extraction system

Tests the complete flow from session end through extraction to storage.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from amplifier.memory.commands.exit_command import handle_exit
from amplifier.memory.transcript_tracker import add_transcript_record
from amplifier.memory.transcript_tracker import get_transcript_by_session


@pytest.fixture
def temp_transcripts_dir(monkeypatch):
    """Create temporary transcripts directory with isolated state"""
    import tempfile as tmp

    with tmp.TemporaryDirectory() as tmpdir:
        transcripts_dir = Path(tmpdir)

        # Create isolated data directory for this test
        data_dir = Path(tmpdir) / ".data"
        data_dir.mkdir()

        # Patch the transcript tracker to use test directory
        import amplifier.memory.transcript_tracker as tracker_module

        tracker_file = data_dir / "transcripts.json"
        monkeypatch.setattr(tracker_module, "TRANSCRIPTS_FILE", tracker_file)

        # Patch state tracker to use test directory
        import amplifier.memory.state_tracker as state_module

        state_file = data_dir / ".extraction_state.json"
        monkeypatch.setattr(state_module, "STATE_FILE", state_file)

        yield transcripts_dir


@pytest.fixture
def sample_transcript(temp_transcripts_dir):
    """Create a sample transcript file"""
    session_id = "e2e_test"
    transcript_path = temp_transcripts_dir / f"session_{session_id}.jsonl"

    messages = [
        {"role": "user", "content": "I prefer Python for backend work"},
        {"role": "assistant", "content": "I'll remember your Python preference"},
        {"role": "user", "content": "We decided to use PostgreSQL"},
        {"role": "assistant", "content": "PostgreSQL decision noted"},
    ]

    with open(transcript_path, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    return session_id, transcript_path


def test_e2e_session_end_to_extraction(temp_transcripts_dir, sample_transcript):
    """End-to-end: SessionEnd → register → extraction start"""
    session_id, transcript_path = sample_transcript

    # Mock the extractor and watchdog
    with (
        patch("amplifier.memory.commands.exit_command.start_extraction") as mock_start,
        patch("amplifier.memory.commands.exit_command.get_extraction_status") as mock_status,
    ):
        # Mock no extraction running
        mock_status.return_value.status = "idle"
        mock_start.return_value = True

        # Call exit command (as SessionEnd hook would)
        result = handle_exit(session_id, transcript_path)

        # Verify success
        assert result["success"] is True
        assert result["extraction_started"] is True

        # Verify transcript was registered
        record = get_transcript_by_session(session_id)
        assert record is not None
        assert record.session_id == session_id
        assert Path(record.transcript_path) == transcript_path

        # Verify extraction was started
        mock_start.assert_called_once()


def test_e2e_multiple_sessions_queued(temp_transcripts_dir):
    """End-to-end: Multiple sessions → all registered → extraction processes sequentially"""
    # Create multiple transcripts
    session_ids = ["e2e_multi1", "e2e_multi2", "e2e_multi3"]
    transcript_paths = []

    for session_id in session_ids:
        transcript_path = temp_transcripts_dir / f"session_{session_id}.jsonl"
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"role": "user", "content": "test"}) + "\n")
        transcript_paths.append(transcript_path)

    with (
        patch("amplifier.memory.commands.exit_command.start_extraction") as mock_start,
        patch("amplifier.memory.commands.exit_command.get_extraction_status") as mock_status,
    ):
        # First session starts extraction
        mock_status.return_value.status = "idle"
        mock_start.return_value = True

        result1 = handle_exit(session_ids[0], transcript_paths[0])
        assert result1["extraction_started"] is True

        # Subsequent sessions see extraction running
        mock_status.return_value.status = "running"

        result2 = handle_exit(session_ids[1], transcript_paths[1])
        assert result2["success"] is True
        assert result2["extraction_started"] is False

        result3 = handle_exit(session_ids[2], transcript_paths[2])
        assert result3["success"] is True
        assert result3["extraction_started"] is False

        # All sessions registered
        for session_id in session_ids:
            record = get_transcript_by_session(session_id)
            assert record is not None


def test_e2e_extraction_worker_processes_transcripts(temp_transcripts_dir, sample_transcript):
    """End-to-end: Worker processes registered transcripts"""
    session_id, transcript_path = sample_transcript

    # Register transcript
    add_transcript_record(session_id, str(transcript_path))

    # Mock the processor
    with patch("amplifier.memory.extraction_worker.process_transcript") as mock_process:
        from amplifier.memory.processor import ExtractionResult

        mock_process.return_value = ExtractionResult(
            session_id=session_id,
            memories_extracted=2,
            success=True,
            error=None,
        )

        # Import after mocking to use the mock
        from amplifier.memory.extraction_worker import run_extraction_worker

        # Run worker
        stats = run_extraction_worker(temp_transcripts_dir)

        # Verify processing
        assert stats["transcripts_processed"] >= 1
        assert stats["memories_extracted"] >= 2

        # Verify transcript marked as processed
        record = get_transcript_by_session(session_id)
        assert record.processed is True


def test_e2e_extraction_with_errors_continues(temp_transcripts_dir):
    """End-to-end: Extraction continues after individual transcript errors"""
    # Create multiple transcripts
    session_ids = ["e2e_err1", "e2e_err2", "e2e_err3"]

    for session_id in session_ids:
        transcript_path = temp_transcripts_dir / f"session_{session_id}.jsonl"
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"role": "user", "content": "test"}) + "\n")
        add_transcript_record(session_id, str(transcript_path))

    # Mock processor to fail on second transcript
    with patch("amplifier.memory.extraction_worker.process_transcript") as mock_process:
        from amplifier.memory.processor import ExtractionResult

        def side_effect(path):
            session = path.stem.replace("session_", "")
            if session == "e2e_err2":
                return ExtractionResult(
                    session_id=session,
                    memories_extracted=0,
                    success=False,
                    error="Extraction failed",
                )
            return ExtractionResult(
                session_id=session,
                memories_extracted=1,
                success=True,
                error=None,
            )

        mock_process.side_effect = side_effect

        from amplifier.memory.extraction_worker import run_extraction_worker

        # Run worker
        stats = run_extraction_worker(temp_transcripts_dir)

        # Verify all transcripts were attempted
        assert stats["transcripts_processed"] == 3

        # Verify successful extractions recorded
        assert stats["memories_extracted"] >= 2  # err1 and err3


def test_e2e_hook_integration_with_exit_command(temp_transcripts_dir, sample_transcript):
    """End-to-end: SessionEnd hook → exit command → extraction"""
    from amplifier.memory.hooks.session_end import handle_session_end

    session_id, transcript_path = sample_transcript

    with (
        patch("amplifier.memory.hooks.session_end.handle_exit") as mock_exit,
    ):
        mock_exit.return_value = {
            "success": True,
            "message": "Extraction started",
            "extraction_started": True,
        }

        # Call hook (as Claude Code would)
        result = handle_session_end(session_id, transcript_path)

        # Verify hook called exit command
        mock_exit.assert_called_once_with(session_id, transcript_path)

        # Verify result propagated
        assert result["success"] is True
        assert result["extraction_started"] is True


def test_e2e_complete_flow_with_mocked_extraction(temp_transcripts_dir, sample_transcript):
    """Complete flow: Hook → Exit → Worker → Storage (all mocked)"""
    session_id, transcript_path = sample_transcript

    # Mock all external dependencies
    with (
        patch("amplifier.memory.processor.MemoryExtractor") as mock_extractor_cls,
        patch("amplifier.memory.processor.MemoryStore") as mock_store_cls,
        patch("amplifier.memory.commands.exit_command.start_extraction") as mock_start,
        patch("amplifier.memory.commands.exit_command.get_extraction_status") as mock_status,
    ):
        # Setup mocks
        mock_status.return_value.status = "idle"
        mock_start.return_value = True

        mock_extractor = mock_extractor_cls.return_value
        mock_extractor.extract_from_messages_intelligent = AsyncMock(
            return_value={
                "memories": [
                    {"content": "Python preference", "type": "preference", "importance": 0.8, "tags": []},
                    {"content": "PostgreSQL decision", "type": "decision", "importance": 0.9, "tags": []},
                ]
            }
        )

        mock_store = mock_store_cls.return_value

        # 1. SessionEnd hook receives event
        from amplifier.memory.hooks.session_end import handle_session_end

        hook_result = handle_session_end(session_id, str(transcript_path))
        assert hook_result["success"] is True

        # 2. Transcript registered
        record = get_transcript_by_session(session_id)
        assert record is not None

        # 3. Process transcript (as worker would)
        from amplifier.memory.processor import process_transcript

        process_result = process_transcript(transcript_path)

        # 4. Verify complete flow
        assert process_result.success is True
        assert process_result.memories_extracted == 2
        assert mock_store.add_memory.call_count == 2
