#!/usr/bin/env python3
"""
Claude Code hook for PostToolUse events - minimal wrapper for claim validation.
Reads JSON from stdin, calls amplifier modules, writes JSON to stdout.
"""

import asyncio
import json
import sys
from pathlib import Path

# Get the amplifier root directory (3 levels up from this file)
amplifier_root = Path(__file__).resolve().parent.parent.parent

# Add amplifier venv to Python path FIRST (so we get claude-code-sdk and other dependencies)
venv_site_packages = amplifier_root / ".venv" / "lib"
if venv_site_packages.exists():
    # Find the python3.x directory
    python_dirs = list(venv_site_packages.glob("python3.*"))
    if python_dirs:
        site_packages = python_dirs[0] / "site-packages"
        if site_packages.exists():
            sys.path.insert(0, str(site_packages))

# Add amplifier to path
sys.path.insert(0, str(amplifier_root))

# Load environment variables from .env file
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

# Import logger from the same directory
sys.path.insert(0, str(Path(__file__).parent))
from hook_logger import HookLogger  # noqa: E402

logger = HookLogger("post_tool_use")

try:
    from amplifier.memory import MemoryStore
    from amplifier.validation import ClaimValidator
except ImportError as e:
    logger.error(f"Failed to import amplifier modules: {e}")
    # Exit gracefully to not break hook chain
    json.dump({}, sys.stdout)
    sys.exit(0)


async def main():
    """Read input, validate claims, return warnings if contradictions found"""
    try:
        # Check if memory system is enabled
        import os

        memory_enabled = os.getenv("MEMORY_SYSTEM_ENABLED", "false").lower() in ["true", "1", "yes"]
        if not memory_enabled:
            logger.info("Memory system disabled via MEMORY_SYSTEM_ENABLED env var")
            # Return empty response and exit gracefully
            json.dump({}, sys.stdout)
            return

        logger.info("Starting claim validation")
        logger.cleanup_old_logs()  # Clean up old logs on each run

        # Read JSON input
        raw_input = sys.stdin.read()
        logger.info(f"Received input length: {len(raw_input)}")

        input_data = json.loads(raw_input)

        # Extract tool usage info for DDD tracking
        tool_name = input_data.get("tool_name")
        tool_params = input_data.get("parameters", {})

        # DDD file modification tracking (if DDD session active)
        if tool_name in ["Edit", "Write"]:
            file_path = tool_params.get("file_path")
            if file_path:
                try:
                    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "tools"))
                    from ddd_hooks import handle_post_tool_use_edit
                    from ddd_hooks import is_ddd_session_active

                    if is_ddd_session_active():
                        handle_post_tool_use_edit(file_path)
                        logger.info(f"DDD file modification logged: {file_path}")
                except Exception as e:
                    logger.warning(f"DDD file tracking failed (non-critical): {e}")

        # Extract message
        message = input_data.get("message", {})
        role = message.get("role", "")
        content = message.get("content", "")

        logger.debug(f"Message role: {role}")
        logger.debug(f"Content length: {len(content)}")

        # Skip if not assistant message or too short
        if role != "assistant" or not content or len(content) < 50:
            logger.info(f"Skipping: role={role}, content_len={len(content)}")
            json.dump({}, sys.stdout)
            return

        # Initialize modules
        logger.info("Initializing store and validator")
        store = MemoryStore()
        validator = ClaimValidator()

        # Get all memories for validation
        memories = store.get_all()
        logger.info(f"Total memories for validation: {len(memories)}")

        # Validate text for claims
        logger.info("Validating text for claims")
        validation_result = validator.validate_text(content, memories)
        logger.info(f"Has contradictions: {validation_result.has_contradictions}")
        logger.info(f"Claims found: {len(validation_result.claims)}")

        # Build response if contradictions found
        output = {}
        if validation_result.has_contradictions:
            warnings = []
            for claim_validation in validation_result.claims:
                if claim_validation.contradicts and claim_validation.confidence > 0.6:
                    claim_text = claim_validation.claim[:100]
                    warnings.append(f"⚠️ Claim may be incorrect: '{claim_text}...'")

                    if claim_validation.evidence:
                        evidence = claim_validation.evidence[0][:150]
                        warnings.append(f"   Memory says: {evidence}")

            if warnings:
                output = {
                    "warning": "\n".join(warnings),
                    "metadata": {
                        "contradictionsFound": sum(1 for c in validation_result.claims if c.contradicts),
                        "claimsChecked": len(validation_result.claims),
                        "source": "amplifier_validation",
                    },
                }

        json.dump(output, sys.stdout)

        if output:
            logger.info(f"Returned {len(warnings) if 'warnings' in locals() else 0} warnings")
        else:
            logger.info("No contradictions found")

    except Exception as e:
        logger.exception("Error during claim validation", e)
        json.dump({}, sys.stdout)


if __name__ == "__main__":
    asyncio.run(main())
