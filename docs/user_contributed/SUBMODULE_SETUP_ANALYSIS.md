# Amplifier Setup Analysis Report

**Date**: 2025-11-10
**Project**: Brand Composer Amplifier
**Status**: Incomplete Setup - Submodule .claude Not Accessible

---

## Executive Summary

Amplifier is correctly installed as a git submodule in `/home/ufeld/dev/brand_composer_amplifyier/amplifier/`, but the Claude Code platform integration is **incomplete**. Slash commands and AI agents are not accessible from the parent project because the `.claude/` directory is nested inside the submodule rather than at the workspace root.

**Current Situation:**
- ✅ Amplifier code and documentation present
- ✅ Complete .claude setup exists in amplifier/
- ✅ CLAUDE.md guidance document exists in parent project
- ❌ .claude directory not accessible from parent project root
- ❌ Slash commands (/ultrathink-task, /ddd:*, etc.) fail
- ❌ AI agents not discoverable
- ❌ Project-specific configuration not in parent project

---

## How Amplifier Should Be Installed

### Two Valid Patterns

#### Pattern 1: Amplifier as Workspace Root (Primary)
**This is the recommended approach for the workspace pattern.**

```bash
cd my-workspace
git clone https://github.com/microsoft/amplifier.git .
git submodule add <project-url> my-project/

# Directory structure:
my-workspace/
├── .claude/              # ← Amplifier's setup (agents, commands, hooks)
├── amplifier/            # ← (would not exist - you ARE in amplifier)
├── my-project/           # ← Your project as submodule
│   └── AGENTS.md         # ← Project-specific guidance
└── CLAUDE.md             # ← Workspace-level guidance
```

**Pros:**
- .claude is at workspace root where Claude Code finds it
- Clean workspace pattern
- All tools and commands immediately available

**Cons:**
- Requires cloning Amplifier into workspace root
- Less applicable if Amplifier updates are important

#### Pattern 2: Project as Sibling (Current Setup)
**This is what brand_composer_amplifyier currently implements.**

```bash
cd some-parent-directory
git clone https://github.com/microsoft/amplifier.git amplifier
mkdir brand_composer_amplifyier
cd brand_composer_amplifyier
git init
# (or clone existing project)
```

**Current Structure:**
```bash
parent-directory/
├── amplifier/            # ← Amplifier workspace (complete with .claude)
│   ├── .claude/          # ← Tools, agents, commands
│   ├── docs/
│   ├── scenarios/
│   ├── CLAUDE.md
│   └── AGENTS.md
│
└── brand_composer_amplifyier/  # ← Your project
    ├── CLAUDE.md              # ← Project guidance (present)
    ├── amplifier -> ../amplifier (if symlinked)
    ├── src/
    ├── docs/
    └── ai_working/
```

**Pros:**
- Project independence
- Can update Amplifier separately
- Clear separation

**Cons:**
- .claude is not accessible from project root
- Requires explicit symlink or configuration
- Slash commands don't work without setup

---

## Current Project Structure Analysis

### What Exists

**In `/home/ufeld/dev/brand_composer_amplifyier/`:**
- ✅ CLAUDE.md (3,320 bytes) - Guidance document
- ✅ amplifier/ - Git submodule (15 directories)
- ✅ ai_context/ - Documentation files
- ✅ ai_working/ - Working files directory
- ✅ src/ - Source code

**In `/home/ufeld/dev/brand_composer_amplifyier/amplifier/.claude/`:**
- ✅ agents/ (32 agent definitions)
  - Analysis engine, bug hunter, zen-architect, security guardian, etc.
- ✅ commands/ (50+ command definitions)
  - /ddd:0-help through /ddd:5-finish
  - /ultrathink-task
  - /designer
  - /transcripts
  - /prime
  - Plus DDD family of commands
- ✅ tools/ (10+ automation scripts)
  - hook_precompact.py - Transcript export
  - hook_post_tool_use.py - Post-tool automation
  - hook_session_start.py - Session initialization
  - subagent-logger.py - Agent logging
  - Various hook handlers
- ✅ settings.json - Hook configuration
  - SessionStart hooks
  - PostToolUse hooks
  - PreCompact hooks
  - Notification handlers

### What's Missing

**In `/home/ufeld/dev/brand_composer_amplifyier/` (Parent Project Root):**
- ❌ .claude/ directory or symlink
- ❌ settings.json configuration
- ❌ Direct access to slash commands
- ❌ Hook configuration for parent project

