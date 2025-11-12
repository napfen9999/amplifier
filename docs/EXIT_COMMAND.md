# Exit Command - Memory Extraction Workflow

The `/exit` command provides a user-controlled way to extract memories from unprocessed transcripts when ending a Claude Code session.

---

## Overview

When you run `/exit`, the system:
1. Checks for unprocessed transcripts
2. Prompts you to extract memories (Y/n)
3. If Yes: Runs synchronous extraction with visible progress
4. Shows completion summary
5. Exits normally

**Key principle**: Memory extraction happens **when you choose**, with **full visibility**, **not hidden in background**.

---

## Usage

### Basic Exit

```bash
/exit
```

### What Happens

**If no unprocessed transcripts**:
```
✓ No unprocessed transcripts
Exiting Claude Code...
```

**If unprocessed transcripts found**:
```
📝 Found 3 unprocessed transcript(s)

Extract memories before exit? (Y/n):
```

---

## Interactive Extraction

### Confirming Extraction (Y)

When you confirm with `Y`:

```
📝 Memory Extraction

Transcripts: [████████░░] 2/3
Current: Processing transcript abc123...

[TRIAGE]     Identifying important ranges... ✓
             Found 3 ranges (28% coverage)

[EXTRACTION] Processing 156 messages...
             [████████████████████████████░░] 85%

[STORAGE]    Saving memories... ✓
             Extracted 12 memories

─────────────────────────────────────────
Completed: 3/3 transcripts
Memories extracted: 38
Time: 1m 45s
```

**Progress indicators**:
- Overall transcript progress bar
- Current transcript being processed
- Stage-by-stage status (Triage → Extraction → Storage)
- Real-time percentage completion
- Memory count as extraction completes

### Declining Extraction (n)

When you decline with `n`:
```
Skipping memory extraction.
Exiting Claude Code...
```

Transcripts remain unprocessed and can be extracted later via `/cleanup`.

---

## Under the Hood

### Watchdog Pattern

The exit command uses a **watchdog pattern** for safety and visibility:

1. **Main Process** (Claude Code session):
   - Spawns extraction worker subprocess
   - Monitors progress via stdout
   - Renders terminal UI
   - Can terminate worker if needed

2. **Worker Subprocess**:
   - Reads extraction queue
   - Processes transcripts with intelligent sampling
   - Writes progress updates as JSON-lines to stdout
   - Saves memories to store
   - Exits when complete

**Benefits**:
- Process isolation (worker can crash without affecting session)
- Clean termination (kill worker subprocess if needed)
- Real-time progress (JSON-lines via stdout)
- Separate logs (worker logs to dedicated file)

### State Tracking

During extraction, state is saved to `.data/memories/.extraction_state.json`:

```json
{
  "status": "running",
  "started_at": "2025-11-12T15:30:00",
  "pid": 12345,
  "transcripts": [
    {"id": "abc123", "status": "completed", "memories": 8},
    {"id": "def456", "status": "in_progress"},
    {"id": "ghi789", "status": "pending"}
  ],
  "last_update": "2025-11-12T15:32:15"
}
```

This enables:
- Progress tracking across sessions
- Crash recovery (see [Crash Recovery Guide](CRASH_RECOVERY.md))
- Resume capability (via `/cleanup` command)

---

## Cancellation

### User Cancellation (Ctrl+C)

Press `Ctrl+C` during extraction to cancel:

```
^C
⚠️  Extraction cancelled by user

Processed: 2/3 transcripts
Memories extracted: 26

State saved. Run `/cleanup` to inspect or resume.
```

**What happens**:
1. Worker subprocess receives termination signal
2. Worker saves current progress
3. State marked as "cancelled"
4. Main process shows cancellation message
5. Exit proceeds normally

**Important**: Memories extracted before cancellation are **saved**. Only unprocessed transcripts remain in queue.

### Recovery After Cancellation

Use `/cleanup` command to:
- Inspect what was completed
- Resume extraction for remaining transcripts
- Clear cancelled state

See [Cleanup Command Guide](CLEANUP_COMMAND.md) for details.

---

## Extraction Process

### Intelligent Sampling

The worker uses **two-pass intelligent extraction**:

**Pass 1: Triage** (~10s per transcript)
- Scans all messages to identify important ranges
- Determines coverage (typically 10-40%)
- Outputs: List of message ranges to extract

**Pass 2: Deep Extraction** (~30-60s per transcript)
- Processes only identified ranges
- Extracts structured memories
- Saves to memory store

