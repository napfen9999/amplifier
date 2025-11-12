"""DDD Conflict Detector - Detect state conflicts when resuming sessions.

This module checks for conflicts between checkpoint state and current filesystem/git state.
Part of Layer 2 (Intelligence) in the DDD implementation.

Philosophy:
- Ruthless simplicity: Use git directly, no complex diff libraries
- Graceful degradation: Work without git (return empty conflicts)
- Conservative detection: Better to warn unnecessarily than miss conflicts
- Clear recommendations: Human-readable next steps
"""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tools.ddd_state_manager import CheckpointData


@dataclass
class FileConflict:
    """Represents a conflict between checkpoint state and current state."""

    file_path: str
    checkpoint_timestamp: str
    last_modified: str
    conflict_type: str  # "modified" | "deleted" | "created"


@dataclass
class ConflictReport:
    """Report of all conflicts found when checking checkpoint state."""

    has_conflicts: bool
    conflicts: list[FileConflict]
    recommendations: list[str]


def check_conflicts(checkpoint: CheckpointData) -> ConflictReport:
    """Check for conflicts when resuming from checkpoint.

    Checks:
    1. Files listed in checkpoint.files_modified still exist
    2. Files haven't been modified since checkpoint timestamp
    3. Git status shows no unexpected changes

    Args:
        checkpoint: CheckpointData from session_manifest

    Returns:
        ConflictReport with findings and recommendations

    Logic:
    - For each file in checkpoint.files_modified:
      - Check if file exists (deleted = conflict)
      - Check git log for modifications after checkpoint.timestamp
      - If modified, add to conflicts list
    - Generate recommendations based on conflicts found
    """
    conflicts: list[FileConflict] = []
    checkpoint_dt = datetime.fromisoformat(checkpoint.timestamp)

    for file_path in checkpoint.files_modified:
        path = Path(file_path)

        if not path.exists():
            conflicts.append(
                FileConflict(
                    file_path=file_path,
                    checkpoint_timestamp=checkpoint.timestamp,
                    last_modified="N/A",
                    conflict_type="deleted",
                )
            )
            continue

        last_modified = get_git_last_modified(file_path)
        if last_modified and last_modified > checkpoint_dt:
            conflicts.append(
                FileConflict(
                    file_path=file_path,
                    checkpoint_timestamp=checkpoint.timestamp,
                    last_modified=last_modified.isoformat(),
                    conflict_type="modified",
                )
            )

    created_files = _check_created_files(checkpoint)
    conflicts.extend(created_files)

    recommendations = _generate_recommendations(conflicts)

    return ConflictReport(has_conflicts=len(conflicts) > 0, conflicts=conflicts, recommendations=recommendations)


def check_file_modifications(files: list[str], since: datetime) -> list[FileConflict]:
    """Check if files were modified after given timestamp using git.

    Uses git log to check file modification history:
    git log --since="<timestamp>" --name-only --pretty=format: -- <file>

    Args:
        files: List of file paths to check
        since: Timestamp to check modifications after

    Returns:
        List of FileConflict objects for modified files

    Git edge cases:
    - File not in git: Skip silently (temporary files OK)
    - Git not available: Return empty list with warning
    - Untracked files: Ignore (might be generated during implementation)
    """
    conflicts: list[FileConflict] = []

    if not _is_git_available():
        return conflicts

    for file_path in files:
        last_modified = get_git_last_modified(file_path)
        if last_modified and last_modified > since:
            conflicts.append(
                FileConflict(
                    file_path=file_path,
                    checkpoint_timestamp=since.isoformat(),
                    last_modified=last_modified.isoformat(),
                    conflict_type="modified",
                )
            )

    return conflicts


def get_git_last_modified(file_path: str) -> datetime | None:
    """Get last git commit timestamp for file.

    Uses: git log -1 --format=%aI -- <file>

    Args:
        file_path: Path to file to check

    Returns:
        datetime of last commit, or None if file not in git
    """
    if not _is_git_available():
        return None

    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%aI", "--", file_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return None

        timestamp_str = result.stdout.strip()
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

    except (subprocess.TimeoutExpired, ValueError, OSError):
        return None


def _is_git_available() -> bool:
    """Check if git is available in the system."""
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, check=False, timeout=2)
        return result.returncode == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False


def _check_created_files(checkpoint: CheckpointData) -> list[FileConflict]:
    """Check for files created after checkpoint that might conflict.

    Uses git status to find untracked or newly committed files that weren't
    in the checkpoint's files_modified list.

    Args:
        checkpoint: CheckpointData to check against

    Returns:
        List of FileConflict objects for newly created files
    """
    if not _is_git_available():
        return []

    conflicts: list[FileConflict] = []
    checkpoint_dt = datetime.fromisoformat(checkpoint.timestamp)

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=False, timeout=5
        )

        if result.returncode != 0:
            return conflicts

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            status = line[:2]
            file_path = line[3:].strip()

            if (status.startswith("??") or status.startswith("A")) and file_path not in checkpoint.files_modified:
                last_modified = get_git_last_modified(file_path)
                if not last_modified or last_modified > checkpoint_dt:
                    conflicts.append(
                        FileConflict(
                            file_path=file_path,
                            checkpoint_timestamp=checkpoint.timestamp,
                            last_modified=last_modified.isoformat() if last_modified else datetime.now().isoformat(),
                            conflict_type="created",
                        )
                    )

    except (subprocess.TimeoutExpired, OSError):
        pass

    return conflicts


def _generate_recommendations(conflicts: list[FileConflict]) -> list[str]:
    """Generate human-readable recommendations based on conflicts found.

    Args:
        conflicts: List of FileConflict objects

    Returns:
        List of recommendation strings
    """
    if not conflicts:
        return ["No conflicts detected - safe to resume"]

    recommendations: list[str] = []

    modified_files = [c for c in conflicts if c.conflict_type == "modified"]
    deleted_files = [c for c in conflicts if c.conflict_type == "deleted"]
    created_files = [c for c in conflicts if c.conflict_type == "created"]

    if modified_files:
        recommendations.append(
            f"{len(modified_files)} file(s) were modified externally - review changes before continuing"
        )
        for conflict in modified_files[:3]:
            recommendations.append(f"  - {conflict.file_path} modified at {conflict.last_modified}")
        if len(modified_files) > 3:
            recommendations.append(f"  ... and {len(modified_files) - 3} more")

    if deleted_files:
        recommendations.append(f"{len(deleted_files)} file(s) were deleted - restore from checkpoint or skip chunk")
        for conflict in deleted_files[:3]:
            recommendations.append(f"  - {conflict.file_path}")
        if len(deleted_files) > 3:
            recommendations.append(f"  ... and {len(deleted_files) - 3} more")

    if created_files:
        recommendations.append(
            f"{len(created_files)} file(s) were created externally - may conflict with planned changes"
        )
        for conflict in created_files[:3]:
            recommendations.append(f"  - {conflict.file_path}")
        if len(created_files) > 3:
            recommendations.append(f"  ... and {len(created_files) - 3} more")

    recommendations.append("Resolve conflicts before resuming or use --force to override")

    return recommendations
