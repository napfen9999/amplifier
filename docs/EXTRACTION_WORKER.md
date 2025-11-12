# Extraction Worker Architecture

The extraction worker is a subprocess that processes memory extraction queues, providing process isolation, progress visibility, and crash recovery for transcript processing.

---

## Overview

The extraction worker implements the **watchdog pattern**:
- **Main process** (Claude Code session): Spawns worker, monitors progress, renders UI
- **Worker subprocess**: Performs extraction work, reports progress, exits on completion

**Key benefits**:
- **Process isolation**: Worker crashes don't affect Claude Code
- **Clean termination**: Kill subprocess if needed without killing session
- **Real-time progress**: JSON-lines communication via stdout
- **Separate logs**: Worker logs independently to dedicated file

---

## Architecture

### Process Structure

```
┌─────────────────────────────────────┐
│   Main Process (Claude Code)       │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  Watchdog Manager           │   │
│  │  • Spawns subprocess        │   │
│  │  • Monitors stdout          │   │
│  │  • Renders terminal UI      │   │
│  │  • Can kill if needed       │   │
│  └─────────────────────────────┘   │
│              │                      │
│              │ spawn                │
│              ▼                      │
│  ┌─────────────────────────────┐   │
│  │  Extraction Worker          │◄──┼─── subprocess
│  │  (separate process)         │   │
│  │                             │   │
│  │  • Reads queue              │   │
│  │  • Processes transcripts    │   │
│  │  • Writes progress (stdout) │   │
│  │  • Logs to file             │   │
│  │  • Saves memories           │   │
│  │  • Exits on completion      │   │
│  └─────────────────────────────┘   │
│              │                      │
│              │ stdout (JSON-lines)  │
│              ▼                      │
│  ┌─────────────────────────────┐   │
│  │  Terminal UI                │   │
│  │  • Progress bars            │   │
│  │  • Stage indicators         │   │
│  │  • Memory counts            │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

---

## Worker Subprocess

### Entry Point

**File**: `amplifier/memory/extraction_worker.py`

**Invocation**:
```bash
python -m amplifier.memory.extraction_worker
```

**Arguments**: None (reads queue from file)

---

### Main Loop

```python
async def main():
    """Main extraction worker loop"""
    # 1. Setup logging to file
    setup_logging()

    # 2. Load unprocessed transcripts
    transcripts = get_unprocessed_transcripts()

    if not transcripts:
        print(json.dumps({"type": "no_work"}))
        return

    # 3. Report start
    print(json.dumps({
        "type": "start",
        "total_transcripts": len(transcripts)
    }))

    # 4. Process each transcript
    total_memories = 0
    for idx, transcript in enumerate(transcripts):
        try:
            memories = await process_transcript(transcript, idx + 1, len(transcripts))
            total_memories += memories

            # Mark as processed
            mark_transcript_processed(transcript.session_id, memories)

        except Exception as e:
            logger.error(f"Failed to process {transcript.session_id}: {e}")
            print(json.dumps({
                "type": "error",
                "session_id": transcript.session_id,
                "error": str(e)
            }))

    # 5. Report completion
    print(json.dumps({
        "type": "summary",
        "transcripts": len(transcripts),
        "memories": total_memories
    }))
