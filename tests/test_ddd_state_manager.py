"""Tests for DDD State Manager - All state file I/O operations.

Tests cover:
- Data model serialization/deserialization
- Session manifest CRUD operations
- Checkpoint CRUD operations
- Implementation status markdown updates
- Error handling (corrupted JSON, missing files)
- Directory creation
- Edge cases (empty lists, None values)
"""

import json
import time

import pytest

from tools.ddd_state_manager import CheckpointData
from tools.ddd_state_manager import Session
from tools.ddd_state_manager import SessionManifest
from tools.ddd_state_manager import get_latest_checkpoint
from tools.ddd_state_manager import load_checkpoint
from tools.ddd_state_manager import load_session_manifest
from tools.ddd_state_manager import save_checkpoint
from tools.ddd_state_manager import save_session_manifest
from tools.ddd_state_manager import update_impl_status


class TestDataModels:
    """Test data model serialization and deserialization."""

    def test_session_to_from_dict(self):
        """Session serialization round-trip."""
        session = Session(
            session_id="sess_001",
            started="2025-01-12T10:00:00Z",
            ended="2025-01-12T11:00:00Z",
            chunks_completed=["1.1", "1.2"],
            tokens_used=5000,
            status="completed",
        )

        session_dict = session.to_dict()
        restored = Session.from_dict(session_dict)

        assert restored.session_id == session.session_id
        assert restored.started == session.started
        assert restored.ended == session.ended
        assert restored.chunks_completed == session.chunks_completed
        assert restored.tokens_used == session.tokens_used
        assert restored.status == session.status

    def test_session_with_none_ended(self):
        """Session with None ended value serializes correctly."""
        session = Session(
            session_id="sess_002",
            started="2025-01-12T10:00:00Z",
            ended=None,
            chunks_completed=[],
            tokens_used=0,
            status="active",
        )

        session_dict = session.to_dict()
        restored = Session.from_dict(session_dict)

        assert restored.ended is None
        assert restored.chunks_completed == []

    def test_session_manifest_to_from_dict(self):
        """SessionManifest serialization round-trip."""
        session1 = Session(
            session_id="sess_001",
            started="2025-01-12T10:00:00Z",
            ended="2025-01-12T11:00:00Z",
            chunks_completed=["1.1"],
            tokens_used=3000,
            status="completed",
        )

        session2 = Session(
            session_id="sess_002",
            started="2025-01-12T12:00:00Z",
            ended=None,
            chunks_completed=["1.2"],
            tokens_used=2000,
            status="active",
        )

        manifest = SessionManifest(
            sessions=[session1, session2],
            total_chunks=5,
            completed_chunks=["1.1", "1.2"],
            current_session="sess_002",
        )

        manifest_dict = manifest.to_dict()
        restored = SessionManifest.from_dict(manifest_dict)

        assert len(restored.sessions) == 2
        assert restored.sessions[0].session_id == "sess_001"
        assert restored.sessions[1].session_id == "sess_002"
        assert restored.total_chunks == 5
        assert restored.completed_chunks == ["1.1", "1.2"]
        assert restored.current_session == "sess_002"

    def test_session_manifest_empty_defaults(self):
        """SessionManifest with empty values uses defaults."""
        manifest_dict = {}
        manifest = SessionManifest.from_dict(manifest_dict)

        assert manifest.sessions == []
        assert manifest.total_chunks == 0
        assert manifest.completed_chunks == []
        assert manifest.current_session is None

    def test_checkpoint_data_to_from_dict(self):
        """CheckpointData serialization round-trip."""
        checkpoint = CheckpointData(
            checkpoint_id="chk_001",
            timestamp="2025-01-12T10:30:00Z",
            session_id="sess_001",
            chunk="1.1",
            files_modified=["src/module.py", "tests/test_module.py"],
            test_status="passing",
            context={"key": "value", "nested": {"data": 123}},
            next_actions=["Implement 1.2", "Write tests"],
        )

        checkpoint_dict = checkpoint.to_dict()
        restored = CheckpointData.from_dict(checkpoint_dict)

        assert restored.checkpoint_id == checkpoint.checkpoint_id
        assert restored.timestamp == checkpoint.timestamp
        assert restored.session_id == checkpoint.session_id
        assert restored.chunk == checkpoint.chunk
        assert restored.files_modified == checkpoint.files_modified
        assert restored.test_status == checkpoint.test_status
        assert restored.context == checkpoint.context
        assert restored.next_actions == checkpoint.next_actions

    def test_checkpoint_with_empty_lists(self):
        """CheckpointData with empty lists serializes correctly."""
        checkpoint = CheckpointData(
            checkpoint_id="chk_002",
            timestamp="2025-01-12T10:30:00Z",
            session_id="sess_001",
            chunk="1.1",
            files_modified=[],
            test_status="not_run",
            context={},
            next_actions=[],
        )

        checkpoint_dict = checkpoint.to_dict()
        restored = CheckpointData.from_dict(checkpoint_dict)

        assert restored.files_modified == []
        assert restored.context == {}
        assert restored.next_actions == []


