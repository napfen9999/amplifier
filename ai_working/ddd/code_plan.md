# Code Implementation Plan - Exit-Command Feature

**Generated**: 2025-11-12
**Based on**: Phase 1 plan + Phase 2 documentation
**Branch**: feature/exit-command

---

## Summary

This implementation adds user-controlled memory extraction via `/exit` command with visible progress, crash recovery, and state management. It builds on existing background processing architecture (queue + processor) by adding:

1. **Transcript tracking system** - Centralized record of all transcripts and their processing status
2. **Synchronous extraction workflow** - Watchdog pattern with subprocess for user-initiated extraction
3. **Crash recovery system** - State tracking for resuming interrupted extractions
4. **User commands** - `/exit` and `/cleanup` for user control

**Philosophy alignment**: Ruthless simplicity, modular design (bricks & studs), no future-proofing.

---

## Current State Analysis

### Existing Architecture (Working)

**Background Processing System**:
- ✅ `amplifier/memory/queue.py` - JSONL-based extraction queue
- ✅ `amplifier/memory/processor.py` - Background daemon polls queue, processes items
- ✅ `.claude/tools/hook_stop.py` - Queues extractions on session end
- ✅ `amplifier/memory/core.py` - Memory storage
- ✅ `amplifier/memory/filter.py` - Message filtering
- ✅ `amplifier/memory/router.py` - Event routing

**Test Coverage**:
- ✅ `tests/memory/test_queue.py` - Queue operations tested
- ✅ `tests/memory/test_router.py` - Router logic tested
- ✅ `tests/memory/test_filter.py` - Filtering tested

### What's Missing (Need to Build)

**New Modules** (6 files):
- ❌ `amplifier/memory/transcript_tracker.py` - Track transcript processing state
- ❌ `amplifier/memory/extraction_worker.py` - Subprocess worker for extraction
- ❌ `amplifier/memory/watchdog.py` - Spawn/monitor worker subprocess
- ❌ `amplifier/memory/state_tracker.py` - Crash recovery state management
- ❌ `amplifier/memory/terminal_ui.py` - ASCII progress rendering
- ❌ `amplifier/memory/extraction_logger.py` - Centralized extraction logging

**New Commands** (2 files):
- ❌ `.claude/commands/exit.md` - Exit command definition
- ❌ `.claude/commands/cleanup.md` - Cleanup command definition

**Updated Modules** (2 files):
- ⚠️ `.claude/tools/hook_stop.py` - Add transcript tracking integration
- ⚠️ `amplifier/memory/processor.py` - Add logging integration

**New Tests** (6 files):
- ❌ `tests/memory/test_transcript_tracker.py`
- ❌ `tests/memory/test_extraction_worker.py`
- ❌ `tests/memory/test_watchdog.py`
- ❌ `tests/memory/test_state_tracker.py`
- ❌ `tests/memory/test_terminal_ui.py`
- ❌ `tests/integration/test_exit_workflow.py`

---

## Files to Change

### NEW FILE: amplifier/memory/transcript_tracker.py

**Purpose**: Track which transcripts have been processed for memory extraction

**Current State**: Does not exist

**Required Changes**: Create from scratch

**Module Specification**:

```python
"""Centralized transcript tracking system"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json

@dataclass
class TranscriptRecord:
    """Record of a transcript file"""
    session_id: str
    transcript_path: str
    created_at: str  # ISO8601
    processed: bool = False
    processed_at: str | None = None
    memories_extracted: int = 0

# Public API
def load_transcripts() -> list[TranscriptRecord]:
    """Load all transcript records from .data/transcripts.json"""

def save_transcripts(records: list[TranscriptRecord]) -> None:
    """Save transcript records to .data/transcripts.json"""

def add_transcript_record(session_id: str, transcript_path: str) -> None:
    """Add new transcript to tracking"""

def mark_transcript_processed(
    session_id: str,
    memories_count: int
) -> None:
    """Mark transcript as processed with memory count"""

def get_unprocessed_transcripts() -> list[TranscriptRecord]:
    """Get all transcripts where processed=False"""

def get_transcript_by_session(session_id: str) -> TranscriptRecord | None:
    """Get specific transcript record"""
```

**Storage**: `.data/transcripts.json`

**Data Format**:
```json
{
  "version": "1.0",
  "transcripts": [
    {
      "session_id": "abc123",
      "transcript_path": "/path/to/transcript.jsonl",
      "created_at": "2025-11-12T15:30:00",
      "processed": true,
      "processed_at": "2025-11-12T15:35:00",
      "memories_extracted": 15
    }
  ]
}
```

**Dependencies**: None (pure data management)

**Estimated lines**: ~150

**Philosophy check**: ✅ Single responsibility (track transcripts), no abstractions, file-based storage (simple), clear API (studs)

---

### NEW FILE: amplifier/memory/state_tracker.py

**Purpose**: Track extraction state for crash recovery

**Current State**: Does not exist

