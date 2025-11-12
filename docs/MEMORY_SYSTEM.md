# Memory System Documentation

## Overview

The Amplifier Memory System provides persistent memory extraction and retrieval capabilities for Claude Code conversations. It automatically extracts key learnings, decisions, and solutions from conversations and makes them available in future sessions.

The system uses a **queue-based architecture** that decouples hook execution from memory extraction, ensuring fast hook response times and preventing recursive cascade issues.

## Features

- **Queue-based extraction** - Hooks queue sessions for background processing
- **Background processor** - Daemon handles extraction without blocking hooks
- **Sidechain message filtering** - Removes subagent warmup noise from extraction
- **Session persistence** across multiple conversations
- **Relevance search** for contextual memory retrieval
- **Circuit breaker protection** - Throttle protection against hook spam
- **Opt-in system** via environment variable

## Configuration

The memory system is **disabled by default** and must be explicitly enabled.

### Enabling the Memory System

Set the following environment variable in your `.env` file or shell:

```bash
MEMORY_SYSTEM_ENABLED=true
```

### Configuration Options

All configuration options can be set via environment variables:

```bash
# Enable/disable the memory system
MEMORY_SYSTEM_ENABLED=false  # true/1/yes to enable, false/0/no to disable

# Model for memory extraction (fast model recommended)
MEMORY_EXTRACTION_MODEL=claude-3-5-haiku-20241022

# Extraction settings
MEMORY_EXTRACTION_TIMEOUT=120          # Timeout in seconds
MEMORY_EXTRACTION_MAX_MESSAGES=20      # Max messages to process
MEMORY_EXTRACTION_MAX_CONTENT_LENGTH=500  # Max chars per message
MEMORY_EXTRACTION_MAX_MEMORIES=10      # Max memories per session

# Queue processing
EXTRACTION_QUEUE_INTERVAL=30           # Background processor interval (seconds)

# Storage location (directory where memory.json will be stored)
# The actual file will be at: <MEMORY_STORAGE_DIR>/memory.json
MEMORY_STORAGE_DIR=.data/memories

# Maximum total memories to keep in storage
# When this limit is exceeded, oldest/least-accessed memories are rotated out
# Range: 10-100000, Default: 1000
MEMORY_MAX_MEMORIES=1000
```

**Note**: The `MEMORY_STORAGE_DIR` and `MEMORY_MAX_MEMORIES` environment variables control storage behavior. All components (hooks, processor, CLI) automatically use these configured values.

## Architecture

### Components

1. **Claude Code Hooks** (`.claude/tools/`)
   - `hook_stop.py` - Queues sessions for extraction (lightweight, <10ms)
   - `hook_session_start.py` - Retrieves relevant memories at start
   - `hook_post_tool_use.py` - Validates claims against memories

2. **Memory Queue** (`amplifier/memory/queue.py`)
   - JSONL-based queue for pending extractions
   - Fast append operations (non-blocking)
   - Persistent across restarts

3. **Background Processor** (`amplifier/memory/processor.py`)
   - Daemon process handling queued extractions
   - Runs independently of Claude Code hooks
   - Polls queue every 30 seconds (configurable)

4. **Message Filter** (`amplifier/memory/filter.py`)
   - Removes sidechain messages (subagent warmup)
   - Extracts only main conversation content
   - Improves extraction quality

5. **Memory Extraction** (`amplifier/extraction/`)
   - Pattern-based extraction fallback
   - Claude Code SDK support when available
   - Quality filtering and validation

6. **Memory Storage** (`amplifier/memory/`)
   - JSON-based persistent storage
   - Categorized memories with metadata
   - Search and retrieval capabilities

7. **Circuit Breaker** (`amplifier/memory/circuit_breaker.py`)
   - Throttle protection against excessive hook frequency
   - Prevents system overload
   - Automatic recovery after cooldown

### Memory Categories

- **learning** - New knowledge and insights
- **decision** - Important decisions made
- **issue_solved** - Problems solved and their solutions
- **pattern** - Recurring patterns identified
- **context** - Important contextual information

## How It Works

### Queue-Based Architecture

The system decouples hook execution from memory extraction for performance and reliability:

```
Claude Code Session Ends
         ↓
    Stop Hook Fires (lightweight)
         ↓
    Check Circuit Breaker
         ↓
    Queue Session for Extraction (<1ms)
         ↓
    Hook Returns Immediately

         [Background Process]

Background Processor Polls Queue
         ↓
    Read Queued Session
         ↓
    Filter Sidechain Messages
         ↓
    Call Claude SDK for Extraction
         ↓
    Store Memories
         ↓
    Remove from Queue
```

### 1. Session End (Stop Hook)

When a conversation ends (Stop event), the system:
1. Checks if memory system is enabled via environment variable
2. Verifies circuit breaker allows queueing
3. Appends session metadata to extraction queue (<1ms)
4. Returns immediately (no blocking on LLM calls)

**Note**: SubagentStop events are **not** processed to avoid cascade issues and incomplete context.

### 2. Background Processing

The background processor daemon:
1. Polls the extraction queue every 30 seconds (configurable)
2. Reads queued session transcripts
3. Filters sidechain messages (removes subagent warmup)
4. Extracts key memories using Claude SDK
5. Stores memories with metadata (timestamp, tags, importance)
6. Removes processed items from queue

### 3. Memory Retrieval

