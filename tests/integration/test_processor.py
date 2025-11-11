"""Integration tests for background processor"""

import json
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from amplifier.memory.processor import process_extraction_queue
from amplifier.memory.queue import QueuedExtraction
from amplifier.memory.queue import clear_queue
from amplifier.memory.queue import queue_extraction


@pytest.fixture
def clean_queue():
    """Ensure clean queue before and after test"""
    clear_queue()
    yield
    clear_queue()


@pytest.fixture
def mock_transcript(tmp_path):
    """Create a mock transcript file"""
    transcript_file = tmp_path / "test_transcript.jsonl"

    # Create JSONL with conversation messages
    messages = [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
        {"role": "user", "content": "Can you help me with Python?"},
        {"role": "assistant", "content": "Of course! What would you like to know?"},
    ]

    with open(transcript_file, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    return transcript_file


@pytest.mark.asyncio
async def test_processor_extracts_from_queue(clean_queue, mock_transcript):
    """Background processor: queue → extraction → storage"""
    # Queue an item
    item = QueuedExtraction(
        session_id="test-123",
        transcript_path=str(mock_transcript),
        timestamp=datetime.now().isoformat(),
        hook_event="Stop",
    )
    queue_extraction(item)

    # Mock the extractor and store
    with (
        patch("amplifier.memory.processor.MemoryExtractor") as mock_extractor_cls,
        patch("amplifier.memory.processor.MemoryStore") as mock_store_cls,
    ):
        # Setup mocks
        mock_extractor = mock_extractor_cls.return_value
        mock_extractor.extract_from_messages = AsyncMock(
            return_value={"memories": [{"content": "Test memory", "category": "learning"}]}
        )

        mock_store = mock_store_cls.return_value
        mock_store.add_memories_batch = MagicMock()

        # Process queue
        processed = await process_extraction_queue()

        # Verify processing
        assert processed == 1
        mock_extractor.extract_from_messages.assert_called_once()
        mock_store.add_memories_batch.assert_called_once()


@pytest.mark.asyncio
async def test_processor_filters_sidechain(clean_queue, tmp_path):
    """Background processor filters sidechain messages"""
    # Create transcript with sidechain messages
    transcript_file = tmp_path / "test_transcript.jsonl"

    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there", "isSidechain": True},  # Should be filtered
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Answer"},
    ]

    with open(transcript_file, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    # Queue item
    item = QueuedExtraction(
        session_id="test-456",
        transcript_path=str(transcript_file),
        timestamp=datetime.now().isoformat(),
        hook_event="Stop",
    )
    queue_extraction(item)

    # Mock extractor to capture filtered messages
    with (
        patch("amplifier.memory.processor.MemoryExtractor") as mock_extractor_cls,
        patch("amplifier.memory.processor.MemoryStore"),
    ):
        mock_extractor = mock_extractor_cls.return_value

        async def capture_messages(messages, context):
            # Verify sidechain message was filtered out
            assert len(messages) == 3  # 4 original - 1 sidechain
            return {"memories": []}

        mock_extractor.extract_from_messages = AsyncMock(side_effect=capture_messages)

        # Process
        await process_extraction_queue()


@pytest.mark.asyncio
async def test_processor_handles_errors_gracefully(clean_queue, mock_transcript):
    """Bad transcript → logged error, queue cleared"""
    # Queue item with bad transcript path
    item = QueuedExtraction(
        session_id="test-789",
        transcript_path="/nonexistent/path.jsonl",
        timestamp=datetime.now().isoformat(),
        hook_event="Stop",
    )
    queue_extraction(item)

    # Process should not crash
    processed = await process_extraction_queue()

    # Item should be removed even though processing failed
    assert processed == 0  # Nothing successfully processed


@pytest.mark.asyncio
async def test_processor_removes_processed_items(clean_queue, mock_transcript):
    """Verify items removed from queue after successful processing"""
    from amplifier.memory.queue import get_queued_items

    # Queue item
    item = QueuedExtraction(
        session_id="test-999",
        transcript_path=str(mock_transcript),
        timestamp=datetime.now().isoformat(),
        hook_event="Stop",
    )
    queue_extraction(item)

    # Verify queued
    assert len(get_queued_items()) == 1

    # Mock successful extraction
    with (
        patch("amplifier.memory.processor.MemoryExtractor") as mock_extractor_cls,
        patch("amplifier.memory.processor.MemoryStore"),
    ):
        mock_extractor = mock_extractor_cls.return_value
        mock_extractor.extract_from_messages = AsyncMock(return_value={"memories": []})

        # Process
        await process_extraction_queue()

    # Verify removed from queue
    assert len(get_queued_items()) == 0


@pytest.mark.asyncio
async def test_processor_skips_short_transcripts(clean_queue, tmp_path):
    """Processor skips transcripts with too few messages"""
    # Create short transcript (only 1 message)
    transcript_file = tmp_path / "short_transcript.jsonl"
    with open(transcript_file, "w") as f:
        f.write(json.dumps({"role": "user", "content": "Hi"}) + "\n")

    # Queue item
    item = QueuedExtraction(
        session_id="test-short",
        transcript_path=str(transcript_file),
        timestamp=datetime.now().isoformat(),
        hook_event="Stop",
    )
    queue_extraction(item)

    # Process
    processed = await process_extraction_queue()

    # Should skip (not process)
    assert processed == 0
