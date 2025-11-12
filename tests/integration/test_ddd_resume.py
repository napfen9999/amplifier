"""Integration tests for DDD resume and conflict detection.

Tests resume behavior:
- Resume with no conflicts
- Resume with file conflicts
- Conflict detection and reporting
- Recovery recommendations

Philosophy: Test behavior (does resume work safely?), not code inspection.
"""

import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from tools.ddd_conflict_detector import check_conflicts
from tools.ddd_orchestrator import resume_session
from tools.ddd_orchestrator import start_session
from tools.ddd_state_manager import CheckpointData
from tools.ddd_state_manager import save_checkpoint


@pytest.fixture
def code_plan(tmp_path: Path) -> Path:
    """Create code_plan.md for testing."""
    plan_content = """# Code Implementation Plan

**Chunk 1.1: Module A** (~100 lines)
**File**: tools/mod_a.py
**Complexity**: simple

**Chunk 1.2: Module B** (~100 lines)
**File**: tools/mod_b.py
**Complexity**: simple
"""
    plan_path = tmp_path / "code_plan.md"
    plan_path.write_text(plan_content)
    return plan_path


@pytest.fixture
def mock_agents() -> list:
    """Return mock agent list."""
    from tools.ddd_agent_selector import AgentMetadata

    return [
        AgentMetadata(
            name="modular-builder",
            description="Builds self-contained modules",
            specializations=["modular"],
            location=Path("test"),
        )
    ]


@pytest.fixture
def setup_state_dir(tmp_path: Path, monkeypatch):
    """Setup isolated state directory for tests."""
    state_dir = tmp_path / "ai_working" / "ddd"
    state_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", state_dir)
    monkeypatch.setattr("tools.ddd_state_manager.SESSION_MANIFEST_PATH", state_dir / "session_manifest.json")
    monkeypatch.setattr("tools.ddd_state_manager.CHECKPOINTS_DIR", state_dir / "checkpoints")
    monkeypatch.setattr("tools.ddd_state_manager.IMPL_STATUS_PATH", state_dir / "impl_status.md")

    code_plan_path = tmp_path / "ai_working" / "ddd" / "code_plan.md"
    code_plan_path.parent.mkdir(parents=True, exist_ok=True)

    yield state_dir, code_plan_path


def test_resume_no_conflicts(code_plan: Path, mock_agents: list, setup_state_dir: tuple, monkeypatch):
    """Test: Resume succeeds when no conflicts.

    Scenario:
    1. Create checkpoint
    2. No file modifications
    3. resume_session() succeeds
    4. Continues execution
    """
    state_dir, code_plan_path = setup_state_dir
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    code_plan_path.write_text(code_plan.read_text())

    session = start_session(code_plan)

    checkpoint = CheckpointData(
        checkpoint_id=f"{session.session_id}_test_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        session_id=session.session_id,
        chunk="1.1",
        files_modified=["tools/mod_a.py"],
        test_status="passing",
        context={"tokens_used": 1000, "completed_chunks": ["1.1"]},
        next_actions=["Continue with chunk 1.2"],
    )
    save_checkpoint(checkpoint)

    mock_git_diff = Mock(return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""))
    monkeypatch.setattr("subprocess.run", mock_git_diff)

    resumed = resume_session()

    assert resumed.session_id == session.session_id
    assert resumed.tokens_used == 1000
    assert "1.1" in resumed.completed


def test_resume_with_modified_file_conflict(code_plan: Path, mock_agents: list, setup_state_dir: tuple, monkeypatch):
    """Test: Resume detects modified file conflict.

    Scenario:
    1. Create checkpoint listing file1.py
    2. Mock git to show file1.py modified after checkpoint
    3. resume_session() raises error
    4. Error message explains conflict
    """
    state_dir, code_plan_path = setup_state_dir
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    code_plan_path.write_text(code_plan.read_text())

    session = start_session(code_plan)

    checkpoint_time = datetime.now(UTC)
    checkpoint = CheckpointData(
        checkpoint_id=f"{session.session_id}_test_{checkpoint_time.strftime('%Y%m%d_%H%M%S')}",
        timestamp=checkpoint_time.isoformat().replace("+00:00", "Z"),
        session_id=session.session_id,
        chunk="1.1",
        files_modified=["tools/mod_a.py"],
        test_status="passing",
        context={"tokens_used": 1000, "completed_chunks": ["1.1"]},
        next_actions=["Continue with chunk 1.2"],
    )
    save_checkpoint(checkpoint)

    def mock_git_run(args, **kwargs):
        if "diff" in args and "--name-only" in args:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="tools/mod_a.py\n", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", mock_git_run)

    with pytest.raises(ValueError) as exc_info:
        resume_session()

    assert "conflicts detected" in str(exc_info.value).lower()


