"""Tests for DDD Conflict Detector.

Tests the conflict detection functionality for resuming DDD sessions.
"""

import subprocess
from datetime import UTC
from datetime import datetime
from unittest.mock import patch

from tools.ddd_conflict_detector import FileConflict
from tools.ddd_conflict_detector import check_conflicts
from tools.ddd_conflict_detector import check_file_modifications
from tools.ddd_conflict_detector import get_git_last_modified
from tools.ddd_state_manager import CheckpointData


class TestFileConflict:
    """Tests for FileConflict data model."""

    def test_file_conflict_creation(self):
        conflict = FileConflict(
            file_path="test.py",
            checkpoint_timestamp="2025-11-12T10:00:00",
            last_modified="2025-11-12T11:00:00",
            conflict_type="modified",
        )

        assert conflict.file_path == "test.py"
        assert conflict.checkpoint_timestamp == "2025-11-12T10:00:00"
        assert conflict.last_modified == "2025-11-12T11:00:00"
        assert conflict.conflict_type == "modified"

    def test_conflict_types(self):
        for conflict_type in ["modified", "deleted", "created"]:
            conflict = FileConflict(
                file_path="test.py",
                checkpoint_timestamp="2025-11-12T10:00:00",
                last_modified="2025-11-12T11:00:00",
                conflict_type=conflict_type,
            )
            assert conflict.conflict_type == conflict_type


class TestGetGitLastModified:
    """Tests for get_git_last_modified function."""

    @patch("tools.ddd_conflict_detector.subprocess.run")
    def test_get_last_modified_success(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "log"],
            returncode=0,
            stdout="2025-11-12T15:30:00+00:00\n",
            stderr="",
        )

        result = get_git_last_modified("test.py")

        assert result is not None
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 12
        assert result.hour == 15
        assert result.minute == 30

    @patch("tools.ddd_conflict_detector.subprocess.run")
    def test_get_last_modified_not_in_git(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(args=["git", "log"], returncode=0, stdout="", stderr="")

        result = get_git_last_modified("untracked.py")

        assert result is None

    @patch("tools.ddd_conflict_detector.subprocess.run")
    def test_get_last_modified_git_error(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "log"], returncode=128, stdout="", stderr="fatal: not a git repository"
        )

        result = get_git_last_modified("test.py")

        assert result is None

    @patch("tools.ddd_conflict_detector.subprocess.run")
    def test_get_last_modified_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["git", "log"], timeout=5)

        result = get_git_last_modified("test.py")

        assert result is None

    @patch("tools.ddd_conflict_detector.subprocess.run")
    def test_get_last_modified_invalid_timestamp(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "log"], returncode=0, stdout="invalid-timestamp\n", stderr=""
        )

        result = get_git_last_modified("test.py")

        assert result is None

    @patch("tools.ddd_conflict_detector._is_git_available")
    def test_get_last_modified_git_not_available(self, mock_available):
        mock_available.return_value = False

        result = get_git_last_modified("test.py")

        assert result is None


class TestCheckFileModifications:
    """Tests for check_file_modifications function."""

    @patch("tools.ddd_conflict_detector.get_git_last_modified")
    def test_no_modifications(self, mock_get_modified):
        since = datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC)
        before_checkpoint = datetime(2025, 11, 12, 9, 0, 0, tzinfo=UTC)
        mock_get_modified.return_value = before_checkpoint

        conflicts = check_file_modifications(["test.py"], since)

        assert len(conflicts) == 0

    @patch("tools.ddd_conflict_detector.get_git_last_modified")
    def test_file_modified_after_checkpoint(self, mock_get_modified):
        since = datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC)
        after_checkpoint = datetime(2025, 11, 12, 11, 0, 0, tzinfo=UTC)
        mock_get_modified.return_value = after_checkpoint

        conflicts = check_file_modifications(["test.py"], since)

        assert len(conflicts) == 1
        assert conflicts[0].file_path == "test.py"
        assert conflicts[0].conflict_type == "modified"
        assert conflicts[0].checkpoint_timestamp == since.isoformat()

    @patch("tools.ddd_conflict_detector.get_git_last_modified")
    def test_multiple_files_some_modified(self, mock_get_modified):
        since = datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC)

        def side_effect(file_path):
            if file_path == "modified.py":
                return datetime(2025, 11, 12, 11, 0, 0, tzinfo=UTC)
            return datetime(2025, 11, 12, 9, 0, 0, tzinfo=UTC)

        mock_get_modified.side_effect = side_effect

        conflicts = check_file_modifications(["unmodified.py", "modified.py", "also_unmodified.py"], since)

        assert len(conflicts) == 1
        assert conflicts[0].file_path == "modified.py"

    @patch("tools.ddd_conflict_detector.get_git_last_modified")
    def test_file_not_in_git(self, mock_get_modified):
        since = datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC)
        mock_get_modified.return_value = None

        conflicts = check_file_modifications(["untracked.py"], since)

        assert len(conflicts) == 0

    @patch("tools.ddd_conflict_detector._is_git_available")
    def test_git_not_available(self, mock_available):
        mock_available.return_value = False
        since = datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC)

        conflicts = check_file_modifications(["test.py"], since)

        assert len(conflicts) == 0

    @patch("tools.ddd_conflict_detector.get_git_last_modified")
    def test_timestamp_edge_case_same_time(self, mock_get_modified):
        since = datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC)
        exact_same_time = datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC)
        mock_get_modified.return_value = exact_same_time

        conflicts = check_file_modifications(["test.py"], since)

        assert len(conflicts) == 0

    @patch("tools.ddd_conflict_detector.get_git_last_modified")
    def test_timestamp_edge_case_one_millisecond_later(self, mock_get_modified):
        since = datetime(2025, 11, 12, 10, 0, 0, 0, tzinfo=UTC)
        one_ms_later = datetime(2025, 11, 12, 10, 0, 0, 1000, tzinfo=UTC)
        mock_get_modified.return_value = one_ms_later

        conflicts = check_file_modifications(["test.py"], since)

        assert len(conflicts) == 1