class TestSessionManifest:
    """Test session manifest file operations."""

    def test_load_nonexistent_returns_default(self, tmp_path, monkeypatch):
        """Loading nonexistent manifest returns default empty manifest."""
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path)
        monkeypatch.setattr("tools.ddd_state_manager.SESSION_MANIFEST_PATH", tmp_path / "session_manifest.json")

        manifest = load_session_manifest()

        assert manifest.sessions == []
        assert manifest.total_chunks == 0
        assert manifest.completed_chunks == []
        assert manifest.current_session is None

    def test_save_creates_directory(self, tmp_path, monkeypatch):
        """Saving manifest creates state directory if it doesn't exist."""
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path / "new_state_dir")
        monkeypatch.setattr(
            "tools.ddd_state_manager.SESSION_MANIFEST_PATH", tmp_path / "new_state_dir" / "session_manifest.json"
        )

        manifest = SessionManifest(total_chunks=3)
        save_session_manifest(manifest)

        assert (tmp_path / "new_state_dir").exists()
        assert (tmp_path / "new_state_dir" / "session_manifest.json").exists()

    def test_save_load_round_trip(self, tmp_path, monkeypatch):
        """Saving and loading manifest preserves data."""
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path)
        monkeypatch.setattr("tools.ddd_state_manager.SESSION_MANIFEST_PATH", tmp_path / "session_manifest.json")

        session = Session(
            session_id="sess_001",
            started="2025-01-12T10:00:00Z",
            ended=None,
            chunks_completed=["1.1", "1.2"],
            tokens_used=4000,
            status="active",
        )

        original = SessionManifest(
            sessions=[session], total_chunks=5, completed_chunks=["1.1", "1.2"], current_session="sess_001"
        )

        save_session_manifest(original)
        loaded = load_session_manifest()

        assert len(loaded.sessions) == 1
        assert loaded.sessions[0].session_id == "sess_001"
        assert loaded.total_chunks == 5
        assert loaded.completed_chunks == ["1.1", "1.2"]
        assert loaded.current_session == "sess_001"

    def test_corrupted_manifest_raises_valueerror(self, tmp_path, monkeypatch):
        """Loading corrupted manifest raises ValueError with clear message."""
        manifest_path = tmp_path / "session_manifest.json"
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path)
        monkeypatch.setattr("tools.ddd_state_manager.SESSION_MANIFEST_PATH", manifest_path)

        manifest_path.write_text("{ invalid json }")

        with pytest.raises(ValueError, match="Corrupted session manifest"):
            load_session_manifest()

    def test_invalid_structure_raises_valueerror(self, tmp_path, monkeypatch):
        """Loading manifest with invalid structure raises ValueError."""
        manifest_path = tmp_path / "session_manifest.json"
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path)
        monkeypatch.setattr("tools.ddd_state_manager.SESSION_MANIFEST_PATH", manifest_path)

        invalid_data = {"sessions": [{"missing": "required_fields"}]}
        manifest_path.write_text(json.dumps(invalid_data))

        with pytest.raises(ValueError, match="Corrupted session manifest"):
            load_session_manifest()

    def test_overwrite_existing_manifest(self, tmp_path, monkeypatch):
        """Saving manifest overwrites existing file."""
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path)
        monkeypatch.setattr("tools.ddd_state_manager.SESSION_MANIFEST_PATH", tmp_path / "session_manifest.json")

        manifest1 = SessionManifest(total_chunks=3)
        save_session_manifest(manifest1)

        manifest2 = SessionManifest(total_chunks=5, completed_chunks=["1.1"])
        save_session_manifest(manifest2)

        loaded = load_session_manifest()
        assert loaded.total_chunks == 5
        assert loaded.completed_chunks == ["1.1"]


