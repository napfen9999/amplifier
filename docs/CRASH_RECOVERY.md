# Crash Recovery System

The crash recovery system tracks extraction state, enabling resumption after interruptions, crashes, or cancellations without losing work.

---

## Overview

The system provides:
1. **Real-time state tracking** during extraction
2. **Crash detection** when worker process dies unexpectedly
3. **Resume capability** to continue from interruption point
4. **Progress preservation** - completed work never lost
5. **Clean recovery** via `/cleanup` command

**Key principle**: Extraction progress is saved continuously. Interruptions can be recovered from, not restarted.

---

## State Tracking

### State File

**Location**: `.data/memories/.extraction_state.json`

**Created**: When extraction starts

**Updated**: After each transcript completes

**Removed**: After successful completion or cleanup

---

### State Schema

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
    },
    {
      "id": "ghi789",
      "status": "pending"
    }
  ],
  "last_update": "2025-11-12T15:32:00"
}
```

### Field Definitions

**status** (string):
- `running`: Extraction currently in progress
- `completed`: Successfully finished
- `failed`: Encountered errors, stopped
- `cancelled`: User interrupted (Ctrl+C)

**started_at** (string, ISO8601):
- When extraction began
- Used to calculate duration

**pid** (integer | null):
- Process ID of worker subprocess
- `null` if not currently running
- Used to detect if process still alive

**transcripts** (array):
- List of all transcripts in queue
- Status tracked per transcript
- Memories count stored on completion

**last_update** (string, ISO8601):
- Last state modification time
- Used to detect stale processes

---

### Transcript Status

Each transcript in the state has:

```json
{
  "id": "abc123",
  "status": "pending | in_progress | completed | failed",
  "memories": 8,  // Only if completed
  "completed_at": "2025-11-12T15:31:00",  // Only if completed
  "error": "Timeout"  // Only if failed
}
```

---

## State Lifecycle

### 1. Start

**When**: Extraction begins (via `/exit` or manual trigger)

**Action**: Create state file

```python
state = ExtractionState(
    status="running",
    started_at=datetime.now().isoformat(),
    pid=os.getpid(),
    transcripts=[
        {"id": t.session_id, "status": "pending"}
        for t in transcripts
    ],
    last_update=datetime.now().isoformat()
)
save_extraction_state(state)
```

---

### 2. Progress

**When**: Transcript processing starts/completes

**Action**: Update state

```python
# Starting transcript
state.transcripts[idx]["status"] = "in_progress"
state.last_update = datetime.now().isoformat()
save_extraction_state(state)

# Completing transcript
state.transcripts[idx]["status"] = "completed"
state.transcripts[idx]["memories"] = memories_count
state.transcripts[idx]["completed_at"] = datetime.now().isoformat()
state.last_update = datetime.now().isoformat()
save_extraction_state(state)
```

---

### 3. Completion

**When**: All transcripts processed successfully

**Action**: Mark complete, then remove state

```python
state.status = "completed"
save_extraction_state(state)

# Then cleanup automatically
clear_extraction_state()
```

**Normal flow**: State file removed on success.

---

### 4. Cancellation

**When**: User presses Ctrl+C during extraction

**Action**: Mark cancelled, preserve state

```python
state.status = "cancelled"
state.last_update = datetime.now().isoformat()
save_extraction_state(state)
```

**State preserved** for potential resume.

---

### 5. Crash

**When**: Worker process dies unexpectedly

**Action**: State file left in "running" status with stale PID

**Detection**: `/cleanup` checks if PID still exists

```python
if state.status == "running" and not process_exists(state.pid):
    # Crashed - process is dead but state says running
    state.status = "crashed"
```

---

## Crash Detection

### How Crashes Are Detected

**Via `/cleanup` command**:

```python
def detect_state():
    """Determine current extraction state"""
    if not state_file_exists():
        return "no_state"

    state = load_extraction_state()

    if state.status in ["completed", "failed", "cancelled"]:
        return state.status

    if state.status == "running":
        if process_exists(state.pid):
            return "running"
        else:
            return "crashed"  # Process dead

    return "unknown"
