"""Integration tests for processor

Tests the full integration of extraction pipeline with storage.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from amplifier.memory.processor import process_transcript


@pytest.fixture
def temp_transcript():
    """Create temporary transcript file"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        # Write sample conversation
        messages = [
            {"role": "user", "content": "I prefer Python for backend development"},
            {"role": "assistant", "content": "I'll remember your preference for Python backends"},
            {"role": "user", "content": "We decided to use PostgreSQL for the database"},
            {"role": "assistant", "content": "Got it, I'll use PostgreSQL in our designs"},
        ]

        for msg in messages:
            f.write(json.dumps(msg) + "\n")

        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    temp_path.unlink(missing_ok=True)


def test_process_transcript_integration(temp_transcript):
    """Process transcript: load → extract → store"""
    from unittest.mock import AsyncMock

    # Mock the extractor and store to verify integration
    with (
        patch("amplifier.memory.processor.MemoryExtractor") as mock_extractor_cls,
        patch("amplifier.memory.processor.MemoryStore") as mock_store_cls,
    ):
        # Mock extraction result (async)
        mock_extractor = mock_extractor_cls.return_value
        mock_extractor.extract_from_messages_intelligent = AsyncMock(
            return_value={
                "memories": [
                    {"content": "User prefers Python", "type": "preference", "importance": 0.8, "tags": ["python"]},
                    {"content": "Using PostgreSQL", "type": "decision", "importance": 0.9, "tags": ["postgresql"]},
                ]
            }
        )

        # Mock store
        mock_store = mock_store_cls.return_value

        # Process
        result = process_transcript(temp_transcript)

        # Verify result
        assert result.success is True
        assert result.memories_extracted == 2
        assert result.error is None

        # Verify extractor was called
        mock_extractor.extract_from_messages_intelligent.assert_called_once()

        # Verify memories were saved to store
        assert mock_store.add_memory.call_count == 2


def test_process_transcript_handles_empty_file():
    """Empty transcript → zero memories extracted"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        temp_path = Path(f.name)

    try:
        with patch("amplifier.memory.processor.MemoryExtractor"):
            result = process_transcript(temp_path)

            assert result.success is True
            assert result.memories_extracted == 0
            assert "No messages" in result.error
    finally:
        temp_path.unlink()


def test_process_transcript_handles_invalid_json():
    """Invalid JSON → error returned"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        # Write invalid JSON
        f.write("not valid json\n")
        f.write('{"valid": "json"}\n')
        temp_path = Path(f.name)

    try:
        result = process_transcript(temp_path)

        assert result.success is False
        assert result.memories_extracted == 0
        assert result.error is not None
        assert "Invalid JSON" in result.error
    finally:
        temp_path.unlink()


def test_process_transcript_handles_missing_file():
    """Missing file → FileNotFoundError raised"""
    fake_path = Path("/tmp/nonexistent_transcript_12345.jsonl")

    with pytest.raises(FileNotFoundError):
        process_transcript(fake_path)


def test_process_transcript_handles_extraction_failure(temp_transcript):
    """Extraction failure → error result returned"""
    from unittest.mock import AsyncMock

    with patch("amplifier.memory.processor.MemoryExtractor") as mock_extractor_cls:
        # Mock extraction to raise error (async)
        mock_extractor = mock_extractor_cls.return_value
        mock_extractor.extract_from_messages_intelligent = AsyncMock(side_effect=RuntimeError("API error"))

        result = process_transcript(temp_transcript)

        assert result.success is False
        assert result.memories_extracted == 0
        assert "API error" in result.error


def test_process_transcript_session_id_extraction(temp_transcript):
    """Session ID extracted from filename"""
    from unittest.mock import AsyncMock

    # Rename to standard format
    session_id = "test123"
    renamed_path = temp_transcript.parent / f"session_{session_id}.jsonl"
    temp_transcript.rename(renamed_path)

    try:
        with (
            patch("amplifier.memory.processor.MemoryExtractor") as mock_extractor_cls,
            patch("amplifier.memory.processor.MemoryStore"),
        ):
            mock_extractor = mock_extractor_cls.return_value
            mock_extractor.extract_from_messages_intelligent = AsyncMock(return_value={"memories": []})

            result = process_transcript(renamed_path)

            assert result.session_id == session_id
    finally:
        renamed_path.unlink(missing_ok=True)


def test_process_transcript_includes_session_metadata(temp_transcript):
    """Memories include session ID in metadata"""
    from unittest.mock import AsyncMock

    with (
        patch("amplifier.memory.processor.MemoryExtractor") as mock_extractor_cls,
        patch("amplifier.memory.processor.MemoryStore") as mock_store_cls,
    ):
        mock_extractor = mock_extractor_cls.return_value
        mock_extractor.extract_from_messages_intelligent = AsyncMock(
            return_value={"memories": [{"content": "Test memory", "type": "learning", "importance": 0.5, "tags": []}]}
        )

        mock_store = mock_store_cls.return_value

        process_transcript(temp_transcript)

        # Check that add_memory was called with metadata including session_id
        call_args = mock_store.add_memory.call_args[0][0]
        assert "session_id" in call_args.metadata
