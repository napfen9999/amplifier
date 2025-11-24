"""DDD State Manager - All state file I/O operations for session-aware DDD workflow.

This module handles reading/writing state files for the DDD implementation workflow:
- Session manifests tracking sessions and chunk completion
- Checkpoints for handoff between sessions
- Implementation status markdown logs

Philosophy: Ruthless simplicity - just file I/O, no caching, clear errors.
"""

import json
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

STATE_DIR = Path("ai_working/ddd")
SESSION_MANIFEST_PATH = STATE_DIR / "session_manifest.json"
CHECKPOINTS_DIR = STATE_DIR / "checkpoints"
IMPL_STATUS_PATH = STATE_DIR / "impl_status.md"


@dataclass
class Session:
    """Single implementation session tracking."""

    session_id: str
    started: str
    ended: str | None
    chunks_completed: list[str]
    tokens_used: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        return cls(**data)


@dataclass
class SessionManifest:
    """Top-level manifest tracking all sessions and overall progress."""

    sessions: list[Session] = field(default_factory=list)
    total_chunks: int = 0
    completed_chunks: list[str] = field(default_factory=list)
    current_session: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessions": [s.to_dict() for s in self.sessions],
            "total_chunks": self.total_chunks,
            "completed_chunks": self.completed_chunks,
            "current_session": self.current_session,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionManifest":
        sessions = [Session.from_dict(s) for s in data.get("sessions", [])]
        return cls(
            sessions=sessions,
            total_chunks=data.get("total_chunks", 0),
            completed_chunks=data.get("completed_chunks", []),
            current_session=data.get("current_session"),
        )


@dataclass
class CheckpointData:
    """Checkpoint data for handoff between sessions."""

    checkpoint_id: str
    timestamp: str
    session_id: str
    chunk: str
    files_modified: list[str]
    test_status: str
    context: dict[str, Any]
    next_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CheckpointData":
        return cls(**data)


def load_session_manifest() -> SessionManifest:
    """Load session manifest from disk, return default if doesn't exist."""
    if not SESSION_MANIFEST_PATH.exists():
        return SessionManifest()

    try:
        with open(SESSION_MANIFEST_PATH) as f:
            data = json.load(f)
        return SessionManifest.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ValueError(f"Corrupted session manifest at {SESSION_MANIFEST_PATH}: {e}") from e


def save_session_manifest(manifest: SessionManifest) -> None:
    """Save session manifest to disk, create directory if needed."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    with open(SESSION_MANIFEST_PATH, "w") as f:
        json.dump(manifest.to_dict(), f, indent=2)


def load_checkpoint(checkpoint_id: str) -> CheckpointData:
    """Load checkpoint from disk."""
    checkpoint_path = CHECKPOINTS_DIR / f"{checkpoint_id}.json"

    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    try:
        with open(checkpoint_path) as f:
            data = json.load(f)
        return CheckpointData.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ValueError(f"Corrupted checkpoint at {checkpoint_path}: {e}") from e


def save_checkpoint(checkpoint: CheckpointData) -> None:
    """Save checkpoint to disk, create directory if needed."""
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

    checkpoint_path = CHECKPOINTS_DIR / f"{checkpoint.checkpoint_id}.json"
    with open(checkpoint_path, "w") as f:
        json.dump(checkpoint.to_dict(), f, indent=2)


def get_latest_checkpoint() -> CheckpointData | None:
    """Find most recent checkpoint file, return None if none exist."""
    if not CHECKPOINTS_DIR.exists():
        return None

    checkpoint_files = list(CHECKPOINTS_DIR.glob("*.json"))
    if not checkpoint_files:
        return None

    latest_file = max(checkpoint_files, key=lambda p: p.stat().st_mtime)

    try:
        with open(latest_file) as f:
            data = json.load(f)
        return CheckpointData.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise ValueError(f"Corrupted checkpoint at {latest_file}: {e}") from e


def update_impl_status(session_id: str, chunk: str, status: str) -> None:
    """Append implementation status to markdown log.

    Format: - [status] Chunk X.Y: [title] ([timestamp])
    Groups by session with headers.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    status_line = f"- [{status}] Chunk {chunk} ({timestamp})\n"

    if IMPL_STATUS_PATH.exists():
        content = IMPL_STATUS_PATH.read_text()

        session_header = f"## Session {session_id}\n"
        if session_header in content:
            lines = content.split("\n")
            insert_idx = None
            for i, line in enumerate(lines):
                if line == session_header.strip():
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith("## Session"):
                            insert_idx = j
                            break
                    if insert_idx is None:
                        insert_idx = len(lines)
                    break

            if insert_idx is not None:
                lines.insert(insert_idx, status_line.rstrip())
                content = "\n".join(lines) + "\n"
        else:
            content += f"\n{session_header}{status_line}"

        IMPL_STATUS_PATH.write_text(content)
    else:
        content = f"# DDD Implementation Status\n\n## Session {session_id}\n{status_line}"
        IMPL_STATUS_PATH.write_text(content)
