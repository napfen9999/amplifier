# Phase 4: Code Implementation (Session-Aware)

**Implement code in chunks across multiple sessions with automatic state preservation**

---

## Goal

Implement the code plan systematically while managing token budget and preserving state across session boundaries. The session-aware orchestrator automatically handles checkpointing, resumption, and sub-agent delegation.

**Why session-aware**: Large implementations exhaust context windows. Automatic session management ensures seamless multi-session workflows without manual state tracking.

---

## Overview

The session-aware implementation phase operates differently from traditional single-session coding:

**Traditional approach**:
```
Start session → Implement all chunks → Run out of context → Manual recovery
```

**Session-aware approach**:
```
Start session → Auto-checkpoint → Session handoff → Resume seamlessly → Repeat
```

**Key capabilities**:
- **Token budget tracking**: Monitors usage, triggers checkpoints before exhaustion
- **Automatic checkpointing**: After every chunk and before session handoff
- **State persistence**: All decisions and progress saved to files
- **Sub-agent delegation**: Maximizes context savings through specialized agents
- **Seamless resume**: Next session loads state and continues automatically

---

## The Workflow

### Starting a Session

**First time** (no prior state):
```bash
/ddd:4-code
```

**Resuming** (from checkpoint):
```bash
make ddd-continue
# or
/ddd:4-code --resume
```

The orchestrator:
1. Loads session manifest
2. Identifies completed chunks
3. Reads last checkpoint
4. Continues from next chunk

---

## State Files

The session-aware system maintains these files:

### `ai_working/ddd/impl_status.md`

Human-readable progress tracking:

```markdown
# Implementation Status

## Session 1 - 2025-11-12 14:00
- ✅ Chunk 1.1: State Manager (45 minutes)
- ✅ Chunk 1.2: Session Manifest (30 minutes)
- ⏸️ Paused at: Chunk 1.3 (token budget low)

## Session 2 - 2025-11-12 16:00
- ✅ Chunk 1.3: Checkpoint System (resumed)
- ✅ Chunk 2.1: Budget Tracker
...
```

Auto-updated via `PostToolUse:Edit` hook.

### `ai_working/ddd/session_manifest.json`

Machine-readable session tracking:

```json
{
  "sessions": [
    {
      "session_id": "abc123",
      "started": "2025-11-12T14:00:00",
      "ended": "2025-11-12T15:30:00",
      "chunks_completed": ["1.1", "1.2"],
      "tokens_used": 145000,
      "status": "handoff"
    },
    {
      "session_id": "def456",
      "started": "2025-11-12T16:00:00",
      "status": "in_progress",
      "current_chunk": "2.1"
    }
  ],
  "total_chunks": 15,
  "completed_chunks": ["1.1", "1.2", "1.3", "2.1"]
}
```

### `ai_working/ddd/checkpoints/`

Per-chunk state snapshots:

```json
// checkpoints/session_001_chunk_1.2.json
{
  "checkpoint_id": "cp_1.2_abc123",
  "timestamp": "2025-11-12T14:45:00",
  "chunk": "1.2",
  "files_modified": [
    "tools/ddd_state_manager.py",
    "tests/test_state_manager.py"
  ],
  "test_status": "passing",
  "next_actions": [
    "Implement checkpoint serialization",
    "Add git auto-commit"
  ]
}
```

---

## Token Budget Management

The budget tracker monitors usage and triggers handoffs:

**Tracking**:
```python
# Heuristic estimation
base_tokens = num_files * 1000
dependency_tokens = num_deps * 500
complexity_multiplier = 1.0 to 3.0

estimated_chunk_tokens = base_tokens * complexity_multiplier + dependency_tokens
```

**Decision points**:
```python
if remaining_tokens < 30000:
    # Conservative threshold
    trigger_checkpoint()
    prepare_handoff()

if estimated_chunk_tokens > remaining_tokens:
    # Don't start chunk we can't finish
    trigger_handoff_now()
```

---

## Sub-Agent Delegation

The agent selector chooses the best agent for each chunk:

**Dynamic discovery**:
```python
# Scans .claude/agents/ for available agents
agents = discover_agents()  # Reads YAML metadata

# Matches chunk to agent capabilities
selected = select_agent(chunk, agents)  # Uses heuristics
```

**Agent metadata** (YAML frontmatter):
```yaml
---
name: modular-builder
capabilities: [implementation, testing, basic-refactoring]
specializations: [module-building, interface-implementation]
avoid_for: [architecture-design, complex-debugging]
chunk_types: [code-creation, file-generation]
token_cost: medium
---
```

