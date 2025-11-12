# DDD Plan: Exit-Command Feature

**Status**: Phase 1 Planning
**Created**: 2025-11-12
**Branch**: feature/exit-command

---

## Problem Statement

**What we're solving**: Users currently have no way to extract memories from unprocessed transcripts when exiting Claude Code sessions. The background processor runs silently with no visibility, and users have no control over when extraction happens.

**Why it matters**:
- Memory extraction happens invisibly in background - user has no control
- No feedback on progress or completion
- No way to verify what was processed
- Crashed extractions leave orphaned state with no recovery
- User wants **synchronous, visible processing** when they choose to exit

**User value**:
- Control over memory extraction timing
- Clear visibility into extraction progress
- Confidence that transcripts were processed
- Ability to recover from crashed extractions
- No hidden background work

---

## Proposed Solution

### High-Level Approach

**Watchdog Pattern with Subprocess Execution**:

1. `/exit` command checks for unprocessed transcripts
2. Prompts user: "Extract memories from unprocessed transcripts? (Y/n)"
3. If Yes: Spawns subprocess worker that processes queue
4. Main process monitors subprocess, shows progress in terminal UI
5. Progress updates via JSON-lines from subprocess stdout
6. State tracking for crash recovery
7. `/cleanup` command to inspect/resume crashed extractions
8. Logs written to `.data/memories/logs/` in parent repo

**Key Components**:
- Transcript tracking system (`transcripts.json`)
- Exit command (`.claude/commands/exit.md`)
- Cleanup command (`.claude/commands/cleanup.md`)
- Extraction worker (subprocess)
- Watchdog manager (spawns/monitors subprocess)
- Terminal UI (ASCII progress bar + status)
- State tracker (crash recovery)
- Logging system

---

## Alternatives Considered

### Alternative 1: Direct Synchronous Processing (Simpler)

**Approach**: `/exit` command directly calls `process_extraction_queue()` without subprocess

**Pros**:
- Simpler implementation (no subprocess management)
- Fewer moving parts
- Easier debugging

**Cons**:
- ❌ Blocks Claude Code from exiting if extraction hangs
- ❌ No isolation if extraction crashes
- ❌ Can't kill runaway extraction without killing session
- ❌ All output mixed with Claude Code logs

**Verdict**: ❌ **Rejected** - User explicitly wants **watchdog pattern** for safety

### Alternative 2: Background Processing with Polling (Middle Ground)

**Approach**: Spawn background daemon, `/exit` polls for completion

**Pros**:
- Process isolation
- Can timeout and exit

**Cons**:
- ❌ Requires daemon management (start/stop)
- ❌ More complex than subprocess
- ❌ Polling creates UI lag

**Verdict**: ❌ **Rejected** - Watchdog with subprocess is cleaner

### Alternative 3: Watchdog + Subprocess (Recommended)

**Approach**: Main process spawns subprocess worker, monitors via stdout

**Pros**:
- ✅ Process isolation (worker can crash without affecting session)
- ✅ Clean termination (kill subprocess if needed)
- ✅ Real-time progress (JSON-lines via stdout)
- ✅ Clean logs (worker logs to separate file)
- ✅ Matches user's Task Manager analogy

**Cons**:
- Slightly more complex than direct execution
- Requires subprocess spawning

**Verdict**: ✅ **CHOSEN** - Best balance of safety, visibility, control

---

## Architecture & Design

### Key Interfaces ("Studs")

#### 1. Transcript Tracking Interface

```python
@dataclass
class TranscriptRecord:
    """Record of a transcript file"""
    session_id: str
    transcript_path: str
    created_at: str  # ISO8601
    processed: bool = False
    processed_at: str | None = None
    memories_extracted: int = 0

def get_unprocessed_transcripts() -> list[TranscriptRecord]:
    """Get all transcripts that haven't been processed"""

def mark_transcript_processed(session_id: str, memories_count: int) -> None:
    """Mark transcript as processed"""

def add_transcript_record(session_id: str, transcript_path: str) -> None:
    """Add new transcript to tracking"""
```