class TestCheckpoints:
    """Test checkpoint file operations."""

    def test_save_creates_directory(self, tmp_path, monkeypatch):
        """Saving checkpoint creates checkpoints directory."""
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path)
        monkeypatch.setattr("tools.ddd_state_manager.CHECKPOINTS_DIR", tmp_path / "checkpoints")

        checkpoint = CheckpointData(
            checkpoint_id="chk_001",
            timestamp="2025-01-12T10:30:00Z",
            session_id="sess_001",
            chunk="1.1",
            files_modified=["src/module.py"],
            test_status="passing",
            context={},
            next_actions=["Next step"],
        )

        save_checkpoint(checkpoint)

        assert (tmp_path / "checkpoints").exists()
        assert (tmp_path / "checkpoints" / "chk_001.json").exists()

    def test_load_checkpoint_success(self, tmp_path, monkeypatch):
        """Loading existing checkpoint returns correct data."""
        monkeypatch.setattr("tools.ddd_state_manager.CHECKPOINTS_DIR", tmp_path)

        checkpoint = CheckpointData(
            checkpoint_id="chk_001",
            timestamp="2025-01-12T10:30:00Z",
            session_id="sess_001",
            chunk="1.1",
            files_modified=["src/module.py", "tests/test_module.py"],
            test_status="passing",
            context={"key": "value"},
            next_actions=["Implement 1.2"],
        )

        save_checkpoint(checkpoint)
        loaded = load_checkpoint("chk_001")

        assert loaded.checkpoint_id == "chk_001"
        assert loaded.session_id == "sess_001"
        assert loaded.chunk == "1.1"
        assert loaded.files_modified == ["src/module.py", "tests/test_module.py"]
        assert loaded.test_status == "passing"
        assert loaded.context == {"key": "value"}
        assert loaded.next_actions == ["Implement 1.2"]

    def test_load_nonexistent_checkpoint_raises_filenotfound(self, tmp_path, monkeypatch):
        """Loading nonexistent checkpoint raises FileNotFoundError."""
        monkeypatch.setattr("tools.ddd_state_manager.CHECKPOINTS_DIR", tmp_path)

        with pytest.raises(FileNotFoundError, match="Checkpoint not found"):
            load_checkpoint("nonexistent")

    def test_corrupted_checkpoint_raises_valueerror(self, tmp_path, monkeypatch):
        """Loading corrupted checkpoint raises ValueError."""
        monkeypatch.setattr("tools.ddd_state_manager.CHECKPOINTS_DIR", tmp_path)

        checkpoint_path = tmp_path / "chk_corrupted.json"
        checkpoint_path.write_text("{ invalid json }")

        with pytest.raises(ValueError, match="Corrupted checkpoint"):
            load_checkpoint("chk_corrupted")

    def test_get_latest_checkpoint_with_no_checkpoints(self, tmp_path, monkeypatch):
        """get_latest_checkpoint returns None when directory is empty."""
        monkeypatch.setattr("tools.ddd_state_manager.CHECKPOINTS_DIR", tmp_path / "empty_checkpoints")

        result = get_latest_checkpoint()
        assert result is None

    def test_get_latest_checkpoint_with_no_directory(self, tmp_path, monkeypatch):
        """get_latest_checkpoint returns None when directory doesn't exist."""
        monkeypatch.setattr("tools.ddd_state_manager.CHECKPOINTS_DIR", tmp_path / "nonexistent")

        result = get_latest_checkpoint()
        assert result is None

    def test_get_latest_checkpoint_returns_most_recent(self, tmp_path, monkeypatch):
        """get_latest_checkpoint returns most recently modified checkpoint."""
        monkeypatch.setattr("tools.ddd_state_manager.CHECKPOINTS_DIR", tmp_path)

        chk1 = CheckpointData(
            checkpoint_id="chk_001",
            timestamp="2025-01-12T10:00:00Z",
            session_id="sess_001",
            chunk="1.1",
            files_modified=[],
            test_status="passing",
            context={},
            next_actions=[],
        )

        chk2 = CheckpointData(
            checkpoint_id="chk_002",
            timestamp="2025-01-12T11:00:00Z",
            session_id="sess_001",
            chunk="1.2",
            files_modified=[],
            test_status="passing",
            context={},
            next_actions=[],
        )

        chk3 = CheckpointData(
            checkpoint_id="chk_003",
            timestamp="2025-01-12T12:00:00Z",
            session_id="sess_001",
            chunk="1.3",
            files_modified=[],
            test_status="passing",
            context={},
            next_actions=[],
        )

        save_checkpoint(chk1)
        time.sleep(0.01)
        save_checkpoint(chk2)
        time.sleep(0.01)
        save_checkpoint(chk3)

        latest = get_latest_checkpoint()
        assert latest is not None
        assert latest.checkpoint_id == "chk_003"

    def test_get_latest_checkpoint_corrupted_raises(self, tmp_path, monkeypatch):
        """get_latest_checkpoint raises ValueError for corrupted file."""
        monkeypatch.setattr("tools.ddd_state_manager.CHECKPOINTS_DIR", tmp_path)

        checkpoint_path = tmp_path / "chk_corrupted.json"
        checkpoint_path.write_text("{ invalid json }")

        with pytest.raises(ValueError, match="Corrupted checkpoint"):
            get_latest_checkpoint()


