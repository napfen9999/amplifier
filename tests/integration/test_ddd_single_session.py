"""Integration tests for single-session DDD workflows.

Tests complete workflow execution:
- Start session
- Execute all chunks
- Complete successfully
- Checkpoint creation
- Status tracking

Philosophy: Test behavior (does it work?), not code inspection.
"""

import json
from pathlib import Path

import pytest

from tools.ddd_orchestrator import execute_chunk
from tools.ddd_orchestrator import start_session
from tools.ddd_state_manager import load_session_manifest


@pytest.fixture
def minimal_code_plan(tmp_path: Path) -> Path:
    """Create minimal code_plan.md for testing."""
    plan_content = """# Code Implementation Plan

## Layer 1: Foundation

**Chunk 1.1: Test Module A** (~100 lines)
**File**: tools/test_a.py
**Complexity**: simple

Simple test module A.

**Chunk 1.2: Test Module B** (~100 lines)
**File**: tools/test_b.py
**Complexity**: simple

Simple test module B.

## Layer 2: Integration

**Chunk 2.1: Integration Module** (~150 lines)
**File**: tools/integration.py
**Dependencies**: Chunk 1.1, Chunk 1.2
**Complexity**: medium

Integration module combining A and B.
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

    yield state_dir


def test_complete_single_session(minimal_code_plan: Path, mock_agents: list, setup_state_dir: Path, monkeypatch):
    """Test: Start session → Execute all chunks → Complete successfully.

    Scenario:
    1. Create minimal code_plan.md with 3 simple chunks
    2. start_session()
    3. Loop: execute_chunk() for all 3
    4. Verify: session status updates
    5. Verify: checkpoints created for each chunk
    6. Verify: impl_status.md contains all chunks
    """
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    session = start_session(minimal_code_plan)

    assert session.session_id is not None
    assert len(session.chunks) == 3
    assert len(session.completed) == 0
    assert session.tokens_used == 0

    manifest_path = setup_state_dir / "session_manifest.json"
    assert manifest_path.exists()

    manifest = load_session_manifest()
    assert len(manifest.sessions) == 1
    assert manifest.sessions[0].session_id == session.session_id
    assert manifest.sessions[0].status == "active"

    for chunk in session.chunks:
        result = execute_chunk(chunk, session)
        assert result["action"] == "completed"
        assert result["chunk_id"] == chunk.id

    manifest = load_session_manifest()
    session_record = manifest.sessions[0]
    assert len(session_record.chunks_completed) == 3
    assert session_record.tokens_used > 0

    checkpoints_dir = setup_state_dir / "checkpoints"
    checkpoint_files = list(checkpoints_dir.glob("*.json"))
    assert len(checkpoint_files) == 3

    impl_status_path = setup_state_dir / "impl_status.md"
    assert impl_status_path.exists()
    status_content = impl_status_path.read_text()
    assert "1.1" in status_content
    assert "1.2" in status_content
    assert "2.1" in status_content
    assert "COMPLETED" in status_content


def test_chunk_dependency_resolution(minimal_code_plan: Path, mock_agents: list, setup_state_dir: Path, monkeypatch):
    """Test: Chunks execute in dependency order.

    Scenario:
    - Chunk 2.1 depends on 1.1, 1.2
    - Chunk 1.1, 1.2 have no dependencies
    - Verify: 1.1 and 1.2 execute before 2.1
    - Verify: 2.1 doesn't start until dependencies done
    """
    from tools.ddd_chunk_analyzer import get_next_chunk
    from tools.ddd_chunk_analyzer import parse_code_plan

    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    chunks = parse_code_plan(minimal_code_plan)

    assert chunks[0].id == "1.1"
    assert chunks[0].dependencies == []

    assert chunks[1].id == "1.2"
    assert chunks[1].dependencies == []

    assert chunks[2].id == "2.1"
    assert "1.1" in chunks[2].dependencies
    assert "1.2" in chunks[2].dependencies

    next_chunk = get_next_chunk(chunks, [])
    assert next_chunk is not None
    assert next_chunk.id in ["1.1", "1.2"]

    next_chunk = get_next_chunk(chunks, ["1.1"])
    assert next_chunk is not None
    assert next_chunk.id == "1.2"

    next_chunk = get_next_chunk(chunks, ["1.1", "1.2"])
    assert next_chunk is not None
    assert next_chunk.id == "2.1"

    next_chunk = get_next_chunk(chunks, ["1.1"])
    assert next_chunk is not None
    assert next_chunk.id != "2.1"


def test_checkpoint_creation_per_chunk(minimal_code_plan: Path, mock_agents: list, setup_state_dir: Path, monkeypatch):
    """Test: Checkpoint created after each chunk completion.

    Verify checkpoint files exist with correct metadata.
    """
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    session = start_session(minimal_code_plan)
    checkpoints_dir = setup_state_dir / "checkpoints"

    for i, chunk in enumerate(session.chunks):
        result = execute_chunk(chunk, session)
        assert result["action"] == "completed"

        checkpoint_files = list(checkpoints_dir.glob("*.json"))
        assert len(checkpoint_files) == i + 1

        latest_checkpoint = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
        with open(latest_checkpoint) as f:
            checkpoint_data = json.load(f)

        assert checkpoint_data["session_id"] == session.session_id
        assert checkpoint_data["chunk"] == chunk.id
        assert "tokens_used" in checkpoint_data["context"]
        assert "completed_chunks" in checkpoint_data["context"]


def test_session_tracks_token_usage(minimal_code_plan: Path, mock_agents: list, setup_state_dir: Path, monkeypatch):
    """Test: Token usage accumulates correctly across chunks."""
    monkeypatch.setattr("tools.ddd_agent_selector.discover_agents", lambda: mock_agents)

    session = start_session(minimal_code_plan)
    assert session.tokens_used == 0

    initial_tokens = 0
    for chunk in session.chunks:
        result = execute_chunk(chunk, session)
        assert result["action"] == "completed"
        assert session.tokens_used > initial_tokens
        initial_tokens = session.tokens_used

    manifest = load_session_manifest()
    session_record = manifest.sessions[0]
    assert session_record.tokens_used == session.tokens_used
    assert session_record.tokens_used > 0
