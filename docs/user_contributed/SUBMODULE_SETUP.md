# Amplifier Submodule Setup Guide

⚠️ **AUTHORITATIVE GUIDE** - This is the single source of truth for Amplifier submodule setup

**Complete guide for integrating Amplifier as a git submodule in other projects**

**Last Updated**: 2025-11-10
**Tested With**: Brand Composer Amplifier (reference implementation)
**Status**: ✅ Production-Ready

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture: Standard vs Inverted Setup](#architecture-standard-vs-inverted-setup)
3. [Quick Start](#quick-start)
4. [Step-by-Step Setup](#step-by-step-setup)
5. [Dependency Management](#dependency-management)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)
8. [Automated Setup Script](#automated-setup-script)

---

## Overview

Amplifier can be used in two ways:

**Standard Setup**: Amplifier is the main project
- `.claude/` is at repository root
- Python modules in `amplifier/` subdirectory
- Direct Claude Code integration

**Inverted Setup** (This Guide): Amplifier as submodule
- Parent project is the main repository
- Amplifier added as git submodule
- Requires symlink + Python path configuration
- Claude Code integration through symlink

**This guide covers the Inverted Setup**, which allows you to use Amplifier's features in your own projects.

---

## Architecture: Standard vs Inverted Setup

### Standard Setup (Amplifier as Main Project)

```
amplifier/                    # Repository root
├── .claude/                  # Claude Code integration
│   ├── commands/            # Slash commands
│   ├── agents/              # AI agents
│   └── tools/               # Hooks & utilities
├── amplifier/               # Python package (nested!)
│   ├── memory/
│   ├── knowledge/
│   └── synthesis/
└── pyproject.toml
```

**Pros**:
- Simple setup
- Direct Claude Code access
- All features immediately available

**Cons**:
- Amplifier must be your main project
- Can't combine with existing projects

---

### Inverted Setup (Amplifier as Submodule)

```
your-project/                 # Your main repository
├── .claude -> amplifier/.claude  # Symlink (CRITICAL!)
├── amplifier/                # Git submodule
│   ├── .claude/             # Claude Code integration
│   ├── amplifier/           # Python package (nested!)
│   └── pyproject.toml
├── your_code/
└── pyproject.toml           # Your project's dependencies
```

**Pros**:
- Keep your project structure
- Add Amplifier features as needed
- Easy to update Amplifier

**Cons**:
- Requires symlink setup
- Dependency management considerations
- Python path configuration needed

---

## Quick Start

For the impatient:

```bash
# 1. Add Amplifier as submodule
git submodule add https://github.com/yourusername/amplifier.git amplifier
git submodule update --init --recursive

# 2. Create symlinks for Claude Code integration (but NOT .vscode)
ln -s amplifier/.claude .claude
ln -s amplifier/.ai .ai

# Create local .vscode settings (excludes amplifier from analysis)
mkdir -p .vscode
cat > .vscode/settings.json << 'EOF'
{
  "python.analysis.exclude": ["**/amplifier/**"],
  "python.analysis.ignore": ["amplifier"],
  "files.watcherExclude": {"**/amplifier/**": true},
  "search.exclude": {"**/amplifier/**": true}
}
EOF

# 3. Configure parent project .env (per-project control)
cat > .env << 'EOF'
MEMORY_SYSTEM_ENABLED=true
MEMORY_MAX_MEMORIES=1000
ANTHROPIC_API_KEY=your-api-key-here
EOF

# 4. Install dependencies (Option A: In parent project)
uv pip install networkx langchain langchain-core langchain-openai \
               pydantic-settings rapidfuzz tiktoken pyvis

# 5. Verify
python3 -c "
import sys
sys.path.insert(0, 'amplifier')
from amplifier.knowledge import graph_builder
print('✅ Amplifier working!')
"
```

**Done!** Claude Code features and Amplifier modules now available.

---

## Step-by-Step Setup

### Step 1: Add Amplifier as Git Submodule

```bash
# Navigate to your project root
cd /path/to/your/project

# Add Amplifier as submodule
git submodule add https://github.com/yourusername/amplifier.git amplifier

# Initialize and update
git submodule update --init --recursive

# Commit the submodule addition
git add .gitmodules amplifier
git commit -m "Add Amplifier as git submodule"
```

**Result**: `amplifier/` directory in your project root.

---

### Step 2: Create Symlinks for Claude Code Integration

**Critical Step**: Claude Code looks for configuration directories at workspace root.

**Two symlinks needed**:
- `.claude/` - Claude Code features (commands, agents, tools, hooks)
- `.ai/` - AI context files and documentation

**❌ DO NOT symlink `.vscode/`** - This causes VS Code to scan the entire amplifier submodule (15,000+ files), resulting in thousands of errors.

```bash
# From your project root
ln -s amplifier/.claude .claude
ln -s amplifier/.ai .ai

# Verify symlinks
ls -la | grep -E "^l.*(claude|ai)"
# Should show:
# .ai -> amplifier/.ai
# .claude -> amplifier/.claude
```

**What this does**:
- Makes all Amplifier's slash commands available
- Enables 30+ AI agents
- Activates hooks (SessionStart, PostToolUse, etc.)
- Provides Amplifier tools and utilities

**Verification**:
```bash
# List available commands
ls .claude/commands/
# Should show: ddd, prime, ultrathink-task, etc.

# List available agents
ls .claude/agents/
# Should show: 30 agent files
```

---

### Step 2b: Configure VS Code to Exclude Amplifier Submodule

**Why This Step is Critical**: Symlinking `.vscode/` causes VS Code to analyze the entire Amplifier submodule (15,000+ files), resulting in:
- 9,000+ errors from analyzing amplifier's internal code
- 354+ warnings
- Slow editor performance
- Constant background analysis

**Solution**: Create a local `.vscode/settings.json` that excludes the amplifier submodule.

```bash
# Create local .vscode directory
mkdir -p .vscode
```

Then create `.vscode/settings.json` with the following content:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.analysis.diagnosticMode": "workspace",
  "python.analysis.typeCheckingMode": "standard",

  // CRITICAL: Exclude amplifier submodule from analysis
  "python.analysis.exclude": [
    "**/amplifier/**",
    "**/.venv/**",
    "**/node_modules/**",
    "**/__pycache__/**"
  ],
  "python.analysis.ignore": [
    "amplifier",
    ".venv",
    "__pycache__"
  ],

  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.rulers": [120]
  },

  "ruff.nativeServer": "on",
  "ruff.exclude": [
    "**/amplifier/**",
    "**/.venv/**"
  ],

  "python.testing.pytestEnabled": false,
  "python.testing.unittestEnabled": false,

  "files.watcherExclude": {
    "**/amplifier/**": true,
    "**/.venv/**": true,
    "**/node_modules/**": true,
    "**/__pycache__/**": true,
    "**/.pytest_cache/**": true
  },
  "search.exclude": {
    "**/amplifier/**": true,
    "**/.venv": true,
    "**/__pycache__": true,
    "**/.data": true
  }
}
```

**What this does**:
- Prevents VS Code from scanning amplifier's 15,000+ files
- Eliminates thousands of irrelevant errors/warnings
- Improves editor performance significantly
- Keeps your project's Python analysis focused on your code

**Verification**:
```bash
# Check VS Code isn't analyzing amplifier
# Open VS Code and verify:
# - No errors from amplifier/ directory
# - Status bar shows reasonable file count
# - "Problems" panel only shows your project's issues
```

---

### Step 3: Configure .env for Per-Project Control

**Critical for Multi-Project Usage**: Each parent project can independently enable/disable Amplifier features via `.env` configuration.

#### Create Parent Project .env

In your parent project root (NOT in the amplifier submodule):

```bash
# your-project/.env
MEMORY_SYSTEM_ENABLED=true     # Enable memory system for THIS project
MEMORY_MAX_MEMORIES=1000       # Maximum memories to keep (rotation kicks in above this)
ANTHROPIC_API_KEY=sk-ant-...   # REQUIRED for memory extraction (get at console.anthropic.com)
```

**Available Memory Configuration:**
- `MEMORY_SYSTEM_ENABLED`: Enable/disable memory system (`true`/`false`)
- `MEMORY_MAX_MEMORIES`: Maximum memories to keep (default: 1000, range: 10-100000)
  - When exceeded, oldest/least-accessed memories are automatically rotated out
  - Higher values use more disk space but retain more history
- `ANTHROPIC_API_KEY`: **REQUIRED** for memory extraction (LLM-based memory generation)
  - Get your API key at https://console.anthropic.com/settings/keys
  - Add credits to your Anthropic Console account (pay-as-you-go billing)
  - **Note**: Your Claude Code subscription (Pro/Max) **cannot** be used for the SDK
  - The Memory System uses the Anthropic API (separate billing) for programmatic access
  - Memory extraction with Haiku 4.5 is very cost-effective (~$0.001-0.01 per session)

**Why This Works**:
1. Hook loads **submodule `.env`** first (safe defaults: `MEMORY_SYSTEM_ENABLED=false`)
2. Hook loads **parent `.env`** second with `override=True` (your project's settings win)
3. Each parent project controls feature activation independently

**Example Multi-Project Setup**:
```
project-a/
├── .env (MEMORY_SYSTEM_ENABLED=true)   # Memory active
└── amplifier/ (submodule)

project-b/
├── .env (MEMORY_SYSTEM_ENABLED=false)  # Memory disabled
└── amplifier/ (same submodule!)
```

**Same submodule, different behavior per project.**

**Verification**:
```bash
# Test hook respects parent .env
echo '{"event": "Stop"}' | .venv/bin/python3 .claude/tools/hook_stop.py 2>&1 | grep -i "memory system"
# Should show: "Starting memory extraction" (if enabled)
#           or "Memory system disabled" (if disabled)
```

---

### Step 4: Fix Python Import Path for Hooks

**Critical Step**: Hooks need access to both Amplifier modules AND venv dependencies (like `claude-code-sdk`).

#### Problem 1: Symlinked paths need `.resolve()`

Without `.resolve()`, Python follows the symlink path instead of the real path, breaking imports.

#### Problem 2: Hooks run with system Python

Hooks use `#!/usr/bin/env python3` (system Python) which doesn't have access to dependencies installed in `.venv` (like `claude-code-sdk`, required by memory/extraction modules).

#### Solution: Update All Three Hooks

**Files to update**:
- `amplifier/.claude/tools/hook_stop.py`
- `amplifier/.claude/tools/hook_session_start.py`
- `amplifier/.claude/tools/hook_post_tool_use.py`

**For each hook, add venv site-packages to Python path BEFORE importing amplifier modules**:

```python
# Get the amplifier root directory (3 levels up from this file)
# IMPORTANT: Use .resolve() to handle symlinks correctly
amplifier_root = Path(__file__).resolve().parent.parent.parent

# Add amplifier venv to Python path FIRST (so we get claude-code-sdk and other dependencies)
venv_site_packages = amplifier_root / ".venv" / "lib"
if venv_site_packages.exists():
    # Find the python3.x directory
    python_dirs = list(venv_site_packages.glob("python3.*"))
    if python_dirs:
        site_packages = python_dirs[0] / "site-packages"
        if site_packages.exists():
            sys.path.insert(0, str(site_packages))

# Add amplifier to path
sys.path.insert(0, str(amplifier_root))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()
```

**What this does**:
1. **Resolves symlinks**: `.resolve()` finds the real path through symlinks
2. **Adds venv dependencies**: System Python can now find `claude-code-sdk` and other packages
3. **Adds amplifier modules**: Python can import from `amplifier.memory`, `amplifier.extraction`, etc.

**Why this matters**:
- **Without venv path**: `ImportError: No module named 'amplifier.extraction'` (claude-code-sdk missing)
- **Without .resolve()**: Wrong directory → import failures
- **With both fixes**: Hooks work correctly in submodule setup

**Verification**:
```bash
# Test all three hooks
echo '{}' | python3 .claude/tools/hook_stop.py 2>&1 | grep -i error
echo '{}' | python3 .claude/tools/hook_session_start.py 2>&1 | grep -i error
echo '{}' | python3 .claude/tools/hook_post_tool_use.py 2>&1 | grep -i error

# All three should show NO import errors
# If you see "Failed to import amplifier modules", the venv path fix is missing
```

**Verification with verbose logging**:
```bash
# Check the hook logs for detailed information
tail -20 amplifier/.claude/logs/stop_hook_$(date +%Y%m%d).log
tail -20 amplifier/.claude/logs/session_start_$(date +%Y%m%d).log

# Should NOT see:
# - "Failed to import amplifier modules"
# - "No module named 'amplifier.extraction'"
# - "No module named 'claude-code-sdk'"
```

---

### Step 5: Choose Dependency Management Strategy

You have two options for managing Amplifier's dependencies:

#### Option A: Install in Parent Project (Recommended)

Install Amplifier dependencies directly in your project's virtual environment:

```bash
# Activate your project's venv
source .venv/bin/activate  # or your venv activation command

# Install Amplifier dependencies
uv pip install networkx langchain langchain-core langchain-openai \
               pydantic-settings rapidfuzz tiktoken pyvis
```

**Pros**:
- Simple - single virtual environment
- Python imports work immediately
- Easy to manage

**Cons**:
- Amplifier dependencies mixed with yours
- Larger dependency tree

---

#### Option B: Separate Virtual Environments (Advanced)

Keep Amplifier dependencies in submodule's own venv:

```bash
# Navigate to submodule
cd amplifier

# Sync Amplifier dependencies
uv sync

# Note the venv location
# amplifier/.venv is created
```

**Then configure Python path**:
```python
# In your code
import sys
sys.path.insert(0, 'amplifier')  # Amplifier modules
sys.path.insert(0, 'amplifier/.venv/lib/python3.12/site-packages')  # Dependencies
```

**Pros**:
- Clean separation
- Amplifier dependencies isolated

**Cons**:
- More complex path management
- Two venvs to maintain

**Recommendation**: Use Option A unless you have specific isolation requirements.

---

### Step 6: Configure Python Imports

In your Python code, add Amplifier to the module search path:

```python
import sys
from pathlib import Path

# Add Amplifier to Python path
sys.path.insert(0, str(Path(__file__).parent / 'amplifier'))

# Now you can import Amplifier modules
from amplifier.memory import MemoryStore
from amplifier.knowledge import graph_builder
from amplifier.synthesis import analyst
```

**Pro Tip**: Add this to a central configuration file:
```python
# your_project/config.py
import sys
from pathlib import Path

# Configure Amplifier path once
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'amplifier'))
```

Then in your code:
```python
from your_project.config import PROJECT_ROOT  # Configures path
from amplifier.memory import MemoryStore  # Now works
```

---

## Dependency Management

### Understanding the Nested Structure

Amplifier has a **nested Python package structure**:

```
amplifier/                # Git submodule directory
├── pyproject.toml       # Amplifier's dependencies defined here
└── amplifier/           # Python package (nested!)
    ├── __init__.py
    ├── memory/
    ├── knowledge/       # Advanced feature
    └── synthesis/       # Advanced feature
```

**Important**: Dependencies are defined in `amplifier/pyproject.toml` but must be installed in the active Python environment.

---

### Core Dependencies (Always Required)

These are needed for basic Amplifier functionality:

```toml
# From amplifier/pyproject.toml [project.dependencies]
python = "^3.11"
click = "^8.1.7"
# ... (basic dependencies)
```

**Installation**:
```bash
# These are typically already in your project
# If not:
uv pip install click
```

---

### Advanced Dependencies (Optional)

Required only for Advanced Features:

```toml
# From amplifier/pyproject.toml [project.optional-dependencies]
[advanced]
networkx = "^3.5"           # Knowledge graphs
langchain = "^1.0.5"         # AI synthesis
langchain-core = "^1.0.4"    # LLM abstractions
langchain-openai = "^1.0.2"  # OpenAI integration
pydantic-settings = "^2.11.0"  # Settings
rapidfuzz = "^3.14.3"       # Fuzzy matching
tiktoken = "^0.12.0"        # Token counting
pyvis = "^0.3.2"            # Graph visualization
```

**Installation**:
```bash
uv pip install networkx langchain langchain-core langchain-openai \
               pydantic-settings rapidfuzz tiktoken pyvis
```

**See**: [ADVANCED_FEATURES.md](./ADVANCED_FEATURES.md) for details on Advanced Features.

---

### Updating Dependencies

When Amplifier updates its dependencies:

```bash
# Pull latest Amplifier
cd amplifier
git pull origin main

# Check for new dependencies
cat pyproject.toml

# Install any new dependencies
cd ..
uv pip install <new-dependencies>
```

---

## Verification

### Verify Setup Checklist

Run these tests to ensure everything works:

#### 1. Symlink Test
```bash
ls -la .claude
# Expected: .claude -> amplifier/.claude
```

#### 2. Commands Test
```bash
ls .claude/commands/ | wc -l
# Expected: 12 (or more)
```

#### 3. Agents Test
```bash
ls .claude/agents/ | wc -l
# Expected: 30 (or more)
```

#### 4. Hook Test
```bash
echo '{}' | python3 .claude/tools/hook_session_start.py 2>&1 | grep -i "error"
# Expected: No import errors
```

#### 5. Python Import Test
```bash
python3 -c "
import sys
sys.path.insert(0, 'amplifier')
from amplifier.memory import MemoryStore
from amplifier.search import Search
from amplifier.content_loader import ContentLoader
print('✅ Core modules working!')
"
```

#### 6. Advanced Features Test (if installed)
```bash
python3 -c "
import sys
sys.path.insert(0, 'amplifier')
from amplifier.knowledge import graph_builder, graph_search, tension_detector
from amplifier.synthesis import analyst, synthesist, triage
from amplifier import knowledge_synthesis, knowledge_integration
print('✅ Advanced features working!')
"
```

---

## Troubleshooting

### Issue: "Path .vscode was not found" and "Path .ai was not found"

**Symptom**: Error messages when starting Claude Code:
```
Path /path/to/project/.vscode was not found.
Path /path/to/project/.ai was not found.
```

**Cause**: Claude Code looks for configuration directories at workspace root

**Solution**: Create symlinks for all three config directories
```bash
# From your project root
ln -s amplifier/.claude .claude
ln -s amplifier/.vscode .vscode
ln -s amplifier/.ai .ai

# Verify all three symlinks
ls -la | grep -E "^l.*(claude|vscode|ai)"
# Should show:
# .ai -> amplifier/.ai
# .claude -> amplifier/.claude
# .vscode -> amplifier/.vscode
```

**Note**: These warnings are harmless but the symlinks eliminate them and ensure full Claude Code integration.

---

### Issue: Claude Code can't find commands

**Symptom**: Slash commands not available

**Solution**: Check symlink
```bash
ls -la .claude
# Should show: .claude -> amplifier/.claude

# If missing, create it:
ln -s amplifier/.claude .claude
```

---

### Issue: Hook import errors

**Symptom**: `ModuleNotFoundError: No module named 'amplifier.memory'`

**Solution**: Fix path resolution in hook
```python
# Edit: amplifier/.claude/tools/hook_session_start.py
# Line 13: Add .resolve()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
```

---

### Issue: Python imports fail

**Symptom**: `ModuleNotFoundError: No module named 'amplifier'`

**Solution**: Add Amplifier to Python path
```python
import sys
sys.path.insert(0, 'amplifier')  # Before imports
```

---

### Issue: Advanced features not working

**Symptom**: `ModuleNotFoundError: No module named 'networkx'`

**Solution**: Install advanced dependencies
```bash
uv pip install networkx langchain langchain-core langchain-openai \
               pydantic-settings rapidfuzz tiktoken pyvis
```

---

### Issue: Git submodule not updating

**Symptom**: Amplifier submodule stuck on old commit

**Solution**: Update submodule
```bash
git submodule update --remote amplifier
cd amplifier
git checkout main
git pull
cd ..
git add amplifier
git commit -m "Update Amplifier submodule"
```

---

### Issue: Pyright hangs during `make check`

**Symptom**: Type checking hangs indefinitely after ruff checks pass
```bash
$ make check
Running ruff format...
269 files left unchanged
Running ruff check...
All checks passed!
Running pyright...
uv run pyright
# <hangs here indefinitely>
```

**Cause**: Pyright attempts to scan symlinked directories (`.claude/`, `.ai/`) and the `amplifier/` submodule, which contain Python files that import from the `amplifier` package. These imports cannot be resolved in the parent project context.

**Solution**: Add exclusions to `pyproject.toml`
```toml
[tool.pyright]
pythonVersion = "3.11"
typeCheckingMode = "standard"
reportMissingTypeStubs = false
exclude = [
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "**/__pycache__",
    "scripts",
    "amplifier",      # Git submodule
    ".claude",        # Symlink to amplifier/.claude/
    ".ai",            # Symlink to amplifier/.ai/
]
```

**Verification**:
```bash
$ uv run pyright
0 errors, 0 warnings, 0 informations
✅ Completes in ~5 seconds
```

**Why this works**: The symlinked tools (`.claude/tools/*.py`) import from `amplifier.memory`, `amplifier.search`, etc. These imports fail in the parent project context because the Amplifier package isn't available at the parent level. Excluding these directories tells pyright to only check your project code, not the Amplifier submodule or its tooling.

---

### Issue: Two Python environments conflict

**Symptom**: Imports work in one place, fail in another

**Solution**: Check which Python is active
```bash
which python3
# Should point to your project's venv

# Verify path setup
python3 -c "import sys; print('\n'.join(sys.path))"
# Should include 'amplifier' directory
```

---

## Automated Setup Script

Save this as `setup_amplifier_submodule.sh` in your project root:

```bash
#!/bin/bash
# Automated Amplifier submodule setup script

set -e  # Exit on error

PROJECT_ROOT=$(pwd)
AMPLIFIER_REPO="${AMPLIFIER_REPO:-https://github.com/yourusername/amplifier.git}"

echo "=================================================="
echo "Amplifier Submodule Setup"
echo "=================================================="
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Amplifier Repo: $AMPLIFIER_REPO"
echo ""

# Step 1: Add submodule
echo "Step 1: Adding Amplifier as git submodule..."
if [ -d "amplifier" ]; then
    echo "  ℹ️  Amplifier directory already exists"
else
    git submodule add "$AMPLIFIER_REPO" amplifier
    git submodule update --init --recursive
    echo "  ✅ Submodule added"
fi

# Step 2: Create symlink
echo ""
echo "Step 2: Creating symlink for Claude Code integration..."
if [ -L ".claude" ]; then
    echo "  ℹ️  Symlink already exists"
else
    ln -s amplifier/.claude .claude
    echo "  ✅ Symlink created: .claude -> amplifier/.claude"
fi

# Step 3: Fix hook path resolution
echo ""
echo "Step 3: Fixing Python path resolution in hooks..."
HOOK_FILE="amplifier/.claude/tools/hook_session_start.py"
if grep -q "Path(__file__).resolve()" "$HOOK_FILE"; then
    echo "  ℹ️  Hook already fixed"
else
    # Backup original
    cp "$HOOK_FILE" "${HOOK_FILE}.backup"

    # Fix the path resolution
    sed -i 's/Path(__file__).parent/Path(__file__).resolve().parent/g' "$HOOK_FILE"
    echo "  ✅ Hook fixed (backup saved as ${HOOK_FILE}.backup)"
fi

# Step 4: Install core dependencies
echo ""
echo "Step 4: Installing Amplifier dependencies..."
echo "  Installing core dependencies..."
uv pip install click 2>&1 | grep -v "^Resolved" || true

# Step 5: Install advanced dependencies (optional)
echo ""
read -p "Install Advanced Features? (Knowledge Graphs, AI Synthesis) [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  Installing advanced dependencies..."
    uv pip install networkx langchain langchain-core langchain-openai \
                   pydantic-settings rapidfuzz tiktoken pyvis
    echo "  ✅ Advanced features installed"
else
    echo "  ⏭️  Skipped advanced features"
fi

# Step 6: Verify installation
echo ""
echo "Step 6: Verifying installation..."

# Test symlink
if [ -L ".claude" ]; then
    echo "  ✅ Symlink verified"
else
    echo "  ❌ Symlink missing"
fi

# Test Python imports
echo "  Testing Python imports..."
python3 -c "
import sys
sys.path.insert(0, 'amplifier')
from amplifier.memory import MemoryStore
print('  ✅ Core modules working')
" 2>&1 | tail -1

# Test advanced features if installed
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 -c "
import sys
sys.path.insert(0, 'amplifier')
from amplifier.knowledge import graph_builder
print('  ✅ Advanced features working')
" 2>&1 | tail -1
fi

echo ""
echo "=================================================="
echo "Setup Complete! 🎉"
echo "=================================================="
echo ""
echo "Available features:"
echo "  • 12 Claude Code slash commands"
echo "  • 30 AI agents"
echo "  • Memory store, search, content loader"
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  • Knowledge graphs"
    echo "  • AI synthesis engines"
fi
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code to load new commands"
echo "  2. Try: /prime to load Amplifier context"
echo "  3. See: amplifier/docs/ADVANCED_FEATURES.md"
echo ""
```

**Usage**:
```bash
chmod +x setup_amplifier_submodule.sh
./setup_amplifier_submodule.sh
```

---

## Best Practices

### 1. Keep Amplifier Updated

```bash
# Regularly update Amplifier
cd amplifier
git pull origin main
cd ..
git add amplifier
git commit -m "Update Amplifier submodule to latest"
```

### 2. Pin to Stable Versions

For production, pin to specific Amplifier versions:

```bash
cd amplifier
git checkout v1.2.3  # Specific stable version
cd ..
git add amplifier
git commit -m "Pin Amplifier to v1.2.3"
```

### 3. Document Your Setup

Add to your project's README:

```markdown
## Amplifier Integration

This project uses [Amplifier](https://github.com/yourusername/amplifier)
as a git submodule for knowledge processing and AI capabilities.

### Setup
See [Amplifier Submodule Setup](amplifier/docs/SUBMODULE_SETUP.md)

### Update Amplifier
\`\`\`bash
git submodule update --remote amplifier
\`\`\`
```

### 4. Include in CI/CD

```yaml
# .github/workflows/test.yml
- name: Initialize submodules
  run: git submodule update --init --recursive

- name: Install dependencies
  run: |
    uv pip install -r requirements.txt
    uv pip install networkx langchain  # Amplifier deps
```

---

## Migration from Standalone

If moving from standalone Amplifier to submodule setup:

```bash
# 1. Backup your project
cp -r your-project your-project-backup

# 2. Remove old Amplifier files
rm -rf amplifier/

# 3. Add as submodule
git submodule add https://github.com/yourusername/amplifier.git amplifier

# 4. Create symlink
ln -s amplifier/.claude .claude

# 5. Install dependencies
uv pip install networkx langchain langchain-core langchain-openai \
               pydantic-settings rapidfuzz tiktoken pyvis

# 6. Update import paths
# Find/replace: "from amplifier." -> "from amplifier."
# Add sys.path.insert(0, 'amplifier') where needed

# 7. Test thoroughly
python3 -m pytest tests/
```

---

## References

- [Amplifier Repository](https://github.com/yourusername/amplifier)
- [Advanced Features Guide](./ADVANCED_FEATURES.md)
- [Git Submodules Documentation](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [DISCOVERIES.md](../DISCOVERIES.md) - Detailed technical insights

---

## Getting Help

**Issues?**
1. Check [Troubleshooting](#troubleshooting) section above
2. Review [DISCOVERIES.md](../DISCOVERIES.md) for known issues
3. File an issue on [GitHub](https://github.com/yourusername/amplifier/issues)

**Contributing?**
See [CONTRIBUTING.md](../CONTRIBUTING.md)

---

**Last Updated**: 2025-11-10
**Tested With**: Brand Composer Amplifier, Python 3.12.3, uv 0.5.18
