# Transcript Tracking System

The transcript tracking system maintains a record of all Claude Code session transcripts, tracking which have been processed for memory extraction and which are pending.

---

## Overview

The system provides:
1. **Automatic recording** of new transcripts as they're created
2. **Status tracking** (processed vs. unprocessed)
3. **Memory count** for completed extractions
4. **Timestamp metadata** for creation and processing times
5. **Single source of truth** for transcript state

**Key principle**: Every transcript is tracked from creation through processing, providing complete visibility into extraction history.

---

## How It Works

### Automatic Tracking Flow

```
1. Claude Code session ends
   ↓
2. Hook creates transcript file
   ↓
3. Hook calls transcript tracker
   ↓
4. New record added to transcripts.json
   ↓
5. Record marked as processed: false
   ↓
6. Extraction processes transcript
   ↓
7. Record marked as processed: true
   ↓
8. Memory count stored
```

**No manual tracking needed** - happens automatically on session stop.

---

## Data Structure

### Storage Location

```
.data/transcripts.json
```

Located in the parent repository (not amplifier submodule).

### JSON Schema

```json
{
  "version": "1.0",
  "transcripts": [
    {
      "session_id": "abc123",
      "transcript_path": "/path/to/transcript_abc123.jsonl",
      "created_at": "2025-11-12T15:30:00",
      "processed": true,
      "processed_at": "2025-11-12T15:35:00",
      "memories_extracted": 15
    },
    {
      "session_id": "def456",
      "transcript_path": "/path/to/transcript_def456.jsonl",
      "created_at": "2025-11-12T16:45:00",
      "processed": false,
      "processed_at": null,
      "memories_extracted": 0
    }
  ]
}
```

### Field Definitions

**version** (string):
- Format version of this JSON structure
- Currently: "1.0"

**session_id** (string):
- Unique identifier for Claude Code session
- Matches transcript filename
- Format: UUID or timestamp-based

**transcript_path** (string):
- Absolute path to JSONL transcript file
- Used to locate transcript for processing

**created_at** (string, ISO8601):
- When transcript file was created
- Set by hook on session end
- Format: `YYYY-MM-DDTHH:MM:SS`

**processed** (boolean):
- `false`: Unprocessed, pending extraction
- `true`: Processed, memories extracted

**processed_at** (string | null, ISO8601):
- When extraction completed
- `null` if not yet processed
- Format: `YYYY-MM-DDTHH:MM:SS`

**memories_extracted** (integer):
- Count of memories extracted from transcript
- `0` if not yet processed
- Updated after successful extraction

---

## API Reference

### Core Functions

```python
from amplifier.memory.transcript_tracker import (
    add_transcript_record,
    mark_transcript_processed,
    get_unprocessed_transcripts,
    get_all_transcripts
)

# Add new transcript (called by hook)
add_transcript_record(
    session_id="abc123",
    transcript_path="/path/to/transcript.jsonl"
)

# Mark as processed (called by extraction worker)
mark_transcript_processed(
    session_id="abc123",
    memories_count=15
)

# Get unprocessed transcripts (called by exit command)
unprocessed = get_unprocessed_transcripts()
# Returns: list[TranscriptRecord]

# Get all transcripts (for reporting)
all_transcripts = get_all_transcripts()
# Returns: list[TranscriptRecord]
```

### Data Model

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class TranscriptRecord:
    """Record of a transcript file"""
    session_id: str
    transcript_path: str
    created_at: str  # ISO8601
    processed: bool = False
    processed_at: Optional[str] = None  # ISO8601
    memories_extracted: int = 0
```

---

## Integration Points

### 1. Session Stop Hook

**File**: `.claude/tools/hook_stop.py`

**When**: Claude Code session ends

**Action**: Creates transcript record

```python
from amplifier.memory.transcript_tracker import add_transcript_record

# After transcript file created
add_transcript_record(
    session_id=session_id,
    transcript_path=transcript_path
)
```

**Result**: New record added with `processed: false`

---

### 2. Extraction Worker

**File**: `amplifier/memory/extraction_worker.py`

**When**: Transcript extraction completes

**Action**: Updates transcript record

```python
from amplifier.memory.transcript_tracker import mark_transcript_processed