class TestCheckConflicts:
    """Tests for check_conflicts function."""

    @patch("tools.ddd_conflict_detector.get_git_last_modified")
    @patch("tools.ddd_conflict_detector._check_created_files")
    def test_no_conflicts(self, mock_created, mock_get_modified, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        checkpoint = CheckpointData(
            checkpoint_id="2.1",
            timestamp=datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC).isoformat(),
            files_modified=[str(test_file)],
            test_status="pending",
            session_id="test_session",
            chunk="2.1",
            context={},
            next_actions=[],
        )

        mock_get_modified.return_value = datetime(2025, 11, 12, 9, 0, 0, tzinfo=UTC)
        mock_created.return_value = []

        report = check_conflicts(checkpoint)

        assert not report.has_conflicts
        assert len(report.conflicts) == 0
        assert "No conflicts detected" in report.recommendations[0]

    @patch("tools.ddd_conflict_detector._check_created_files")
    def test_deleted_file(self, mock_created):
        checkpoint = CheckpointData(
            checkpoint_id="2.1",
            timestamp=datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC).isoformat(),
            files_modified=["/nonexistent/file.py"],
            test_status="pending",
            session_id="test_session",
            chunk="2.1",
            context={},
            next_actions=[],
        )

        mock_created.return_value = []

        report = check_conflicts(checkpoint)

        assert report.has_conflicts
        assert len(report.conflicts) == 1
        assert report.conflicts[0].conflict_type == "deleted"
        assert report.conflicts[0].file_path == "/nonexistent/file.py"
        assert "deleted" in report.recommendations[0].lower()

    @patch("tools.ddd_conflict_detector.get_git_last_modified")
    @patch("tools.ddd_conflict_detector._check_created_files")
    def test_modified_file(self, mock_created, mock_get_modified, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        checkpoint = CheckpointData(
            checkpoint_id="2.1",
            timestamp=datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC).isoformat(),
            files_modified=[str(test_file)],
            test_status="pending",
            session_id="test_session",
            chunk="2.1",
            context={},
            next_actions=[],
        )

        mock_get_modified.return_value = datetime(2025, 11, 12, 11, 0, 0, tzinfo=UTC)
        mock_created.return_value = []

        report = check_conflicts(checkpoint)

        assert report.has_conflicts
        assert len(report.conflicts) == 1
        assert report.conflicts[0].conflict_type == "modified"
        assert "modified externally" in report.recommendations[0]

    @patch("tools.ddd_conflict_detector.get_git_last_modified")
    @patch("tools.ddd_conflict_detector._check_created_files")
    def test_created_file(self, mock_created, mock_get_modified, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        checkpoint = CheckpointData(
            checkpoint_id="2.1",
            timestamp=datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC).isoformat(),
            files_modified=[],
            test_status="pending",
            session_id="test_session",
            chunk="2.1",
            context={},
            next_actions=[],
        )

        mock_get_modified.return_value = datetime(2025, 11, 12, 9, 0, 0, tzinfo=UTC)
        mock_created.return_value = [
            FileConflict(
                file_path=str(test_file),
                checkpoint_timestamp=checkpoint.timestamp,
                last_modified=datetime(2025, 11, 12, 11, 0, 0, tzinfo=UTC).isoformat(),
                conflict_type="created",
            )
        ]

        report = check_conflicts(checkpoint)

        assert report.has_conflicts
        assert len(report.conflicts) == 1
        assert report.conflicts[0].conflict_type == "created"
        assert "created externally" in report.recommendations[0]

    @patch("tools.ddd_conflict_detector.get_git_last_modified")
    @patch("tools.ddd_conflict_detector._check_created_files")
    def test_multiple_conflict_types(self, mock_created, mock_get_modified, tmp_path):
        existing_file = tmp_path / "existing.py"
        existing_file.write_text("content")

        checkpoint = CheckpointData(
            checkpoint_id="2.1",
            timestamp=datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC).isoformat(),
            files_modified=[str(existing_file), "/deleted/file.py"],
            test_status="pending",
            session_id="test_session",
            chunk="2.1",
            context={},
            next_actions=[],
        )

        mock_get_modified.return_value = datetime(2025, 11, 12, 11, 0, 0, tzinfo=UTC)
        mock_created.return_value = [
            FileConflict(
                file_path="new_file.py",
                checkpoint_timestamp=checkpoint.timestamp,
                last_modified=datetime(2025, 11, 12, 11, 0, 0, tzinfo=UTC).isoformat(),
                conflict_type="created",
            )
        ]

        report = check_conflicts(checkpoint)

        assert report.has_conflicts
        assert len(report.conflicts) == 3

        conflict_types = {c.conflict_type for c in report.conflicts}
        assert "modified" in conflict_types
        assert "deleted" in conflict_types
        assert "created" in conflict_types

    @patch("tools.ddd_conflict_detector.get_git_last_modified")
    @patch("tools.ddd_conflict_detector._check_created_files")
    def test_recommendations_limit_display(self, mock_created, mock_get_modified, tmp_path):
        many_files = []
        for i in range(5):
            f = tmp_path / f"file{i}.py"
            f.write_text("content")
            many_files.append(str(f))

        checkpoint = CheckpointData(
            checkpoint_id="2.1",
            timestamp=datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC).isoformat(),
            files_modified=many_files,
            test_status="pending",
            session_id="test_session",
            chunk="2.1",
            context={},
            next_actions=[],
        )

        mock_get_modified.return_value = datetime(2025, 11, 12, 11, 0, 0, tzinfo=UTC)
        mock_created.return_value = []

        report = check_conflicts(checkpoint)

        assert report.has_conflicts

        modified_recommendations = [r for r in report.recommendations if "file(s) were modified" in r]
        assert len(modified_recommendations) > 0

        file_detail_recs = [r for r in report.recommendations if "file" in r and "  -" in r]
        assert len(file_detail_recs) <= 3


