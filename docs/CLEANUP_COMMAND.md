# Cleanup Command - Extraction State Management

The `/cleanup` command provides inspection and recovery for memory extraction state, allowing you to view, resume, or clear extraction status when needed.

---

## Overview

The cleanup command helps manage extraction state by:
1. Detecting if extraction is running, completed, or crashed
2. Showing detailed state information
3. Offering to resume interrupted extractions
4. Cleaning up completed or cancelled state

**Key principle**: Provides full transparency and control over extraction state without hidden automation.

---

## Usage

### Basic Usage

```bash
/cleanup
```

The command automatically detects the current state and presents appropriate options.

---

## State Detection

### No State Found

```
✓ No extraction state found

Memory extraction system is clean. No active or pending extractions.
```

**What this means**: Normal operation. No extractions running or interrupted.

---

### Extraction Running

```
⚠️  Extraction Currently Running

Started: 2025-11-12 15:30:00
PID: 12345
Progress: 2/5 transcripts

The extraction worker is currently processing. You can:
- Wait for it to complete
- Cancel it with Ctrl+C if needed
- Check logs: .data/memories/logs/extraction_latest.log

Run /cleanup again after it completes to clear state.
```

**What this means**: Another process is actively extracting. Let it finish or cancel it first.

---

### Extraction Completed Successfully

```
✓ Extraction Completed Successfully

Started: 2025-11-12 15:30:00
Completed: 2025-11-12 15:35:00
Duration: 5m

Results:
• Transcripts processed: 5
• Memories extracted: 42
• Errors: 0

State file can be cleaned up.

Clean up state? (Y/n):
```

**Options**:
- **Y**: Removes state file
- **n**: Keeps state file for reference

---

### Extraction Failed

```
⚠️  Extraction Failed

Started: 2025-11-12 15:30:00
Failed: 2025-11-12 15:32:15
Duration: 2m 15s

Results:
• Transcripts processed: 2/5
• Memories extracted: 18
• Errors: 3

Error details:
• transcript_abc123: Missing API key
• transcript_def456: Timeout after 120s
• transcript_ghi789: Corrupt file

Options:
1. View detailed logs
2. Clear state (discard remaining transcripts)
3. Exit (keep state for investigation)

Choose option (1-3):
```

**Options**:
- **1**: Opens log file in viewer
- **2**: Removes state, abandons remaining transcripts
- **3**: Exits, keeps state for later investigation

---

### Extraction Cancelled by User

```
⚠️  Extraction Was Cancelled

Started: 2025-11-12 15:30:00
Cancelled: 2025-11-12 15:32:00
Duration: 2m (interrupted)

Progress before cancellation:
• Transcripts processed: 2/5
• Memories extracted: 18
• Remaining: 3 transcripts

Options:
1. Resume extraction (process remaining transcripts)
2. Clear state (abandon remaining transcripts)
3. Exit (keep state for later decision)

Choose option (1-3):
```

**Options**:
- **1**: Resumes extraction from where it stopped
- **2**: Removes state, abandons remaining transcripts
- **3**: Exits, keeps state for later decision

---

### Extraction Crashed

```
⚠️  Extraction Process Crashed

Started: 2025-11-12 15:30:00
Last update: 2025-11-12 15:32:00
PID: 12345 (process not found)

Progress before crash:
• Transcripts processed: 2/5
• Memories extracted: 18
• Remaining: 3 transcripts

Last known stage: EXTRACTION
Last transcript: transcript_def456

Check logs for crash details:
  .data/memories/logs/extraction_latest.log

Options:
1. Resume extraction (process remaining transcripts)
2. View crash logs
3. Clear state (abandon remaining transcripts)
4. Exit (keep state for investigation)

Choose option (1-4):
```

**Options**:
- **1**: Attempts to resume from crash point
- **2**: Opens log file showing crash details
- **3**: Removes state, abandons remaining transcripts
- **4**: Exits, keeps state for investigation

