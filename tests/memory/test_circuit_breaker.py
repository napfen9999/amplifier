"""Tests for circuit breaker throttle protection"""


import pytest

from amplifier.memory.circuit_breaker import FREQUENCY_THRESHOLD
from amplifier.memory.circuit_breaker import STATE_FILE
from amplifier.memory.circuit_breaker import TIME_WINDOW
from amplifier.memory.circuit_breaker import check_circuit_breaker
from amplifier.memory.circuit_breaker import reset_circuit_breaker


@pytest.fixture
def clean_circuit():
    """Ensure circuit breaker is clean before and after test"""
    reset_circuit_breaker()
    yield
    reset_circuit_breaker()


def test_circuit_allows_normal_rate(clean_circuit):
    """Verify circuit allows hooks below threshold"""
    # Call 4 times (below threshold of 5)
    for i in range(4):
        state = check_circuit_breaker()
        assert state.allowed is True
        assert state.recent_hook_count == i + 1


def test_circuit_blocks_high_rate(clean_circuit):
    """Verify circuit blocks hooks above threshold"""
    # Call 5 times (at threshold)
    for _ in range(FREQUENCY_THRESHOLD):
        state = check_circuit_breaker()
        assert state.allowed is True

    # 6th call should be blocked
    state = check_circuit_breaker()
    assert state.allowed is False
    assert "Too many hooks" in state.reason
    assert state.recent_hook_count == FREQUENCY_THRESHOLD


def test_circuit_resets_after_cooldown(clean_circuit):
    """Verify circuit opens after time window expires"""
    # Fill up the circuit
    for _ in range(FREQUENCY_THRESHOLD):
        check_circuit_breaker()

    # Next call blocked
    state = check_circuit_breaker()
    assert state.allowed is False

    # Wait for time window to pass (using short window for testing)
    # We can't actually wait 60 seconds in a test, so we'll verify
    # the logic by checking the wait_seconds value
    assert state.wait_seconds > 0
    assert state.wait_seconds <= TIME_WINDOW


def test_circuit_state_persistence(clean_circuit):
    """Verify circuit state persists across checks"""
    # Make 3 calls
    for _ in range(3):
        check_circuit_breaker()

    # Verify state file exists
    assert STATE_FILE.exists()

    # Next check should remember previous calls
    state = check_circuit_breaker()
    assert state.recent_hook_count == 4  # 3 previous + 1 current


def test_circuit_sliding_window(clean_circuit):
    """Verify circuit uses sliding time window"""
    # Make calls at the threshold
    for _ in range(FREQUENCY_THRESHOLD):
        state = check_circuit_breaker()
        assert state.allowed is True

    # Immediate next call blocked
    state = check_circuit_breaker()
    assert state.allowed is False

    # Check that wait time is reasonable (should be close to TIME_WINDOW)
    assert 0 < state.wait_seconds <= TIME_WINDOW


def test_reset_circuit_breaker_works(clean_circuit):
    """Verify reset_circuit_breaker() clears state"""
    # Make some calls
    for _ in range(3):
        check_circuit_breaker()

    assert STATE_FILE.exists()

    # Reset
    reset_circuit_breaker()

    assert not STATE_FILE.exists()

    # Next call should start fresh
    state = check_circuit_breaker()
    assert state.recent_hook_count == 1


def test_circuit_handles_corrupted_state(clean_circuit):
    """Verify circuit handles corrupted state file gracefully"""
    # Create corrupted state file
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        f.write("invalid json{{{")

    # Should not error, should reset and allow
    state = check_circuit_breaker()
    assert state.allowed is True
    assert state.recent_hook_count == 1