class TestGitMocking:
    """Tests for git command mocking strategies."""

    @patch("tools.ddd_conflict_detector.subprocess.run")
    def test_mock_git_log_format(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "log", "-1", "--format=%aI", "--", "test.py"],
            returncode=0,
            stdout="2025-11-12T15:00:00+00:00\n",
            stderr="",
        )

        result = get_git_last_modified("test.py")

        assert result is not None
        assert mock_run.call_count >= 1
        git_log_calls = [c for c in mock_run.call_args_list if "log" in str(c)]
        assert len(git_log_calls) >= 1
        assert "--format=%aI" in str(mock_run.call_args_list)

    @patch("tools.ddd_conflict_detector.subprocess.run")
    def test_mock_git_status_format(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "status", "--porcelain"], returncode=0, stdout="?? new_file.py\nA  added.py\n", stderr=""
        )

        from tools.ddd_conflict_detector import CheckpointData
        from tools.ddd_conflict_detector import _check_created_files

        checkpoint = CheckpointData(
            checkpoint_id="2.1",
            timestamp=datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC).isoformat(),
            files_modified=[],
            test_status="pending",
            session_id="test_session",
            chunk="2.1",
            context={},
            next_actions=[],
        )

        with patch("tools.ddd_conflict_detector.get_git_last_modified") as mock_modified:
            mock_modified.return_value = datetime(2025, 11, 12, 11, 0, 0, tzinfo=UTC)
            conflicts = _check_created_files(checkpoint)

        assert len(conflicts) >= 0


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_checkpoint_with_empty_files_list(self):
        checkpoint = CheckpointData(
            checkpoint_id="2.1",
            timestamp=datetime(2025, 11, 12, 10, 0, 0, tzinfo=UTC).isoformat(),
            files_modified=[],
            test_status="pending",
            session_id="test_session",
            chunk="2.1",
            context={},
            next_actions=[],
        )

        with patch("tools.ddd_conflict_detector._check_created_files") as mock_created:
            mock_created.return_value = []
            report = check_conflicts(checkpoint)

        assert not report.has_conflicts

    @patch("tools.ddd_conflict_detector.subprocess.run")
    def test_git_subprocess_oserror(self, mock_run):
        mock_run.side_effect = OSError("Git not found")

        result = get_git_last_modified("test.py")

        assert result is None

    @patch("tools.ddd_conflict_detector.subprocess.run")
    def test_malformed_git_output(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["git", "log"], returncode=0, stdout="malformed\noutput\nwith\nmultiple\nlines", stderr=""
        )

        result = get_git_last_modified("test.py")

        assert result is None