# After successful extraction
mark_transcript_processed(
    session_id=session_id,
    memories_count=memories_extracted
)
```

**Result**: Record updated with `processed: true` and memory count

---

### 3. Exit Command

**File**: `.claude/commands/exit.md`

**When**: User runs `/exit`

**Action**: Checks for unprocessed transcripts

```python
from amplifier.memory.transcript_tracker import get_unprocessed_transcripts

unprocessed = get_unprocessed_transcripts()

if unprocessed:
    print(f"📝 Found {len(unprocessed)} unprocessed transcript(s)")
    # Prompt user to extract
```

**Result**: Shows count of pending transcripts

---

### 4. Cleanup Command

**File**: `.claude/commands/cleanup.md`

**When**: User runs `/cleanup`

**Action**: May display transcript statistics

```python
from amplifier.memory.transcript_tracker import get_all_transcripts

all_transcripts = get_all_transcripts()
processed = [t for t in all_transcripts if t.processed]
unprocessed = [t for t in all_transcripts if not t.processed]

print(f"Total transcripts: {len(all_transcripts)}")
print(f"Processed: {len(processed)}")
print(f"Pending: {len(unprocessed)}")
```

**Result**: Provides overview of transcript state

---

## Use Cases

### Use Case 1: Check Pending Work

**Goal**: See how many transcripts need processing

**Command**:
```bash
# Via exit command
/exit
# Shows: "Found 3 unprocessed transcript(s)"

# Or programmatically
python3 -c "
from amplifier.memory.transcript_tracker import get_unprocessed_transcripts
print(f'Unprocessed: {len(get_unprocessed_transcripts())}')
"
```

---

### Use Case 2: Verify Processing Complete

**Goal**: Confirm all transcripts have been processed

**Command**:
```bash
python3 -c "
from amplifier.memory.transcript_tracker import get_all_transcripts

all_transcripts = get_all_transcripts()
unprocessed = [t for t in all_transcripts if not t.processed]

if not unprocessed:
    print('✓ All transcripts processed')
else:
    print(f'⚠️  {len(unprocessed)} transcripts pending')
    for t in unprocessed:
        print(f'  • {t.session_id}: {t.created_at}')
"
```

---

### Use Case 3: Audit Memory Extraction History

**Goal**: See which transcripts yielded the most memories

**Command**:
```bash
python3 -c "
from amplifier.memory.transcript_tracker import get_all_transcripts

transcripts = get_all_transcripts()
processed = [t for t in transcripts if t.processed]
processed.sort(key=lambda t: t.memories_extracted, reverse=True)

print('Top 5 transcripts by memory count:')
for t in processed[:5]:
    print(f'  {t.memories_extracted} memories: {t.session_id}')
"
```

---

### Use Case 4: Find Old Unprocessed Transcripts

**Goal**: Identify transcripts that have been pending for a long time

**Command**:
```bash
python3 -c "
from amplifier.memory.transcript_tracker import get_unprocessed_transcripts
from datetime import datetime, timedelta

unprocessed = get_unprocessed_transcripts()
cutoff = datetime.now() - timedelta(days=7)

old = [
    t for t in unprocessed
    if datetime.fromisoformat(t.created_at) < cutoff
]

if old:
    print(f'⚠️  {len(old)} transcripts pending >7 days:')
    for t in old:
        print(f'  • {t.session_id}: {t.created_at}')
else:
    print('✓ No old pending transcripts')
"
```

---

## File Management

### Creating New Tracking File

**First run**: File created automatically on first transcript

```python
# In transcript_tracker.py
import json
from pathlib import Path

def _ensure_tracking_file():
    """Create tracking file if doesn't exist"""
    if not TRANSCRIPTS_FILE.exists():
        TRANSCRIPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"version": "1.0", "transcripts": []}
        TRANSCRIPTS_FILE.write_text(json.dumps(data, indent=2))
```

---

### Concurrent Access Safety

**Problem**: Multiple processes might access file simultaneously

**Solution**: File locking during read/write

```python
import fcntl

def _read_with_lock():
    """Read with file lock"""
    with open(TRANSCRIPTS_FILE, 'r') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock
        data = json.load(f)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
        return data