**Storage**: `.data/transcripts.json`

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

#### 2. Extraction Worker Interface

```python
async def run_extraction_worker() -> ExtractionResult:
    """
    Worker process that extracts memories from queue.
    Writes JSON-lines progress updates to stdout.
    Returns summary result.
    """

@dataclass
class ExtractionResult:
    transcripts_processed: int
    total_memories: int
    time_taken: float
    errors: list[str]
```

**Progress updates** (JSON-lines to stdout):
```json
{"type": "start", "total_transcripts": 5}
{"type": "progress", "current": 1, "total": 5, "session_id": "abc123", "stage": "triage"}
{"type": "triage_complete", "session_id": "abc123", "ranges": 3, "coverage": 0.25}
{"type": "extraction_complete", "session_id": "abc123", "memories": 8}
{"type": "summary", "transcripts": 5, "memories": 42, "time": "2m 15s"}
```

#### 3. Watchdog Interface

```python
def run_extraction_with_watchdog() -> ExtractionResult:
    """
    Spawn subprocess worker, monitor progress, show UI.
    Returns result when subprocess completes.
    """
```

#### 4. State Tracker Interface

```python
@dataclass
class ExtractionState:
    """State tracking for crash recovery"""
    status: str  # "running" | "completed" | "failed" | "cancelled"
    started_at: str
    pid: int | None
    transcripts: list[dict]
    last_update: str

def save_extraction_state(state: ExtractionState) -> Path:
    """Save state to .data/memories/.extraction_state.json"""

def load_extraction_state() -> ExtractionState | None:
    """Load state if exists"""

def clear_extraction_state() -> None:
    """Clear state after successful completion"""
```

#### 5. Terminal UI Interface

```python
class TerminalUI:
    """ASCII-based progress UI"""

    def __enter__(self):
        """Setup terminal"""

    def __exit__(self, *args):
        """Cleanup terminal"""

    def update(self, progress_data: dict) -> None:
        """Update progress display"""

    def show_summary(self, result: ExtractionResult) -> None:
        """Show final summary"""
```

**UI Layout**:
```
📝 Memory Extraction

Transcripts: [████████░░] 4/5
Current: Processing transcript def456...

[TRIAGE]     Identifying important ranges... ✓
             Found 3 ranges (28% coverage)

[EXTRACTION] Processing 156 messages...
             [████████████████████████████░░] 85%

[STORAGE]    Saving memories... ✓
             Extracted 12 memories

─────────────────────────────────────────
Completed: 4/5 transcripts
Memories extracted: 38
Time: 1m 45s
```

### Module Boundaries

#### Brick 1: Transcript Tracking (`amplifier/memory/transcript_tracker.py`)
- **Purpose**: Track which transcripts have been processed
- **Inputs**: Session ID, transcript path
- **Outputs**: List of unprocessed transcripts
- **Storage**: `.data/transcripts.json`
- **Dependencies**: None (pure data management)

#### Brick 2: Extraction Worker (`amplifier/memory/extraction_worker.py`)
- **Purpose**: Subprocess that processes extraction queue
- **Inputs**: None (reads from queue file)
- **Outputs**: JSON-lines progress to stdout
- **Dependencies**: `processor.py`, `queue.py`, existing extraction system
- **Runnable**: `python -m amplifier.memory.extraction_worker`

#### Brick 3: Watchdog Manager (`amplifier/memory/watchdog.py`)
- **Purpose**: Spawn and monitor extraction worker subprocess
- **Inputs**: None (checks queue automatically)
- **Outputs**: ExtractionResult
- **Dependencies**: `extraction_worker.py`, `terminal_ui.py`, `state_tracker.py`

