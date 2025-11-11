"""Background memory extraction processor

Daemon process that polls extraction queue and processes pending sessions
without blocking Claude Code hooks.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from amplifier.extraction.core import MemoryExtractor
from amplifier.memory.core import MemoryStore
from amplifier.memory.filter import filter_sidechain_messages
from amplifier.memory.queue import get_queued_items
from amplifier.memory.queue import remove_from_queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
POLL_INTERVAL = 30  # seconds


async def process_extraction_queue() -> int:
    """Process all queued extraction items

    Returns:
        Number of items processed successfully
    """
    items = get_queued_items()

    if not items:
        logger.info("[PROCESSOR] No items in queue")
        return 0

    logger.info(f"[PROCESSOR] Processing {len(items)} queued items")

    # Initialize extractor and store
    extractor = MemoryExtractor()
    store = MemoryStore()

    processed = 0

    for item in items:
        try:
            logger.info(f"[PROCESSOR] Processing session {item.session_id}")

            # Read transcript
            transcript_path = Path(item.transcript_path)
            if not transcript_path.exists():
                logger.warning(f"[PROCESSOR] Transcript not found: {transcript_path}")
                remove_from_queue(item.session_id)
                continue

            # Load messages
            messages = []
            with open(transcript_path) as f:
                for line in f:
                    if line.strip():
                        messages.append(json.loads(line))

            # Filter sidechain messages
            messages = filter_sidechain_messages(messages)

            if len(messages) < 2:
                logger.info(f"[PROCESSOR] Skipping {item.session_id} (too few messages)")
                remove_from_queue(item.session_id)
                continue

            # Extract memories
            logger.info(f"[PROCESSOR] Extracting from {len(messages)} messages")
            result = await extractor.extract_from_messages(messages, context=None)

            # Store memories
            if result and "memories" in result:
                store.add_memories_batch(result)
                logger.info(f"[PROCESSOR] Stored {len(result['memories'])} memories")

            # Remove from queue
            remove_from_queue(item.session_id)
            processed += 1

        except Exception as e:
            logger.error(f"[PROCESSOR] Error processing {item.session_id}: {e}")
            # Leave in queue for retry
            continue

    logger.info(f"[PROCESSOR] Completed: {processed}/{len(items)} successful")
    return processed


async def run_processor() -> None:
    """Run background processor daemon

    Polls queue every POLL_INTERVAL seconds and processes pending items.
    Runs indefinitely until interrupted.
    """
    logger.info(f"[PROCESSOR] Starting daemon (poll interval: {POLL_INTERVAL}s)")

    while True:
        try:
            await process_extraction_queue()
        except Exception as e:
            logger.error(f"[PROCESSOR] Unexpected error: {e}")

        # Wait before next poll
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run_processor())
