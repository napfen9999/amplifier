"""Tests for extraction logging system"""

import logging
import tempfile
from pathlib import Path

import pytest

from amplifier.memory.extraction_logger import get_extraction_logger
from amplifier.memory.extraction_logger import setup_extraction_logging


@pytest.fixture
def temp_log_dir(monkeypatch):
    """Create temporary log directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"

        # Patch the LOG_DIR constant
        import amplifier.memory.extraction_logger as logger_module

        monkeypatch.setattr(logger_module, "LOG_DIR", log_dir)

        # Reset global logger
        monkeypatch.setattr(logger_module, "_extraction_logger", None)

        yield log_dir


def test_setup_extraction_logging(temp_log_dir):
    """Test setting up extraction logging"""
    logger = setup_extraction_logging()

    # Verify logger created
    assert logger is not None
    assert logger.name == "amplifier.extraction"

    # Verify log directory created
    assert temp_log_dir.exists()

    # Verify log file created
    log_files = list(temp_log_dir.glob("extraction_*.log"))
    assert len(log_files) == 1

    log_file = log_files[0]
    assert log_file.name.startswith("extraction_")
    assert log_file.suffix == ".log"


def test_setup_extraction_logging_with_level(temp_log_dir):
    """Test setting up logging with custom level"""
    logger = setup_extraction_logging(log_level=logging.DEBUG)

    assert logger.level == logging.DEBUG


def test_get_extraction_logger(temp_log_dir):
    """Test getting extraction logger"""
    logger = get_extraction_logger()

    # Should create logger if not exists
    assert logger is not None
    assert logger.name == "amplifier.extraction"


def test_get_extraction_logger_returns_same_instance(temp_log_dir):
    """Test that get_extraction_logger returns same instance"""
    logger1 = get_extraction_logger()
    logger2 = get_extraction_logger()

    assert logger1 is logger2


def test_setup_extraction_logging_idempotent(temp_log_dir):
    """Test that setup_extraction_logging is idempotent"""
    logger1 = setup_extraction_logging()
    logger2 = setup_extraction_logging()

    # Should return same instance
    assert logger1 is logger2

    # Should only create one log file
    log_files = list(temp_log_dir.glob("extraction_*.log"))
    assert len(log_files) == 1


def test_logger_writes_to_file(temp_log_dir):
    """Test that logger actually writes to file"""
    logger = setup_extraction_logging()

    # Write a test message
    test_message = "Test extraction log message"
    logger.info(test_message)

    # Find log file
    log_files = list(temp_log_dir.glob("extraction_*.log"))
    assert len(log_files) == 1

    # Read log file and verify message
    log_content = log_files[0].read_text()
    assert test_message in log_content
    assert "INFO:" in log_content


def test_log_format(temp_log_dir):
    """Test log message format"""
    logger = setup_extraction_logging()
    logger.info("Test message")

    # Read log file
    log_files = list(temp_log_dir.glob("extraction_*.log"))
    log_content = log_files[0].read_text()

    # Verify format: [YYYY-MM-DD HH:MM:SS] LEVEL: Message
    assert "[20" in log_content  # Year starts with 20
    assert "] INFO: Test message" in log_content


def test_multiple_log_levels(temp_log_dir):
    """Test logging at different levels"""
    logger = setup_extraction_logging(log_level=logging.DEBUG)

    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Read log file
    log_files = list(temp_log_dir.glob("extraction_*.log"))
    log_content = log_files[0].read_text()

    # Verify all levels present
    assert "DEBUG: Debug message" in log_content
    assert "INFO: Info message" in log_content
    assert "WARNING: Warning message" in log_content
    assert "ERROR: Error message" in log_content


def test_log_file_encoding(temp_log_dir):
    """Test that log file handles UTF-8 encoding"""
    logger = setup_extraction_logging()

    # Log message with Unicode characters
    logger.info("Testing Unicode: 📝 Memory extraction complete ✅")

    # Read log file
    log_files = list(temp_log_dir.glob("extraction_*.log"))
    log_content = log_files[0].read_text(encoding="utf-8")

    # Verify Unicode characters preserved
    assert "📝" in log_content
    assert "✅" in log_content


def test_logger_has_file_and_console_handlers(temp_log_dir):
    """Test that logger has both file and console handlers"""
    logger = setup_extraction_logging()

    # Should have 2 handlers: file and console
    assert len(logger.handlers) == 2

    # Verify handler types
    handler_types = {type(h).__name__ for h in logger.handlers}
    assert "FileHandler" in handler_types
    assert "StreamHandler" in handler_types


def test_log_filename_format(temp_log_dir):
    """Test log filename format includes timestamp"""
    setup_extraction_logging()

    # Find log file
    log_files = list(temp_log_dir.glob("extraction_*.log"))
    assert len(log_files) == 1

    filename = log_files[0].name

    # Verify format: extraction_YYYYMMDD_HHMMSS.log
    assert filename.startswith("extraction_")
    assert filename.endswith(".log")

    # Extract timestamp part
    timestamp_part = filename[len("extraction_") : -len(".log")]

    # Should be in format YYYYMMDD_HHMMSS (15 characters: 8 + 1 + 6)
    assert len(timestamp_part) == 15
    assert "_" in timestamp_part
