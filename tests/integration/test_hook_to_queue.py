"""Integration tests for hook to queue flow"""


import pytest

from amplifier.memory.circuit_breaker import FREQUENCY_THRESHOLD
from amplifier.memory.circuit_breaker import reset_circuit_breaker
from amplifier.memory.queue import QUEUE_FILE
from amplifier.memory.queue import clear_queue
from amplifier.memory.queue import get_queued_items
from amplifier.memory.router import route_hook_event


@pytest.fixture
def clean_state():
    """Ensure clean queue and circuit breaker state"""
    clear_queue()
    reset_circuit_breaker()
    yield
    clear_queue()
    reset_circuit_breaker()


def test_stop_hook_queues_extraction(clean_state):
    """End-to-end: Stop event results in queue entry"""
    # Simulate Stop event
    payload = {
        "transcript_path": "/path/to/transcript.jsonl",
        "event": "Stop",
    }

    # Route the event
    action = route_hook_event("Stop", payload)

    # Should queue
    assert action.action == "queue"
    assert "queued for extraction" in action.reason


def test_subagent_stop_skipped(clean_state):
    """End-to-end: SubagentStop event is skipped (no queue entry)"""
    # Simulate SubagentStop event
    payload = {
        "transcript_path": "/path/to/transcript.jsonl",
        "event": "SubagentStop",
    }

    # Route the event
    action = route_hook_event("SubagentStop", payload)

    # Should skip
    assert action.action == "skip"
    assert "SubagentStop" in action.reason
    assert "incomplete context" in action.reason

    # Verify nothing queued
    items = get_queued_items()
    assert len(items) == 0


def test_hook_respects_circuit_breaker(clean_state):
    """End-to-end: Circuit breaker prevents queueing when triggered"""
    payload = {"transcript_path": "/path/to/transcript.jsonl", "event": "Stop"}

    # Fill up circuit breaker
    for _ in range(FREQUENCY_THRESHOLD):
        action = route_hook_event("Stop", payload)
        assert action.action == "queue"

    # Next call should be blocked
    action = route_hook_event("Stop", payload)
    assert action.action == "skip"
    assert "Circuit breaker active" in action.reason


def test_queue_file_created_on_first_queue(clean_state):
    """Verify queue file is created when first item queued"""
    from datetime import datetime

    from amplifier.memory.queue import QueuedExtraction
    from amplifier.memory.queue import queue_extraction

    # Queue an item
    item = QueuedExtraction(
        session_id="test-123",
        transcript_path="/path/to/transcript.jsonl",
        timestamp=datetime.now().isoformat(),
        hook_event="Stop",
    )

    queue_extraction(item)

    # Verify file exists
    assert QUEUE_FILE.exists()

    # Verify content
    items = get_queued_items()
    assert len(items) == 1
    assert items[0].session_id == "test-123"