**Required Changes**: Create from scratch

**Module Specification**:

```python
"""Extraction state tracking for crash recovery"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json

@dataclass
class TranscriptState:
    """State of individual transcript in extraction"""
    id: str
    status: str  # "pending" | "in_progress" | "completed"
    memories: int = 0
    completed_at: str | None = None

@dataclass
class ExtractionState:
    """Overall extraction state"""
    status: str  # "running" | "completed" | "failed" | "cancelled"
    started_at: str
    pid: int | None
    transcripts: list[TranscriptState]
    last_update: str

# Public API
def save_extraction_state(state: ExtractionState) -> Path:
    """Save state to .data/memories/.extraction_state.json"""

def load_extraction_state() -> ExtractionState | None:
    """Load state if exists, None otherwise"""

def clear_extraction_state() -> None:
    """Delete state file after successful completion"""

def update_transcript_progress(
    session_id: str,
    status: str,
    memories: int = 0
) -> None:
    """Update specific transcript status in state"""
```

**Storage**: `.data/memories/.extraction_state.json`

**Data Format**:
```json
{
  "status": "running",
  "started_at": "2025-11-12T15:30:00",
  "pid": 12345,
  "transcripts": [
    {
      "id": "abc123",
      "status": "completed",
      "memories": 8,
      "completed_at": "2025-11-12T15:31:00"
    },
    {
      "id": "def456",
      "status": "in_progress"
    }
  ],
  "last_update": "2025-11-12T15:32:00"
}
```

**Dependencies**: None

**Estimated lines**: ~180

**Philosophy check**: ✅ Simple file-based persistence, clear state model, no over-engineering

---

### NEW FILE: amplifier/memory/extraction_logger.py

**Purpose**: Centralized logging for extraction operations

**Current State**: Does not exist

**Required Changes**: Create from scratch

**Module Specification**:

```python
"""Centralized extraction logging"""
import logging
from pathlib import Path
from datetime import datetime

def setup_extraction_logging() -> logging.Logger:
    """Setup logger for extraction operations

    Creates log file in .data/memories/logs/extraction_TIMESTAMP.log
    Returns configured logger.
    """

def get_extraction_logger() -> logging.Logger:
    """Get configured extraction logger"""

# Log file location: .data/memories/logs/extraction_TIMESTAMP.log
```

**Storage**: `.data/memories/logs/extraction_TIMESTAMP.log`

**Log Format**:
```
[2025-11-12 15:30:00] INFO: Starting extraction of 3 transcripts
[2025-11-12 15:30:15] INFO: [TRIAGE] Transcript abc123: Found 3 ranges (28% coverage)
[2025-11-12 15:30:45] INFO: [EXTRACTION] Transcript abc123: Extracted 8 memories
[2025-11-12 15:31:00] INFO: [STORAGE] Transcript abc123: Saved successfully
```

**Dependencies**: Standard library logging

**Estimated lines**: ~100

**Philosophy check**: ✅ Simple file-based logging, timestamp-based filenames, standard library only

---

### NEW FILE: amplifier/memory/terminal_ui.py

**Purpose**: ASCII-based progress rendering for terminal

**Current State**: Does not exist

**Required Changes**: Create from scratch

**Module Specification**:

```python
"""ASCII-based terminal progress UI"""
from dataclasses import dataclass

@dataclass
class ProgressState:
    """Current progress state"""
    total_transcripts: int
    completed_transcripts: int
    current_session_id: str | None
    current_stage: str | None  # "triage" | "extraction" | "storage"
    stage_progress: float = 0.0  # 0.0 to 1.0
    memories_extracted: int = 0

class TerminalUI:
    """ASCII progress UI renderer"""

    def __enter__(self):
        """Setup terminal (hide cursor, etc.)"""

    def __exit__(self, *args):
        """Cleanup terminal (show cursor, etc.)"""

    def update(self, state: ProgressState) -> None:
        """Update progress display"""

    def show_summary(self,
                     transcripts: int,
                     memories: int,
                     time: str) -> None:
        """Show completion summary"""

# UI renders like:
# 📝 Memory Extraction
#
# Transcripts: [████████░░] 2/3
# Current: Processing transcript def456...
#
# [TRIAGE]     Identifying important ranges... ✓
#              Found 3 ranges (28% coverage)
#
# [EXTRACTION] Processing 156 messages...
#              [████████████████░░] 85%
```

**Dependencies**: None (pure rendering logic)

**Estimated lines**: ~200

**Philosophy check**: ✅ ASCII-only (no external deps), simple state machine, pure rendering

---

### NEW FILE: amplifier/memory/extraction_worker.py

**Purpose**: Subprocess worker that processes extraction queue

**Current State**: Does not exist

**Required Changes**: Create from scratch

**Module Specification**:

