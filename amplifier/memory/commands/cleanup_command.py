"""Cleanup command for extraction state management

Provides commands to clean up extraction state after completion or crashes.
Allows users to manually reset the extraction system.

Usage:
    from amplifier.memory.commands.cleanup_command import cleanup_extraction

    # Clean up after completion
    cleanup_extraction()
"""

from amplifier.memory.extraction_logger import get_extraction_logger
from amplifier.memory.watchdog import cleanup_extraction_state
from amplifier.memory.watchdog import get_extraction_status
from amplifier.memory.watchdog import stop_extraction


def cleanup_extraction(force: bool = False) -> dict[str, bool | str]:
    """Clean up extraction state

    Removes extraction state file after completion. Can force cleanup
    even if extraction is running (stops it first).

    Args:
        force: If True, stop running extraction before cleanup

    Returns:
        Dict with:
        - success: Whether cleanup succeeded
        - message: Human-readable status message
        - stopped: Whether running extraction was stopped
    """
    logger = get_extraction_logger()

    logger.info(f"Cleanup command: force={force}")

    # Check current status
    status = get_extraction_status()

    # If running and not forcing, refuse
    if status.status == "running" and not force:
        logger.warning("Cleanup refused: extraction running (use force=True to stop)")
        return {
            "success": False,
            "message": "Extraction is running. Use force=True to stop and clean up.",
            "stopped": False,
        }

    # If running and forcing, stop first
    stopped = False
    if status.status == "running" and force:
        logger.info("Force cleanup: stopping extraction first")
        try:
            stop_result = stop_extraction()
            if not stop_result:
                logger.error("Failed to stop extraction")
                return {
                    "success": False,
                    "message": "Failed to stop running extraction",
                    "stopped": False,
                }
            stopped = True
            logger.info("Extraction stopped")
        except Exception as e:
            logger.error(f"Error stopping extraction: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error stopping extraction: {e}",
                "stopped": False,
            }

    # Cleanup state
    try:
        cleanup_result = cleanup_extraction_state()

        if not cleanup_result:
            # Should not happen (cleanup_extraction_state returns False only if running)
            logger.warning("Cleanup refused by state manager")
            return {
                "success": False,
                "message": "Cleanup refused (extraction may still be running)",
                "stopped": stopped,
            }

        logger.info("Extraction state cleaned up")
        return {
            "success": True,
            "message": "Extraction state cleaned up" + (" (extraction stopped)" if stopped else ""),
            "stopped": stopped,
        }

    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Cleanup failed: {e}",
            "stopped": stopped,
        }


def get_cleanup_recommendations() -> dict[str, bool | str | list[str]]:
    """Get cleanup recommendations based on current state

    Analyzes extraction status and provides recommendations for cleanup.

    Returns:
        Dict with:
        - should_cleanup: Whether cleanup is recommended
        - reason: Explanation of recommendation
        - actions: List of recommended actions
    """
    status = get_extraction_status()

    if status.status == "idle":
        return {
            "should_cleanup": False,
            "reason": "No extraction state to clean up",
            "actions": [],
        }

    if status.status == "running":
        return {
            "should_cleanup": False,
            "reason": "Extraction is currently running",
            "actions": [
                "Wait for extraction to complete",
                "Or use cleanup_extraction(force=True) to stop and clean up",
            ],
        }

    if status.status == "completed":
        return {
            "should_cleanup": True,
            "reason": "Extraction completed successfully",
            "actions": [
                "Run cleanup_extraction() to remove state file",
                "This allows starting fresh extractions",
            ],
        }

    if status.status == "failed":
        return {
            "should_cleanup": True,
            "reason": "Extraction completed with errors",
            "actions": [
                "Review logs for errors",
                "Run cleanup_extraction() to remove state file",
                "Fix any issues before re-running extraction",
            ],
        }

    if status.status == "crashed":
        return {
            "should_cleanup": True,
            "reason": "Extraction process crashed",
            "actions": [
                "Review logs for crash details",
                "Run cleanup_extraction() to remove stale state",
                "Investigate crash cause before re-running",
            ],
        }

    return {
        "should_cleanup": False,
        "reason": f"Unknown status: {status.status}",
        "actions": ["Check extraction logs", "Contact support if issue persists"],
    }
