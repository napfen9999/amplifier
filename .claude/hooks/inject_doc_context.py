#!/usr/bin/env python3
"""
UserPromptSubmit Hook: Injects documentation context into prompts.

Triggers on: Every user prompt
Behavior: Adds context that Claude will see

Injects:
1. Current documentation requirements
2. Key files to check before changes
"""

import json
import sys
from pathlib import Path


def get_active_specs() -> list[str]:
    """Find active FEATURE_STRATEGY.md files."""
    ai_working = Path("ai_working")
    if not ai_working.exists():
        return []

    specs = []
    for spec in ai_working.glob("*/FEATURE_STRATEGY.md"):
        # Get the feature name from the directory
        feature_dir = spec.parent.name
        specs.append(feature_dir)

    return specs


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    prompt = input_data.get("prompt", "")

    # Check if prompt seems to be about implementation
    implementation_keywords = [
        "implement",
        "add",
        "create",
        "build",
        "write",
        "code",
        "function",
        "class",
        "api",
        "endpoint",
        "feature",
    ]

    is_implementation = any(kw in prompt.lower() for kw in implementation_keywords)

    if is_implementation:
        active_specs = get_active_specs()

        context_parts = [
            "Doc Requirements:",
            "- Check docs/architecture/CONTRACTS.md before API changes",
            "- Check ai_context/DATA_MODEL.md before schema changes",
            "- Run tests after code changes (make test)",
        ]

        if active_specs:
            context_parts.append(f"- Active specs: {', '.join(active_specs)}")

        # Print context - this gets injected into Claude's context
        # For UserPromptSubmit, stdout with exit 0 is added as context
        print("\n".join(context_parts))

    sys.exit(0)


if __name__ == "__main__":
    main()
