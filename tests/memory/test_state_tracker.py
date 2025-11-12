"""Tests for extraction state tracking system"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from amplifier.memory.state_tracker import ExtractionState
from amplifier.memory.state_tracker import TranscriptState
from amplifier.memory.state_tracker import clear_extraction_state
from amplifier.memory.state_tracker import load_extraction_state
from amplifier.memory.state_tracker import save_extraction_state
from amplifier.memory.state_tracker import update_transcript_progress


@pytest.fixture
def temp_state_file(monkeypatch):
    """Create temporary state file for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / ".extraction_state.json"

        # Patch the STATE_FILE constant
        import amplifier.memory.state_tracker as tracker_module

        monkeypatch.setattr(tracker_module, "STATE_FILE", state_file)

        yield state_file


def test_transcript_state_creation():
    """Test TranscriptState dataclass creation"""
    state = TranscriptState(
        id="test123",
        status="pending",
    )

    assert state.id == "test123"
    assert state.status == "pending"
    assert state.memories == 0
    assert state.completed_at is None


def test_extraction_state_creation():
    """Test ExtractionState dataclass creation"""
    transcript_states = [
        TranscriptState(id="test1", status="completed", memories=5),
        TranscriptState(id="test2", status="in_progress"),
    ]

    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=12345,
        transcripts=transcript_states,
        last_update="2025-11-12T15:32:00",
    )

    assert state.status == "running"
    assert state.pid == 12345
    assert len(state.transcripts) == 2


def test_save_extraction_state(temp_state_file):
    """Test saving extraction state"""
    transcript_states = [
        TranscriptState(id="test1", status="pending"),
        TranscriptState(id="test2", status="in_progress"),
    ]

    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=12345,
        transcripts=transcript_states,
        last_update="2025-11-12T15:32:00",
    )

    save_extraction_state(state)

    # Verify file was created
    assert temp_state_file.exists()

    # Verify content
    with open(temp_state_file) as f:
        data = json.load(f)

    assert data["status"] == "running"
    assert data["pid"] == 12345
    assert len(data["transcripts"]) == 2

    # Verify last_update was updated
    last_update = datetime.fromisoformat(data["last_update"])
    assert last_update is not None


def test_load_extraction_state(temp_state_file):
    """Test loading extraction state"""
    # Create state
    transcript_states = [
        TranscriptState(id="test1", status="completed", memories=10),
    ]

    original_state = ExtractionState(
        status="completed",
        started_at="2025-11-12T15:30:00",
        pid=None,
        transcripts=transcript_states,
        last_update="2025-11-12T15:35:00",
    )

    save_extraction_state(original_state)

    # Load and verify
    loaded_state = load_extraction_state()
    assert loaded_state is not None
    assert loaded_state.status == "completed"
    assert loaded_state.pid is None
    assert len(loaded_state.transcripts) == 1
    assert loaded_state.transcripts[0].id == "test1"
    assert loaded_state.transcripts[0].memories == 10


def test_load_nonexistent_state(temp_state_file):
    """Test loading state when file doesn't exist"""
    state = load_extraction_state()
    assert state is None


def test_load_corrupt_state(temp_state_file):
    """Test loading corrupt JSON file"""
    # Write invalid JSON
    temp_state_file.parent.mkdir(parents=True, exist_ok=True)
    temp_state_file.write_text("{ invalid json }")

    # Should return None instead of crashing
    state = load_extraction_state()
    assert state is None


def test_clear_extraction_state(temp_state_file):
    """Test clearing extraction state"""
    # Create state
    state = ExtractionState(
        status="completed",
        started_at="2025-11-12T15:30:00",
        pid=None,
        transcripts=[],
        last_update="2025-11-12T15:35:00",
    )

    save_extraction_state(state)
    assert temp_state_file.exists()

    # Clear state
    clear_extraction_state()

    # Verify file was deleted
    assert not temp_state_file.exists()


def test_clear_nonexistent_state(temp_state_file):
    """Test clearing state when file doesn't exist"""
    # Should not crash
    clear_extraction_state()


def test_update_transcript_progress(temp_state_file):
    """Test updating transcript progress"""
    # Create initial state
    transcript_states = [
        TranscriptState(id="test1", status="pending"),
        TranscriptState(id="test2", status="pending"),
    ]

    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=12345,
        transcripts=transcript_states,
        last_update="2025-11-12T15:30:00",
    )

    save_extraction_state(state)

    # Update test1 to in_progress
    update_transcript_progress("test1", "in_progress")

    # Verify update
    updated_state = load_extraction_state()
    assert updated_state is not None

    test1 = next(t for t in updated_state.transcripts if t.id == "test1")
    assert test1.status == "in_progress"

    # Other transcript unchanged
    test2 = next(t for t in updated_state.transcripts if t.id == "test2")
    assert test2.status == "pending"


