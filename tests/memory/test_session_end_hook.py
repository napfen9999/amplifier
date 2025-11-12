"""Tests for SessionEnd hook integration"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from amplifier.memory.hooks.session_end import get_hook_status
from amplifier.memory.hooks.session_end import handle_session_end


@pytest.fixture
def temp_transcripts_dir():
    """Create temporary transcripts directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        transcripts_dir = Path(tmpdir)
        yield transcripts_dir


def test_handle_session_end_with_path_object(temp_transcripts_dir):
    """Test hook with Path object"""
    # Create transcript
    transcript_path = temp_transcripts_dir / "session_test.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')

    # Mock the underlying exit command
    with patch("amplifier.memory.hooks.session_end.handle_exit") as mock_exit:
        mock_exit.return_value = {
            "success": True,
            "message": "Transcript registered",
            "extraction_started": True,
        }

        result = handle_session_end("test", transcript_path)

    assert result["success"] is True
    assert result["extraction_started"] is True

    # Verify exit command was called with Path
    mock_exit.assert_called_once()
    call_args = mock_exit.call_args[0]
    assert call_args[0] == "test"
    assert isinstance(call_args[1], Path)


def test_handle_session_end_with_string_path(temp_transcripts_dir):
    """Test hook with string path"""
    # Create transcript
    transcript_path = temp_transcripts_dir / "session_str.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')

    # Mock the underlying exit command
    with patch("amplifier.memory.hooks.session_end.handle_exit") as mock_exit:
        mock_exit.return_value = {
            "success": True,
            "message": "Transcript registered",
            "extraction_started": True,
        }

        # Pass as string
        result = handle_session_end("str", str(transcript_path))

    assert result["success"] is True

    # Verify exit command was called with Path (converted from string)
    mock_exit.assert_called_once()
    call_args = mock_exit.call_args[0]
    assert call_args[0] == "str"
    assert isinstance(call_args[1], Path)
    assert call_args[1] == transcript_path


def test_handle_session_end_propagates_exit_result(temp_transcripts_dir):
    """Test hook propagates exit command result"""
    transcript_path = temp_transcripts_dir / "session_prop.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')

    expected_result = {
        "success": False,
        "message": "Test error message",
        "extraction_started": False,
    }

    with patch("amplifier.memory.hooks.session_end.handle_exit") as mock_exit:
        mock_exit.return_value = expected_result

        result = handle_session_end("prop", transcript_path)

    # Result should be exactly what exit command returned
    assert result == expected_result


def test_handle_session_end_logs_session_id(temp_transcripts_dir):
    """Test hook logs session ID"""
    transcript_path = temp_transcripts_dir / "session_log.jsonl"
    transcript_path.write_text('{"role": "user", "content": "test"}\n')

    with (
        patch("amplifier.memory.hooks.session_end.handle_exit") as mock_exit,
        patch("amplifier.memory.hooks.session_end.get_extraction_logger") as mock_logger,
    ):
        mock_exit.return_value = {"success": True, "message": "ok", "extraction_started": True}

        logger_instance = mock_logger.return_value

        handle_session_end("log_test", transcript_path)

        # Verify logging
        logger_instance.info.assert_called_once()
        log_message = logger_instance.info.call_args[0][0]
        assert "SessionEnd hook" in log_message
        assert "log_test" in log_message


def test_get_hook_status():
    """Test hook status reporting"""
    status = get_hook_status()

    assert status["hook_name"] == "SessionEnd"
    assert status["integration_status"] == "active"
    assert "memory extraction" in status["description"]


def test_handle_session_end_multiple_sessions_sequence(temp_transcripts_dir):
    """Test handling multiple session ends in sequence"""
    # Simulate multiple sessions ending
    results = []

    for i in range(1, 4):
        transcript_path = temp_transcripts_dir / f"session_multi{i}.jsonl"
        transcript_path.write_text('{"role": "user", "content": "test"}\n')

        with patch("amplifier.memory.hooks.session_end.handle_exit") as mock_exit:
            # First session starts extraction, others queue
            mock_exit.return_value = {
                "success": True,
                "message": f"Session {i}",
                "extraction_started": (i == 1),
            }

            result = handle_session_end(f"multi{i}", transcript_path)
            results.append(result)

    # Verify all succeeded
    assert all(r["success"] for r in results)

    # First started extraction, others didn't
    assert results[0]["extraction_started"] is True
    assert results[1]["extraction_started"] is False
    assert results[2]["extraction_started"] is False