```

**Process existence check**:
```python
def process_exists(pid):
    """Check if process is still running"""
    try:
        os.kill(pid, 0)  # Signal 0 = existence check
        return True
    except OSError:
        return False
```

---

### Types of Crashes

#### 1. Clean Crash

**Cause**: Worker caught exception, logged error, exited with code 1

**State**: `status: "failed"`, error details in log

**Recovery**: Check logs, fix issue, resume

---

#### 2. Hard Crash

**Cause**: Segfault, kill -9, system reboot

**State**: `status: "running"`, PID doesn't exist

**Recovery**: `/cleanup` detects crash, offers resume

---

#### 3. Hang (Appears as Crash)

**Cause**: Worker stuck, appears dead

**State**: `status: "running"`, PID exists but no progress

**Detection**: Compare `last_update` to current time

```python
def is_stale(state):
    """Check if state hasn't updated in 10+ minutes"""
    last_update = datetime.fromisoformat(state.last_update)
    elapsed = datetime.now() - last_update
    return elapsed.total_seconds() > 600
```

**Recovery**: Kill stale process, then resume

---

## Recovery Process

### Automatic Resume

**When running `/cleanup` after crash**:

```
⚠️  Extraction Process Crashed

Progress before crash:
• Transcripts processed: 2/5
• Remaining: 3 transcripts

Options:
1. Resume extraction
2. View crash logs
3. Clear state
4. Exit

Choose option: 1
```

**What happens**:

```python
def resume_extraction():
    """Resume interrupted extraction"""
    # 1. Load existing state
    state = load_extraction_state()

    # 2. Find remaining transcripts
    remaining = [
        t for t in state.transcripts
        if t["status"] in ["pending", "failed"]
    ]

    # 3. Count completed memories
    completed_memories = sum(
        t.get("memories", 0)
        for t in state.transcripts
        if t["status"] == "completed"
    )

    # 4. Process remaining
    new_memories = process_transcripts(remaining)

    # 5. Update totals
    total_memories = completed_memories + new_memories

    # 6. Clean up state
    clear_extraction_state()

    return total_memories
```

---

### What Gets Preserved

**On resume**:
- ✅ Completed transcripts (not reprocessed)
- ✅ Memory counts from completed (added to new total)
- ✅ Remaining transcript queue
- ✅ Extraction configuration

**On resume**:
- ❌ In-progress transcript (must restart that one)
- ❌ Temporary LLM state (no checkpointing mid-transcript)
- ❌ Worker PID (new process spawned)

---

## State File Operations

### Save State

```python
from amplifier.memory.state_tracker import save_extraction_state

state = ExtractionState(
    status="running",
    started_at=datetime.now().isoformat(),
    pid=os.getpid(),
    transcripts=transcripts,
    last_update=datetime.now().isoformat()
)

save_extraction_state(state)
```

**File locking**: Uses exclusive lock during write to prevent corruption.

---

### Load State

```python
from amplifier.memory.state_tracker import load_extraction_state

state = load_extraction_state()

if state:
    print(f"Status: {state.status}")
    print(f"Progress: {completed_count}/{total_count}")
else:
    print("No extraction state found")
```

**Returns**: `ExtractionState` object or `None` if file doesn't exist.

---

### Clear State

```python
from amplifier.memory.state_tracker import clear_extraction_state

clear_extraction_state()
```

**Action**: Removes `.extraction_state.json` file.

**Use**: After successful completion or when abandoning work.

---

## Concurrent Access Safety

### File Locking

```python
import fcntl

def save_extraction_state(state):
    """Save state with file lock"""
    with open(STATE_FILE, 'w') as f:
        # Exclusive lock
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)

        json.dump(dataclasses.asdict(state), f, indent=2)

        # Unlock
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

**Why needed**: Multiple processes might try to read/write state:
- Worker subprocess updating progress
- Main process checking status
- `/cleanup` command inspecting state

---

### Atomic Updates