#### Brick 4: State Tracker (`amplifier/memory/state_tracker.py`)
- **Purpose**: Track extraction state for crash recovery
- **Inputs**: State updates
- **Outputs**: Saved state JSON
- **Storage**: `.data/memories/.extraction_state.json`
- **Dependencies**: None

#### Brick 5: Terminal UI (`amplifier/memory/terminal_ui.py`)
- **Purpose**: ASCII progress rendering
- **Inputs**: Progress updates (dict)
- **Outputs**: Terminal display
- **Dependencies**: None (pure rendering)

#### Brick 6: Exit Command (`.claude/commands/exit.md`)
- **Purpose**: User-facing exit command
- **Inputs**: User Y/n response
- **Outputs**: Calls watchdog if Yes
- **Dependencies**: `watchdog.py`, `transcript_tracker.py`

#### Brick 7: Cleanup Command (`.claude/commands/cleanup.md`)
- **Purpose**: Inspect and resume crashed extractions
- **Inputs**: None (reads state file)
- **Outputs**: Shows state, offers resume/clear
- **Dependencies**: `state_tracker.py`, `watchdog.py`

#### Brick 8: Logging System (`amplifier/memory/extraction_logger.py`)
- **Purpose**: Centralized extraction logging
- **Inputs**: Log messages
- **Outputs**: Log files in `.data/memories/logs/`
- **Dependencies**: None

---

## Files to Change

### Non-Code Files (Phase 2)

#### New Documentation
- [ ] `docs/EXIT_COMMAND.md` - Exit command user guide
- [ ] `docs/CLEANUP_COMMAND.md` - Cleanup command user guide
- [ ] `docs/TRANSCRIPT_TRACKING.md` - Transcript tracking system docs
- [ ] `docs/EXTRACTION_WORKER.md` - Worker subprocess architecture
- [ ] `docs/CRASH_RECOVERY.md` - State tracking and recovery guide

#### Updated Documentation
- [ ] `docs/MEMORY_SYSTEM.md` - Add exit workflow section
- [ ] `README.md` - Add exit command to feature list

#### New Commands
- [ ] `.claude/commands/exit.md` - Exit command definition
- [ ] `.claude/commands/cleanup.md` - Cleanup command definition

### Code Files (Phase 4)

#### New Modules
- [ ] `amplifier/memory/transcript_tracker.py` - Transcript tracking system
- [ ] `amplifier/memory/extraction_worker.py` - Worker subprocess
- [ ] `amplifier/memory/watchdog.py` - Watchdog manager
- [ ] `amplifier/memory/state_tracker.py` - State persistence
- [ ] `amplifier/memory/terminal_ui.py` - Progress UI
- [ ] `amplifier/memory/extraction_logger.py` - Logging utilities

#### Updated Modules
- [ ] `amplifier/memory/processor.py` - Add logging integration
- [ ] `.claude/tools/hook_stop.py` - Call transcript tracker

#### New Tests
- [ ] `tests/memory/test_transcript_tracker.py` - Transcript tracking tests
- [ ] `tests/memory/test_extraction_worker.py` - Worker tests
- [ ] `tests/memory/test_watchdog.py` - Watchdog tests
- [ ] `tests/memory/test_state_tracker.py` - State tracking tests
- [ ] `tests/memory/test_terminal_ui.py` - UI rendering tests
- [ ] `tests/integration/test_exit_workflow.py` - End-to-end exit tests

#### New Logs Directory
- [ ] `.data/memories/logs/` - Log directory (created at runtime)

---

## Philosophy Alignment

### Ruthless Simplicity

**Start minimal**:
- ✅ Simple ASCII UI (not Rich library initially)
- ✅ JSON-lines for progress (not complex protocol)
- ✅ File-based state tracking (not database)
- ✅ Direct subprocess spawn (not daemon management)

**Avoid future-proofing**:
- ❌ NOT building: Resume from specific transcript
- ❌ NOT building: Parallel extraction workers
- ❌ NOT building: Distributed extraction
- ❌ NOT building: Real-time progress streaming via SSE

