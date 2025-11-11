# Hotfix: Disable SubagentStop Hook

**Date**: 2025-11-11
**Severity**: 🔴 Critical
**Status**: ✅ Applied

---

## Problem

SubagentStop hook was triggering recursive cascade via LLM API calls:

```
Hook → Claude SDK → Spawns Subagent → SubagentStop → Hook → ♾️
```

**Impact**:
- 4,125 memory extraction subagents auto-spawned
- 412× amplification (from ~10 real sessions)
- 3.5 hours session thrashing
- ~4,000 unnecessary LLM API calls

**Root Cause**: `extraction/core.py` calls Claude SDK in hook context, spawning new subagents.

**See**: `MEMORY_SYSTEM_ARCHITECTURE_ANALYSIS.md` for complete forensic analysis.

---

## Hotfix Applied

**File**: `.claude/settings.json`

**Change**: Removed SubagentStop hook registration

```diff
     "Stop": [
       {
         "hooks": [
           {
             "type": "command",
             "command": "$CLAUDE_PROJECT_DIR/.claude/tools/hook_stop.py"
           }
         ]
       }
     ],
-    "SubagentStop": [
-      {
-        "hooks": [
-          {
-            "type": "command",
-            "command": "$CLAUDE_PROJECT_DIR/.claude/tools/hook_stop.py"
-          }
-        ]
-      }
-    ],
```

**Effect**:
- ✅ Cascade stopped immediately
- ✅ Memory extraction only on Stop (complete conversations)
- ✅ No more subagent spawning from hooks
- ✅ Normal session behavior restored

---

## Testing

**Before hotfix**:
- SubagentStop fires → calls LLM → spawns subagent → infinite loop
- 12,466 hook invocations in 3.5 hours
- System unusable

**After hotfix**:
- SubagentStop no longer registered
- Only Stop hook fires (at session end)
- No cascade
- Normal performance

**Test**:
```bash
# Enable memory system
echo "MEMORY_SYSTEM_ENABLED=true" >> .env

# Run a session with subagents
# (Will NOT trigger cascade anymore)

# Check logs
tail -100 .claude/logs/stop_hook_*.log
# Should only see Stop events, no SubagentStop spam
```

---

## What This Means

### Memory Extraction Behavior

**Before**:
- Extracted on EVERY subagent completion (SubagentStop)
- Incomplete context (subagent transcripts are warmup-only)
- Triggered cascade

**After**:
- Extracts only on session end (Stop)
- Complete conversation context
- No cascade risk

### Side Effects

**Lost functionality** (was broken anyway):
- ❌ No real-time memory extraction during subagent execution
  - This never worked correctly (incomplete transcripts)
  - Not a meaningful loss

**Preserved functionality**:
- ✅ Memory extraction at session end
- ✅ Complete conversation context
- ✅ SessionStart memory injection
- ✅ All memory CLI commands

---

## Next Steps

This is a **temporary hotfix** to stop the bleeding.

**Complete solution** (DDD Phase 2) will implement:
1. Hook-level event detection (skip SubagentStop explicitly)
2. Sidechain message filtering
3. Queue-based background processing (remove LLM calls from hooks)
4. Complete test suite

**See**: DDD Phase 1 Plan (to be created) for full refactor design.

---

## Revert Instructions

If this hotfix needs to be reverted (not recommended):

```bash
cd amplifier
git revert <this-commit-hash>
# This will re-enable SubagentStop hook
# WARNING: Will re-trigger cascade if memory system enabled
```

---

## References

- `MEMORY_SYSTEM_ARCHITECTURE_ANALYSIS.md` - Complete forensic analysis
- `HOOK_SPAM_ANALYSIS.md` - Initial findings
- `MEMORY_SYSTEM_FINDINGS.md` - Problem identification
- GitHub Issue #7881 - SubagentStop session ID identification

---

**Impact**: 🔴 Critical → ✅ Resolved
**Risk**: None (removes broken functionality)
**Rollout**: Immediate (already applied)
