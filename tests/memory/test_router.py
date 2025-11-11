"""Tests for hook event routing"""

import pytest

from amplifier.memory.circuit_breaker import FREQUENCY_THRESHOLD
from amplifier.memory.circuit_breaker import reset_circuit_breaker
from amplifier.memory.router import route_hook_event


@pytest.fixture
def clean_circuit():
    """Ensure circuit breaker is clean before and after test"""
    reset_circuit_breaker()
    yield
    reset_circuit_breaker()


def test_router_skips_subagent_stop(clean_circuit):
    """Verify SubagentStop events are skipped"""
    action = route_hook_event("SubagentStop", {})

    assert action.action == "skip"
    assert "SubagentStop" in action.reason
    assert "incomplete context" in action.reason


def test_router_queues_stop(clean_circuit):
    """Verify Stop events are queued"""
    action = route_hook_event("Stop", {})

    assert action.action == "queue"
    assert "queued for extraction" in action.reason


def test_router_respects_circuit_breaker(clean_circuit):
    """Verify router respects circuit breaker state"""
    # Fill up circuit breaker
    for _ in range(FREQUENCY_THRESHOLD):
        route_hook_event("Stop", {})

    # Next call should be blocked by circuit
    action = route_hook_event("Stop", {})

    assert action.action == "skip"
    assert "Circuit breaker active" in action.reason
    assert "Too many hooks" in action.reason


def test_router_handles_unknown_events(clean_circuit):
    """Verify unknown event types are skipped"""
    action = route_hook_event("UnknownEvent", {})

    assert action.action == "skip"
    assert "Unknown event type" in action.reason


def test_router_with_payload(clean_circuit):
    """Verify router accepts payload parameter"""
    payload = {"session_id": "test", "data": {"foo": "bar"}}

    # Should not error with payload
    action = route_hook_event("Stop", payload)

    assert action.action == "queue"


def test_router_subagent_stop_bypasses_circuit(clean_circuit):
    """Verify SubagentStop is skipped even when circuit is open"""
    # SubagentStop should be skipped regardless of circuit state
    action = route_hook_event("SubagentStop", {})

    assert action.action == "skip"
    assert "SubagentStop" in action.reason