**Clear over clever**:
- Simple data structures (dataclasses)
- Clear function names (`run_extraction_with_watchdog`)
- Direct subprocess communication (stdout)

### Modular Design

**Bricks (self-contained modules)**:
1. `transcript_tracker.py` - Pure data management
2. `extraction_worker.py` - Runnable subprocess
3. `watchdog.py` - Process management
4. `state_tracker.py` - File-based persistence
5. `terminal_ui.py` - Pure rendering
6. `extraction_logger.py` - Logging only

**Studs (interfaces)**:
- `TranscriptRecord` dataclass
- `ExtractionResult` dataclass
- `ExtractionState` dataclass
- `get_unprocessed_transcripts()` function
- `run_extraction_worker()` function
- Progress update JSON schema

**Regeneratable**:
- Each brick can be rewritten from its interface spec
- Interfaces are stable, implementations flexible
- Tests verify behavior at interface level

### Bricks and Studs

**Example**: Can completely rewrite `terminal_ui.py` (switch ASCII to Rich) without touching other bricks, as long as:
- Constructor signature unchanged
- `update(progress_data: dict)` signature unchanged
- `show_summary(result: ExtractionResult)` signature unchanged

---

## Test Strategy

### Unit Tests

#### `test_transcript_tracker.py`
- Test add_transcript_record()
- Test mark_transcript_processed()
- Test get_unprocessed_transcripts()
- Test JSON persistence
- Test concurrent access safety

#### `test_extraction_worker.py`
- Test worker processes queue items
- Test progress JSON-lines output
- Test graceful error handling
- Test timeout behavior

#### `test_watchdog.py`
- Test subprocess spawning
- Test progress monitoring
- Test subprocess termination (normal/kill)
- Test timeout handling
- Test state tracking integration

#### `test_state_tracker.py`
- Test save_extraction_state()
- Test load_extraction_state()
- Test clear_extraction_state()
- Test concurrent access

#### `test_terminal_ui.py`
- Test progress bar rendering
- Test stage indicators
- Test summary display
- Test terminal cleanup

### Integration Tests

#### `test_exit_workflow.py`
- Test full exit flow: prompt → worker → progress → completion
- Test cancellation (Ctrl+C)
- Test crash recovery
- Test cleanup command

### User Testing

**Manual test scenarios**:

1. **Happy path**:
   - Start session, create transcripts
   - Run `/exit`
   - Select "Y"
   - Verify progress UI shows
   - Verify completion summary
   - Verify transcripts marked processed

2. **Cancellation**:
   - Run `/exit`, select "Y"
   - Press Ctrl+C during extraction
   - Verify worker subprocess terminates
   - Run `/cleanup`
   - Verify state shows "cancelled"

3. **Crash recovery**:
   - Kill worker subprocess mid-extraction (simulate crash)
   - Run `/cleanup`
   - Verify shows crashed state
   - Resume extraction
   - Verify completes successfully

4. **Error handling**:
   - Queue extraction with invalid transcript path
   - Run `/exit`, select "Y"
   - Verify graceful error handling
   - Verify continues to next transcript

5. **No transcripts**:
   - Run `/exit` with no unprocessed transcripts
   - Verify message "No unprocessed transcripts"
   - Verify exits normally

---

## Implementation Approach

### Phase 2 (Docs) - Document the Design

**Order** (dependencies first):
1. `docs/TRANSCRIPT_TRACKING.md` - Core concept
2. `docs/EXTRACTION_WORKER.md` - Worker architecture
3. `docs/CRASH_RECOVERY.md` - State tracking
4. `docs/EXIT_COMMAND.md` - User guide
5. `docs/CLEANUP_COMMAND.md` - Cleanup guide
6. Update `docs/MEMORY_SYSTEM.md` - Add exit workflow
7. Update `README.md` - Add feature

**Style**: Write as if already implemented (retcon writing)

### Phase 4 (Code) - Implement in Small Commits