**Matching algorithm**:
1. Check dependencies: none → prefer `modular-builder`
2. Check token estimate: >10k → warn user
3. Match layer to agent specializations
4. Default fallback: always `modular-builder`

**No hardcoding** - algorithm reads metadata dynamically.

---

## Checkpointing

Automatic checkpoints occur:

1. **After every chunk completion**:
   - Tests pass
   - Files committed
   - State saved

2. **Before session handoff**:
   - Token budget low
   - Manual checkpoint requested
   - PreCompact hook triggered

3. **On demand**:
   ```bash
   make ddd-checkpoint
   ```

**What's saved**:
- Session state (current chunk, completed chunks)
- Files modified
- Test results
- Context (recent decisions, known issues)
- Next actions

---

## Session Handoff

When budget runs low:

1. **Orchestrator triggers checkpoint**:
   ```python
   if remaining_tokens < 30000:
       checkpoint(session_state)
       prepare_handoff()
   ```

2. **State persisted**:
   - impl_status.md updated
   - session_manifest.json updated
   - Checkpoint JSON saved
   - Git commit created

3. **Handoff message shown**:
   ```
   ⏸️ Session Budget Low - Checkpointed

   Progress: 8/15 chunks complete
   Last completed: Chunk 2.3 (Agent Selector)
   Next: Chunk 3.1 (Session Startup)

   To resume:
   make ddd-continue

   or in new session:
   /ddd:4-code --resume
   ```

---

## Resuming a Session

When resuming:

1. **Load session manifest**:
   ```python
   manifest = load_session_manifest()
   last_session = manifest.sessions[-1]
   completed = manifest.completed_chunks
   ```

2. **Load last checkpoint**:
   ```python
   checkpoint = load_checkpoint(last_session.session_id)
   context = checkpoint.context
   next_actions = checkpoint.next_actions
   ```

3. **Detect conflicts** (optional):
   ```python
   conflicts = check_conflicts(
       files_modified=checkpoint.files_modified,
       code_plan_hash=checkpoint.code_plan_hash
   )

   if conflicts:
       present_conflicts_to_user()
   ```

4. **Continue from next chunk**:
   ```python
   next_chunk = get_next_chunk(completed)
   execute_chunk(next_chunk)
   ```

---

## Hook Integration

### PostToolUse:Edit Hook

Auto-updates impl_status.md when files change:

```python
# .claude/hooks/post_tool_use.py
if tool_name in ["Edit", "Write"]:
    if Path("ai_working/ddd/impl_status.md").exists():
        append_to_status(f"Modified {file_path} at {timestamp}")
```

Simple append-only logging.

### PreCompact Hook

Emergency checkpoint before session compaction:

```python
# .claude/tools/hook_precompact.py
def emergency_ddd_checkpoint():
    if is_ddd_session_active():
        force_checkpoint()
        create_resume_instructions()
        git_commit("Emergency checkpoint before compaction")
```

Already exists at `.claude/tools/hook_precompact.py` - extended for DDD.

---

## Conflict Detection

When resuming, the conflict detector checks:

**File modifications**:
- Were files changed outside the session?
- Do checkpointed file hashes match current?

**Dependency changes**:
- Did code_plan.md change?
- Were dependencies added/removed?

**Code plan modifications**:
- Did chunk definitions change?
- Was sequencing altered?

**Resolution options**:
- **Warn**: Continue but inform user
- **Rollback**: Restore checkpoint state
- **Manual merge**: Let user resolve conflicts

---

## Commands

### `make ddd-continue`

Resume from last checkpoint:

```bash
make ddd-continue
```

Equivalent to `/ddd:4-code --resume`.

### `make ddd-status`

Show current progress:

```bash
make ddd-status
```

Output:
```
DDD Implementation Status

Session: 2 (active)
Progress: 8/15 chunks (53%)
Current: Chunk 3.1 - Session Startup
Last completed: Chunk 2.3 - Agent Selector
Tokens used: 87,000 / 200,000 (43%)

Recent activity:
  ✅ Chunk 2.1 - Budget Tracker (35 min)
  ✅ Chunk 2.2 - Chunk Analyzer (28 min)
  ✅ Chunk 2.3 - Agent Selector (42 min)

Next: Chunk 3.1 - Session Startup
```

### `make ddd-checkpoint`

Force checkpoint:

```bash
make ddd-checkpoint
```

Creates checkpoint even if budget not low.

---

## Example Session Flow

### Session 1

```
14:00 - Start /ddd:4-code
14:05 - Chunk 1.1 complete (State Manager) - checkpoint
14:45 - Chunk 1.2 complete (Session Manifest) - checkpoint
15:20 - Chunk 1.3 in progress (Checkpoint System)
15:30 - Token budget low (145k used)
15:30 - Auto-checkpoint
15:30 - Session handoff message
15:31 - User closes session
```