def test_update_transcript_to_completed(temp_state_file):
    """Test updating transcript to completed status"""
    # Create initial state
    transcript_states = [
        TranscriptState(id="test1", status="in_progress"),
    ]

    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=12345,
        transcripts=transcript_states,
        last_update="2025-11-12T15:30:00",
    )

    save_extraction_state(state)

    # Mark as completed
    update_transcript_progress("test1", "completed", memories=15)

    # Verify update
    updated_state = load_extraction_state()
    assert updated_state is not None

    test1 = updated_state.transcripts[0]
    assert test1.status == "completed"
    assert test1.memories == 15
    assert test1.completed_at is not None

    # Verify completed_at is ISO8601
    completed_at = datetime.fromisoformat(test1.completed_at)
    assert completed_at is not None


def test_update_nonexistent_transcript(temp_state_file):
    """Test updating transcript that doesn't exist in state"""
    # Create state without the transcript
    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=12345,
        transcripts=[],
        last_update="2025-11-12T15:30:00",
    )

    save_extraction_state(state)

    # Try to update nonexistent transcript (should not crash)
    update_transcript_progress("nonexistent", "completed", memories=10)

    # State should be unchanged
    updated_state = load_extraction_state()
    assert updated_state is not None
    assert len(updated_state.transcripts) == 0


def test_update_with_no_state(temp_state_file):
    """Test updating transcript when no state file exists"""
    # Should not crash
    update_transcript_progress("test1", "completed", memories=10)


def test_backup_created_before_save(temp_state_file):
    """Test that backup is created before modifications"""
    # Create initial state
    initial_state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=12345,
        transcripts=[TranscriptState(id="test1", status="pending")],
        last_update="2025-11-12T15:30:00",
    )

    save_extraction_state(initial_state)

    # Modify state
    initial_state.status = "completed"
    save_extraction_state(initial_state)

    # Check backup exists
    backup_path = temp_state_file.with_suffix(".json.backup")
    assert backup_path.exists()

    # Verify backup contains original status
    with open(backup_path) as f:
        backup_data = json.load(f)

    assert backup_data["status"] == "running"  # Original status


def test_file_ends_with_newline(temp_state_file):
    """Test that JSON file ends with newline character"""
    state = ExtractionState(
        status="completed",
        started_at="2025-11-12T15:30:00",
        pid=None,
        transcripts=[],
        last_update="2025-11-12T15:35:00",
    )

    save_extraction_state(state)

    # Read raw file content
    content = temp_state_file.read_text()

    # Verify ends with newline
    assert content.endswith("\n")


def test_json_formatting(temp_state_file):
    """Test that JSON is properly formatted with indentation"""
    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=12345,
        transcripts=[TranscriptState(id="test1", status="pending")],
        last_update="2025-11-12T15:30:00",
    )

    save_extraction_state(state)

    # Read raw content
    content = temp_state_file.read_text()

    # Verify indentation (should have spaces for pretty-printing)
    assert "  " in content  # Has indentation
    assert '"status"' in content  # Has quoted keys


def test_multiple_transcript_updates(temp_state_file):
    """Test sequence of transcript updates"""
    # Create state with 3 transcripts
    transcript_states = [
        TranscriptState(id="test1", status="pending"),
        TranscriptState(id="test2", status="pending"),
        TranscriptState(id="test3", status="pending"),
    ]

    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=12345,
        transcripts=transcript_states,
        last_update="2025-11-12T15:30:00",
    )

    save_extraction_state(state)

    # Update all transcripts in sequence
    update_transcript_progress("test1", "in_progress")
    update_transcript_progress("test1", "completed", memories=5)
    update_transcript_progress("test2", "in_progress")
    update_transcript_progress("test2", "completed", memories=8)
    update_transcript_progress("test3", "in_progress")

    # Verify final state
    final_state = load_extraction_state()
    assert final_state is not None

    test1 = next(t for t in final_state.transcripts if t.id == "test1")
    assert test1.status == "completed"
    assert test1.memories == 5

    test2 = next(t for t in final_state.transcripts if t.id == "test2")
    assert test2.status == "completed"
    assert test2.memories == 8

    test3 = next(t for t in final_state.transcripts if t.id == "test3")
    assert test3.status == "in_progress"
    assert test3.memories == 0


def test_state_with_null_pid(temp_state_file):
    """Test state with null PID (process not running)"""
    state = ExtractionState(
        status="completed",
        started_at="2025-11-12T15:30:00",
        pid=None,  # No active process
        transcripts=[],
        last_update="2025-11-12T15:35:00",
    )

    save_extraction_state(state)

    # Load and verify
    loaded_state = load_extraction_state()
    assert loaded_state is not None
    assert loaded_state.pid is None