```

---

### Progress Reporting

**Communication protocol**: JSON-lines to stdout

**Message types**:

#### 1. Start Message

```json
{"type": "start", "total_transcripts": 5}
```

Sent once at beginning.

---

#### 2. Progress Message

```json
{
  "type": "progress",
  "current": 2,
  "total": 5,
  "session_id": "def456",
  "stage": "triage"
}
```

Sent when starting new transcript.

**Stages**: `triage` | `extraction` | `storage`

---

#### 3. Triage Complete

```json
{
  "type": "triage_complete",
  "session_id": "def456",
  "ranges": 3,
  "coverage": 0.28
}
```

Sent after triage pass identifies important ranges.

---

#### 4. Extraction Progress

```json
{
  "type": "extraction_progress",
  "session_id": "def456",
  "messages_processed": 85,
  "messages_total": 156,
  "percent": 54
}
```

Sent periodically during deep extraction.

---

#### 5. Extraction Complete

```json
{
  "type": "extraction_complete",
  "session_id": "def456",
  "memories": 12
}
```

Sent after transcript fully processed.

---

#### 6. Error Message

```json
{
  "type": "error",
  "session_id": "def456",
  "error": "Timeout after 120s"
}
```

Sent if transcript processing fails.

---

#### 7. Summary Message

```json
{
  "type": "summary",
  "transcripts": 5,
  "memories": 42,
  "time": "2m 15s"
}
```

Sent once at end.

---

## Two-Pass Extraction

The worker uses **intelligent two-pass extraction** to optimize processing.

### Pass 1: Triage (~10s per transcript)

**Goal**: Identify important message ranges

**Process**:
1. Load full transcript (all messages)
2. Send to LLM with triage prompt
3. LLM identifies 3-10 ranges of interesting conversation
4. Calculate coverage (% of transcript)

**Output**: List of message ranges to extract deeply

**Example output**:
```json
{
  "ranges": [
    {"start": 5, "end": 42, "reason": "Design discussion of new feature"},
    {"start": 88, "end": 103, "reason": "Debugging session with insights"},
    {"start": 150, "end": 175, "reason": "Architecture decision"}
  ],
  "coverage": 0.28
}
```

---

### Pass 2: Deep Extraction (~30-60s per transcript)

**Goal**: Extract structured memories from identified ranges

**Process**:
1. For each range from triage:
   - Extract messages in range
   - Send to LLM with extraction prompt
   - LLM returns structured memories
   - Validate and save

2. Aggregate all memories
3. Save to memory store

**Output**: Structured memories saved to store

---

### Why Two-Pass?

**Alternative**: Process entire transcript deeply in one pass

**Problems with one-pass**:
- Slow (processes all messages, even unimportant)
- Expensive (sends all messages to LLM)
- Lower quality (LLM overwhelmed by volume)

**Benefits of two-pass**:
- Fast triage (finds important parts quickly)
- Focused extraction (processes only what matters)
- Better quality (LLM focuses on relevant content)
- Cost-effective (only deep process important ranges)

---

## State Management

### State Tracker Integration

**File**: `amplifier/memory/state_tracker.py`

**Worker updates state throughout processing**:

```python
from amplifier.memory.state_tracker import (
    save_extraction_state,
    ExtractionState
)

# Start
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

# Progress
for transcript in transcripts:
    # Update transcript status
    state.transcripts[idx]["status"] = "in_progress"
    save_extraction_state(state)

    # Process...

    # Mark complete
    state.transcripts[idx]["status"] = "completed"
    state.transcripts[idx]["memories"] = memories_count
    save_extraction_state(state)

# Complete
state.status = "completed"
save_extraction_state(state)
```

---

### State File Location

```
.data/memories/.extraction_state.json
```

**Purpose**: Enables crash recovery and cleanup command inspection.

See [Crash Recovery Guide](CRASH_RECOVERY.md) for details.

---

## Logging

### Log File Location

```
.data/memories/logs/extraction_worker_YYYY-MM-DD_HH-MM-SS.log
.data/memories/logs/extraction_latest.log  # Symlink
```

Located in **parent repository** (not amplifier submodule).

---

### Log Configuration

```python
import logging

def setup_logging():
    """Configure worker logging"""
    log_dir = Path(".data/memories/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Timestamped log file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"extraction_worker_{timestamp}.log"

    # Also create symlink to latest
    latest_link = log_dir / "extraction_latest.log"
    if latest_link.exists():
        latest_link.unlink()
    latest_link.symlink_to(log_file)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            # Note: stdout used for progress JSON, not logs
        ]
    )
```

---

### What Gets Logged

**INFO level**:
- Worker start/stop
- Transcript processing start/end
- Triage results (ranges found, coverage)
- Extraction results (memories extracted)
- State updates

**WARNING level**:
- Timeouts (with fallback action)
- Missing API keys
- Retry attempts

**ERROR level**:
- Failed transcripts (with error details)
- Corrupt transcript files
- API errors
- Unexpected exceptions

**Example log**:
```
2025-11-12 15:30:00 [INFO] Worker started (PID: 12345)
2025-11-12 15:30:00 [INFO] Found 5 unprocessed transcripts
2025-11-12 15:30:00 [INFO] Starting transcript 1/5: abc123
2025-11-12 15:30:10 [INFO] Triage complete: 3 ranges, 28% coverage
2025-11-12 15:30:55 [INFO] Extraction complete: 8 memories
2025-11-12 15:30:56 [INFO] Starting transcript 2/5: def456
2025-11-12 15:31:06 [INFO] Triage complete: 2 ranges, 15% coverage
2025-11-12 15:31:40 [INFO] Extraction complete: 6 memories
...
2025-11-12 15:35:00 [INFO] All transcripts processed
2025-11-12 15:35:00 [INFO] Total memories: 42
2025-11-12 15:35:00 [INFO] Worker exiting
```

---

## Error Handling

### Graceful Degradation

The worker handles errors without crashing the entire batch.

#### Missing API Key

```python
try:
    memories = await extract_memories(transcript)