At conversation start (SessionStart event), the system:
1. Checks if memory system is enabled
2. Searches for relevant memories based on user prompt
3. Retrieves recent memories for context
4. Provides memories as additional context to Claude

### 4. Claim Validation

After tool use (PostToolUse event), the system:
1. Checks if memory system is enabled
2. Validates assistant claims against stored memories
3. Provides warnings if contradictions found

## Memory Storage Format

Memories are stored in JSON format at `<MEMORY_STORAGE_DIR>/memory.json` (default: `.data/memories/memory.json`):

```json
{
  "memories": [
    {
      "content": "Memory content text",
      "category": "learning",
      "metadata": {
        "tags": ["sdk", "claude"],
        "importance": 0.8,
        "extraction_method": "sdk"
      },
      "id": "uuid",
      "timestamp": "2025-08-26T10:10:13.391379",
      "accessed_count": 2
    }
  ],
  "metadata": {
    "version": "2.0",
    "created": "2025-08-23T05:00:26",
    "last_updated": "2025-08-26T10:26:23",
    "count": 25
  },
  "decisions_made": ["List of decisions"],
  "issues_solved": ["List of solved issues"],
  "key_learnings": ["List of learnings"]
}
```

## Queue Format

The extraction queue is stored at `.data/extraction_queue.jsonl`:

```jsonl
{"session_id": "abc123", "transcript_path": "/path/to/transcript.jsonl", "timestamp": "2025-11-11T14:30:00", "hook_event": "Stop"}
{"session_id": "def456", "transcript_path": "/path/to/transcript.jsonl", "timestamp": "2025-11-11T14:35:00", "hook_event": "Stop"}
```

## Background Processor

### Starting the Processor

The background processor runs as a separate daemon:

```bash
# Start processor in background
python -m amplifier.memory.processor &

# Or use screen/tmux for persistent session
screen -S memory-processor python -m amplifier.memory.processor
```

### Processor Status

Check processor activity:

```bash
# Check if running
ps aux | grep "memory.processor"

# View recent extractions
tail -f .claude/logs/processor_$(date +%Y%m%d).log
```

## Debugging

### Log Files

When enabled, the memory system logs to `.claude/logs/`:
- `stop_hook_YYYYMMDD.log` - Stop hook logs (queueing operations)
- `session_start_YYYYMMDD.log` - Session start logs
- `post_tool_use_YYYYMMDD.log` - Post tool use logs
- `processor_YYYYMMDD.log` - Background processor logs

Logs are automatically rotated after 7 days.

### Common Issues

1. **Memory system not activating**
   - Ensure `MEMORY_SYSTEM_ENABLED=true` is set
   - Check logs in `.claude/logs/` for errors
   - Verify background processor is running

2. **No memories being extracted**
   - Check extraction queue: `cat .data/extraction_queue.jsonl`
   - Verify background processor is running: `ps aux | grep memory.processor`
   - Review processor logs for errors
   - Check conversation has substantive content

3. **Queue growing but not processing**
   - Background processor may not be running
   - Check processor logs for errors
   - Verify Claude SDK credentials are valid
   - Check timeout settings

4. **Circuit breaker activated**
   - Too many hook events in short period
   - Check logs for "Circuit breaker" messages
   - System will automatically recover after cooldown

## Memory Rotation

When the number of stored memories exceeds `MEMORY_MAX_MEMORIES`, automatic rotation removes the oldest/least-accessed memories.

### How Rotation Works

1. **Trigger**: Activated when memories exceed configured limit (default: 1000)

2. **Sorting**: Memories are ranked by:
   - **Primary**: Access count (how often retrieved)
   - **Secondary**: Timestamp (how recent)

3. **Removal**: Oldest and least-accessed memories are removed first

4. **Retention**: Most valuable memories (frequently accessed + recent) are kept

### Configuration

```bash
# Set custom limit via environment variable
MEMORY_MAX_MEMORIES=5000  # Keep up to 5000 memories

# Valid range: 10-100000
# Values outside range are clamped to min/max
```

### Example

**Before Rotation:**
- 1100 memories in storage
- Limit: 1000

**After Rotation:**
- 1000 memories retained (most accessed + recent)
- 100 memories removed (rarely used + old)
- Log message: `INFO: Rotated out 100 old memories`

### Monitoring

Check memory count in storage:
```python
from amplifier.memory import MemoryStore
store = MemoryStore()
count = len(store.get_all())
print(f"Current memories: {count}")
print(f"Limit: {store.max_memories}")
```

## Performance Characteristics

- **Hook execution**: <10ms (queue append only)
- **Background processing**: 30-60 seconds per session
- **Memory retrieval**: <100ms (indexed search)
- **No blocking operations** in Claude Code hooks

## Implementation Philosophy

The memory system follows the project's core philosophies:

- **Ruthless Simplicity** - File-based queue, simple polling
- **Modular Design** - Self-contained modules with stable interfaces
- **Fail Gracefully** - Circuit breaker prevents overload
- **Direct Integration** - Minimal wrappers around functionality
- **Architectural Integrity** - Queue-based decoupling prevents cascade

## Security Considerations

- Memories may contain sensitive information
- Storage is local to the machine
- No external API calls for storage
- Background processor runs with user permissions
- Queue files readable only by user

## Future Enhancements

Potential improvements while maintaining simplicity:

- Vector similarity search for better retrieval
- Memory decay/aging for relevance
- Cross-project memory sharing
- Memory export/import capabilities
- Distributed processing for multi-machine setups