**Chunk 1: Transcript Tracking Foundation**
- `transcript_tracker.py` implementation
- `test_transcript_tracker.py` tests
- Integration with `hook_stop.py`
- COMMIT: "feat: Add transcript tracking system"

**Chunk 2: State Tracking**
- `state_tracker.py` implementation
- `test_state_tracker.py` tests
- COMMIT: "feat: Add extraction state tracking for crash recovery"

**Chunk 3: Logging System**
- `extraction_logger.py` implementation
- Create `.data/memories/logs/` structure
- COMMIT: "feat: Add extraction logging system"

**Chunk 4: Terminal UI**
- `terminal_ui.py` implementation
- `test_terminal_ui.py` tests
- COMMIT: "feat: Add ASCII progress terminal UI"

**Chunk 5: Extraction Worker**
- `extraction_worker.py` implementation
- Progress JSON-lines output
- `test_extraction_worker.py` tests
- COMMIT: "feat: Add extraction worker subprocess"

**Chunk 6: Watchdog Manager**
- `watchdog.py` implementation
- Subprocess spawning and monitoring
- `test_watchdog.py` tests
- COMMIT: "feat: Add watchdog extraction manager"

**Chunk 7: Exit Command**
- `.claude/commands/exit.md` definition
- Integration with watchdog
- COMMIT: "feat: Add /exit command with extraction prompt"

**Chunk 8: Cleanup Command**
- `.claude/commands/cleanup.md` definition
- State inspection and resume logic
- COMMIT: "feat: Add /cleanup command for crash recovery"

**Chunk 9: Integration Tests**
- `test_exit_workflow.py` end-to-end tests
- COMMIT: "test: Add exit workflow integration tests"

**Chunk 10: Documentation Updates**
- Update processor.py with logging
- Final documentation polish
- COMMIT: "docs: Complete exit-command documentation"

---

## Success Criteria

**Feature complete when**:

1. **Functional**:
   - [ ] `/exit` command prompts for extraction
   - [ ] Extraction runs synchronously with progress UI
   - [ ] Progress shows in real-time
   - [ ] Completion summary displays
   - [ ] Transcripts tracked and marked processed
   - [ ] `/cleanup` shows crashed extractions
   - [ ] State recovery works

2. **User Experience**:
   - [ ] Progress visible and clear
   - [ ] Cancellation works cleanly (Ctrl+C)
   - [ ] Error messages are helpful
   - [ ] Logs are readable and useful
   - [ ] No hidden background processing

3. **Robustness**:
   - [ ] Subprocess isolation works
   - [ ] Crash recovery functions
   - [ ] Timeouts handled gracefully
   - [ ] Concurrent access safe
   - [ ] No orphaned processes

4. **Quality**:
   - [ ] All unit tests pass
   - [ ] Integration tests pass
   - [ ] Manual testing scenarios complete
   - [ ] Documentation complete
   - [ ] Philosophy principles followed

---

## Next Steps

✅ Plan complete and approved

➡️ **Ready for**: `/ddd:2-docs`

**Process**:
1. User reviews and approves this plan
2. Run `/ddd:2-docs` to update all documentation
3. Run `/ddd:3-code-plan` to prepare implementation
4. Run `/ddd:4-code` to implement in chunks (with commit approval at each chunk)
5. Run `/ddd:5-finish` for cleanup and finalization

---

## Notes for Implementation

**User requirement**: "ich will vorallem bich jeden einzelnen commit beim coding abhken müssen"
- User wants to approve EACH commit during Phase 4
- Implement in very small chunks
- Request approval before each `git commit`
- Keep commits granular and focused

**Philosophy checks**:
- Before each commit, verify ruthless simplicity
- Check that brick boundaries are clear
- Ensure interfaces are stable
- Validate against "can we regenerate this brick from its spec?"

**Testing discipline**:
- Write tests before implementation
- Test interfaces, not internals
- Integration tests verify behavior
- Manual testing confirms user experience

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