except MissingAPIKeyError:
    logger.warning(f"Skipping {transcript.session_id}: No API key")
    print(json.dumps({
        "type": "error",
        "session_id": transcript.session_id,
        "error": "Missing ANTHROPIC_API_KEY"
    }))
    continue  # Skip to next transcript
```

**Result**: Continues processing other transcripts

---

#### Timeout

```python
try:
    memories = await asyncio.wait_for(
        extract_memories(transcript),
        timeout=120.0
    )
except asyncio.TimeoutError:
    logger.warning(f"Timeout for {transcript.session_id}, using fallback")
    # Fallback: process last 50 messages only
    memories = await extract_memories_simple(transcript, last_n=50)
```

**Result**: Falls back to simpler extraction

---

#### Corrupt Transcript

```python
try:
    messages = load_transcript(transcript.transcript_path)
except JSONDecodeError:
    logger.error(f"Corrupt transcript: {transcript.session_id}")
    print(json.dumps({
        "type": "error",
        "session_id": transcript.session_id,
        "error": "Corrupt transcript file"
    }))
    continue
```

**Result**: Skips corrupt file, continues with others

---

#### API Error

```python
try:
    memories = await extract_memories(transcript)
except AnthropicAPIError as e:
    if e.status_code == 429:  # Rate limit
        logger.warning("Rate limit hit, waiting...")
        await asyncio.sleep(60)
        # Retry once
        memories = await extract_memories(transcript)
    else:
        logger.error(f"API error: {e}")
        raise  # Fail this transcript
```

**Result**: Retries rate limits, fails on other API errors

---

## Watchdog Manager

**File**: `amplifier/memory/watchdog.py`

**Purpose**: Spawns and monitors worker subprocess

### Manager Responsibilities

1. **Spawn subprocess**:
   ```python
   process = subprocess.Popen(
       ["python", "-m", "amplifier.memory.extraction_worker"],
       stdout=subprocess.PIPE,
       stderr=subprocess.PIPE,
       text=True,
       bufsize=1  # Line buffered
   )
   ```

2. **Monitor stdout**:
   ```python
   for line in process.stdout:
       try:
           message = json.loads(line)
           handle_progress_message(message)
       except json.JSONDecodeError:
           logger.warning(f"Invalid progress message: {line}")
   ```

3. **Render UI**:
   ```python
   def handle_progress_message(message):
       if message["type"] == "progress":
           terminal_ui.update_progress(
               current=message["current"],
               total=message["total"]
           )
       elif message["type"] == "triage_complete":
           terminal_ui.show_triage_results(
               ranges=message["ranges"],
               coverage=message["coverage"]
           )
       # ... other message types
   ```

4. **Handle termination**:
   ```python
   try:
       return_code = process.wait()
       if return_code == 0:
           terminal_ui.show_success()
       else:
           terminal_ui.show_error(return_code)
   except KeyboardInterrupt:
       process.terminate()
       terminal_ui.show_cancelled()
   ```

---

## Terminal UI

**File**: `amplifier/memory/terminal_ui.py`

**Purpose**: ASCII progress rendering

### UI Components

**Progress bar**:
```
Transcripts: [████████░░] 4/5
```

**Current status**:
```
Current: Processing transcript def456...
```

**Stage indicators**:
```
[TRIAGE]     Identifying important ranges... ✓
             Found 3 ranges (28% coverage)
```

**Extraction progress**:
```
[EXTRACTION] Processing 156 messages...
             [████████████████████████████░░] 85%
```

**Storage confirmation**:
```
[STORAGE]    Saving memories... ✓
             Extracted 12 memories