See [Extraction Worker Architecture](EXTRACTION_WORKER.md) for technical details.

### Progress Updates

Worker subprocess writes JSON-lines to stdout:

```json
{"type": "start", "total_transcripts": 3}
{"type": "progress", "current": 1, "session_id": "abc123", "stage": "triage"}
{"type": "triage_complete", "session_id": "abc123", "ranges": 3, "coverage": 0.28}
{"type": "extraction_complete", "session_id": "abc123", "memories": 8}
{"type": "summary", "transcripts": 3, "memories": 38, "time": "1m 45s"}
```

Main process parses these updates and renders the terminal UI.

---

## Logging

### Log Files

Extraction logs are written to `.data/memories/logs/` in the **parent repository** (not amplifier submodule):

```
.data/memories/logs/
├── extraction_worker_2025-11-12_15-30-00.log
├── extraction_worker_2025-11-12_16-45-00.log
└── extraction_latest.log  # Symlink to most recent
```

### Log Contents

Logs capture:
- Transcript processing start/end
- Triage pass results (ranges identified, coverage)
- Extraction pass results (memories extracted)
- Errors and warnings
- Timing information

**Example log entry**:
```
2025-11-12 15:30:15 [INFO] Starting extraction for abc123
2025-11-12 15:30:25 [INFO] Triage complete: 3 ranges, 28% coverage
2025-11-12 15:31:10 [INFO] Extraction complete: 8 memories
2025-11-12 15:31:12 [INFO] Saved to memory store
```

### Viewing Logs

```bash
# View latest extraction log
cat .data/memories/logs/extraction_latest.log

# View specific extraction
cat .data/memories/logs/extraction_worker_2025-11-12_15-30-00.log

# Tail during extraction (from another terminal)
tail -f .data/memories/logs/extraction_latest.log
```

---

## Error Handling

### Graceful Degradation

The system handles common errors gracefully:

**Missing API Key**:
```
⚠️  ANTHROPIC_API_KEY not found
    Skipping transcript abc123 (extraction requires API key)

Processed: 0/3 transcripts
Errors: 3 (missing API key)
```

**Insufficient Credits**:
```
⚠️  Anthropic account has insufficient credits
    Skipping transcript abc123

Processed: 2/3 transcripts
Errors: 1 (insufficient credits)
Memories extracted: 26
```

**Timeout**:
```
⚠️  Extraction timeout for transcript abc123
    Using fallback: processing last 50 messages

Processed: 3/3 transcripts
Warnings: 1 (timeout, used fallback)
Memories extracted: 35
```

**Corrupt Transcript**:
```
⚠️  Cannot read transcript def456 (corrupt file)
    Skipping...

Processed: 2/3 transcripts
Errors: 1 (corrupt transcript)
Memories extracted: 26
```

### Error Recovery

After errors:
1. Other transcripts continue processing
2. Error details logged to file
3. Summary shows error count
4. Use `/cleanup` to inspect specific failures

---

## Transcript Tracking

### Tracking System

The system tracks which transcripts have been processed in `.data/transcripts.json`:

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

**Automatically updated**:
- When transcript created (hook adds entry with `processed: false`)
- When extraction completes (marked `processed: true`)
- When memories extracted (count stored)

See [Transcript Tracking Guide](TRANSCRIPT_TRACKING.md) for technical details.

---

## Command Behavior

### Session State

Exit command behavior depends on session state:

**Active session with transcripts**:
- Check for unprocessed transcripts
- Prompt user for extraction
- Show progress if confirmed

**Session with no activity**:
- No transcripts to process
- Exit immediately

**Background processor running**:
- Exit command is independent
- Both can run simultaneously (different processes)

### Exit Flow

Complete exit flow:
1. `/exit` command invoked
2. Check for unprocessed transcripts
3. If found: Prompt user
4. If Yes: Run extraction (synchronous, visible)
5. Show summary
6. Normal Claude Code exit

**Total time**: Depends on transcripts (typically 1-3 minutes for 3-5 transcripts)

---

## Related Commands

- **`/cleanup`** - Inspect crashed extractions, resume or clear state
  - See [Cleanup Command Guide](CLEANUP_COMMAND.md)

---

## Configuration

Exit command uses these environment variables:

- `ANTHROPIC_API_KEY` - Required for extraction (LLM-based triage)
- `MEMORY_SYSTEM_ENABLED` - If false, skips extraction (default: true)
- `CLAUDE_PROJECT_DIR` - Base directory for data paths

No additional configuration needed.

---