class TestImplementationStatus:
    """Test implementation status markdown log operations."""

    def test_creates_directory_and_file(self, tmp_path, monkeypatch):
        """update_impl_status creates directory and file if they don't exist."""
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path / "new_state")
        monkeypatch.setattr("tools.ddd_state_manager.IMPL_STATUS_PATH", tmp_path / "new_state" / "impl_status.md")

        update_impl_status("sess_001", "1.1", "completed")

        assert (tmp_path / "new_state").exists()
        assert (tmp_path / "new_state" / "impl_status.md").exists()

    def test_first_status_creates_header(self, tmp_path, monkeypatch):
        """First status creates header and session section."""
        status_path = tmp_path / "impl_status.md"
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path)
        monkeypatch.setattr("tools.ddd_state_manager.IMPL_STATUS_PATH", status_path)

        update_impl_status("sess_001", "1.1", "completed")

        content = status_path.read_text()
        assert "# DDD Implementation Status" in content
        assert "## Session sess_001" in content
        assert "[completed] Chunk 1.1" in content

    def test_adds_to_existing_session(self, tmp_path, monkeypatch):
        """Adding status to existing session appends to that section."""
        status_path = tmp_path / "impl_status.md"
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path)
        monkeypatch.setattr("tools.ddd_state_manager.IMPL_STATUS_PATH", status_path)

        update_impl_status("sess_001", "1.1", "completed")
        update_impl_status("sess_001", "1.2", "in_progress")

        content = status_path.read_text()
        lines = content.split("\n")

        session_idx = None
        for i, line in enumerate(lines):
            if "## Session sess_001" in line:
                session_idx = i
                break

        assert session_idx is not None

        session_content = "\n".join(lines[session_idx:])
        assert "[completed] Chunk 1.1" in session_content
        assert "[in_progress] Chunk 1.2" in session_content

    def test_creates_new_session_section(self, tmp_path, monkeypatch):
        """Adding status for new session creates new section."""
        status_path = tmp_path / "impl_status.md"
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path)
        monkeypatch.setattr("tools.ddd_state_manager.IMPL_STATUS_PATH", status_path)

        update_impl_status("sess_001", "1.1", "completed")
        update_impl_status("sess_002", "2.1", "started")

        content = status_path.read_text()
        assert "## Session sess_001" in content
        assert "## Session sess_002" in content
        assert "[completed] Chunk 1.1" in content
        assert "[started] Chunk 2.1" in content

    def test_status_includes_timestamp(self, tmp_path, monkeypatch):
        """Status entries include ISO timestamp."""
        status_path = tmp_path / "impl_status.md"
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path)
        monkeypatch.setattr("tools.ddd_state_manager.IMPL_STATUS_PATH", status_path)

        update_impl_status("sess_001", "1.1", "completed")

        content = status_path.read_text()
        assert "[completed] Chunk 1.1" in content
        assert "2025-" in content
        assert "Z)" in content

    def test_multiple_sessions_maintain_order(self, tmp_path, monkeypatch):
        """Multiple sessions maintain chronological order."""
        status_path = tmp_path / "impl_status.md"
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path)
        monkeypatch.setattr("tools.ddd_state_manager.IMPL_STATUS_PATH", status_path)

        update_impl_status("sess_001", "1.1", "completed")
        update_impl_status("sess_002", "2.1", "started")
        update_impl_status("sess_001", "1.2", "completed")

        content = status_path.read_text()
        lines = content.split("\n")

        sess1_idx = None
        sess2_idx = None
        for i, line in enumerate(lines):
            if "## Session sess_001" in line and sess1_idx is None:
                sess1_idx = i
            elif "## Session sess_002" in line:
                sess2_idx = i

        assert sess1_idx is not None
        assert sess2_idx is not None

        sess1_section = "\n".join(lines[sess1_idx : sess2_idx if sess2_idx else None])
        assert "[completed] Chunk 1.1" in sess1_section
        assert "[completed] Chunk 1.2" in sess1_section


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_session_list(self, tmp_path, monkeypatch):
        """Manifest with empty sessions list works correctly."""
        monkeypatch.setattr("tools.ddd_state_manager.STATE_DIR", tmp_path)
        monkeypatch.setattr("tools.ddd_state_manager.SESSION_MANIFEST_PATH", tmp_path / "session_manifest.json")

        manifest = SessionManifest(sessions=[], total_chunks=0, completed_chunks=[], current_session=None)

        save_session_manifest(manifest)
        loaded = load_session_manifest()

        assert loaded.sessions == []
        assert loaded.completed_chunks == []

    def test_checkpoint_with_complex_context(self, tmp_path, monkeypatch):
        """Checkpoint with nested complex context serializes correctly."""
        monkeypatch.setattr("tools.ddd_state_manager.CHECKPOINTS_DIR", tmp_path)

        complex_context = {
            "string": "value",
            "number": 123,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"deep": {"structure": {"with": "values"}}},
        }

        checkpoint = CheckpointData(
            checkpoint_id="chk_complex",
            timestamp="2025-01-12T10:30:00Z",
            session_id="sess_001",
            chunk="1.1",
            files_modified=[],
            test_status="passing",
            context=complex_context,
            next_actions=[],
        )

        save_checkpoint(checkpoint)
        loaded = load_checkpoint("chk_complex")

        assert loaded.context == complex_context

    def test_very_long_file_lists(self, tmp_path, monkeypatch):
        """Checkpoint with very long file lists works correctly."""
        monkeypatch.setattr("tools.ddd_state_manager.CHECKPOINTS_DIR", tmp_path)

        files = [f"src/module_{i}.py" for i in range(100)]

        checkpoint = CheckpointData(
            checkpoint_id="chk_many_files",
            timestamp="2025-01-12T10:30:00Z",
            session_id="sess_001",
            chunk="1.1",
            files_modified=files,
            test_status="passing",
            context={},
            next_actions=[],
        )

        save_checkpoint(checkpoint)
        loaded = load_checkpoint("chk_many_files")

        assert len(loaded.files_modified) == 100
        assert loaded.files_modified[0] == "src/module_0.py"
        assert loaded.files_modified[99] == "src/module_99.py"

    def test_unicode_in_content(self, tmp_path, monkeypatch):
        """Unicode content in strings is preserved correctly."""
        monkeypatch.setattr("tools.ddd_state_manager.CHECKPOINTS_DIR", tmp_path)

        checkpoint = CheckpointData(
            checkpoint_id="chk_unicode",
            timestamp="2025-01-12T10:30:00Z",
            session_id="sess_001",
            chunk="1.1",
            files_modified=["src/unicode_✨.py"],
            test_status="passing",
            context={"message": "Unicode test: 日本語, emoji: 🎉"},
            next_actions=["Next: 测试"],
        )

        save_checkpoint(checkpoint)
        loaded = load_checkpoint("chk_unicode")

        assert "✨" in loaded.files_modified[0]
        assert "🎉" in loaded.context["message"]
        assert "测试" in loaded.next_actions[0]
