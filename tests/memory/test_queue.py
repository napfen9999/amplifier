"""Tests for extraction queue management"""

import json
from datetime import datetime

import pytest

from amplifier.memory.queue import QUEUE_FILE
from amplifier.memory.queue import QueuedExtraction
from amplifier.memory.queue import clear_queue
from amplifier.memory.queue import get_queued_items
from amplifier.memory.queue import queue_extraction
from amplifier.memory.queue import remove_from_queue


@pytest.fixture
def clean_queue():
    """Ensure queue is clean before and after test"""
    clear_queue()
    yield
    clear_queue()


def test_queue_extraction_appends(clean_queue):
    """Verify queue_extraction() writes to JSONL file"""
    item = QueuedExtraction(
        session_id="test-123",
        transcript_path="/path/to/transcript.jsonl",
        timestamp=datetime.now().isoformat(),
        hook_event="Stop",
    )

    queue_extraction(item)

    # Verify file exists and contains data
    assert QUEUE_FILE.exists()

    with open(QUEUE_FILE) as f:
        lines = f.readlines()
        assert len(lines) == 1

        data = json.loads(lines[0])
        assert data["session_id"] == "test-123"
        assert data["hook_event"] == "Stop"


def test_queue_extraction_appends_multiple(clean_queue):
    """Verify multiple items can be queued"""
    for i in range(3):
        item = QueuedExtraction(
            session_id=f"test-{i}",
            transcript_path=f"/path/to/transcript-{i}.jsonl",
            timestamp=datetime.now().isoformat(),
            hook_event="Stop",
        )
        queue_extraction(item)

    # Verify all items queued
    with open(QUEUE_FILE) as f:
        lines = f.readlines()
        assert len(lines) == 3


def test_get_queued_items_returns_all(clean_queue):
    """Verify get_queued_items() returns all items"""
    # Queue 3 items
    for i in range(3):
        item = QueuedExtraction(
            session_id=f"test-{i}",
            transcript_path=f"/path/to/transcript-{i}.jsonl",
            timestamp=datetime.now().isoformat(),
            hook_event="Stop",
        )
        queue_extraction(item)

    # Retrieve items
    items = get_queued_items()

    assert len(items) == 3
    assert items[0].session_id == "test-0"
    assert items[1].session_id == "test-1"
    assert items[2].session_id == "test-2"


def test_get_queued_items_empty_when_no_file(clean_queue):
    """Verify get_queued_items() returns empty list when no queue file"""
    items = get_queued_items()
    assert items == []


def test_remove_from_queue_deletes(clean_queue):
    """Verify remove_from_queue() removes specific item"""
    # Queue 3 items
    for i in range(3):
        item = QueuedExtraction(
            session_id=f"test-{i}",
            transcript_path=f"/path/to/transcript-{i}.jsonl",
            timestamp=datetime.now().isoformat(),
            hook_event="Stop",
        )
        queue_extraction(item)

    # Remove middle item
    remove_from_queue("test-1")

    # Verify remaining items
    items = get_queued_items()
    assert len(items) == 2
    assert items[0].session_id == "test-0"
    assert items[1].session_id == "test-2"


def test_remove_from_queue_handles_missing_session(clean_queue):
    """Verify remove_from_queue() handles non-existent session gracefully"""
    item = QueuedExtraction(
        session_id="test-123",
        transcript_path="/path/to/transcript.jsonl",
        timestamp=datetime.now().isoformat(),
        hook_event="Stop",
    )
    queue_extraction(item)

    # Remove non-existent session (should not error)
    remove_from_queue("non-existent")

    # Original item should still exist
    items = get_queued_items()
    assert len(items) == 1


def test_clear_queue_works(clean_queue):
    """Verify clear_queue() deletes queue file"""
    # Queue an item
    item = QueuedExtraction(
        session_id="test-123",
        transcript_path="/path/to/transcript.jsonl",
        timestamp=datetime.now().isoformat(),
        hook_event="Stop",
    )
    queue_extraction(item)

    assert QUEUE_FILE.exists()

    # Clear queue
    clear_queue()

    assert not QUEUE_FILE.exists()
    assert get_queued_items() == []