## Best Practices

### When to Use

**Good scenarios**:
- ✅ Ending session after productive work
- ✅ When you want memories extracted now
- ✅ Before switching projects
- ✅ After long sessions with many exchanges

**Alternative workflows**:
- Background processor handles extraction asynchronously
- `/cleanup` for on-demand inspection and extraction

### Performance Considerations

**Extraction time scales with**:
- Number of unprocessed transcripts (1-3 min per transcript)
- Transcript size (triage scans all messages)
- API latency (network and Anthropic response times)

**Tips**:
- Decline extraction if in a hurry (transcripts remain in queue)
- Use background processor for automatic extraction
- Run `/cleanup` later if you cancelled

---

## Troubleshooting

### Exit hangs during extraction

**Symptoms**: Progress UI stops updating

**Causes**:
- Network timeout waiting for API
- Worker subprocess crashed

**Solutions**:
- Press `Ctrl+C` to cancel
- Run `/cleanup` to inspect state
- Check logs at `.data/memories/logs/extraction_latest.log`

### Transcripts not detected

**Symptoms**: Exit says "No unprocessed transcripts" but you had a session

**Causes**:
- Transcript tracking not initialized
- Hook didn't run (check `.claude/tools/hook_stop.py`)

**Solutions**:
- Verify `MEMORY_SYSTEM_ENABLED=true` in `.env`
- Check transcript exists in `.data/transcripts/`
- Inspect `.data/transcripts.json` for entries

### Extraction fails with errors

**Symptoms**: All transcripts show errors

**Causes**:
- Missing ANTHROPIC_API_KEY
- Invalid API key
- Insufficient credits

**Solutions**:
- Set `ANTHROPIC_API_KEY` in `.env`
- Verify API key is valid
- Check Anthropic account credits

---

## Technical Details

For developers and advanced users:

- **Architecture**: [Extraction Worker Architecture](EXTRACTION_WORKER.md)
- **State Tracking**: [Crash Recovery Guide](CRASH_RECOVERY.md)
- **Transcript System**: [Transcript Tracking Guide](TRANSCRIPT_TRACKING.md)
- **Memory System**: [Memory System Overview](MEMORY_SYSTEM.md)

---

## Examples

### Example 1: Normal Exit with Extraction

```
$ /exit

📝 Found 2 unprocessed transcript(s)

Extract memories before exit? (Y/n): Y

📝 Memory Extraction

Transcripts: [██████████] 2/2
Current: Processing transcript def456...

[TRIAGE]     Identifying important ranges... ✓
             Found 2 ranges (15% coverage)

[EXTRACTION] Processing 89 messages...
             [████████████████████████████████] 100%

[STORAGE]    Saving memories... ✓
             Extracted 6 memories

─────────────────────────────────────────
Completed: 2/2 transcripts
Memories extracted: 14
Time: 1m 25s

✓ Extraction complete
Exiting Claude Code...
```

### Example 2: Exit Without Extraction

```
$ /exit

📝 Found 1 unprocessed transcript(s)

Extract memories before exit? (Y/n): n

Skipping memory extraction.
Transcripts remain in queue (use /cleanup to process later).

Exiting Claude Code...
```

### Example 3: Cancellation

```
$ /exit

📝 Found 3 unprocessed transcript(s)

Extract memories before exit? (Y/n): Y

📝 Memory Extraction

Transcripts: [██████░░░░] 2/3
Current: Processing transcript ghi789...

[TRIAGE]     Identifying important ranges...
^C
⚠️  Extraction cancelled by user

Processed: 2/3 transcripts
Memories extracted: 18
Remaining: 1 transcript

State saved. Run `/cleanup` to inspect or resume.

Exiting Claude Code...
```

---

## Summary

The `/exit` command provides:
- **User control** over when extraction happens
- **Full visibility** into extraction progress
- **Graceful handling** of errors and cancellation
- **Clean recovery** via state tracking
- **No hidden background work** - you see everything

Use `/exit` when you want memories extracted **now**, with full visibility and control.

For automatic background extraction, rely on the background processor.
For inspection and recovery, use the `/cleanup` command.

---

**Related Documentation**:
- [Cleanup Command](CLEANUP_COMMAND.md) - Inspect and resume extractions
- [Crash Recovery](CRASH_RECOVERY.md) - State tracking and recovery
- [Transcript Tracking](TRANSCRIPT_TRACKING.md) - How transcripts are tracked
- [Memory System Overview](MEMORY_SYSTEM.md) - Complete memory system architecture
