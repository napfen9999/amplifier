# Planning Framework

Templates and guidelines for chunked planning.

## Phase Structure

### Phase 0: Sparring (BEFORE Documentation)

Ask these questions:

1. **Problem**: What is the concrete problem? (Symptom vs Root Cause)
2. **Who**: Who has the problem? (User/System/Developer)
3. **Impact**: What happens if we do nothing?
4. **Boundaries**: What is explicitly OUT of scope?
5. **Dependencies**: What depends on this? What does this depend on?
6. **Success Criteria**: How do we know it works? (Measurable)
7. **MVP**: What's the minimum viable solution?
8. **Hypotheses**: What are our assumptions?

### Phase 1: Documentation

Create `ai_working/YYYY-MM-DD_<feature-name>/`:

```
ai_working/2026-01-15_new-feature/
├── FEATURE_STRATEGY.md    # Main spec
├── CURRENT_STATE.md       # Analysis
└── SESSION_NOTES.md       # Progress tracking
```

### Phase 2: Planning

Break into chunks:
- 1 Chunk = 1 Session (~2-3 files max)
- Each chunk has clear Definition of Done
- Quality Gate between phases

### Phase 3: Execution

For each chunk:
1. Read FEATURE_STRATEGY.md
2. Implement changes
3. Run tests
4. Update SESSION_NOTES.md
5. Mark chunk as done

### Phase 4: Session Handoff

Before `/compact` or ending session:

```markdown
## Session Handoff - YYYY-MM-DD HH:MM

### Completed
- [x] Task 1
- [x] Task 2

### In Progress
- [ ] Task 3 (70% done, need to...)

### Blockers
- Issue X needs clarification

### Next Steps
1. Complete Task 3
2. Start Task 4
```

## Anti-Patterns

- Starting implementation without sparring
- No documentation before code
- Chunks too large (>3 files)
- No session handoff before compact
- No quality gates between phases

## Templates

### FEATURE_STRATEGY.md Template

```markdown
# Feature: <Name>

**Date**: YYYY-MM-DD
**Status**: PLANNING | IN_PROGRESS | DONE

## Problem Statement
[What problem? Who has it? What's the impact?]

## Scope
### MUST
- ...

### SHOULD
- ...

### WON'T
- ...

## Current State
- `file.py:123` - Current implementation
- ...

## Target State
[Architecture diagram, key changes]

## Phases

### Phase 1: Foundation
- Chunk A: [files, DoD]
- Chunk B: [files, DoD]

### Phase 2: Core
- Chunk C: [files, DoD]
- Chunk D: [files, DoD]

## Quality Gates
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Code reviewed

## Session Log
| Date | Session | Progress |
|------|---------|----------|
| | | |
```
