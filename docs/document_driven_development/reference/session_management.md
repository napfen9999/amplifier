# Session Management Reference

**Technical reference for DDD session-aware implementation system**

---

## Overview

The session management system enables seamless multi-session DDD implementations through automatic state preservation, token budget tracking, and intelligent resumption.

**Core components**:
- State persistence (files, not memory)
- Token budget tracking
- Checkpoint system
- Sub-agent delegation
- Conflict detection

---

## State Files

### impl_status.md

**Location**: `ai_working/ddd/impl_status.md`

**Purpose**: Human-readable progress tracking

**Format**:
```markdown
# Implementation Status

## Session [N] - [YYYY-MM-DD HH:MM]
- ✅ Chunk X.Y: [Title] ([duration])
- ✅ Chunk X.Z: [Title] ([duration])
- ⏸️ Paused at: Chunk A.B (reason: [token budget low | manual])

## Session [N+1] - [YYYY-MM-DD HH:MM]
- ✅ Chunk A.B: [Title] (resumed, [duration])
...
```

**Auto-updated by**: `PostToolUse:Edit` hook

**Manual updates**: Not required (system maintains)

---

### session_manifest.json

**Location**: `ai_working/ddd/session_manifest.json`

**Purpose**: Machine-readable session tracking

**Schema**:
```json
{
  "sessions": [
    {
      "session_id": "string (UUID)",
      "started": "ISO-8601 datetime",
      "ended": "ISO-8601 datetime | null",
      "chunks_completed": ["string (chunk IDs)"],
      "tokens_used": "integer",
      "status": "in_progress | handoff | completed"
    }
  ],
  "total_chunks": "integer",
  "completed_chunks": ["string (chunk IDs)"],
  "current_session": "string (session_id) | null"
}
```

**Example**:
```json
{
  "sessions": [
    {
      "session_id": "abc123-def456-ghi789",
      "started": "2025-11-12T14:00:00Z",
      "ended": "2025-11-12T15:30:00Z",
      "chunks_completed": ["1.1", "1.2"],
      "tokens_used": 145000,
      "status": "handoff"
    },
    {
      "session_id": "jkl012-mno345-pqr678",
      "started": "2025-11-12T16:00:00Z",
      "ended": null,
      "chunks_completed": ["1.3", "2.1"],
      "tokens_used": 87000,
      "status": "in_progress"
    }
  ],
  "total_chunks": 15,
  "completed_chunks": ["1.1", "1.2", "1.3", "2.1"],
  "current_session": "jkl012-mno345-pqr678"
}
```

---

### Checkpoint Files

**Location**: `ai_working/ddd/checkpoints/session_[NNN]_chunk_[X.Y].json`

**Purpose**: Per-chunk state snapshots

**Schema**:
```json
{
  "checkpoint_id": "string (cp_[chunk]_[session])",
  "timestamp": "ISO-8601 datetime",
  "session_id": "string (UUID)",
  "chunk": "string (chunk ID)",
  "files_modified": ["string (file paths)"],
  "test_status": "passing | failing | not_run",
  "context": {
    "decisions": ["string (recent decisions)"],
    "issues": ["string (known issues)"],
    "notes": "string (any additional context)"
  },
  "next_actions": ["string (what to do next)"]
}
```

**Example**:
```json
{
  "checkpoint_id": "cp_2.1_abc123",
  "timestamp": "2025-11-12T14:45:00Z",
  "session_id": "abc123-def456-ghi789",
  "chunk": "2.1",
  "files_modified": [
    "tools/ddd_budget_tracker.py",
    "tests/test_budget_tracker.py"
  ],
  "test_status": "passing",
  "context": {
    "decisions": [
      "Used heuristic estimation (1000 tokens/file)",
      "Set handoff threshold to 30k tokens"
    ],
    "issues": [],
    "notes": "Tests cover basic estimation, add complex cases later"
  },
  "next_actions": [
    "Implement Chunk 2.2 (Chunk Analyzer)",
    "Add edge case tests for budget tracker"
  ]
}
```

---

## API Reference

### State Manager

**Module**: `tools/ddd_state_manager.py`

**Functions**:

```python
def load_session_manifest() -> SessionManifest:
    """Load current session manifest from file."""

def save_session_manifest(manifest: SessionManifest) -> None:
    """Save session manifest to file."""

def load_checkpoint(checkpoint_id: str) -> CheckpointData:
    """Load specific checkpoint by ID."""

def save_checkpoint(checkpoint: CheckpointData) -> None:
    """Save checkpoint to file."""

def update_impl_status(session_id: str, chunk: str, status: str) -> None:
    """Append status update to impl_status.md."""
```

---

### Budget Tracker

**Module**: `tools/ddd_budget_tracker.py`

**Functions**:

