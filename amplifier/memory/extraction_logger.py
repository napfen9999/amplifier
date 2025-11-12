"""Centralized extraction logging

Provides dedicated logger for extraction operations with file output.
Logs are written to timestamped files in .data/memories/logs/

Log format: [YYYY-MM-DD HH:MM:SS] LEVEL: Message
"""

import logging
from datetime import datetime
from pathlib import Path

# Log directory
LOG_DIR = Path(".data/memories/logs")

# Global logger instance
_extraction_logger: logging.Logger | None = None


def setup_extraction_logging(log_level: int = logging.INFO) -> logging.Logger:
    """Setup logger for extraction operations

    Creates log file in .data/memories/logs/extraction_TIMESTAMP.log
    Configures formatting and handlers.

    Args:
        log_level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    global _extraction_logger

    # If already configured, return existing logger
    if _extraction_logger is not None:
        return _extraction_logger

    # Create log directory
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger("amplifier.extraction")
    logger.setLevel(log_level)

    # Clear any existing handlers (avoid duplicates)
    logger.handlers.clear()

    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"extraction_{timestamp}.log"

    # Create file handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(file_handler)

    # Also add console handler for visibility during extraction
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Store globally
    _extraction_logger = logger

    logger.info(f"Extraction logging initialized: {log_file}")

    return logger


def get_extraction_logger() -> logging.Logger:
    """Get configured extraction logger

    If logger hasn't been setup yet, calls setup_extraction_logging() first.

    Returns:
        Configured logger instance
    """
    global _extraction_logger

    if _extraction_logger is None:
        return setup_extraction_logging()

    return _extraction_logger
