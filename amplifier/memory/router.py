"""Hook event routing

Determines appropriate action for each hook event based on event type
and circuit breaker state.
"""

import logging
from dataclasses import dataclass
from typing import Any
from typing import Literal

from .circuit_breaker import check_circuit_breaker

logger = logging.getLogger(__name__)


@dataclass
class HookAction:
    """Action to take for hook event

    Attributes:
        action: What to do (skip, queue, or error)
        reason: Explanation for decision
    """

    action: Literal["skip", "queue", "error"]
    reason: str


def route_hook_event(event_name: str, payload: dict[str, Any]) -> HookAction:
    """Determine action for hook event

    Applies routing rules based on event type and system state.

    Rules:
    1. Skip SubagentStop events (incomplete context)
    2. Check circuit breaker (prevent cascade)
    3. Queue Stop events for extraction

    Args:
        event_name: Hook event type ("Stop", "SubagentStop", etc.)
        payload: Event payload data

    Returns:
        Action to take (skip, queue, or error)
    """
    # Rule 1: Skip SubagentStop events entirely
    if event_name == "SubagentStop":
        return HookAction(action="skip", reason="SubagentStop events are skipped (incomplete context)")

    # Rule 2: Check circuit breaker
    circuit_state = check_circuit_breaker()
    if not circuit_state.allowed:
        return HookAction(action="skip", reason=f"Circuit breaker active: {circuit_state.reason}")

    # Rule 3: Stop events should be queued
    if event_name == "Stop":
        return HookAction(action="queue", reason="Stop event queued for extraction")

    # Fallback: Skip unknown events
    return HookAction(action="skip", reason=f"Unknown event type: {event_name}")