---

## Resuming Extraction

When you choose to resume an interrupted or crashed extraction:

### Resume Process

```
📝 Resuming Memory Extraction

Remaining transcripts: 3

Transcripts: [██████████░░░░] 2/5 → 3/5
Current: Processing transcript ghi789...

[TRIAGE]     Identifying important ranges... ✓
             Found 4 ranges (35% coverage)

[EXTRACTION] Processing 203 messages...
             [████████████████████████████████] 100%

[STORAGE]    Saving memories... ✓
             Extracted 15 memories

─────────────────────────────────────────
Completed: 5/5 transcripts
Memories extracted: 51 (18 previous + 33 new)
Time: 3m 25s

✓ Extraction complete
State cleaned up automatically.
```

**What happens**:
1. Loads previous state
2. Identifies remaining transcripts
3. Processes each one with full progress UI
4. Adds to existing memory count
5. Cleans up state on success

---

## State File Location

The extraction state is stored at:
```
.data/memories/.extraction_state.json
```

### State File Structure

```json
{
  "status": "cancelled",
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
      "status": "completed",
      "memories": 10,
      "completed_at": "2025-11-12T15:32:00"
    },
    {
      "id": "ghi789",
      "status": "pending"
    },
    {
      "id": "jkl012",
      "status": "pending"
    },
    {
      "id": "mno345",
      "status": "pending"
    }
  ],
  "last_update": "2025-11-12T15:32:00"
}
```

**Fields**:
- `status`: running | completed | failed | cancelled
- `started_at`: ISO8601 timestamp
- `pid`: Process ID of worker (null if not running)
- `transcripts`: Array of transcript status
- `last_update`: Last state modification time

---

## Manual State Investigation

### View State File

```bash
cat .data/memories/.extraction_state.json | python3 -m json.tool
```

Shows formatted JSON state for manual inspection.

### Check Process Still Running

```bash
ps aux | grep 12345
```

Verifies if PID in state file is still active.

### View Recent Logs

```bash
cat .data/memories/logs/extraction_latest.log
```

Shows latest extraction log for troubleshooting.

### Find All Extraction Logs

```bash
ls -lt .data/memories/logs/extraction_worker_*.log
```

Lists all extraction logs sorted by time (newest first).

---

## Common Scenarios

### Scenario 1: Forgot if Extraction Completed

**Problem**: You ran `/exit` yesterday, not sure if extraction finished.

**Solution**:
```bash
/cleanup
```

**Result**: Shows completion status and offers to clean up state.

---

### Scenario 2: Extraction Cancelled by Mistake

**Problem**: Pressed Ctrl+C during extraction, want to continue.

**Solution**:
```bash
/cleanup
# Select option 1: Resume extraction
```

**Result**: Continues from where it stopped, processes remaining transcripts.

---

### Scenario 3: Computer Crashed During Extraction

**Problem**: System reboot interrupted extraction, not sure what completed.

**Solution**:
```bash
/cleanup
# View state showing what completed
# Select option 1: Resume extraction
```

**Result**: Resumes from crash point, only processes unfinished transcripts.

---

### Scenario 4: Extraction Seems Stuck

**Problem**: Extraction running for very long time, might be hung.

**Solution**:
```bash
# Terminal 1: Check if process alive
ps aux | grep extraction_worker

# Terminal 2: Check log for recent activity
tail -f .data/memories/logs/extraction_latest.log

# If stuck: Kill process
kill <PID>

# Then clean up
/cleanup
# Select appropriate option based on state
```

**Result**: Can investigate, kill if needed, and resume or clean up.

---

### Scenario 5: Want to Retry Failed Transcript

**Problem**: Extraction failed on one transcript due to temporary issue (API timeout).

**Solution**:
```bash
/cleanup
# Shows failed transcripts with error details
# Resume will retry failed transcripts
# Select option 1: Resume extraction
```