```python
def update_transcript_status(session_id, status, **kwargs):
    """Atomically update single transcript status"""
    state = load_extraction_state()

    for transcript in state.transcripts:
        if transcript["id"] == session_id:
            transcript["status"] = status
            transcript.update(kwargs)
            break

    state.last_update = datetime.now().isoformat()
    save_extraction_state(state)
```

**Pattern**: Load → Modify → Save (with locking)

---

## Error Scenarios

### Scenario 1: Worker Crashes Mid-Transcript

**What happens**:
1. Worker processing transcript #3 of 5
2. Worker crashes (segfault, kill -9, system reboot)
3. State file shows: 2 completed, 1 in_progress, 2 pending

**Recovery**:
```bash
/cleanup
# Detects crash
# Offers resume
# Processes: transcript #3 (restart), #4, #5
# Total memories: 2 completed + 3 new
```

**Result**: Transcripts #1 and #2 not reprocessed.

---

### Scenario 2: User Cancels (Ctrl+C)

**What happens**:
1. User presses Ctrl+C during extraction
2. Worker catches signal, marks state as "cancelled"
3. State file shows: N completed, 0 in_progress, M pending

**Recovery**:
```bash
/cleanup
# Detects cancellation
# Offers resume
# Processes: M remaining transcripts
```

**Result**: Previously completed work preserved.

---

### Scenario 3: State File Corruption

**What happens**:
1. Disk error, manual edit, or crash during write
2. State file contains invalid JSON

**Detection**:
```python
try:
    state = load_extraction_state()
except json.JSONDecodeError:
    print("⚠️  State file corrupted")
```

**Recovery**:
```bash
/cleanup
# Detects corruption
# Options:
#   1. View raw file (try to salvage)
#   2. Delete corrupt state (lose recovery info)
#   3. Exit (manual investigation)
```

**Manual recovery**:
```bash
# View corrupt file
cat .data/memories/.extraction_state.json

# Try to fix manually
vim .data/memories/.extraction_state.json

# Or restore from backup if exists
cp .data/memories/.extraction_state.json.backup .data/memories/.extraction_state.json
```

---

### Scenario 4: Stale State (Old Running Process)

**What happens**:
1. Extraction started days ago
2. Process long dead but state says "running"
3. `last_update` timestamp is old

**Detection**:
```python
if state.status == "running":
    if not process_exists(state.pid):
        return "crashed"
    elif is_stale(state):
        return "stale"
```

**Recovery**:
```bash
/cleanup
# Detects stale state
# Treats as crashed
# Offers resume or cleanup
```

---

## Best Practices

### For Users

✅ **DO**:
- Use `/cleanup` after any interruption
- Check logs if crash happens
- Resume when possible (preserves completed work)
- Clear state if abandoning work