def test_resume_with_deleted_file_conflict(code_plan: Path, mock_agents: list, setup_state_dir: tuple, monkeypatch):
    """Test: Resume detects deleted file conflict.

    Scenario:
    1. Create checkpoint listing file1.py
    2. File is no longer present
    3. resume_session() detects deletion
    4. Reports conflict
    """
    state_dir, code_plan_path = setup_state_dir
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    code_plan_path.write_text(code_plan.read_text())

    session = start_session(code_plan)

    checkpoint = CheckpointData(
        checkpoint_id=f"{session.session_id}_test_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        session_id=session.session_id,
        chunk="1.1",
        files_modified=["tools/mod_a.py"],
        test_status="passing",
        context={"tokens_used": 1000, "completed_chunks": ["1.1"]},
        next_actions=["Continue with chunk 1.2"],
    )
    save_checkpoint(checkpoint)

    def mock_git_run(args, **kwargs):
        if "diff" in args:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    def mock_path_exists(self):
        return "mod_a.py" not in str(self)

    monkeypatch.setattr("subprocess.run", mock_git_run)
    monkeypatch.setattr("pathlib.Path.exists", mock_path_exists)

    conflict_report = check_conflicts(checkpoint)

    assert conflict_report.has_conflicts
    deleted_conflicts = [c for c in conflict_report.conflicts if c.conflict_type == "deleted"]
    assert len(deleted_conflicts) > 0


def test_resume_conflict_recommendations(code_plan: Path, mock_agents: list, setup_state_dir: tuple, monkeypatch):
    """Test: Conflict detection provides helpful recommendations.

    Verify: Recommendations include steps to resolve conflicts.
    """
    state_dir, code_plan_path = setup_state_dir
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    code_plan_path.write_text(code_plan.read_text())

    session = start_session(code_plan)

    checkpoint = CheckpointData(
        checkpoint_id=f"{session.session_id}_test_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        session_id=session.session_id,
        chunk="1.1",
        files_modified=["tools/mod_a.py", "tools/mod_b.py"],
        test_status="passing",
        context={"tokens_used": 1000, "completed_chunks": ["1.1"]},
        next_actions=["Continue with chunk 1.2"],
    )
    save_checkpoint(checkpoint)

    def mock_git_run(args, **kwargs):
        if "diff" in args and "--name-only" in args:
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="tools/mod_a.py\ntools/mod_b.py\n", stderr=""
            )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", mock_git_run)

    conflict_report = check_conflicts(checkpoint)

    assert conflict_report.has_conflicts
    assert len(conflict_report.recommendations) > 0

    recommendations_text = "\n".join(conflict_report.recommendations)
    assert "git" in recommendations_text.lower() or "commit" in recommendations_text.lower()


def test_checkpoint_no_conflicts_when_no_modifications(
    code_plan: Path, mock_agents: list, setup_state_dir: tuple, monkeypatch
):
    """Test: Checkpoint with no file modifications never triggers conflicts."""
    state_dir, code_plan_path = setup_state_dir
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    code_plan_path.write_text(code_plan.read_text())

    session = start_session(code_plan)

    checkpoint = CheckpointData(
        checkpoint_id=f"{session.session_id}_test_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        session_id=session.session_id,
        chunk="1.1",
        files_modified=[],
        test_status="passing",
        context={"tokens_used": 1000, "completed_chunks": ["1.1"]},
        next_actions=["Continue with chunk 1.2"],
    )
    save_checkpoint(checkpoint)

    mock_git_diff = Mock(return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""))
    monkeypatch.setattr("subprocess.run", mock_git_diff)

    conflict_report = check_conflicts(checkpoint)

    assert not conflict_report.has_conflicts
    assert len(conflict_report.conflicts) == 0


def test_resume_restores_complete_state(code_plan: Path, mock_agents: list, setup_state_dir: tuple, monkeypatch):
    """Test: Resume fully restores session state from checkpoint."""
    state_dir, code_plan_path = setup_state_dir
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    code_plan_path.write_text(code_plan.read_text())

    session = start_session(code_plan)
    original_session_id = session.session_id

    checkpoint = CheckpointData(
        checkpoint_id=f"{session.session_id}_test_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        session_id=session.session_id,
        chunk="1.1",
        files_modified=["tools/mod_a.py"],
        test_status="passing",
        context={"tokens_used": 5000, "completed_chunks": ["1.1"]},
        next_actions=["Continue with chunk 1.2"],
    )
    save_checkpoint(checkpoint)

    mock_git_diff = Mock(return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""))
    monkeypatch.setattr("subprocess.run", mock_git_diff)

    resumed = resume_session()

    assert resumed.session_id == original_session_id
    assert resumed.tokens_used == 5000
    assert resumed.completed == ["1.1"]
    assert len(resumed.chunks) == 2