---

## Why Slash Commands Don't Work

### How Claude Code Locates .claude

1. When you run `claude` from `/home/ufeld/dev/brand_composer_amplifyier/`
2. Claude Code looks for `.claude/` at:
   - Current directory: `/home/ufeld/dev/brand_composer_amplifyier/.claude/` ← NOT FOUND
   - Parent directories: `/home/ufeld/dev/.claude/`, `/home/ufeld/.claude/`, etc. ← NOT FOUND

3. Never finds it in: `/home/ufeld/dev/brand_composer_amplifyier/amplifier/.claude/`

### Result
- Slash commands undefined (/ultrathink-task fails)
- Agents not discoverable
- Hooks don't execute
- No workspace-level setup

---

## Solution: Making .claude Accessible

### Option 1: Symlink (Simplest)

```bash
cd /home/ufeld/dev/brand_composer_amplifyier

# Create symlink to amplifier's .claude
ln -s amplifier/.claude .claude

# Verify
ls -la .claude
# Should show: .claude -> amplifier/.claude
```

**Pros:**
- Simple one-time setup
- No duplication
- Updates to amplifier automatically reflected
- Works with all slash commands

**Cons:**
- Windows WSL symlink issues if not handled correctly
- Relative symlink breaks if moved

### Option 2: Copy .claude (Safety First)

```bash
cd /home/ufeld/dev/brand_composer_amplifyier

# Copy entire directory
cp -r amplifier/.claude ./.claude

# Then update paths in settings.json if needed
```

**Pros:**
- Complete independence
- No symlink issues
- Can customize without affecting amplifier

**Cons:**
- Duplication
- Manual updates when amplifier changes
- More disk space

### Option 3: Use Parent Amplifier Directory

**If you want to run Claude from parent directory:**

```bash
cd /home/ufeld/dev
claude
```

Then reference projects as @amplifier/my-project or @brand_composer_amplifyier/

**Pros:**
- No setup needed
- Amplifier's .claude works immediately
- Single workspace for both projects

**Cons:**
- Less project-focused
- Broader scope than needed

---

## Recommended Configuration

### For This Project Setup

**Execute once:**
```bash
cd /home/ufeld/dev/brand_composer_amplifyier
ln -s amplifier/.claude .claude
```

**Then verify:**
```bash
# All these should work
ls -la .claude
cat .claude/commands/ultrathink-task.md
ls .claude/agents/
```

**In Claude Code (from parent directory):**
```
I'm working on the brand_composer_amplifyier project.
Run /ultrathink-task to see if slash commands work.
```

---

## Complete Amplifier Installation Checklist

### Prerequisites
- [x] Python 3.11+ available
- [x] Node.js installed
- [x] pnpm installed
- [x] uv installed
- [x] Git installed

### Amplifier Installation
- [x] Amplifier cloned to `amplifier/` subdirectory
- [x] Git submodule properly registered
- [ ] **MISSING**: .claude symlink/copy to parent root
- [ ] **MISSING**: make install run in parent project

### Project Setup
- [x] CLAUDE.md exists (parent project guidance)
- [ ] **TODO**: .claude/settings.json configured for parent project
- [ ] **TODO**: Project-specific AGENTS.md (if needed)
- [ ] **TODO**: Hook configuration for build checks

### Verification Commands

```bash
# 1. Check submodule status
cd /home/ufeld/dev/brand_composer_amplifyier
git submodule status
# Should show: 1f967ed [hash] amplifier (with commit)

# 2. Check amplifier .claude exists
ls -la amplifier/.claude/commands/ | wc -l
# Should show: 50+

# 3. Verify symlink creation
ln -s amplifier/.claude .claude
ls -la .claude

# 4. Check specific commands
cat .claude/commands/ultrathink-task.md

# 5. Verify agents
ls .claude/agents/ | wc -l
# Should show: 32+

# 6. Test settings.json
cat .claude/settings.json | head -20
```

---

## Files Analyzed

### Main Documentation
- ✅ `/amplifier/README.md` - Setup instructions, workspace pattern
- ✅ `/amplifier/.claude/README.md` - Platform architecture
- ✅ `/amplifier/docs/WORKSPACE_PATTERN.md` - Detailed pattern explanation
- ✅ `/brand_composer_amplifyier/CLAUDE.md` - Project guidance

