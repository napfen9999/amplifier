"""Circuit breaker for hook throttle protection

Prevents hook cascade by limiting hook frequency to 5 events per minute.
Tracks timestamps in JSON file for persistence across sessions.
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_FILE = Path(".data/circuit_breaker_state.json")
FREQUENCY_THRESHOLD = 5  # Max hooks per minute
TIME_WINDOW = 60  # seconds


@dataclass
class CircuitState:
    """Circuit breaker state

    Attributes:
        allowed: Whether hook action is allowed
        reason: Explanation for decision
        wait_seconds: Seconds until circuit opens (if blocked)
        recent_hook_count: Number of recent hooks in time window
    """

    allowed: bool
    reason: str
    wait_seconds: int
    recent_hook_count: int


def check_circuit_breaker() -> CircuitState:
    """Check if safe to proceed with hook action

    Tracks hook invocations and blocks if frequency exceeds threshold.
    Uses sliding time window to prevent spam.

    Returns:
        Circuit state with decision
    """
    state = _load_state()
    now = time.time()

    # Remove timestamps older than time window
    recent = [ts for ts in state.get("timestamps", []) if now - ts < TIME_WINDOW]

    # Check threshold
    if len(recent) >= FREQUENCY_THRESHOLD:
        wait = int(TIME_WINDOW - (now - min(recent)))
        return CircuitState(
            allowed=False,
            reason=f"Too many hooks ({len(recent)} in {TIME_WINDOW}s)",
            wait_seconds=wait,
            recent_hook_count=len(recent),
        )

    # Record this invocation
    recent.append(now)
    _save_state({"timestamps": recent})

    return CircuitState(
        allowed=True,
        reason="Within frequency threshold",
        wait_seconds=0,
        recent_hook_count=len(recent),
    )


def _load_state() -> dict:
    """Load circuit breaker state from file

    Returns:
        State dictionary with timestamps list
    """
    if not STATE_FILE.exists():
        return {"timestamps": []}

    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        # Corrupted state, reset
        return {"timestamps": []}


def _save_state(state: dict) -> None:
    """Save circuit breaker state to file

    Args:
        state: State dictionary to save
    """
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def reset_circuit_breaker() -> None:
    """Reset circuit breaker state

    Deletes state file. Used for testing and maintenance.
    """
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    logger.info("[CIRCUIT BREAKER] Reset")
