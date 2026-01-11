#!/usr/bin/env python3
"""
PostToolUse Hook: Validates test coverage after code changes.

Triggers on: Write, Edit, MultiEdit
Behavior: Provides feedback to Claude via additionalContext

Checks:
1. Does a test file exist for the modified source file?
2. Has the file been documented in relevant specs?
"""

import json
import sys
from pathlib import Path


def is_source_file(file_path: str) -> bool:
    """Check if file is a source code file (not test, not config)."""
    # Must be code file
    code_extensions = [".py", ".ts", ".tsx", ".js", ".jsx"]
    if not any(file_path.endswith(ext) for ext in code_extensions):
        return False

    # Must not be test file
    test_patterns = ["_test.", ".test.", ".spec.", "/tests/", "/test_"]
    if any(pattern in file_path for pattern in test_patterns):
        return False

    # Must not be config/docs
    excluded_patterns = [
        "/docs/",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        "/.claude/",
        "/ai_working/",
        "/ai_context/",
    ]
    return not any(pattern in file_path for pattern in excluded_patterns)


def find_test_file(source_path: str) -> str | None:
    """Find test file for a source file."""
    path = Path(source_path)
    stem = path.stem
    suffix = path.suffix

    # Common test file patterns
    patterns = [
        # Same directory patterns
        path.parent / f"{stem}_test{suffix}",
        path.parent / f"test_{stem}{suffix}",
        path.parent / f"{stem}.test{suffix}",
        path.parent / f"{stem}.spec{suffix}",
    ]

    # Tests directory patterns
    if "src" in str(path):
        tests_base = Path(str(path).replace("/src/", "/tests/"))
        patterns.extend(
            [
                tests_base.parent / f"test_{stem}{suffix}",
                tests_base.parent / f"{stem}_test{suffix}",
            ]
        )

    # solver_api specific patterns
    if "solver_api" in str(path):
        solver_tests = Path("solver_api/tests")
        patterns.extend(
            [
                solver_tests / f"test_{stem}{suffix}",
                solver_tests / f"{stem}_test{suffix}",
            ]
        )

    for pattern in patterns:
        if pattern.exists():
            return str(pattern)

    return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    # tool_response available but not needed for test file check

    # Only check for Write, Edit, MultiEdit
    if tool_name not in ["Write", "Edit", "MultiEdit"]:
        sys.exit(0)

    file_path = tool_input.get("file_path", "")

    # Only check source files
    if not is_source_file(file_path):
        sys.exit(0)

    # Check for test file
    test_file = find_test_file(file_path)

    if not test_file:
        # Provide context to Claude via JSON output
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"Note: No test file found for {file_path}. Consider adding tests.",
            }
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