```python
"""Extraction worker subprocess
Entry point: python -m amplifier.memory.extraction_worker
"""
import asyncio
import json
import sys

async def main():
    """Main worker loop

    1. Load unprocessed transcripts
    2. Report start (JSON-lines to stdout)
    3. Process each transcript:
       - TRIAGE pass (identify important ranges)
       - EXTRACTION pass (extract from ranges)
       - STORAGE (save memories)
       - Report progress (JSON-lines)
    4. Report summary
    5. Exit
    """

# Progress messages (JSON-lines to stdout):
# {"type": "start", "total_transcripts": 5}
# {"type": "progress", "current": 1, "session_id": "abc123", "stage": "triage"}
# {"type": "triage_complete", "session_id": "abc123", "ranges": 3, "coverage": 0.28}
# {"type": "extraction_progress", "session_id": "abc123", "percentage": 85}
# {"type": "extraction_complete", "session_id": "abc123", "memories": 12}
# {"type": "summary", "transcripts": 5, "memories": 42, "time": "2m 15s"}

if __name__ == "__main__":
    asyncio.run(main())
```

**Dependencies**:
- `transcript_tracker.py` (to get unprocessed)
- `state_tracker.py` (to save progress)
- `extraction_logger.py` (to log)
- `amplifier.extraction.core.MemoryExtractor` (existing)
- `amplifier.memory.core.MemoryStore` (existing)

**Estimated lines**: ~250

**Philosophy check**: ✅ Subprocess isolation, JSON-lines communication (simple), uses existing extractionlogic

---

### NEW FILE: amplifier/memory/watchdog.py

**Purpose**: Spawn and monitor extraction worker subprocess

**Current State**: Does not exist

**Required Changes**: Create from scratch

**Module Specification**:

```python
"""Watchdog manager - spawns and monitors extraction worker"""
import asyncio
import subprocess
import json
from dataclasses import dataclass

@dataclass
class ExtractionResult:
    """Result from extraction run"""
    transcripts_processed: int
    total_memories: int
    time_taken: float
    errors: list[str]

def run_extraction_with_watchdog() -> ExtractionResult:
    """Spawn worker subprocess, monitor progress, show UI

    Returns result when subprocess completes.
    Handles:
    - Subprocess spawning (python -m amplifier.memory.extraction_worker)
    - Progress monitoring (read stdout JSON-lines)
    - Terminal UI rendering
    - State tracking for crash recovery
    - Ctrl+C handling (graceful cancellation)
    """

async def run_extraction_async() -> ExtractionResult:
    """Async version of extraction with watchdog"""
```

**Dependencies**:
- `extraction_worker.py` (spawns as subprocess)
- `terminal_ui.py` (renders progress)
- `state_tracker.py` (saves state for recovery)

**Estimated lines**: ~220

**Philosophy check**: ✅ Simple subprocess management, no complex abstractions, clear separation of concerns

---

### NEW FILE: .claude/commands/exit.md

**Purpose**: Command definition for `/exit` command

**Current State**: Does not exist

**Required Changes**: Create from scratch (already fully documented in Phase 2)

**Content**: See existing `docs/EXIT_COMMAND.md` for complete specification

**Key implementation points**:

```python
# Step 1: Check for unprocessed transcripts
from amplifier.memory.transcript_tracker import get_unprocessed_transcripts
unprocessed = get_unprocessed_transcripts()

# Step 2: Prompt user
if unprocessed:
    print(f"📝 Found {len(unprocessed)} unprocessed transcript(s)")
    response = input("Extract memories before exit? (Y/n): ")

    # Step 3A: If Yes, run extraction
    if response.lower() in ['y', 'yes', '']:
        from amplifier.memory.watchdog import run_extraction_with_watchdog
        result = run_extraction_with_watchdog()
        print(f"✅ Extracted {result.total_memories} memories from {result.transcripts_processed} transcripts")

    # Step 3B: If No, skip
    else:
        print("Skipping memory extraction.")

# Step 4: Exit normally
print("Exiting Claude Code...")
```

**Dependencies**:
- `transcript_tracker.py`
- `watchdog.py`

**Estimated lines**: ~270 (documentation + implementation guidance)

**Philosophy check**: ✅ User control, clear prompts, graceful handling

---

### NEW FILE: .claude/commands/cleanup.md

**Purpose**: Command definition for `/cleanup` command

**Current State**: Does not exist

**Required Changes**: Create from scratch (already fully documented in Phase 2)

**Content**: See existing `docs/CLEANUP_COMMAND.md` for complete specification

**Key implementation points**:

```python
# Step 1: Load and analyze state
from amplifier.memory.state_tracker import load_extraction_state
import os

state = load_extraction_state()

if state is None:
    print("✓ No Extraction State Found")
    print("The memory system is clean - no interrupted extractions to recover.")
    return

# Step 2: Determine state type
if state.status == "completed":
    print("✅ Extraction Completed Successfully")
    # Offer: Clear state, View logs, Exit
elif state.status == "cancelled":
    print("⏸️  Extraction Was Cancelled")
    # Offer: Resume, View logs, Clear state, Exit
elif state.status == "failed":
    print("❌ Extraction Failed")
    # Offer: Resume, View logs, Clear state, Exit
elif state.status == "running":
    # Check if PID exists
    try:
        os.kill(state.pid, 0)
        print("⚡ Extraction In Progress")
        # Offer: Let continue, View logs, Cancel
    except OSError:
        print("⚠️  Extraction Process Crashed")
        # Offer: Resume, View logs, Clear state, Manual investigation, Exit

# Step 3: Execute user's choice
```