**Result**: Retries failed transcripts with fresh attempt.

---

## Error Handling

### Missing State File

```
✓ No extraction state found

Memory extraction system is clean.
```

**Normal**: State file only exists when extraction is active or interrupted.

---

### Corrupt State File

```
⚠️  Extraction State Corrupted

Cannot read state file: .data/memories/.extraction_state.json
Error: Invalid JSON at line 5

Options:
1. View raw state file
2. Delete corrupt state (lose recovery info)
3. Exit (manual investigation needed)

Choose option (1-3):
```

**Rare**: State file became corrupted (disk error, manual edit).

---

### State File Permission Issues

```
⚠️  Cannot Access State File

Permission denied: .data/memories/.extraction_state.json

Fix permissions:
  chmod 644 .data/memories/.extraction_state.json

Or run with appropriate permissions.
```

**Fix**: Correct file permissions.

---

## Logging Integration

### Cleanup Actions Logged

All cleanup command actions are logged to:
```
.data/memories/logs/cleanup_YYYY-MM-DD_HH-MM-SS.log
```

**Log contents**:
- State detected
- User choices
- Actions taken
- Results

**Example log**:
```
2025-11-12 16:00:00 [INFO] Cleanup command invoked
2025-11-12 16:00:00 [INFO] State detected: cancelled
2025-11-12 16:00:00 [INFO] Progress: 2/5 transcripts completed
2025-11-12 16:00:01 [INFO] User chose: Resume extraction
2025-11-12 16:00:01 [INFO] Starting resume from transcript 3/5
2025-11-12 16:03:25 [INFO] Resume complete: 3 additional transcripts processed
2025-11-12 16:03:25 [INFO] Total memories: 51 (18 previous + 33 new)
2025-11-12 16:03:25 [INFO] State cleaned up
```

---

## Best Practices

### When to Use /cleanup

**Good times**:
- After any interrupted extraction
- When you're unsure of extraction status
- Before running new extraction (clear old state)
- When troubleshooting memory issues
- After system crash or reboot

**Not needed**:
- After successful completion (auto-cleans)
- During active extraction (let it finish)
- For routine operation (only for recovery)

---

### State Management Strategy

**Regular workflow**:
1. Run `/exit` → extraction completes → state auto-cleaned
2. No manual cleanup needed

**After interruption**:
1. Run `/cleanup` → see what happened
2. Resume if appropriate
3. Or clear state if not needed

**After crash**:
1. Check logs first (understand what failed)
2. Run `/cleanup` → inspect state
3. Resume if problem fixed
4. Or clear and re-queue if problem persists

---

## Integration with Exit Command

### How They Work Together

**Exit command** (`/exit`):
- Creates state file when extraction starts
- Updates state during processing
- Cleans up state on successful completion
- Leaves state file on interruption/crash

**Cleanup command** (`/cleanup`):
- Reads state file left by exit command
- Offers recovery options
- Can resume interrupted work
- Cleans up when done

**Example flow**:
```
1. /exit → Starts extraction → State created
2. Ctrl+C → Cancelled → State preserved
3. /cleanup → Detects cancelled state → Offers resume
4. Resume → Completes → State cleaned
```

---

## Advanced Usage

### Programmatic State Check

Check state without interactive prompts:

```bash
# Check if state exists
test -f .data/memories/.extraction_state.json && echo "State exists"

# Get state status
python3 -c "
import json
with open('.data/memories/.extraction_state.json') as f:
    state = json.load(f)
    print(f\"Status: {state['status']}\")
    print(f\"Progress: {sum(1 for t in state['transcripts'] if t['status'] == 'completed')}/{len(state['transcripts'])}\")
"
```

---

### Manual State Reset

**Nuclear option** (use with caution):

```bash
# Remove state file
rm .data/memories/.extraction_state.json

# Verify removal
ls .data/memories/.extraction_state.json
# Should show: No such file or directory
```