```python
def estimate_chunk_tokens(chunk: ChunkSpec) -> int:
    """Estimate tokens required for chunk.

    Formula:
        base = num_files * 1000
        deps = num_dependencies * 500
        complexity = complexity_multiplier (1.0-3.0)

        total = (base + deps) * complexity
    """

def check_budget(used_tokens: int, max_tokens: int = 200000) -> BudgetStatus:
    """Check if enough budget to continue.

    Returns:
        - "ok": > 30k remaining
        - "low": 10k-30k remaining
        - "critical": < 10k remaining
    """

def should_handoff(used_tokens: int, estimated_next: int) -> bool:
    """Determine if session should handoff now."""
```

**Constants**:
```python
BASE_TOKENS_PER_FILE = 1000
DEPENDENCY_TOKENS = 500
HANDOFF_THRESHOLD = 30000  # Conservative
COMPLEXITY_MULTIPLIERS = {
    "simple": 1.0,
    "medium": 1.5,
    "complex": 3.0
}
```

---

### Agent Selector

**Module**: `tools/ddd_agent_selector.py`

**Functions**:

```python
def discover_agents() -> List[AgentMetadata]:
    """Scan .claude/agents/ for available agents.

    Returns list of agents with their metadata.
    """

def select_agent(chunk: ChunkSpec, agents: List[AgentMetadata]) -> str:
    """Select best agent for chunk based on metadata.

    Matching algorithm:
    1. Check dependencies: none → prefer modular-builder
    2. Check token estimate: >10k → warn user
    3. Match layer to agent specializations
    4. Default fallback: modular-builder

    Returns: agent name (string)
    """

def parse_agent_metadata(agent_file: Path) -> AgentMetadata:
    """Parse YAML frontmatter from agent file."""
```

**Agent Metadata Format**:
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

---

### Orchestrator

**Module**: `tools/ddd_orchestrator.py`

**Main Loop**:

```python
def start_session() -> SessionState:
    """Start new session or resume existing.

    1. Load session manifest
    2. Check for existing checkpoints
    3. Determine start point
    4. Initialize session state
    """

def execute_chunk(chunk: ChunkSpec, session_state: SessionState) -> ChunkResult:
    """Execute single chunk.

    1. Estimate tokens required
    2. Check budget
    3. Select agent (or execute directly)
    4. Delegate or implement
    5. Run tests
    6. Checkpoint if successful
    """

def checkpoint(session_state: SessionState) -> None:
    """Save current state.

    1. Update impl_status.md
    2. Update session_manifest.json
    3. Create checkpoint JSON
    4. Git commit
    """

def handoff_session(session_state: SessionState) -> None:
    """Prepare for session end.

    1. Final checkpoint
    2. Update manifest status to "handoff"
    3. Show resume instructions
    """
```

---

## Data Models

### SessionState

```python
@dataclass
class SessionState:
    session_id: str
    tokens_used: int
    current_chunk: str
    chunks_completed: List[str]
    chunks_remaining: List[str]
    last_checkpoint: str
```

### ChunkSpec

```python
@dataclass
class ChunkSpec:
    id: str  # "2.6"
    layer: str  # "Layer 2"
    title: str  # "Strategy constraint validation"
    estimated_tokens: int
    dependencies: List[str]  # ["2.5"]
    files_to_create: List[str]
```

### CheckpointData

```python
@dataclass
class CheckpointData:
    checkpoint_id: str
    timestamp: str
    session_state: SessionState
    files_modified: List[str]
    context: Dict[str, Any]
    next_actions: List[str]
```

### AgentMetadata

```python
@dataclass
class AgentMetadata:
    name: str
    capabilities: List[str]
    specializations: List[str]
    avoid_for: List[str]
    chunk_types: List[str]
    token_cost: str  # "low" | "medium" | "high"
```

---

## Configuration

### Environment Variables

None required - all configuration in code and agent metadata.

### Make Commands

**In Makefile**:

```makefile
.PHONY: ddd-continue
ddd-continue:
	@python tools/ddd_orchestrator.py --resume

.PHONY: ddd-status
ddd-status:
	@python tools/ddd_orchestrator.py --status

.PHONY: ddd-checkpoint
ddd-checkpoint:
	@python tools/ddd_orchestrator.py --checkpoint
```

---

## Hooks

### PostToolUse:Edit

**Location**: `.claude/hooks/post_tool_use.py`

**Trigger**: After any Edit/Write tool use

**Action**:
```python
if Path("ai_working/ddd/impl_status.md").exists():
    append_log(f"Modified {file_path} at {timestamp}")
```

**Benefits**:
- Automatic file change tracking
- No manual updates required
- Clear audit trail

---

### PreCompact

**Location**: `.claude/tools/hook_precompact.py`

**Trigger**: Before session compaction (when context window fills)

**Action**:
```python
def emergency_ddd_checkpoint():
    if is_ddd_session_active():
        force_checkpoint()
        create_resume_instructions()
        git_commit("chore: Emergency checkpoint before compaction")
```

**Benefits**:
- Never lose state on surprise compaction
- Automatic recovery possible
- Preserves all progress

---

## Conflict Detection