```

**Summary**:
```
─────────────────────────────────────────
Completed: 4/5 transcripts
Memories extracted: 38
Time: 1m 45s
```

---

## Performance Characteristics

### Timing Expectations

**Per transcript**:
- Triage: 5-15 seconds
- Deep extraction: 20-90 seconds (depends on range count)
- Total: 30-120 seconds per transcript

**For batch of 5 transcripts**:
- Best case: ~2.5 minutes (fast triage, few ranges)
- Typical: ~5 minutes (normal ranges, no errors)
- Worst case: ~10 minutes (many ranges, retries)

---

### Resource Usage

**Memory**:
- Worker process: 100-300 MB
- Depends on transcript size
- Released on exit

**CPU**:
- Low (mostly I/O bound)
- Spikes during triage/extraction
- Idle during API calls

**Network**:
- Depends on LLM API calls
- ~1-5 API calls per transcript
- Retries on failures

---

## Testing

### Unit Testing

**Test worker functions in isolation**:

```python
import pytest
from amplifier.memory.extraction_worker import process_transcript

@pytest.mark.asyncio
async def test_process_transcript(sample_transcript):
    """Test processing single transcript"""
    memories = await process_transcript(sample_transcript, 1, 1)
    assert memories > 0
    assert isinstance(memories, int)

@pytest.mark.asyncio
async def test_triage_pass(sample_transcript):
    """Test triage identifies ranges"""
    ranges = await triage_transcript(sample_transcript)
    assert len(ranges) > 0
    assert all("start" in r and "end" in r for r in ranges)
```

---

### Integration Testing

**Test worker subprocess end-to-end**:

```python
def test_worker_subprocess(tmp_path, sample_transcripts):
    """Test worker subprocess execution"""
    # Setup test environment
    setup_test_transcripts(tmp_path, sample_transcripts)

    # Run worker
    result = subprocess.run(
        ["python", "-m", "amplifier.memory.extraction_worker"],
        capture_output=True,
        text=True,
        timeout=300
    )

    # Verify output
    assert result.returncode == 0
    messages = [json.loads(line) for line in result.stdout.split('\n') if line]
    assert messages[0]["type"] == "start"
    assert messages[-1]["type"] == "summary"
    assert messages[-1]["memories"] > 0
```

---

### Watchdog Testing

**Test manager spawning and monitoring**:

```python
def test_watchdog_manager(sample_transcripts):
    """Test watchdog spawns and monitors worker"""
    from amplifier.memory.watchdog import run_extraction_with_watchdog

    result = run_extraction_with_watchdog()

    assert result.transcripts_processed > 0
    assert result.total_memories > 0
    assert result.errors == []
```

---

## Troubleshooting

### Worker Not Starting

**Symptoms**: Watchdog reports worker failed to start

**Diagnosis**:
```bash
# Try running worker directly
python -m amplifier.memory.extraction_worker
```

**Causes**:
- Import errors (missing dependencies)
- Python path issues
- Permission problems

---

### Worker Hangs

**Symptoms**: No progress for extended time

**Diagnosis**:
```bash
# Check if process still alive
ps aux | grep extraction_worker

# Check logs for activity
tail -f .data/memories/logs/extraction_latest.log
```

**Causes**:
- API timeout (should have 120s timeout)
- Network issues
- Deadlock (rare)

**Solution**: Kill process, check logs, retry

---

### Progress Not Updating

**Symptoms**: UI stuck on one transcript

**Diagnosis**:
```bash
# Check worker stdout
tail -f .data/memories/logs/extraction_latest.log
```

**Causes**:
- Worker crashed (no more JSON output)
- stdout buffer full (unlikely with line buffering)
- Manager parsing error

**Solution**: Check logs, verify JSON-lines valid

---

## Related Documentation

- [Exit Command](EXIT_COMMAND.md) - Uses watchdog to run worker
- [Cleanup Command](CLEANUP_COMMAND.md) - Inspects worker state
- [Crash Recovery](CRASH_RECOVERY.md) - State tracking for recovery
- [Transcript Tracking](TRANSCRIPT_TRACKING.md) - Worker updates tracking
- [Memory System](MEMORY_SYSTEM.md) - Complete system architecture

---

## Summary

The extraction worker provides:
- **Process isolation** via subprocess
- **Progress visibility** via JSON-lines protocol
- **Crash recovery** via state tracking
- **Intelligent extraction** via two-pass processing
- **Graceful degradation** for common errors
- **Independent logging** to dedicated files

**Key design principles**:
- Watchdog pattern for safety
- JSON-lines for simple communication
- Two-pass for efficiency
- Continue on errors (don't fail entire batch)
- State tracking for recovery

---

**Implementation details**: See `amplifier/memory/extraction_worker.py` and `amplifier/memory/watchdog.py` for complete implementation.
