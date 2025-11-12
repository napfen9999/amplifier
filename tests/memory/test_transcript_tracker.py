"""Tests for transcript tracking system"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from amplifier.memory.transcript_tracker import TranscriptRecord
from amplifier.memory.transcript_tracker import add_transcript_record
from amplifier.memory.transcript_tracker import get_all_transcripts
from amplifier.memory.transcript_tracker import get_transcript_by_session
from amplifier.memory.transcript_tracker import get_unprocessed_transcripts
from amplifier.memory.transcript_tracker import load_transcripts
from amplifier.memory.transcript_tracker import mark_transcript_processed
from amplifier.memory.transcript_tracker import save_transcripts


@pytest.fixture
def temp_tracking_file(monkeypatch):
    """Create temporary tracking file for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracking_file = Path(tmpdir) / "transcripts.json"

        # Patch the TRANSCRIPTS_FILE constant
        import amplifier.memory.transcript_tracker as tracker_module

        monkeypatch.setattr(tracker_module, "TRANSCRIPTS_FILE", tracking_file)

        yield tracking_file


def test_transcript_record_creation():
    """Test TranscriptRecord dataclass creation"""
    record = TranscriptRecord(
        session_id="test123",
        transcript_path="/path/to/transcript.jsonl",
        created_at="2025-11-12T15:30:00",
    )

    assert record.session_id == "test123"
    assert record.transcript_path == "/path/to/transcript.jsonl"
    assert record.created_at == "2025-11-12T15:30:00"
    assert record.processed is False
    assert record.processed_at is None
    assert record.memories_extracted == 0


def test_add_transcript_record(temp_tracking_file):
    """Test adding new transcript record"""
    add_transcript_record("test123", "/path/to/transcript.jsonl")

    # Verify file was created
    assert temp_tracking_file.exists()

    # Verify content
    with open(temp_tracking_file) as f:
        data = json.load(f)

    assert data["version"] == "1.0"
    assert len(data["transcripts"]) == 1

    transcript = data["transcripts"][0]
    assert transcript["session_id"] == "test123"
    assert transcript["transcript_path"] == "/path/to/transcript.jsonl"
    assert transcript["processed"] is False
    assert transcript["processed_at"] is None
    assert transcript["memories_extracted"] == 0

    # Verify created_at is ISO8601
    created_at = datetime.fromisoformat(transcript["created_at"])
    assert created_at is not None


def test_add_duplicate_transcript_skipped(temp_tracking_file):
    """Test that duplicate session IDs are skipped"""
    add_transcript_record("test123", "/path/to/transcript1.jsonl")
    add_transcript_record("test123", "/path/to/transcript2.jsonl")  # Duplicate

    # Should only have one record
    transcripts = load_transcripts()
    assert len(transcripts) == 1
    assert transcripts[0].transcript_path == "/path/to/transcript1.jsonl"  # Original path


def test_load_transcripts(temp_tracking_file):
    """Test loading transcript records"""
    # Add some records
    add_transcript_record("test1", "/path/to/transcript1.jsonl")
    add_transcript_record("test2", "/path/to/transcript2.jsonl")

    # Load and verify
    records = load_transcripts()
    assert len(records) == 2
    assert all(isinstance(r, TranscriptRecord) for r in records)

    session_ids = {r.session_id for r in records}
    assert session_ids == {"test1", "test2"}


def test_save_transcripts(temp_tracking_file):
    """Test saving transcript records"""
    records = [
        TranscriptRecord(
            session_id="test1",
            transcript_path="/path/to/transcript1.jsonl",
            created_at="2025-11-12T15:30:00",
        ),
        TranscriptRecord(
            session_id="test2",
            transcript_path="/path/to/transcript2.jsonl",
            created_at="2025-11-12T16:45:00",
            processed=True,
            processed_at="2025-11-12T16:50:00",
            memories_extracted=10,
        ),
    ]

    save_transcripts(records)

    # Verify file content
    with open(temp_tracking_file) as f:
        data = json.load(f)

    assert data["version"] == "1.0"
    assert len(data["transcripts"]) == 2

    # Verify second record is marked processed
    processed_record = next(t for t in data["transcripts"] if t["session_id"] == "test2")
    assert processed_record["processed"] is True
    assert processed_record["memories_extracted"] == 10


def test_mark_transcript_processed(temp_tracking_file):
    """Test marking transcript as processed"""
    # Add unprocessed transcript
    add_transcript_record("test123", "/path/to/transcript.jsonl")

    # Mark as processed
    mark_transcript_processed("test123", 15)

    # Verify update
    records = load_transcripts()
    assert len(records) == 1

    record = records[0]
    assert record.processed is True
    assert record.memories_extracted == 15
    assert record.processed_at is not None

    # Verify processed_at is ISO8601 timestamp
    processed_at = datetime.fromisoformat(record.processed_at)
    assert processed_at is not None


