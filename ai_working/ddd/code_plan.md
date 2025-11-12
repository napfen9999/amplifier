# Code Implementation Plan - Session-Aware DDD Workflow

**Generated**: 2025-11-12
**Based on**: Phase 1 plan.md + Phase 2 documentation

---

## Summary

Implement session management system for DDD Phase 4: file-based state persistence, token budget tracking, dynamic agent discovery, and seamless multi-session workflows.

**Core Value**: Session boundaries become invisible through systematic state management.

---

## Current State Analysis

### ✅ Completed (Phase 2)
- Documentation: 04_code_implementation_session_aware.md (669 lines), session_management.md (720 lines)
- Makefile commands: ddd-continue, ddd-status, ddd-checkpoint (added but not implemented)
- Hook infrastructure: hook_precompact.py, hook_post_tool_use.py, hook_logger.py
- Agent system: 30+ agents with YAML frontmatter in .claude/agents/

### ❌ Missing (To Build)
**7 New Modules**:
1. tools/ddd_state_manager.py - State file I/O (impl_status.md, session_manifest.json, checkpoints/)
2. tools/ddd_chunk_analyzer.py - Parse code_plan.md into ChunkSpec objects
3. tools/ddd_budget_tracker.py - Token estimation with heuristics
4. tools/ddd_agent_selector.py - Dynamic agent discovery from .claude/agents/
5. tools/ddd_conflict_detector.py - Detect state conflicts on resume
6. tools/ddd_hooks.py - Hook handlers (PostToolUse:Edit, PreCompact)
7. tools/ddd_orchestrator.py - Main session loop and CLI