**Dependencies**:
- `state_tracker.py`
- `watchdog.py` (for resume)

**Estimated lines**: ~508 (documentation + implementation guidance)

**Philosophy check**: ✅ Clear state detection, informative output, multiple recovery options

---

### UPDATED FILE: .claude/tools/hook_stop.py

**Purpose**: Add transcript tracking integration

**Current State**: Exists, queues extractions on session stop

**Required Changes**: Add call to transcript tracker after queuing

**Specific Modifications**:

**Location**: After line 246 (after `queue_extraction()` call)

**Add**:
```python
# Add transcript to tracking system
from amplifier.memory.transcript_tracker import add_transcript_record
add_transcript_record(
    session_id=session_id,
    transcript_path=transcript_path
)
logger.info(f"[STOP HOOK] Tracked transcript {session_id}")
```

**Why**: Transcript tracker needs to know about all transcripts when they're created

**Dependencies**: `transcript_tracker.py` (new module)

**Philosophy check**: ✅ Minimal change, single responsibility (hook now tracks + queues)

---

### UPDATED FILE: amplifier/memory/processor.py

**Purpose**: Add logging integration

**Current State**: Exists, processes queued extractions

**Required Changes**: Add extraction logging

**Specific Modifications**:

**Location**: Line 42 (before creating extractor)

**Add**:
```python
# Setup extraction logging
from amplifier.memory.extraction_logger import setup_extraction_logging
logger = setup_extraction_logging()
```

**Location**: After memory extraction (line 86)

**Add**:
```python
# Mark transcript as processed in tracker
from amplifier.memory.transcript_tracker import mark_transcript_processed
mark_transcript_processed(item.session_id, len(result['memories']))
logger.info(f"[PROCESSOR] Marked {item.session_id} as processed")
```

**Why**: Need to update transcript tracking when background processing completes

**Dependencies**: `extraction_logger.py`, `transcript_tracker.py`

**Philosophy check**: ✅ Minimal integration, no architectural changes

---

## Dependencies Between Changes

### Dependency Graph

```
Layer 1 (No Dependencies):
├── transcript_tracker.py
├── state_tracker.py
└── extraction_logger.py

Layer 2 (Depends on Layer 1):
├── terminal_ui.py
└── extraction_worker.py (depends on: transcript_tracker, state_tracker, extraction_logger)

Layer 3 (Depends on Layer 2):
└── watchdog.py (depends on: extraction_worker, terminal_ui, state_tracker)

Layer 4 (Commands - Depends on Layer 3):
├── .claude/commands/exit.md (depends on: transcript_tracker, watchdog)
└── .claude/commands/cleanup.md (depends on: state_tracker, watchdog)

Layer 5 (Integrations - Depends on Layer 1):
├── .claude/tools/hook_stop.py (depends on: transcript_tracker)
└── amplifier/memory/processor.py (depends on: extraction_logger, transcript_tracker)
```

### Build Order

**Phase 1: Foundation (Layer 1)**
1. transcript_tracker.py
2. state_tracker.py
3. extraction_logger.py

**Phase 2: Workers (Layer 2)**
4. terminal_ui.py
5. extraction_worker.py

**Phase 3: Orchestration (Layer 3)**
6. watchdog.py

**Phase 4: Commands (Layer 4)**
7. .claude/commands/exit.md
8. .claude/commands/cleanup.md

**Phase 5: Integrations (Layer 5)**
9. Update .claude/tools/hook_stop.py
10. Update amplifier/memory/processor.py

---

## Implementation Chunks

Breaking implementation into logical, testable chunks with clear commit points.

### Chunk 1: Transcript Tracking Foundation

**Files**:
- `amplifier/memory/transcript_tracker.py` (NEW)
- `tests/memory/test_transcript_tracker.py` (NEW)

**Description**: Core transcript tracking system - load/save/query transcript records

**Why first**: Other modules depend on this (worker, watchdog, hooks)

**Test strategy**:
- Test add_transcript_record() creates record
- Test mark_transcript_processed() updates state
- Test get_unprocessed_transcripts() filters correctly
- Test JSON persistence (save/load roundtrip)
- Test concurrent access safety (if file exists while writing)

**Dependencies**: None

**Commit point**: After unit tests pass

**Estimated effort**: 2-3 hours, ~300 lines total (code + tests)

---

### Chunk 2: State Tracking for Crash Recovery

