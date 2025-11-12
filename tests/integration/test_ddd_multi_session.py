"""Integration tests for multi-session DDD workflows.

Tests session handoff and resume:
- Token budget handoff
- Resume from checkpoint
- Multi-session completion
- State persistence

Philosophy: Test behavior (does handoff work?), not code inspection.
"""

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

from tools.ddd_orchestrator import execute_chunk
from tools.ddd_orchestrator import handoff_session
from tools.ddd_orchestrator import resume_session
from tools.ddd_orchestrator import start_session
from tools.ddd_state_manager import CheckpointData
from tools.ddd_state_manager import load_session_manifest
from tools.ddd_state_manager import save_checkpoint
from tools.ddd_state_manager import save_session_manifest


@pytest.fixture
def code_plan_for_handoff(tmp_path: Path) -> Path:
    """Create code_plan.md with multiple chunks for handoff testing."""
    plan_content = """# Code Implementation Plan

**Chunk 1.1: Module A** (~100 lines)
**File**: tools/mod_a.py
**Complexity**: simple

**Chunk 1.2: Module B** (~100 lines)
**File**: tools/mod_b.py
**Complexity**: simple

**Chunk 1.3: Module C** (~100 lines)
**File**: tools/mod_c.py
**Complexity**: simple

**Chunk 2.1: Integration** (~150 lines)
**File**: tools/integration.py
**Dependencies**: Chunk 1.1, Chunk 1.2, Chunk 1.3
**Complexity**: medium
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


def test_token_budget_handoff(code_plan_for_handoff: Path, mock_agents: list, setup_state_dir: tuple, monkeypatch):
    """Test: Session hands off when budget low.

    Scenario:
    1. Mock tokens_used to approach threshold
    2. execute_chunk() returns {"action": "handoff"}
    3. Verify: handoff checkpoint created
    4. Verify: session status = "handoff"
    """
    state_dir, _ = setup_state_dir
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    session = start_session(code_plan_for_handoff)

    session.tokens_used = 150000

    chunk = session.chunks[0]
    result = execute_chunk(chunk, session)

    assert result["action"] == "handoff"
    assert "Budget exhaustion" in result["reason"]


def test_resume_after_handoff(code_plan_for_handoff: Path, mock_agents: list, setup_state_dir: tuple, monkeypatch):
    """Test: Resume from handoff checkpoint.

    Scenario:
    1. Create checkpoint with handoff status
    2. Call resume_session()
    3. Verify: Resumes at correct chunk
    4. Verify: Tokens_used restored
    5. Verify: Continues from where left off
    """
    state_dir, code_plan_path = setup_state_dir
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    code_plan_path.write_text(code_plan_for_handoff.read_text())

    session = start_session(code_plan_for_handoff)

    execute_chunk(session.chunks[0], session)
    execute_chunk(session.chunks[1], session)

    tokens_before_handoff = session.tokens_used

    manifest = load_session_manifest()
    session_record = manifest.sessions[0]
    session_record.status = "handoff"
    save_session_manifest(manifest)

    checkpoint = CheckpointData(
        checkpoint_id=f"{session.session_id}_handoff_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        session_id=session.session_id,
        chunk="1.2",
        files_modified=[],
        test_status="handoff",
        context={"tokens_used": tokens_before_handoff, "completed_chunks": ["1.1", "1.2"]},
        next_actions=["Resume session"],
    )
    save_checkpoint(checkpoint)

    resumed = resume_session()

    assert resumed.session_id == session.session_id
    assert resumed.tokens_used == tokens_before_handoff
    assert "1.1" in resumed.completed
    assert "1.2" in resumed.completed
    assert len(resumed.completed) == 2


def test_multi_session_complete_workflow(
    code_plan_for_handoff: Path, mock_agents: list, setup_state_dir: tuple, monkeypatch
):
    """Test: Session 1 → Handoff → Session 2 → Complete.

    Full workflow:
    - Session 1: Completes chunks 1.1, 1.2, hands off
    - Session 2: Resumes, completes 1.3, 2.1, done
    - Verify: Both sessions logged in manifest
    - Verify: All chunks marked complete
    """
    state_dir, code_plan_path = setup_state_dir
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    code_plan_path.write_text(code_plan_for_handoff.read_text())

    session1 = start_session(code_plan_for_handoff)
    session1_id = session1.session_id

    execute_chunk(session1.chunks[0], session1)
    execute_chunk(session1.chunks[1], session1)

    manifest = load_session_manifest()
    session_record = manifest.sessions[0]
    session_record.status = "handoff"
    save_session_manifest(manifest)

    checkpoint = CheckpointData(
        checkpoint_id=f"{session1.session_id}_handoff_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        session_id=session1.session_id,
        chunk="1.2",
        files_modified=[],
        test_status="handoff",
        context={"tokens_used": session1.tokens_used, "completed_chunks": ["1.1", "1.2"]},
        next_actions=["Resume session"],
    )
    save_checkpoint(checkpoint)

    session2 = resume_session()
    assert session2.session_id == session1_id

    execute_chunk(session2.chunks[2], session2)
    execute_chunk(session2.chunks[3], session2)

    manifest = load_session_manifest()
    assert len(manifest.sessions) == 1
    final_session = manifest.sessions[0]

    assert len(final_session.chunks_completed) == 4
    assert "1.1" in final_session.chunks_completed
    assert "1.2" in final_session.chunks_completed
    assert "1.3" in final_session.chunks_completed
    assert "2.1" in final_session.chunks_completed


def test_handoff_preserves_state(code_plan_for_handoff: Path, mock_agents: list, setup_state_dir: tuple, monkeypatch):
    """Test: Handoff checkpoint preserves complete session state."""
    state_dir, _ = setup_state_dir
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    session = start_session(code_plan_for_handoff)

    execute_chunk(session.chunks[0], session)

    completed = session.completed.copy()

    session.tokens_used = 150000

    with pytest.raises(SystemExit):
        handoff_session(session, "Test handoff")

    checkpoints_dir = state_dir / "checkpoints"
    checkpoint_files = list(checkpoints_dir.glob("*handoff*.json"))
    assert len(checkpoint_files) > 0

    latest_checkpoint = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
    with open(latest_checkpoint) as f:
        checkpoint_data = json.load(f)

    assert checkpoint_data["session_id"] == session.session_id
    assert checkpoint_data["context"]["tokens_used"] == 150000
    assert checkpoint_data["context"]["completed_chunks"] == completed


def test_multiple_handoffs_same_session(
    code_plan_for_handoff: Path, mock_agents: list, setup_state_dir: tuple, monkeypatch
):
    """Test: Session can handoff multiple times and resume correctly."""
    state_dir, code_plan_path = setup_state_dir
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    code_plan_path.write_text(code_plan_for_handoff.read_text())

    session = start_session(code_plan_for_handoff)
    original_session_id = session.session_id

    execute_chunk(session.chunks[0], session)

    manifest = load_session_manifest()
    session_record = manifest.sessions[0]
    session_record.status = "handoff"
    save_session_manifest(manifest)

    checkpoint1 = CheckpointData(
        checkpoint_id=f"{session.session_id}_handoff1_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        session_id=session.session_id,
        chunk="1.1",
        files_modified=[],
        test_status="handoff",
        context={"tokens_used": session.tokens_used, "completed_chunks": ["1.1"]},
        next_actions=["Resume session"],
    )
    save_checkpoint(checkpoint1)

    resumed1 = resume_session()
    assert resumed1.session_id == original_session_id
    assert len(resumed1.completed) == 1

    execute_chunk(resumed1.chunks[1], resumed1)

    manifest = load_session_manifest()
    session_record = manifest.sessions[0]
    session_record.status = "handoff"
    save_session_manifest(manifest)

    checkpoint2 = CheckpointData(
        checkpoint_id=f"{resumed1.session_id}_handoff2_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        session_id=resumed1.session_id,
        chunk="1.2",
        files_modified=[],
        test_status="handoff",
        context={"tokens_used": resumed1.tokens_used, "completed_chunks": ["1.1", "1.2"]},
        next_actions=["Resume session"],
    )
    save_checkpoint(checkpoint2)

    resumed2 = resume_session()
    assert resumed2.session_id == original_session_id
    assert len(resumed2.completed) == 2
    assert "1.1" in resumed2.completed
    assert "1.2" in resumed2.completed
