---
name: chunked-planning
description: Enforces chunked planning before implementation. Breaks down complex features into phases with quality gates. Use when planning complex features, before major code changes, or implementing multi-day tasks. Triggers on "plan feature", "implement feature", "complex task", "multi-step".
---

# Chunked Planning

Ensures proper planning before implementation of complex features.

## Workflow

1. **Sparring Phase**: Clarify requirements with user
2. **Documentation Phase**: Create FEATURE_STRATEGY.md
3. **Planning Phase**: Break into chunks (1 chunk = 1 session)
4. **Execution Phase**: Implement chunk-by-chunk
5. **Quality Gate**: Verify before next phase

## Templates

See [PLANNING_FRAMEWORK.md](PLANNING_FRAMEWORK.md) for templates.

## Feature Strategy Template

Create `ai_working/YYYY-MM-DD_<feature-name>/FEATURE_STRATEGY.md`:

```markdown
# Feature: <Name>

## Problem Statement
What problem are we solving? Who has it? What's the impact?

## Scope
- MUST: ...
- SHOULD: ...
- WON'T: ...

## Current State
- Relevant files with line numbers
- Existing patterns

## Target State
- Architecture diagram
- Key changes

## Phases
1. Phase 1: Foundation (Chunk A, B)
2. Phase 2: Core (Chunk C, D)
3. Phase 3: Polish (Chunk E)

## Quality Gates
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Code reviewed
```

## Session Handoff

Before context compact or session end:
- Document current progress
- List pending tasks
- Note blockers
- Save to `ai_working/` folder

## When to Use

- Multi-day features
- Features touching >3 files
- Architectural changes
- After user says "let's plan..."
