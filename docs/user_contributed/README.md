# User-Contributed Documentation (Fork)

This directory contains **fork-specific documentation** created by the fork maintainer, separate from the main Amplifier documentation.

**Purpose**: Document fork-specific features, setup patterns, and integrations that are not part of upstream Amplifier. This keeps fork-specific content clearly separated to avoid merge conflicts when pulling upstream changes.

## Contents

### Advanced Features Documentation

**[ADVANCED_FEATURES.md](./ADVANCED_FEATURES.md)** (~3,000 words)
- Complete guide to Amplifier Advanced Features
- Installation instructions
- Feature categories with code examples:
  1. Knowledge Graph Operations (NetworkX)
  2. AI Synthesis Engines (LangChain)
  3. Knowledge Synthesis (tiktoken)
  4. Knowledge Integration (rapidfuzz, pyvis)
- Dependencies reference
- Troubleshooting guide

### Submodule Integration Guide

**[SUBMODULE_SETUP.md](./SUBMODULE_SETUP.md)** (~5,000 words)
- Step-by-step setup for using Amplifier as git submodule
- Inverted setup pattern (Amplifier as submodule vs host)
- Symlink configuration (`.claude` → `amplifier/.claude`)
- Python path resolution with `.resolve()`
- Two dependency management strategies
- Automated setup script
- Troubleshooting section

### Complete System Overview

**[SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)** (~7,000 words)
- What is Amplifier? (comprehensive introduction)
- Core philosophy (5 principles):
  - Ruthless Simplicity
  - Modular Design ("bricks & studs")
  - AI as Co-Pilot
  - Document-Driven Development (DDD)
  - Knowledge Synthesis
- Complete architecture explanation
- Feature categories (Core + Advanced)
- Real-world use cases
- Getting started guide

## Important Note

**This is NOT the main Amplifier documentation.** This directory contains only fork-specific additions.

For main Amplifier documentation, see:
- Core documentation: `../` (parent docs directory)
- Upstream repository: [Amplifier GitHub](https://github.com/anthropics/amplifier)

## Documentation Maintenance

**For fork maintainers**:
- This directory is for fork-specific content only
- Update when fork features or setup processes change
- Reference main docs where appropriate (don't duplicate upstream content)
- Keep this clearly separated to avoid merge conflicts with upstream

**For upstream integration**:
- Changes to core Amplifier features may require updates here
- Test fork-specific setups after pulling upstream changes
- Verify fork features still work after dependency updates

## Testing

Comprehensive test suite validates 100% functionality:
```bash
# Run advanced features test
python3 /tmp/test_advanced_features.py

# Expected: 7/7 tests pass (100%)
```

## Created

**Date**: 2025-11-10
**Context**: Documented Advanced Features setup and verified 100% functionality
**Test Results**: All 7 feature categories operational (NetworkX, LangChain, Knowledge Graph, Synthesis Engines, Knowledge Synthesis, Knowledge Integration)

## Upstream Separation

These documents are maintained **independently** from the upstream Amplifier repository to:
- Avoid merge conflicts when pulling upstream changes
- Document fork-specific features and workflows
- Provide integration guidance specific to this fork's usage patterns

For upstream Amplifier documentation, see the main `docs/` directory (if it exists in upstream).
