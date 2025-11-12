"""Memory extraction processor

Core logic for extracting memories from transcript files.
Integrates the full memory extraction pipeline with storage.
"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from amplifier.extraction.core import MemoryExtractor
from amplifier.memory.core import MemoryStore
from amplifier.memory.extraction_logger import get_extraction_logger
from amplifier.memory.models import Memory


@dataclass
class ExtractionResult:
    """Result of transcript processing

    Attributes:
        session_id: Session ID of processed transcript
        memories_extracted: Number of memories extracted
        success: Whether processing succeeded
        error: Error message if failed, None otherwise
    """

    session_id: str
    memories_extracted: int
    success: bool = True
    error: str | None = None


def process_transcript(transcript_path: Path) -> ExtractionResult:
    """Process a transcript file and extract memories

    Loads transcript messages, extracts memories using Claude Code SDK,
    and stores them in the memory store.

    Args:
        transcript_path: Path to transcript JSONL file

    Returns:
        ExtractionResult with processing statistics

    Raises:
        FileNotFoundError: If transcript file doesn't exist
        ValueError: If transcript file is invalid
    """
    logger = get_extraction_logger()

    if not transcript_path.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    # Extract session ID from filename
    # Expected format: session_SESSIONID.jsonl
    session_id = transcript_path.stem.replace("session_", "")

    try:
        # Load transcript messages
        logger.info(f"Processing transcript: {session_id}")
        messages = _load_transcript(transcript_path)

        if not messages:
            logger.warning(f"No messages found in transcript: {session_id}")
            return ExtractionResult(
                session_id=session_id,
                memories_extracted=0,
                success=True,
                error="No messages in transcript",
            )

        # Extract memories using Claude Code SDK
        logger.info(f"Extracting memories from {len(messages)} messages")
        extractor = MemoryExtractor()
        result = asyncio.run(extractor.extract_from_messages_intelligent(messages, context=session_id))

        # Save memories to store
        memory_store = MemoryStore()
        memories_data = result.get("memories", [])

        saved_count = 0
        for mem_data in memories_data:
            # Convert extraction result to Memory model
            memory = Memory(
                content=mem_data.get("content", ""),
                category=mem_data.get("type", "learning"),
                metadata={
                    "session_id": session_id,
                    "importance": mem_data.get("importance", 0.5),
                    "tags": mem_data.get("tags", []),
                },
            )
            memory_store.add_memory(memory)
            saved_count += 1

        logger.info(f"Saved {saved_count} memories from session: {session_id}")

        return ExtractionResult(
            session_id=session_id,
            memories_extracted=saved_count,
            success=True,
            error=None,
        )

    except Exception as e:
        logger.error(f"Failed to process transcript {session_id}: {e}", exc_info=True)
        return ExtractionResult(
            session_id=session_id,
            memories_extracted=0,
            success=False,
            error=str(e),
        )


def _load_transcript(transcript_path: Path) -> list[dict]:
    """Load messages from JSONL transcript file

    Args:
        transcript_path: Path to transcript JSONL file

    Returns:
        List of message dictionaries

    Raises:
        ValueError: If file is not valid JSONL
    """
    messages = []

    with open(transcript_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
                messages.append(message)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_num}: {e}") from e

    return messages