**Files**:
- `amplifier/memory/state_tracker.py` (NEW)
- `tests/memory/test_state_tracker.py` (NEW)

**Description**: Extraction state persistence for crash recovery

**Why second**: Independent of transcript tracking, needed by worker

**Test strategy**:
- Test save_extraction_state() writes JSON
- Test load_extraction_state() reads correctly
- Test clear_extraction_state() deletes file
- Test update_transcript_progress() modifies state
- Test file doesn't exist case (returns None)

**Dependencies**: None

**Commit point**: After unit tests pass

**Estimated effort**: 2-3 hours, ~350 lines total (code + tests)

---

### Chunk 3: Extraction Logging System

**Files**:
- `amplifier/memory/extraction_logger.py` (NEW)
- Create `.data/memories/logs/` directory structure

**Description**: Centralized logging for extraction operations

**Why third**: Simple utility needed by worker

**Test strategy**:
- Test setup_extraction_logging() creates logger
- Test log file created in correct location
- Test log format (timestamp, level, message)
- Test log file rotation (if old logs pile up)

**Dependencies**: None

**Commit point**: After manual verification (logger works)

**Estimated effort**: 1-2 hours, ~150 lines total (code + basic tests)

---

### Chunk 4: Terminal Progress UI

**Files**:
- `amplifier/memory/terminal_ui.py` (NEW)
- `tests/memory/test_terminal_ui.py` (NEW)

**Description**: ASCII-based progress rendering

**Why fourth**: Independent component, no external dependencies

**Test strategy**:
- Test progress bar rendering (% → visual bar)
- Test stage indicators (triage/extraction/storage)
- Test terminal cleanup (cursor visibility)
- Test summary display format
- Manual terminal testing (visual verification)

**Dependencies**: None

**Commit point**: After unit tests pass + manual terminal verification

**Estimated effort**: 2-3 hours, ~350 lines total (code + tests)

---

### Chunk 5: Extraction Worker Subprocess

**Files**:
- `amplifier/memory/extraction_worker.py` (NEW)
- `tests/memory/test_extraction_worker.py` (NEW)

**Description**: Subprocess that processes transcripts, reports progress

**Why fifth**: Requires transcript_tracker, state_tracker, extraction_logger

**Test strategy**:
- Test worker processes queue items
- Test progress JSON-lines output format
- Test triage → extraction → storage flow
- Test error handling (missing transcript, extraction failure)
- Test graceful shutdown on interrupt
- Integration test with real transcript file

**Dependencies**: transcript_tracker, state_tracker, extraction_logger

**Commit point**: After unit tests pass + integration test

**Estimated effort**: 3-4 hours, ~400 lines total (code + tests)

---

### Chunk 6: Watchdog Manager

**Files**:
- `amplifier/memory/watchdog.py` (NEW)
- `tests/memory/test_watchdog.py` (NEW)

**Description**: Spawn extraction worker, monitor progress, render UI

**Why sixth**: Requires extraction_worker, terminal_ui, state_tracker

**Test strategy**:
- Test subprocess spawning (worker starts)
- Test progress monitoring (read JSON-lines)
- Test terminal UI integration
- Test state tracking integration
- Test Ctrl+C handling (graceful cancellation)
- Test subprocess timeout/crash handling
- Integration test (full extraction flow)

**Dependencies**: extraction_worker, terminal_ui, state_tracker

**Commit point**: After unit tests pass + integration test

**Estimated effort**: 3-4 hours, ~400 lines total (code + tests)

---

### Chunk 7: Exit Command

**Files**:
- `.claude/commands/exit.md` (NEW)

**Description**: User-facing exit command with extraction prompt

**Why seventh**: Requires transcript_tracker, watchdog (all previous chunks)

**Test strategy**:
- Manual testing: Run /exit with unprocessed transcripts
- Manual testing: Run /exit with no unprocessed transcripts
- Manual testing: Accept extraction (Y)
- Manual testing: Decline extraction (n)
- Manual testing: Cancel during extraction (Ctrl+C)

**Dependencies**: transcript_tracker, watchdog

**Commit point**: After manual testing scenarios complete

**Estimated effort**: 1-2 hours (command definition + testing)

---

### Chunk 8: Cleanup Command

**Files**:
- `.claude/commands/cleanup.md` (NEW)

**Description**: State inspection and recovery command

**Why eighth**: Requires state_tracker, watchdog

**Test strategy**:
- Manual testing: Run /cleanup with no state
- Manual testing: Run /cleanup with completed state
- Manual testing: Run /cleanup with cancelled state
- Manual testing: Run /cleanup with crashed state
- Manual testing: Resume extraction
- Manual testing: Clear state

**Dependencies**: state_tracker, watchdog

**Commit point**: After manual testing scenarios complete

**Estimated effort**: 2-3 hours (command definition + testing)

---

### Chunk 9: Hook Integration

**Files**:
- `.claude/tools/hook_stop.py` (UPDATED)

