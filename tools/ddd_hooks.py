"""DDD Hooks - Hook handlers for PostToolUse:Edit and PreCompact events.

These hooks integrate with Claude Code's hook system to automatically track
file modifications and create emergency checkpoints during DDD Phase 4.

Hook handlers are defensive - they must never crash or delay the main workflow.
Only active when DDD session is detected (ai_working/ddd/impl_status.md exists).

Philosophy: Ruthless simplicity - direct file I/O, no complex state management.
"""

import sys
import uuid
from datetime import UTC
from datetime import datetime
from typing import Any

from tools.ddd_state_manager import IMPL_STATUS_PATH
from tools.ddd_state_manager import CheckpointData
from tools.ddd_state_manager import save_checkpoint


def is_ddd_session_active() -> bool:
    """Check if DDD session is currently active.

    Detection strategy:
    - Check if ai_working/ddd/impl_status.md exists
    - If exists and not empty → DDD session active

    Returns: True if DDD session active, False otherwise

    Why this matters:
    - Hooks run for ALL Claude Code sessions
    - We only want to log when DDD Phase 4 is running
    - Prevents spam in non-DDD sessions
    """
    if not IMPL_STATUS_PATH.exists():
        return False

    try:
        content = IMPL_STATUS_PATH.read_text().strip()
        return len(content) > 0
    except Exception:
        return False


def handle_post_tool_use_edit(file_path: str) -> None:
    """Handle PostToolUse event for Edit/Write tools.

    Called automatically by hook_post_tool_use.py when Edit or Write tool used.

    Action: Log file modification to impl_status.md

    Args:
        file_path: Path to file that was edited/written

    Logic:
    1. Check if DDD session active (is_ddd_session_active())
    2. If not active → return silently
    3. If active → append modification to impl_status.md

    Format in impl_status.md:
    "- [MODIFIED] {file_path} ({timestamp})"

    Why this matters:
    - Automatically tracks which files were modified
    - Provides audit trail for debugging
    - Enables conflict detection on resume
    """
    if not is_ddd_session_active():
        return

    try:
        timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        status_line = f"- [MODIFIED] {file_path} ({timestamp})\n"

        if IMPL_STATUS_PATH.exists():
            content = IMPL_STATUS_PATH.read_text()

            lines = content.split("\n")
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].startswith("## Session"):
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith("## Session"):
                            lines.insert(j, status_line.rstrip())
                            break
                    else:
                        lines.append(status_line.rstrip())
                    break
            else:
                lines.append(status_line.rstrip())

            IMPL_STATUS_PATH.write_text("\n".join(lines) + "\n" if lines[-1] else "\n".join(lines))
        else:
            IMPL_STATUS_PATH.write_text(f"# DDD Implementation Status\n\n{status_line}")
    except Exception:
        pass


def handle_pre_compact() -> dict:
    """Handle PreCompact event - emergency checkpoint before compaction.

    Called automatically by hook_precompact.py when Claude is about to compact context.

    Action: Create emergency checkpoint if DDD session active

    Returns: Hook response dict with metadata
    {
        "continue": True,  # Always continue compaction
        "suppressOutput": True,  # Don't show checkpoint message to user
        "metadata": {
            "checkpoint_created": True/False,
            "checkpoint_id": str | None
        }
    }

    Logic:
    1. Check if DDD session active
    2. If not active → return {"continue": True, "metadata": {"checkpoint_created": False}}
    3. If active:
       a. Determine current chunk (read from impl_status.md last entry)
       b. Create CheckpointData with emergency=True flag
       c. save_checkpoint()
       d. Return success metadata

    Why this matters:
    - Compaction erases context → need checkpoint first
    - Emergency checkpoints allow session recovery
    - User can resume from last known good state
    """
    if not is_ddd_session_active():
        return {"continue": True, "suppressOutput": True, "metadata": {"checkpoint_created": False}}

    try:
        session_info = get_current_session_info()

        if not session_info:
            return {"continue": True, "suppressOutput": True, "metadata": {"checkpoint_created": False}}

        checkpoint_id = f"emergency_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        checkpoint = CheckpointData(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            session_id=session_info.get("session_id", "unknown"),
            chunk=session_info.get("last_chunk", "unknown"),
            files_modified=session_info.get("files_modified", []),
            test_status="unknown",
            context={"emergency": True, "reason": "pre_compact"},
            next_actions=["Resume from checkpoint after compaction"],
        )

        save_checkpoint(checkpoint)

        return {
            "continue": True,
            "suppressOutput": True,
            "metadata": {"checkpoint_created": True, "checkpoint_id": checkpoint_id},
        }
    except Exception as e:
        print(f"Warning: Failed to create emergency checkpoint: {e}", file=sys.stderr)
        return {"continue": True, "suppressOutput": True, "metadata": {"checkpoint_created": False, "error": str(e)}}


def get_current_session_info() -> dict[str, Any]:
    """Get current session information from impl_status.md.

    Parses impl_status.md to extract:
    - Current session ID (from last ## Session header)
    - Last chunk worked on (from last entry)
    - Files modified in session

    Returns: Dict with session info or empty dict if no active session
    {
        "session_id": str,
        "last_chunk": str,  # e.g., "1.2"
        "files_modified": list[str]
    }

    Parsing strategy:
    - Read impl_status.md backwards
    - Find last ## Session {id} header → that's current session
    - Find last - [status] entry → that's last chunk
    - Collect all file paths from [MODIFIED] entries in this session
    """
    if not IMPL_STATUS_PATH.exists():
        return {}

    try:
        content = IMPL_STATUS_PATH.read_text()
        lines = content.split("\n")

        session_id = None
        last_chunk = None
        files_modified = []
        in_current_session = False

        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()

            if line.startswith("## Session"):
                if session_id is None:
                    parts = line.split()
                    if len(parts) >= 3:
                        session_id = parts[2]
                        in_current_session = True
                else:
                    break

            if in_current_session and line.startswith("- ["):
                if "Chunk" in line and last_chunk is None:
                    chunk_parts = line.split("Chunk")
                    if len(chunk_parts) > 1:
                        chunk_str = chunk_parts[1].strip().split()[0]
                        last_chunk = chunk_str

                if "[MODIFIED]" in line:
                    file_path_parts = line.split("[MODIFIED]")
                    if len(file_path_parts) > 1:
                        file_path = file_path_parts[1].split("(")[0].strip()
                        if file_path:
                            files_modified.append(file_path)

        if session_id:
            return {"session_id": session_id, "last_chunk": last_chunk or "unknown", "files_modified": files_modified}

        return {}
    except Exception:
        return {}