### Configuration
- ✅ `/amplifier/.claude/settings.json` - Hook configuration (160 lines)
  - SessionStart hooks
  - PostToolUse hooks (Edit, MultiEdit, Write)
  - PreCompact hooks (transcript export)
  - Notification hooks

### Agents (32 total)
Examples:
- `zen-architect` - Architecture design
- `bug-hunter` - Issue diagnosis
- `test-coverage` - Test recommendations
- `component-designer` - UI component design
- `security-guardian` - Security review
- Plus 27 more specialized agents

### Commands (50+ total)
Structure:
- `/ultrathink-task` - Metacognitive problem solving
- `/ddd:*` - Document-Driven Development workflow
  - `/ddd:0-help` through `/ddd:5-finish`
  - `/ddd:prime`
  - `/ddd:status`
- `/designer` - Design system commands
- `/transcripts` - Conversation management
- `/modular-build` - Modular development
- Plus 40+ more commands

### Philosophy Documents
- ✅ IMPLEMENTATION_PHILOSOPHY.md
- ✅ MODULAR_DESIGN_PHILOSOPHY.md
- ✅ Design system philosophy (4 documents)
- ✅ DISCOVERY.md (learnings log)

---

## Key Insights

### 1. Workspace Pattern Maturity
Amplifier's workspace pattern is **complete and production-ready**:
- Clear separation of Amplifier workspace from projects
- Multiple project support (side-by-side)
- Independent git histories
- Persistent context via AGENTS.md

### 2. .claude Directory Role
The `.claude/` directory at workspace root is **critical infrastructure**:
- **Agents**: 32 specialized AI assistants
- **Commands**: 50+ reusable workflows
- **Hooks**: Automated actions on events
- **Settings**: Configuration for permissions, MCP, tools

### 3. Current Blocking Issue
The **only thing preventing this from working** is the physical location:
- `.claude` is in `amplifier/.claude/`
- Claude Code looks for it in `.`
- Simple symlink fixes everything

### 4. Documentation Quality
All documentation is **exceptionally thorough**:
- Consistent philosophy across 20+ docs
- Clear examples and anti-patterns
- Theory grounded in research (psychology, human factors)
- Implementation guidance with exact steps

---

## Implementation Path

### Immediate (Fix .claude Access)
```bash
cd /home/ufeld/dev/brand_composer_amplifyier
ln -s amplifier/.claude .claude
```

### Short Term (Verify Everything Works)
```bash
# Test slash commands
/ultrathink-task Brainstorm ideas for feature X

# Test agents
# (via /agents or within tasks)

# Verify hooks
# (Run make check and look for automation)
```

### Medium Term (Customize)
- Create project-specific AGENTS.md if needed
- Add custom commands to .claude/commands/
- Adjust settings.json for project needs
- Document custom agents

### Long Term (Enhance)
- Add custom agents for domain-specific tasks
- Create specialized slash commands
- Integrate with project build system
- Build custom tools in .claude/tools/

---

## Conclusions

### Current State
✅ **Amplifier is properly installed as submodule**
❌ **Claude Code integration incomplete (missing .claude symlink)**

### Root Cause
The `.claude/` directory is nested inside the `amplifier/` submodule, but Claude Code expects it at the workspace root.

### Solution
Create a symlink: `ln -s amplifier/.claude .claude`

### Impact
One command enables:
- 50+ slash commands
- 32 AI agents
- Hook automation
- Workspace configuration
- All Amplifier tooling

---

## Recommendations

### Immediate Actions
1. **Create symlink** to make .claude accessible
2. **Test slash commands** to verify setup
3. **Document** this in project README or setup guide

### Future Improvements
1. Consider adding setup instructions to brand_composer_amplifyier/README.md
2. Create project-specific documentation referencing Amplifier tools
3. Add custom agents for brand composition domain
4. Build specialized commands for solver workflows

### Documentation to Reference
When working with this setup, refer to:
- `amplifier/README.md` - Installation and getting started
- `amplifier/CLAUDE.md` - Workspace guidance
- `amplifier/docs/CREATE_YOUR_OWN_TOOLS.md` - Building custom tools
- `brand_composer_amplifyier/CLAUDE.md` - Project-specific context

---

**Report Status**: ✅ Complete
**Last Updated**: 2025-11-10