**Description**: Add transcript tracking to session stop hook

**Why ninth**: Requires transcript_tracker, minimal change

**Test strategy**:
- Manual testing: End Claude Code session
- Verify transcript added to tracking file
- Verify extraction still queued (existing behavior)

**Dependencies**: transcript_tracker

**Commit point**: After manual testing verification

**Estimated effort**: 30 minutes (small change + testing)

---

### Chunk 10: Processor Integration

**Files**:
- `amplifier/memory/processor.py` (UPDATED)

**Description**: Add extraction logging and transcript tracking updates

**Why tenth**: Requires extraction_logger, transcript_tracker

**Test strategy**:
- Manual testing: Queue extraction, run processor
- Verify logs created in correct location
- Verify transcript marked as processed
- Verify existing functionality unchanged

**Dependencies**: extraction_logger, transcript_tracker

**Commit point**: After manual testing verification

**Estimated effort**: 30 minutes (small change + testing)

---

### Chunk 11: Integration Tests

**Files**:
- `tests/integration/test_exit_workflow.py` (NEW)

**Description**: End-to-end tests for complete exit workflow

**Why eleventh**: All modules must be implemented first

**Test strategy**:
- Test full exit flow: prompt → worker → progress → completion
- Test cancellation (Ctrl+C during extraction)
- Test crash recovery
- Test cleanup command scenarios

**Dependencies**: All previous chunks

**Commit point**: After integration tests pass

**Estimated effort**: 2-3 hours (comprehensive test coverage)

---

## Proper Sequencing

**Critical path**:
```
transcript_tracker → extraction_worker → watchdog → exit command
state_tracker → extraction_worker → watchdog → cleanup command
extraction_logger → extraction_worker
terminal_ui → watchdog
```

**Parallel opportunities**:
- Chunks 1, 2, 3, 4 can be built in parallel (no dependencies between them)
- Chunk 5 requires 1, 2, 3 complete
- Chunk 6 requires 4, 5 complete
- Chunks 7, 8 require 6 complete
- Chunks 9, 10 can happen in parallel after chunk 1 complete
- Chunk 11 requires all previous chunks

**Recommended order**: Sequential (1→2→3→4→5→6→7→8→9→10→11) to minimize context switching and enable continuous testing

---

## Complexity Check

### New Abstractions: 5

1. **TranscriptRecord** - Justification: Track transcript state in structured way
2. **ExtractionState** - Justification: Enable crash recovery with progress preservation
3. **ProgressState** - Justification: Decouple progress tracking from UI rendering
4. **ExtractionResult** - Justification: Type-safe result from watchdog
5. **TerminalUI** - Justification: Context manager for terminal cleanup

**Alternative considered**: Single monolithic class handling everything
**Why chosen**: Modular "bricks" approach - each class does one thing, can be regenerated independently

### Right-Sizing

**Largest module**: `extraction_worker.py` (~250 lines)
- ✅ Fits in AI context window (~4000-8000 lines)
- ✅ Has clear boundaries (subprocess entry point)
- ✅ Independently testable (can run as `python -m amplifier.memory.extraction_worker`)
- ✅ Regeneratable from spec (interface defined in docs)

**All other modules**: <250 lines each
- ✅ All fit comfortably in context window
- ✅ All have clear single responsibility
- ✅ All have defined interfaces ("studs")

---

## Estimated Effort

| Component | Effort | Lines |
|-----------|--------|-------|
| Chunk 1: Transcript Tracking | 2-3 hours | ~300 |
| Chunk 2: State Tracking | 2-3 hours | ~350 |
| Chunk 3: Logging System | 1-2 hours | ~150 |
| Chunk 4: Terminal UI | 2-3 hours | ~350 |
| Chunk 5: Extraction Worker | 3-4 hours | ~400 |
| Chunk 6: Watchdog Manager | 3-4 hours | ~400 |
| Chunk 7: Exit Command | 1-2 hours | ~50 |
| Chunk 8: Cleanup Command | 2-3 hours | ~100 |
| Chunk 9: Hook Integration | 30 min | ~10 |
| Chunk 10: Processor Integration | 30 min | ~15 |
| Chunk 11: Integration Tests | 2-3 hours | ~300 |

**Total**: 21-30 hours, ~2,425 new lines of code (including tests)

**Buffer**: Add 20% for debugging, revisions, documentation polish = 25-36 hours

---

## Testing Strategy

### Unit Tests (Per Chunk)

**Testing Philosophy**:
- Test interfaces, not internals
- Test behavior at "stud" level
- Minimal mocking (prefer real file I/O)
- Fast execution (<100ms per test)

**Coverage Target**: 80%+ for new modules

### Integration Tests

**File**: `tests/integration/test_exit_workflow.py`

**Scenarios**:
1. Full exit flow (happy path)
2. Cancellation (Ctrl+C)
3. Crash recovery
4. Cleanup command states
5. Resume extraction

**Philosophy**: Test complete user journeys, not individual functions