### Conflict Types

**1. File modifications**:
- Checkpoint says file X has hash H1
- Current file X has hash H2
- **Resolution**: Warn user, offer rollback or merge

**2. Code plan changes**:
- Checkpoint references chunk 2.3
- code_plan.md no longer has chunk 2.3
- **Resolution**: Ask user if plan changed intentionally

**3. Dependency changes**:
- Checkpoint says chunk 2.3 depends on 2.1, 2.2
- code_plan.md now says 2.3 depends on 2.1 only
- **Resolution**: Verify with user, update dependencies

### Resolution Workflow

```python
def check_conflicts(checkpoint: CheckpointData) -> List[Conflict]:
    conflicts = []

    # Check file modifications
    for file_path in checkpoint.files_modified:
        if file_changed_externally(file_path, checkpoint.timestamp):
            conflicts.append(FileModifiedConflict(file_path))

    # Check code plan
    if code_plan_hash != checkpoint.code_plan_hash:
        conflicts.append(CodePlanChangedConflict())

    # Check dependencies
    for chunk in checkpoint.next_chunks:
        if dependencies_changed(chunk):
            conflicts.append(DependencyChangedConflict(chunk))

    return conflicts
```

**User options**:
- **Continue anyway**: Ignore conflicts, may cause issues
- **Rollback to checkpoint**: Restore exact state
- **Manual merge**: Review and resolve conflicts manually

---

## Troubleshooting

### Problem: Session won't resume

**Symptoms**:
- `make ddd-continue` fails
- Error: "No session manifest found"

**Diagnosis**:
```bash
ls ai_working/ddd/session_manifest.json
# Should exist

cat ai_working/ddd/session_manifest.json | jq .
# Should be valid JSON
```

**Solutions**:
1. Check if session_manifest.json exists
2. Verify JSON is valid
3. Check for `current_session` field
4. If corrupt, restore from git history

---

### Problem: Token budget exceeded

**Symptoms**:
- Session compacts mid-chunk
- PreCompact hook didn't trigger

**Diagnosis**:
```bash
grep "tokens_used" ai_working/ddd/session_manifest.json
# Check if exceeded 200k
```

**Solutions**:
1. Lower `HANDOFF_THRESHOLD` in budget_tracker.py
2. Increase chunk granularity (smaller chunks)
3. Delegate more to sub-agents (saves context)

---

### Problem: Wrong agent selected

**Symptoms**:
- Complex chunk sent to simple agent
- Agent fails or takes too long

**Diagnosis**:
```bash
grep "avoid_for" .claude/agents/[agent-name].md
# Check agent capabilities
```

**Solutions**:
1. Update agent metadata (add to `avoid_for`)
2. Add chunk type hints in code_plan.md
3. Override agent selection manually

---

### Problem: Checkpoint conflicts

**Symptoms**:
- Resume shows conflicts
- Files modified externally

**Diagnosis**:
```bash
git diff [checkpoint-commit] -- [conflicted-file]
# See what changed
```

**Solutions**:
1. If intentional: Accept current state
2. If accidental: Rollback to checkpoint
3. If unsure: Manual review and merge

---

## Performance

### Token Efficiency

**Without session management**:
- 100 iterations × 2000 tokens = 200,000 tokens (context limit)
- Manual state tracking (error-prone)

**With session management**:
- 100 iterations × 10 tokens = 1,000 tokens (99.5% savings)
- Automatic state tracking (reliable)

### Session Duration

**Typical session**:
- 3-5 chunks per session
- 60-90 minutes per session
- ~150k tokens used

**Handoff overhead**:
- Checkpoint: ~30 seconds
- Resume: ~60 seconds
- **Total**: <2 minutes per handoff

---

## Best Practices

### Checkpoint Frequency

**Recommended**:
- After every chunk completion
- Before any risky operation
- When manually requested

**Not recommended**:
- Mid-chunk (incomplete state)
- Before tests run (unknown if works)
- Too frequently (overhead)

### Sub-Agent Delegation

**Maximize delegation**:
- Simple chunks → always delegate
- Complex chunks → delegate if agent capable
- Architecture decisions → don't delegate

**Agent selection criteria**:
1. Chunk has no dependencies → modular-builder
2. Chunk is code-heavy → modular-builder
3. Chunk needs architecture → keep in main session
4. Chunk is refactoring → check agent metadata

### State File Maintenance

**Do**:
- Commit state files with code changes
- Keep files in sync (all or nothing)
- Review impl_status.md periodically

**Don't**:
- Manually edit session_manifest.json (use API)
- Delete checkpoints (needed for rollback)
- Commit partial state (breaks resume)

---

## Related Documentation

- [Phase 4: Code Implementation (Session-Aware)](../phases/04_code_implementation_session_aware.md)
- [File Crawling](../core_concepts/file_crawling.md)
- [Context Poisoning](../core_concepts/context_poisoning.md)

---

**Return to**: [Reference](README.md) | [Main Index](../README.md)