❌ **DON'T**:
- Manually edit state file
- Delete state file without checking
- Assume extraction auto-resumes (it doesn't)

---

### For Developers

✅ **DO**:
- Update state after each transcript completes
- Use file locking for all state operations
- Save state before potentially crashing operations
- Clear state on successful completion
- Test crash recovery scenarios

❌ **DON'T**:
- Cache state in memory (always load fresh)
- Skip locking (causes corruption)
- Leave state file after success
- Assume state file always valid

---

## Testing Crash Recovery

### Simulating Crashes

#### Test 1: Kill Worker Mid-Extraction

```bash
# Terminal 1: Start extraction
/exit
# Select Y to extract

# Terminal 2: Kill worker while running
ps aux | grep extraction_worker
kill -9 <PID>

# Terminal 1: Run cleanup
/cleanup
# Should detect crash
# Verify resume works
```

---

#### Test 2: Interrupt with Ctrl+C

```bash
# Start extraction
/exit

# Press Ctrl+C after 1-2 transcripts

# Check state
cat .data/memories/.extraction_state.json
# Should show "cancelled" status

# Resume
/cleanup
# Select option 1: Resume
```

---

#### Test 3: Corrupt State File

```bash
# Start extraction, let 1 transcript complete, then kill

# Corrupt state file
echo "invalid json" > .data/memories/.extraction_state.json

# Run cleanup
/cleanup
# Should detect corruption
# Options should include viewing/deleting
```

---

### Automated Tests

```python
import pytest
from amplifier.memory.state_tracker import (
    save_extraction_state,
    load_extraction_state,
    clear_extraction_state
)

def test_crash_recovery(tmp_path, monkeypatch):
    """Test crash recovery flow"""
    # Setup
    monkeypatch.setattr("amplifier.memory.state_tracker.STATE_FILE", tmp_path / "state.json")

    # Create initial state
    state = ExtractionState(
        status="running",
        started_at="2025-11-12T15:30:00",
        pid=12345,
        transcripts=[
            {"id": "t1", "status": "completed", "memories": 5},
            {"id": "t2", "status": "in_progress"},
            {"id": "t3", "status": "pending"}
        ],
        last_update="2025-11-12T15:32:00"
    )
    save_extraction_state(state)

    # Simulate crash (load state, PID doesn't exist)
    loaded = load_extraction_state()
    assert loaded.status == "running"
    assert loaded.pid == 12345

    # Resume extraction
    remaining = [t for t in loaded.transcripts if t["status"] != "completed"]
    assert len(remaining) == 2  # t2, t3

    # Verify completed work preserved
    completed = [t for t in loaded.transcripts if t["status"] == "completed"]
    assert completed[0]["memories"] == 5
```

---

## Monitoring and Debugging

### Check Current State

```bash
# Is extraction running?
python3 -c "
from amplifier.memory.state_tracker import load_extraction_state
state = load_extraction_state()
if state:
    print(f'Status: {state.status}')
    print(f'PID: {state.pid}')
    completed = sum(1 for t in state.transcripts if t['status'] == 'completed')
    print(f'Progress: {completed}/{len(state.transcripts)}')
else:
    print('No extraction state')
"
```

---

### View State History

```bash
# Find all state backups
ls -lt .data/memories/.extraction_state.json*

# View specific backup
cat .data/memories/.extraction_state.json.backup | python3 -m json.tool
```

---

### Track State Changes

```bash
# Watch state file for changes
watch -n 1 'cat .data/memories/.extraction_state.json | python3 -m json.tool'
```

---

## Integration with Commands

### Exit Command

**Creates state**: When extraction starts

```python
# In /exit command
state = ExtractionState(
    status="running",
    started_at=datetime.now().isoformat(),
    pid=worker_pid,
    transcripts=unprocessed_transcripts,
    last_update=datetime.now().isoformat()
)
save_extraction_state(state)
```

**Clears state**: On successful completion

```python
# After extraction completes
clear_extraction_state()
```

---

### Cleanup Command

**Loads state**: To determine what to show user

```python
# In /cleanup command
state = load_extraction_state()

if not state:
    print("✓ No extraction state found")
    return

if state.status == "cancelled":
    show_resume_options(state)
elif state.status == "crashed":
    show_crash_recovery_options(state)
elif state.status == "completed":
    show_cleanup_options(state)
```

---

## Related Documentation

- [Exit Command](EXIT_COMMAND.md) - Creates and manages state
- [Cleanup Command](CLEANUP_COMMAND.md) - Uses state for recovery
- [Extraction Worker](EXTRACTION_WORKER.md) - Updates state during processing
- [Transcript Tracking](TRANSCRIPT_TRACKING.md) - Permanent transcript records
- [Memory System](MEMORY_SYSTEM.md) - Complete system architecture

---

## Summary

The crash recovery system provides:
- **Continuous state tracking** during extraction
- **Crash detection** via PID checks
- **Resume capability** from interruption points
- **Work preservation** - never lose completed extractions
- **Clean recovery** via `/cleanup` command

**Key benefits**:
- Interruptions don't lose work
- Can resume from any crash type
- State always reflects truth
- Recovery is user-initiated, not automatic

**Design principles**:
- Save state after each transcript (granular checkpoints)
- File locking prevents corruption
- PID tracking enables crash detection
- User controls recovery (not automatic)

---

**Implementation details**: See `amplifier/memory/state_tracker.py` for complete implementation.