**Files after Session 1**:
- `impl_status.md` - Shows Session 1 progress
- `session_manifest.json` - Session 1 entry
- `checkpoints/session_001_chunk_1.2.json` - Last checkpoint
- Git commits - 3 commits (1 per chunk)

### Session 2

```
16:00 - User runs: make ddd-continue
16:01 - Load manifest (Session 1 found)
16:01 - Load checkpoint (1.2)
16:02 - Resume Chunk 1.3 (Checkpoint System)
16:35 - Chunk 1.3 complete - checkpoint
17:10 - Chunk 2.1 complete (Budget Tracker) - checkpoint
17:45 - Chunk 2.2 complete (Chunk Analyzer) - checkpoint
18:20 - Chunk 2.3 in progress (Agent Selector)
```

**Seamless continuation** - no manual state tracking required.

---

## Git Worktree Integration (Optional - Layer 5)

**Status**: Future enhancement, not core requirement.

**Purpose**: Isolate session state per feature branch.

**When to use**:
- Multiple features in parallel
- State isolation needed
- Branch-specific checkpoints

**For now**: Core workflow works without worktrees.

See Layer 5 (Chunk 5.1) in code_plan.md for implementation details.

---

## Philosophy Alignment

### Ruthless Simplicity

**What we built**:
- File-based state (not database)
- Simple checkpointing (not complex event system)
- Explicit orchestration (not magic)

**What we avoided**:
- ML prediction (just heuristics)
- Complex retry logic (fail fast)
- Distributed coordination (single-user tool)

### Modular Design

**Bricks** (self-contained):
1. State Manager - handles all file I/O
2. Budget Tracker - pure math, no side effects
3. Agent Selector - reads agent dir, returns name
4. Orchestrator - coordinates other bricks
5. Hooks Integration - connects to Claude Code hooks

**Studs** (interfaces):
- State files format (JSON schema, markdown format)
- Orchestrator API (function signatures)
- Chunk spec format (dataclass)
- Checkpoint format (JSON schema)

Each module < 300 lines, regeneratable from spec.

---

## Common Issues and Solutions

### Issue: Session Resumed but Context Missing

**Symptom**: Agent doesn't remember previous decisions

**Cause**: Checkpoint context not loaded

**Fix**: Ensure orchestrator loads checkpoint.context:
```python
checkpoint = load_checkpoint(session_id)
context = checkpoint.context  # Load this!
```

### Issue: Token Budget Exceeded

**Symptom**: Session compacted mid-chunk

**Cause**: Budget tracker threshold too high

**Fix**: Lower threshold in budget_tracker.py:
```python
HANDOFF_THRESHOLD = 30000  # Was 50000
```

### Issue: Wrong Agent Selected

**Symptom**: Complex chunk sent to simple agent

**Cause**: Agent metadata incomplete

**Fix**: Update agent metadata:
```yaml
avoid_for: [complex-debugging, multi-file-refactoring]
```

---

## Integration with Other Phases

**Phase 3 (Implementation Planning)**:
- Creates code_plan.md with chunk definitions
- Estimates used by budget tracker
- Dependencies drive agent selection

**Phase 5 (Testing)**:
- Tests verify each checkpoint
- Test results saved in checkpoint
- Failures pause for human intervention

---

## Output of Phase 4

When complete:
- ✅ All code implemented
- ✅ All tests passing
- ✅ impl_status.md shows full progress
- ✅ session_manifest.json complete
- ✅ Git history shows all chunks
- ✅ No manual state tracking required

**Ready for**: [Phase 5: Testing and Verification](05_testing_and_verification.md)

---

## Tips for Success

**For AI Assistants**:
- Trust the orchestrator - let it manage state
- Use sub-agents aggressively - save context
- Checkpoint after every chunk - always
- Check token budget regularly
- Don't fight the system - work with it

**For Humans**:
- Review checkpoints periodically
- Approve handoffs when prompted
- Monitor impl_status.md for progress
- Trust the resume process

---

## Next Phase

**When Phase 4 complete**: [Phase 5: Testing and Verification](05_testing_and_verification.md)

**Before proceeding**:
- All chunks implemented
- All tests passing
- Git history clean
- Ready for final verification

---

**Return to**: [Phases](README.md) | [Main Index](../README.md)

**Prerequisites**: [Phase 3: Implementation Planning](03_implementation_planning.md)

**Related**: [Session Management Reference](../reference/session_management.md) | [File Crawling](../core_concepts/file_crawling.md)