### Manual Testing

**Required before each commit**:
- Run the actual command
- Verify terminal output
- Check file system state
- Confirm existing features work

**User Testing Plan**:

**Scenario 1: Happy Path**
1. Start Claude Code session
2. Create some transcripts
3. Run `/exit`
4. Select "Y"
5. Verify progress UI shows
6. Verify completion summary
7. Verify transcripts marked processed

**Scenario 2: Cancellation**
1. Run `/exit`, select "Y"
2. Press Ctrl+C during extraction
3. Verify worker subprocess terminates
4. Run `/cleanup`
5. Verify state shows "cancelled"

**Scenario 3: Crash Recovery**
1. Kill worker subprocess mid-extraction (simulate crash)
2. Run `/cleanup`
3. Verify shows crashed state
4. Resume extraction
5. Verify completes successfully

**Scenario 4: Error Handling**
1. Queue extraction with invalid transcript path
2. Run `/exit`, select "Y"
3. Verify graceful error handling
4. Verify continues to next transcript

**Scenario 5: No Transcripts**
1. Run `/exit` with no unprocessed transcripts
2. Verify message "No unprocessed transcripts"
3. Verify exits normally

---

## Commit Strategy

### Commit Message Format

```
<type>: <subject>

<body>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types**: feat (new feature), test (add tests), refactor, docs

### Commit Plan

**Commit 1**: Transcript tracking system
```
feat: Add transcript tracking system for memory extraction

- Add TranscriptRecord dataclass for tracking state
- Add transcript_tracker module with JSON persistence
- Track processed status and memory counts
- Tests included

Tests passing: test_transcript_tracker.py
```

**Commit 2**: State tracking for crash recovery
```
feat: Add extraction state tracking for crash recovery

- Add ExtractionState model for crash recovery
- Add state_tracker module with JSON persistence
- Track extraction progress at transcript level
- Enable resume after crash/cancellation
- Tests included

Tests passing: test_state_tracker.py
```

**Commit 3**: Extraction logging system
```
feat: Add extraction logging system

- Add extraction_logger module
- Create .data/memories/logs/ structure
- Timestamp-based log files
- Centralized logging configuration
```

**Commit 4**: Terminal progress UI
```
feat: Add ASCII progress terminal UI

- Add TerminalUI class for progress rendering
- Progress bars, stage indicators
- Completion summary display
- Tests included

Tests passing: test_terminal_ui.py
```

**Commit 5**: Extraction worker subprocess
```
feat: Add extraction worker subprocess

- Add extraction_worker module (runnable as subprocess)
- Processes transcripts with progress reporting
- JSON-lines progress protocol
- Two-pass extraction (triage + deep)
- Tests included

Tests passing: test_extraction_worker.py
Entry point: python -m amplifier.memory.extraction_worker
```

**Commit 6**: Watchdog extraction manager
```
feat: Add watchdog extraction manager

- Add watchdog module for subprocess management
- Spawns extraction worker subprocess
- Monitors progress via stdout (JSON-lines)
- Renders terminal UI
- Tracks state for crash recovery
- Tests included

Tests passing: test_watchdog.py
```

**Commit 7**: Exit command with extraction prompt
```
feat: Add /exit command with extraction prompt

- Add .claude/commands/exit.md command definition
- Prompts user to extract memories before exit
- Integrates with watchdog manager
- Synchronous extraction with visible progress

Manual testing complete: all scenarios pass
```

**Commit 8**: Cleanup command for crash recovery
```
feat: Add /cleanup command for crash recovery

- Add .claude/commands/cleanup.md command definition
- Detects 6 state types (no state, running, completed, cancelled, crashed, failed)
- Offers appropriate recovery actions
- Resume, view logs, clear state, manual investigation

Manual testing complete: all scenarios pass
```

**Commit 9**: Integrate transcript tracking with hook
```
feat: Integrate transcript tracking with stop hook

- Update hook_stop.py to call transcript tracker
- Tracks all transcripts as they're created
- Maintains existing queue behavior

Manual testing complete: hook works as expected
```

**Commit 10**: Integrate logging with processor
```
feat: Integrate extraction logging with processor

- Update processor.py to use extraction logger
- Update transcript tracker after processing
- Maintains existing processing behavior

Manual testing complete: processor works as expected
```

**Commit 11**: End-to-end integration tests
```
test: Add exit workflow integration tests

- Add test_exit_workflow.py
- Tests full exit flow (prompt → worker → completion)
- Tests cancellation (Ctrl+C)
- Tests crash recovery
- Tests cleanup command