def _write_with_lock(data):
    """Write with file lock"""
    with open(TRANSCRIPTS_FILE, 'w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
        json.dump(data, f, indent=2)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
```

---

### Backup Strategy

**Automated backups** on each write:

```python
def _backup_before_write():
    """Create backup before modifying"""
    if TRANSCRIPTS_FILE.exists():
        backup_path = TRANSCRIPTS_FILE.with_suffix('.json.backup')
        shutil.copy2(TRANSCRIPTS_FILE, backup_path)
```

**Manual backup**:
```bash
cp .data/transcripts.json .data/transcripts.json.backup
```

---

## Maintenance

### View Current State

```bash
# Pretty-print JSON
cat .data/transcripts.json | python3 -m json.tool

# Count transcripts
python3 -c "
import json
with open('.data/transcripts.json') as f:
    data = json.load(f)
    print(f\"Total transcripts: {len(data['transcripts'])}\")
"
```

---

### Clean Up Old Processed Records

**Goal**: Remove records for transcripts processed >30 days ago

```bash
python3 -c "
import json
from datetime import datetime, timedelta
from pathlib import Path

TRANSCRIPTS_FILE = Path('.data/transcripts.json')
cutoff = datetime.now() - timedelta(days=30)

with open(TRANSCRIPTS_FILE) as f:
    data = json.load(f)

# Keep recent + unprocessed
data['transcripts'] = [
    t for t in data['transcripts']
    if not t['processed'] or
       datetime.fromisoformat(t['processed_at']) > cutoff
]

with open(TRANSCRIPTS_FILE, 'w') as f:
    json.dump(data, f, indent=2)

print(f\"Kept {len(data['transcripts'])} records\")
"
```

---

### Migrate to New Schema Version

**When**: Schema version changes (e.g., 1.0 → 2.0)

```python
def migrate_v1_to_v2(old_data):
    """Migrate from v1.0 to v2.0"""
    # Example: Add new field
    for transcript in old_data['transcripts']:
        transcript['extraction_method'] = 'two-pass'  # New field

    old_data['version'] = '2.0'
    return old_data

# Apply migration
with open(TRANSCRIPTS_FILE) as f:
    data = json.load(f)

if data['version'] == '1.0':
    data = migrate_v1_to_v2(data)
    with open(TRANSCRIPTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)
```

---

## Error Handling

### Missing Tracking File

**Symptom**: File doesn't exist on first read

**Behavior**: Automatically created

```python
def get_all_transcripts():
    _ensure_tracking_file()  # Creates if missing
    data = _read_with_lock()
    return [TranscriptRecord(**t) for t in data['transcripts']]
```

---

### Corrupt JSON

**Symptom**: File exists but contains invalid JSON

**Detection**:
```bash
python3 -c "
import json
try:
    with open('.data/transcripts.json') as f:
        json.load(f)
    print('✓ JSON valid')
except json.JSONDecodeError as e:
    print(f'⚠️  JSON corrupt: {e}')
"
```

**Recovery**:
```bash
# Restore from backup
cp .data/transcripts.json.backup .data/transcripts.json

# Or manually fix JSON
vim .data/transcripts.json
```

---

### Duplicate Session IDs

**Symptom**: Same session_id appears multiple times

**Prevention**: Check before adding

```python
def add_transcript_record(session_id, transcript_path):
    data = _read_with_lock()

    # Check for duplicate
    if any(t['session_id'] == session_id for t in data['transcripts']):
        logger.warning(f"Transcript {session_id} already tracked")
        return

    # Add new record
    data['transcripts'].append({
        "session_id": session_id,
        "transcript_path": transcript_path,
        "created_at": datetime.now().isoformat(),
        "processed": False,
        "processed_at": None,
        "memories_extracted": 0
    })

    _write_with_lock(data)
```

---

### Missing Transcript File

**Symptom**: Record exists but transcript file doesn't

**Detection**:
```python
from pathlib import Path

def validate_transcript_files():
    """Check all tracked transcripts exist"""
    transcripts = get_all_transcripts()
    missing = []

    for t in transcripts:
        if not Path(t.transcript_path).exists():
            missing.append(t.session_id)

    if missing:
        print(f"⚠️  {len(missing)} transcript files missing:")
        for session_id in missing:
            print(f"  • {session_id}")
```

**Resolution**: Either restore file or remove record

---

## Reporting

### Daily Summary

```python
from amplifier.memory.transcript_tracker import get_all_transcripts
from datetime import datetime, timedelta

# Get today's transcripts
today = datetime.now().date()
transcripts = get_all_transcripts()

today_transcripts = [
    t for t in transcripts
    if datetime.fromisoformat(t.created_at).date() == today
]

today_processed = [t for t in today_transcripts if t.processed]
total_memories = sum(t.memories_extracted for t in today_processed)

print(f"📊 Today's Activity ({today}):")
print(f"  • Transcripts created: {len(today_transcripts)}")
print(f"  • Transcripts processed: {len(today_processed)}")
print(f"  • Memories extracted: {total_memories}")
```

---

### Weekly Summary

```python
from datetime import datetime, timedelta

week_ago = datetime.now() - timedelta(days=7)
transcripts = get_all_transcripts()

week_transcripts = [
    t for t in transcripts
    if datetime.fromisoformat(t.created_at) > week_ago
]

week_processed = [t for t in week_transcripts if t.processed]
total_memories = sum(t.memories_extracted for t in week_processed)

print(f"📊 Last 7 Days:")
print(f"  • Transcripts created: {len(week_transcripts)}")
print(f"  • Transcripts processed: {len(week_processed)}")
print(f"  • Memories extracted: {total_memories}")
print(f"  • Average memories/transcript: {total_memories / len(week_processed) if week_processed else 0:.1f}")
```

---

## Best Practices

### For Users

✅ **DO**:
- Trust automatic tracking
- Use `/exit` to check pending transcripts
- Run `/cleanup` to investigate state
- Check tracking file if something seems wrong

❌ **DON'T**:
- Manually edit transcripts.json (unless recovering from corruption)
- Delete tracking file (loses all history)
- Assume transcripts auto-process (must use `/exit` or background processor)

---

### For Developers

✅ **DO**:
- Use provided API functions (don't access JSON directly)
- Handle file locking for concurrent access
- Create backups before modifying
- Validate data when reading
- Log all tracking operations

❌ **DON'T**:
- Bypass locking mechanisms
- Assume file always exists
- Modify schema without migration
- Cache data across function calls (file may change)

---

## Troubleshooting

### Problem: Transcripts Not Being Tracked

**Symptoms**:
- Session ends but no new record in transcripts.json
- `/exit` says "No unprocessed transcripts" right after session

**Diagnosis**:
```bash
# Check hook ran
ls .claude/tools/hook_stop.py

# Check transcript file created
ls .data/transcripts/*.jsonl | tail -1

# Check tracking file updated
tail -10 .data/transcripts.json
```

**Causes**:
1. Hook not configured in .claude/tools/
2. Hook script has import errors
3. Hook script didn't call tracker
4. Tracker failed silently

**Fix**: Check hook logs, verify tracker import works

---

### Problem: Duplicate Records

**Symptoms**: Same session_id appears multiple times

**Diagnosis**:
```bash
python3 -c "
import json
from collections import Counter

with open('.data/transcripts.json') as f:
    data = json.load(f)

ids = [t['session_id'] for t in data['transcripts']]
duplicates = [id for id, count in Counter(ids).items() if count > 1]

if duplicates:
    print(f'⚠️  Duplicate session IDs: {duplicates}')
else:
    print('✓ No duplicates')
"
```

**Fix**: Manually remove duplicates, keep most recent

---

### Problem: All Transcripts Marked Processed

**Symptoms**: `/exit` always says "No unprocessed transcripts"

**Diagnosis**:
```bash
python3 -c "
import json
with open('.data/transcripts.json') as f:
    data = json.load(f)

unprocessed = [t for t in data['transcripts'] if not t['processed']]
print(f'Unprocessed: {len(unprocessed)}')
"
```

**Causes**:
1. All actually processed
2. Bug marking all as processed
3. State corruption

**Fix**: Check logs, verify extraction actually ran

---

## Related Documentation

- [Exit Command](EXIT_COMMAND.md) - Uses transcript tracking
- [Cleanup Command](CLEANUP_COMMAND.md) - May display tracking stats
- [Extraction Worker](EXTRACTION_WORKER.md) - Updates tracking records
- [Memory System Overview](MEMORY_SYSTEM.md) - Complete memory system

---

## Summary

The transcript tracking system provides:
- **Automatic recording** of all transcripts
- **Status tracking** (processed vs. pending)
- **Memory count** storage
- **Single source of truth** for transcript state
- **API for integration** with other components

**No manual tracking needed** - the system handles everything automatically from session end through memory extraction completion.

---

**Implementation details**: See `amplifier/memory/transcript_tracker.py` for complete implementation.