**State Files** (created by orchestrator):
- ai_working/ddd/impl_status.md
- ai_working/ddd/session_manifest.json
- ai_working/ddd/checkpoints/*.json

**Tests**: Unit tests per module + 3 integration tests

### ⚠️ To Modify
- .claude/tools/hook_precompact.py - Add DDD emergency checkpoint (20 lines)
- .claude/tools/hook_post_tool_use.py - Add impl_status.md logging (15 lines)

---

## Implementation Chunks

### Layer 1: Foundation (No dependencies)

**Chunk 1.1: State Manager** (~300 lines + 200 test lines)
**File**: tools/ddd_state_manager.py, tests/test_ddd_state_manager.py
**Purpose**: All state file I/O operations
**Exports**:
```python
def load_session_manifest() -> SessionManifest
def save_session_manifest(manifest: SessionManifest) -> None
def load_checkpoint(checkpoint_id: str) -> CheckpointData
def save_checkpoint(checkpoint: CheckpointData) -> None
def update_impl_status(session_id, chunk, status) -> None
def get_latest_checkpoint() -> CheckpointData | None
```
**Data Models**:
```python
@dataclass
class SessionManifest:
    sessions: List[Session]
    total_chunks: int
    completed_chunks: List[str]
    current_session: str | None

@dataclass
class CheckpointData:
    checkpoint_id: str
    timestamp: str
    session_id: str
    chunk: str
    files_modified: List[str]
    test_status: str
    context: Dict[str, Any]
    next_actions: List[str]
```
**Agent**: modular-builder
**Test**: CRUD operations, JSON schemas, error handling
**Commit**: "feat: Add DDD state manager with file-based persistence"

**Chunk 1.2: Chunk Analyzer** (~250 lines + 150 test)
**File**: tools/ddd_chunk_analyzer.py, tests/test_ddd_chunk_analyzer.py
**Purpose**: Parse code_plan.md into structured chunks
**Exports**:
```python
def parse_code_plan(plan_path: Path) -> List[ChunkSpec]
def get_next_chunk(chunks: List[ChunkSpec], completed: List[str]) -> ChunkSpec | None
```
**Data Model**:
```python
@dataclass
class ChunkSpec:
    id: str  # "1.1"
    title: str
    estimated_tokens: int
    dependencies: List[str]
    files_to_create: List[str]
    complexity: str  # simple|medium|complex
```
**Agent**: modular-builder
**Test**: Parse this file, handle malformed plans
**Commit**: Part of "feat: Add intelligence layer"

**Chunk 1.3: Budget Tracker** (~200 lines + 150 test)
**File**: tools/ddd_budget_tracker.py, tests/test_ddd_budget_tracker.py
**Purpose**: Token estimation and handoff triggers
**Constants**:
```python
BASE_TOKENS_PER_FILE = 1000
DEPENDENCY_TOKENS = 500
HANDOFF_THRESHOLD = 30000
COMPLEXITY_MULTIPLIERS = {"simple": 1.0, "medium": 1.5, "complex": 3.0}
```
**Exports**:
```python
def estimate_chunk_tokens(chunk: ChunkSpec) -> int
def should_handoff(used_tokens: int, estimated_next: int) -> bool
```
**Agent**: modular-builder
**Test**: Formula accuracy, threshold triggers
**Commit**: Part of "feat: Add intelligence layer"

### Layer 2: Intelligence (Depends on Layer 1)

**Chunk 2.1: Agent Selector** (~300 lines + 200 test)
**File**: tools/ddd_agent_selector.py, tests/test_ddd_agent_selector.py
**Purpose**: Discover agents dynamically from .claude/agents/
**Exports**:
```python
def discover_agents(agents_dir: Path = ".claude/agents") -> List[AgentMetadata]
def select_agent(chunk: ChunkSpec, agents: List[AgentMetadata]) -> str
def parse_agent_frontmatter(agent_file: Path) -> AgentMetadata
```
**Matching Logic**:
1. No dependencies → "modular-builder"
2. Match specializations to chunk type
3. Warn if >10k tokens
4. Fallback to "modular-builder"
**Agent**: modular-builder
**Test**: Parse YAML frontmatter, matching algorithm
**Commit**: "feat: Add agent discovery and conflict detection"

**Chunk 2.2: Conflict Detector** (~250 lines + 150 test)
**File**: tools/ddd_conflict_detector.py, tests/test_ddd_conflict_detector.py
**Purpose**: Detect state conflicts when resuming
**Exports**:
```python
def check_conflicts(checkpoint: CheckpointData) -> List[Conflict]
def check_file_modifications(files: List[str], since: datetime) -> List[FileConflict]
```
**Detection**: Use git to check file modifications since checkpoint timestamp
**Agent**: modular-builder
**Test**: Mock git history, verify detection
**Commit**: "feat: Add agent discovery and conflict detection"

### Layer 3: Orchestration (Depends on ALL above)

**Chunk 3.1: DDD Hooks** (~150 lines)
**File**: tools/ddd_hooks.py
**Purpose**: Hook handlers for PostToolUse:Edit and PreCompact
**Exports**:
```python
def handle_post_tool_use_edit(file_path: str) -> None  # Log to impl_status.md
def handle_pre_compact() -> None  # Emergency checkpoint
def is_ddd_session_active() -> bool  # Check impl_status.md exists
```
**Agent**: modular-builder
**Test**: Manual hook testing
**Commit**: "feat: Add DDD hook handlers"

**Chunk 3.2: Orchestrator Core** (~400 lines)
**File**: tools/ddd_orchestrator.py
**Purpose**: Main session loop and CLI
**Exports**:
```python
def start_session() -> SessionState
def resume_session() -> SessionState
def execute_chunk(chunk: ChunkSpec, session_state: SessionState) -> ChunkResult
def checkpoint(session_state: SessionState) -> None
def handoff_session(session_state: SessionState) -> None
def main()  # CLI entry: --resume, --status, --checkpoint
```
**Main Loop**:
```
LOAD state → PLAN next chunk → CHECK budget → EXECUTE chunk → CHECKPOINT → Repeat
```
**Dependencies**: Uses ALL modules (1.1, 1.2, 1.3, 2.1, 2.2, 3.1)
**Agent**: modular-builder + zen-architect review
**Test**: Manual workflow testing
**Commit**: "feat: Implement DDD orchestrator with session loop"

### Layer 4: Integration

**Chunk 4.1: Hook Integration** (Updates to existing files)
**Files**: .claude/tools/hook_precompact.py, .claude/tools/hook_post_tool_use.py
**Changes**:
- hook_precompact.py: Add ~20 lines to call ddd_hooks.handle_pre_compact() if DDD session active
- hook_post_tool_use.py: Add ~15 lines to call ddd_hooks.handle_post_tool_use_edit() for Edit/Write tools
**Agent**: modular-builder
**Test**: Manual compact trigger
**Commit**: "feat: Integrate DDD hooks into Claude Code hook chain"

**Chunk 4.2: Integration Tests** (~650 lines)
**Files**:
- tests/integration/test_ddd_single_session.py (~200 lines)
- tests/integration/test_ddd_multi_session.py (~250 lines)
- tests/integration/test_ddd_resume.py (~200 lines)
**Test Scenarios**:
1. Single session: Create plan → Execute all chunks → Verify completion
2. Multi-session: Session 1 → Handoff → Resume → Session 2 → Complete
3. Resume with conflicts: Checkpoint → Modify file → Resume → Conflict detected
**Agent**: modular-builder
**Commit**: "test: Add comprehensive DDD workflow integration tests"

### Layer 5: Polish

**Chunk 5.1: Documentation** (~500 lines updates)
**Files**: Inline docstrings across all modules, .claude/commands/ddd.md (if exists)
**Changes**: Add comprehensive docstrings, update command docs
**Agent**: Direct writing
**Commit**: "docs: Update DDD docs and add comprehensive docstrings"

**Chunk 5.2: Error Recovery** (~2000 lines improvements)
**Files**: Enhanced error handling across all modules
**Changes**: Better logging, user-friendly error messages, recovery logic
**Agent**: modular-builder
**Test**: Trigger error conditions
**Commit**: "fix: Add error recovery and enhanced logging"

---

## Dependencies Graph

```
Layer 1 (Foundation):
  1.1 State Manager
  1.2 Chunk Analyzer
  1.3 Budget Tracker

Layer 2 (Intelligence):
  2.1 Agent Selector  ← 1.2 (ChunkSpec type)
  2.2 Conflict Detector ← 1.1 (CheckpointData type)

Layer 3 (Orchestration):
  3.1 DDD Hooks ← 1.1
  3.2 Orchestrator ← ALL (1.1, 1.2, 1.3, 2.1, 2.2, 3.1)

Layer 4 (Integration):
  4.1 Hook Integration ← 3.1, 3.2
  4.2 Integration Tests ← ALL code

Layer 5 (Polish):
  5.1, 5.2 ← ALL code
```

**Sequential execution required** - Cannot parallelize due to dependencies.

---

## Agent Strategy

**Primary**: modular-builder for ALL chunks

**Task Template**:
```
Task modular-builder: "Implement Chunk X.Y from code_plan.md.
Use data models from session_management.md reference.
Follow IMPLEMENTATION_PHILOSOPHY.md ruthless simplicity."
```

**Secondary Agents** (if needed):
- zen-architect: Review orchestrator design (Chunk 3.2)
- bug-hunter: Debug implementation failures
- test-coverage: Suggest additional test cases

---

## Commit Strategy

1. **Commit 1** (After 1.1): "feat: Add DDD state manager"
2. **Commit 2** (After 1.2, 1.3): "feat: Add intelligence layer (chunk analyzer + budget tracker)"
3. **Commit 3** (After 2.1, 2.2): "feat: Add agent discovery and conflict detection"
4. **Commit 4** (After 3.1): "feat: Add DDD hook handlers"
5. **Commit 5** (After 3.2): "feat: Implement DDD orchestrator"
6. **Commit 6** (After 4.1): "feat: Integrate DDD hooks"
7. **Commit 7** (After 4.2): "test: Add integration tests"
8. **Commit 8** (After 5.1, 5.2): "docs: Add docs and error recovery"

All commits include Amplifier co-author attribution.

---

## Estimates

**Total**:
- **Chunks**: 11
- **Tokens**: ~27,500
- **Sessions**: 2-3 (assuming ~15k tokens/session)
- **Calendar Time**: 1-2 days
- **Lines of Code**: ~2800 (code + tests)
- **New Files**: 18
- **Modified Files**: 2-3

---

## Philosophy Compliance

### Ruthless Simplicity ✅
- **NOT building**: ML prediction, databases, distributed coordination, complex retry, MPC
- **ARE building**: File-based state, simple heuristics, git commits, direct I/O, explicit checkpoints
- Start minimal, avoid future-proofing, clear over clever

### Modular Design ✅
- **Bricks**: Each module <400 lines, self-contained
- **Studs**: Clear data models (SessionState, ChunkSpec, etc.), function signatures
- **Regeneratable**: Can rebuild from this spec

---

## Success Criteria

**Functional**:
- [ ] Multi-session workflows (3+ sessions seamlessly)
- [ ] State preservation (never lost)
- [ ] Perfect resumption (make ddd-continue)
- [ ] Auto-checkpointing (after every chunk)

**Quality**:
- [ ] Zero manual state tracking
- [ ] >70% sub-agent delegation
- [ ] Token predictions within 20%
- [ ] Auto impl_status.md updates

**UX**:
- [ ] Invisible session boundaries
- [ ] <30 second resume
- [ ] Clear status always
- [ ] Understandable history

---

## Risk Mitigation

**High Risk**:
1. **Hook Integration** (4.1): Conditional DDD logic, non-blocking, extensive logging
2. **Orchestrator Complexity** (3.2): Incremental build, extensive logging, manual testing first
3. **Token Accuracy** (1.3): Conservative threshold (30k), adjustable constants, logging actual vs estimated

**Dependencies**:
- Python 3.11+ (dataclasses, type hints)
- Git (for conflicts, checkpoints)
- Claude Code Hook API (follow existing patterns)

---

**Status**: ✅ Code plan complete and detailed
**Next**: User approval → `/ddd:4-code` → Execute Chunk 1.1
**Complexity**: Medium-High (new infrastructure, clear requirements)
**Risk**: Low (incremental, testable, philosophy-aligned)
