#!/usr/bin/env python3
"""
Stop Hook: Validates documentation before Claude stops.

Triggers on: When Claude tries to stop
Behavior: Warning only (exit 0), provides reminder

Checks:
1. Are there uncommitted changes?
2. Are modified files documented?
"""

import json
import subprocess
import sys


def get_modified_files() -> list[str]:
    """Get list of modified files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().split("\n") if f]
    except Exception:
        pass
    return []


def get_staged_files() -> list[str]:
    """Get list of staged files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().split("\n") if f]
    except Exception:
        pass
    return []


def is_code_file(file_path: str) -> bool:
    """Check if file is a source code file."""
    code_extensions = [".py", ".ts", ".tsx", ".js", ".jsx"]
    return any(file_path.endswith(ext) for ext in code_extensions)


def is_test_or_doc(file_path: str) -> bool:
    """Check if file is a test or documentation file."""
    patterns = [
        "_test.",
        ".test.",
        ".spec.",
        "/tests/",
        "/test_",
        ".md",
        "/docs/",
        "/ai_context/",
        "/ai_working/",
    ]
    return any(pattern in file_path for pattern in patterns)


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    # Check if stop hook is already active (prevent infinite loops)
    stop_hook_active = input_data.get("stop_hook_active", False)
    if stop_hook_active:
        sys.exit(0)

    # Get all changed files
    modified = get_modified_files()
    staged = get_staged_files()
    all_changed = list(set(modified + staged))

    # Filter to code files (not tests/docs)
    code_files = [f for f in all_changed if is_code_file(f) and not is_test_or_doc(f)]

    if code_files:
        # Check if there are corresponding test changes
        test_changes = [f for f in all_changed if is_test_or_doc(f)]

        # Output is shown in transcript mode (Ctrl-R)
        # For Stop hooks, we don't block, just remind
        if not test_changes and len(code_files) > 0:
            reminder = f"Reminder: {len(code_files)} code file(s) modified. Consider adding/updating tests."
            # This goes to stderr for visibility but doesn't block (exit 0)
            print(reminder, file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