def test_mark_nonexistent_transcript(temp_tracking_file):
    """Test marking nonexistent transcript doesn't crash"""
    # Should not raise exception
    mark_transcript_processed("nonexistent", 10)

    # File should still be created with empty list
    assert temp_tracking_file.exists()
    transcripts = load_transcripts()
    assert len(transcripts) == 0


def test_get_unprocessed_transcripts(temp_tracking_file):
    """Test getting only unprocessed transcripts"""
    # Add mix of processed and unprocessed
    add_transcript_record("test1", "/path/to/transcript1.jsonl")
    add_transcript_record("test2", "/path/to/transcript2.jsonl")
    add_transcript_record("test3", "/path/to/transcript3.jsonl")

    mark_transcript_processed("test2", 10)

    # Get unprocessed
    unprocessed = get_unprocessed_transcripts()
    assert len(unprocessed) == 2

    session_ids = {r.session_id for r in unprocessed}
    assert session_ids == {"test1", "test3"}


def test_get_transcript_by_session(temp_tracking_file):
    """Test getting specific transcript by session ID"""
    add_transcript_record("test1", "/path/to/transcript1.jsonl")
    add_transcript_record("test2", "/path/to/transcript2.jsonl")

    # Get existing transcript
    record = get_transcript_by_session("test2")
    assert record is not None
    assert record.session_id == "test2"
    assert record.transcript_path == "/path/to/transcript2.jsonl"

    # Get nonexistent transcript
    record = get_transcript_by_session("nonexistent")
    assert record is None


def test_get_all_transcripts_alias(temp_tracking_file):
    """Test get_all_transcripts is alias for load_transcripts"""
    add_transcript_record("test1", "/path/to/transcript1.jsonl")
    add_transcript_record("test2", "/path/to/transcript2.jsonl")

    all_records = get_all_transcripts()
    loaded_records = load_transcripts()

    assert len(all_records) == len(loaded_records)
    assert {r.session_id for r in all_records} == {r.session_id for r in loaded_records}


def test_file_ends_with_newline(temp_tracking_file):
    """Test that JSON file ends with newline character"""
    add_transcript_record("test123", "/path/to/transcript.jsonl")

    # Read raw file content
    content = temp_tracking_file.read_text()

    # Verify ends with newline
    assert content.endswith("\n")


def test_backup_created_before_write(temp_tracking_file):
    """Test that backup is created before modifications"""
    # Add initial record
    add_transcript_record("test1", "/path/to/transcript1.jsonl")

    # Modify (mark as processed)
    mark_transcript_processed("test1", 10)

    # Check backup file exists
    backup_path = temp_tracking_file.with_suffix(".json.backup")
    assert backup_path.exists()

    # Verify backup contains original content (unprocessed)
    with open(backup_path) as f:
        backup_data = json.load(f)

    backup_record = backup_data["transcripts"][0]
    assert backup_record["processed"] is False  # Original state
    assert backup_record["memories_extracted"] == 0


def test_empty_file_initialization(temp_tracking_file):
    """Test that empty file is created correctly"""
    # Just load transcripts (should create empty file)
    records = load_transcripts()

    assert records == []
    assert temp_tracking_file.exists()

    # Verify file structure
    with open(temp_tracking_file) as f:
        data = json.load(f)

    assert data["version"] == "1.0"
    assert data["transcripts"] == []


def test_json_formatting(temp_tracking_file):
    """Test that JSON is properly formatted with indentation"""
    add_transcript_record("test123", "/path/to/transcript.jsonl")

    # Read raw content
    content = temp_tracking_file.read_text()

    # Verify indentation (should have spaces for pretty-printing)
    assert "  " in content  # Has indentation
    assert '"version"' in content  # Has quoted keys
    assert '"transcripts"' in content


def test_multiple_operations_sequence(temp_tracking_file):
    """Test realistic sequence of operations"""
    # Session 1: Add and process
    add_transcript_record("session1", "/transcripts/session1.jsonl")
    mark_transcript_processed("session1", 5)

    # Session 2: Add but don't process
    add_transcript_record("session2", "/transcripts/session2.jsonl")

    # Session 3: Add and process
    add_transcript_record("session3", "/transcripts/session3.jsonl")
    mark_transcript_processed("session3", 12)

    # Verify state
    all_records = get_all_transcripts()
    assert len(all_records) == 3

    unprocessed = get_unprocessed_transcripts()
    assert len(unprocessed) == 1
    assert unprocessed[0].session_id == "session2"

    # Verify memory counts
    session1 = get_transcript_by_session("session1")
    assert session1 is not None
    assert session1.memories_extracted == 5

    session3 = get_transcript_by_session("session3")
    assert session3 is not None
    assert session3.memories_extracted == 12