All integration tests passing
```

---

## Risk Assessment

### High Risk Changes

**Risk 1**: Subprocess spawning might fail on some systems
- **Mitigation**: Test on Linux, macOS, Windows WSL2
- **Fallback**: Document system requirements, provide troubleshooting

**Risk 2**: Progress JSON-lines parsing might fail if worker outputs non-JSON
- **Mitigation**: Strict JSON-lines protocol, error handling in watchdog
- **Fallback**: Gracefully handle malformed lines, log errors

**Risk 3**: State file corruption if process crashes mid-write
- **Mitigation**: Atomic write (write to temp, rename)
- **Fallback**: Corrupt state detection, offer manual cleanup

**Risk 4**: Terminal UI might not work in all terminal emulators
- **Mitigation**: Use standard ASCII only, test on common terminals
- **Fallback**: Simplified progress output if rendering fails

### Dependencies to Watch

**External dependencies**:
- None - using standard library only ✅

**Internal dependencies**:
- `amplifier.extraction.core.MemoryExtractor` (existing) - must maintain interface
- `amplifier.memory.core.MemoryStore` (existing) - must maintain interface

**Python version**:
- Requires Python 3.11+ (for `asyncio.timeout`)

### Breaking Changes

**None expected** - all changes are additive:
- New modules added
- Existing modules minimally modified (add logging, tracking)
- Existing queue-based background processing unchanged
- No changes to public APIs

---

## Philosophy Compliance

### Ruthless Simplicity

**✅ Start minimal**:
- Simple ASCII UI (not Rich library)
- JSON-lines for progress (not complex protocol)
- File-based state tracking (not database)
- Direct subprocess spawn (not daemon management)

**✅ Avoid future-proofing**:
- NOT building: Resume from specific transcript
- NOT building: Parallel extraction workers
- NOT building: Distributed extraction
- NOT building: Real-time progress streaming via SSE

**✅ Clear over clever**:
- Simple dataclasses (TranscriptRecord, ExtractionState)
- Clear function names (get_unprocessed_transcripts, run_extraction_with_watchdog)
- Direct subprocess communication (stdout)

### Modular Design (Bricks & Studs)

**Bricks (self-contained modules)**:
1. transcript_tracker.py - Pure data management
2. state_tracker.py - File-based persistence
3. extraction_logger.py - Logging only
4. terminal_ui.py - Pure rendering
5. extraction_worker.py - Runnable subprocess
6. watchdog.py - Process management

**Studs (interfaces)**:
- TranscriptRecord dataclass
- ExtractionState dataclass
- get_unprocessed_transcripts() function
- run_extraction_with_watchdog() function
- Progress update JSON schema

**Regeneratable**: Each brick can be rewritten from its interface spec without touching other bricks.

**Example**: Can completely rewrite terminal_ui.py (ASCII → Rich) without modifying extraction_worker.py or watchdog.py, as long as TerminalUI interface unchanged.

### Right-Sized Modules

**✅ Fit in AI context window**: Largest module ~250 lines
**✅ Clear boundaries**: Each module has single responsibility
**✅ Independently testable**: Each module has unit tests
**✅ Regeneratable from spec**: All interfaces documented in Phase 2 docs

---

## Success Criteria

Code is ready for Phase 4 when:

### Functional Requirements
- [ ] `/exit` command prompts for extraction
- [ ] Extraction runs synchronously with progress UI
- [ ] Progress shows in real-time
- [ ] Completion summary displays
- [ ] Transcripts tracked and marked processed
- [ ] `/cleanup` shows crashed extractions
- [ ] State recovery works
- [ ] Logs written to correct location

### User Experience
- [ ] Progress visible and clear
- [ ] Cancellation works cleanly (Ctrl+C)
- [ ] Error messages are helpful
- [ ] Logs are readable and useful
- [ ] No hidden background processing

### Robustness
- [ ] Subprocess isolation works
- [ ] Crash recovery functions
- [ ] Timeouts handled gracefully
- [ ] Concurrent access safe
- [ ] No orphaned processes

### Quality
- [ ] All unit tests pass (make test)
- [ ] Integration tests pass
- [ ] Manual testing scenarios complete
- [ ] Documentation complete
- [ ] Philosophy principles followed
- [ ] Code review passed

---

## Next Steps

✅ **Phase 3 (Code Planning) Complete**

**Awaiting user approval**

When approved, proceed to Phase 4:

```bash
/ddd:4-code
```

Phase 4 will implement the plan incrementally, with commit approval at each chunk.

---

## Notes for Implementation

### User Preference (from plan.md)

**IMPORTANT**: User clarified they do NOT want approval for every individual commit during Phase 4.

**Approach**:
- Implement in logical chunks (as defined above)
- Test each chunk thoroughly
- Commit when chunk complete and tested
- Present summary progress updates (not individual commits)
- Get approval at major milestones (after multiple chunks)

**Philosophy checks** (self-evaluate before commits):
- Before each commit, verify ruthless simplicity
- Check that brick boundaries are clear
- Ensure interfaces are stable
- Validate against "can we regenerate this brick from its spec?"

### Testing Discipline

- Write tests before implementation (TDD)
- Test interfaces, not internals
- Integration tests verify behavior
- Manual testing confirms user experience

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Ready for**: User approval → Phase 4 implementation
