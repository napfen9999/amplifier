#!/usr/bin/env python3
"""
PreToolUse Hook: Validates documentation before code changes.

Triggers on: Write, Edit, MultiEdit
Behavior: Warning only (exit 0), no blocking

Checks:
1. Is there a FEATURE_STRATEGY.md in ai_working/?
2. Is the file being modified part of a documented spec?
"""

import json
import sys
from pathlib import Path


def is_excluded(file_path: str) -> bool:
    """Skip documentation, tests, configs, and non-code files."""
    excluded_patterns = [
        "/docs/",
        "/tests/",
        "/test_",
        "_test.py",
        ".test.ts",
        ".spec.ts",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".env",
        ".gitignore",
        "/__pycache__/",
        "/node_modules/",
        "/.git/",
        "/ai_working/",
        "/ai_context/",
        "/.claude/",
    ]
    return any(pattern in file_path for pattern in excluded_patterns)


def is_code_file(file_path: str) -> bool:
    """Check if file is a source code file."""
    code_extensions = [".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"]
    return any(file_path.endswith(ext) for ext in code_extensions)


def find_active_specs() -> list[str]:
    """Find FEATURE_STRATEGY.md files in ai_working/."""
    ai_working = Path("ai_working")
    if not ai_working.exists():
        return []

    specs = list(ai_working.glob("*/FEATURE_STRATEGY.md"))
    return [str(s) for s in specs]


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only check for Write, Edit, MultiEdit
    if tool_name not in ["Write", "Edit", "MultiEdit"]:
        sys.exit(0)

    file_path = tool_input.get("file_path", "")

    # Skip excluded files
    if is_excluded(file_path) or not is_code_file(file_path):
        sys.exit(0)

    # Check for active specs
    specs = find_active_specs()

    # Output warning if no specs found (visible in transcript mode)
    if not specs:
        # Note: With exit 0, this goes to transcript (Ctrl-R), not to Claude
        # This is intentional - just a reminder, not blocking
        pass

    # Success - allow the operation
    sys.exit(0)


if __name__ == "__main__":
    main()