**Use only when**:
- State is definitely corrupt beyond repair
- You want to abandon ALL pending work
- You understand you'll lose recovery info

---

## Troubleshooting

### Cleanup Says "Running" But Nothing Happening

**Symptom**: Cleanup reports extraction running, but no progress visible.

**Diagnosis**:
```bash
# Check if process actually exists
ps aux | grep <PID>

# Check recent log activity
tail -20 .data/memories/logs/extraction_latest.log
```

**Solutions**:
- If process dead: State is stale, choose "Clear state"
- If process alive but stuck: Kill process, then cleanup
- If process working: Wait for completion

---

### Resume Fails Immediately

**Symptom**: Choose resume, but fails right away.

**Causes**:
1. **Missing API key**: Set `ANTHROPIC_API_KEY` in environment
2. **Insufficient credits**: Top up Anthropic account
3. **Corrupt transcripts**: Check transcript files exist and are valid JSON

**Solution**: Fix underlying issue, run `/cleanup` again, resume.

---

### State File Keeps Coming Back

**Symptom**: Clean up state, but file reappears.

**Cause**: Extraction still running in background.

**Solution**:
```bash
# Find all extraction processes
ps aux | grep extraction_worker

# Kill them
kill <PID>

# Now cleanup will work
/cleanup
```

---

## Related Commands

- **`/exit`** - Exit Claude Code with optional extraction
  - See [Exit Command Guide](EXIT_COMMAND.md)

---

## Technical Details

For developers and advanced users:

- **Architecture**: [Extraction Worker Architecture](EXTRACTION_WORKER.md)
- **State Tracking**: [Crash Recovery Guide](CRASH_RECOVERY.md)
- **Transcript System**: [Transcript Tracking Guide](TRANSCRIPT_TRACKING.md)
- **Memory System**: [Memory System Overview](MEMORY_SYSTEM.md)

---

## Examples

### Example 1: Resuming After Cancellation

```bash
$ /cleanup

⚠️  Extraction Was Cancelled

Started: 2025-11-12 15:30:00
Cancelled: 2025-11-12 15:32:00

Progress before cancellation:
• Transcripts processed: 2/5
• Memories extracted: 18
• Remaining: 3 transcripts

Options:
1. Resume extraction (process remaining transcripts)
2. Clear state (abandon remaining transcripts)
3. Exit (keep state for later decision)

Choose option (1-3): 1

📝 Resuming Memory Extraction

[Extraction proceeds with progress UI]

✓ Extraction complete
Total memories: 51 (18 previous + 33 new)
State cleaned up.
```

---

### Example 2: Clearing After Crash

```bash
$ /cleanup

⚠️  Extraction Process Crashed

Last update: 2025-11-12 15:32:00
Progress: 2/5 transcripts

Options:
1. Resume extraction
2. View crash logs
3. Clear state
4. Exit

Choose option (1-4): 2

[Opens log viewer showing crash details]

Press Enter to continue...

Choose option (1-4): 3

State cleared.

✓ Cleanup complete
```

---

### Example 3: No State Found

```bash
$ /cleanup

✓ No extraction state found

Memory extraction system is clean. No active or pending extractions.
```

---

## Summary

The `/cleanup` command provides:
- **Inspection** of extraction state
- **Recovery** from interruptions
- **Cleanup** after completion
- **Transparency** into what happened
- **Control** over resumption or abandonment

Use `/cleanup` whenever extraction doesn't complete normally, and you need to:
- See what happened
- Resume interrupted work
- Clean up old state
- Investigate failures

---

**Related Documentation**:
- [Exit Command](EXIT_COMMAND.md) - Memory extraction on exit
- [Crash Recovery](CRASH_RECOVERY.md) - State tracking and recovery
- [Transcript Tracking](TRANSCRIPT_TRACKING.md) - How transcripts are tracked
- [Memory System Overview](MEMORY_SYSTEM.md) - Complete memory system architecture
