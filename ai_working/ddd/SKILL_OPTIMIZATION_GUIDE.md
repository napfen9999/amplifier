# Skill Optimization Process Guide

**Complete guide for optimizing Claude Code skills following DDD Phase 2 principles**

Version: 1.1
Last Updated: 2025-11-16
Based on: 8 skills optimized (283 files processed)
Includes: Reference vs Task naming strategy

---

## Table of Contents

1. [Overview](#overview)
2. [Skill Naming Strategy](#skill-naming-strategy)
3. [When to Optimize](#when-to-optimize)
4. [Phase 2A: Cleanup](#phase-2a-cleanup)
5. [Phase 2B: File Splitting](#phase-2b-file-splitting)
6. [Phase 2C: Hierarchical Linking](#phase-2c-hierarchical-linking)
7. [Phase 2D: Guide Index Updates](#phase-2d-guide-index-updates)
8. [Automation & Agent Delegation](#automation--agent-delegation)
9. [Verification & Quality Control](#verification--quality-control)
10. [Lessons Learned](#lessons-learned)
11. [Checklists & Templates](#checklists--templates)

---

## Overview

### What is Skill Optimization?

Skill optimization is the process of restructuring Claude Code skills to follow DDD (Document-Driven Development) Phase 2 principles:

- **Progressive Disclosure**: 3-tier loading (SKILL.md → categories → examples)
- **Maximum DRY**: Each concept in ONE place only
- **File Size Limits**: All files <500 lines
- **Hierarchical Navigation**: Clear backwards navigation to SKILL.md
- **Complete Indexing**: Every file listed in SKILL.md Guide Index

### Core Philosophy

**Target**: All files <500 lines in Phase 2

**Why 500 lines?**
- Fits comfortably in LLM context windows
- Easy to navigate and understand
- Forces modular organization
- Enables effective progressive disclosure

**Progressive Disclosure Pattern**:
```
SKILL.md (Overview, ~200 lines)
    ↓
Category Files (Organized topics, ~400 lines)
    ↓
Detailed Examples (Specific implementations, ~300 lines)
```

### When Optimization Works

**Good candidates for optimization**:
- Skills with files >500 lines
- Skills with duplicate content
- Skills lacking clear navigation
- Skills with incomplete indexes
- Skills with poor organization

**Not suitable for optimization**:
- Skills already well-structured
- Skills with <10 reference files
- Skills with all files <300 lines

---

## Skill Naming Strategy

### Reference vs Task-Oriented Skills

Claude Code skills fall into two distinct categories, and naming should reflect their primary purpose:

#### Reference Skills (Documentation-focused)

**Name pattern**: `[technology]-[component]-reference`

**Purpose**: Primarily for looking up syntax, APIs, configuration options, and technical specifications.

**Characteristics**:
- Heavy emphasis on reference documentation
- Syntax examples and API specifications
- Configuration options and parameters
- Query languages and command syntax

**Examples**:
- `neo4j-cypher-reference` - Cypher query language syntax and APOC procedures
- `docker-platform-reference` - Docker Hub, Scout, admin panel documentation
- `supabase-platform-reference` - Auth configuration, Storage options, platform settings

**User intent**: "How do I write X?" or "What options are available for Y?"

#### Task-Oriented Skills (Workflow-focused)

**Name pattern**: `[technology]-[domain]` (no suffix)

**Purpose**: Accomplish specific goals and complete workflows.

**Characteristics**:
- Step-by-step guides and tutorials
- Integration patterns and best practices
- End-to-end workflows
- Problem-solving approaches

**Examples**:
- `neo4j-application-dev` - Building applications with Neo4j drivers
- `docker-build-compose` - Building images and orchestrating containers
- `supabase-development` - Building apps with Supabase SDKs

**User intent**: "How do I accomplish X?" or "What's the best way to do Y?"

### Decision Framework

**Use `-reference` suffix when**:
- >70% of content is syntax/API documentation
- Primary use case is "look up how to write X"
- Content resembles official reference documentation
- Users need to quickly find specific syntax/options

**Use task-oriented name when**:
- >70% of content is workflow/tutorial oriented
- Primary use case is "accomplish task X"
- Content focuses on integration and application
- Users need end-to-end guidance

### Benefits of Clear Naming

**For users**:
- Immediate signal about skill purpose
- Faster selection of the right skill
- Clear expectations about content type
- Reduced cognitive load when searching

**For skill creators**:
- Clearer scope boundaries
- Easier to decide what content belongs where
- Less overlap between skills
- More focused skill descriptions

### Implementation Guidelines

When creating or renaming skills:

1. **Analyze content distribution**: What percentage is reference vs workflow?
2. **Identify primary user intent**: Look up syntax vs accomplish task?
3. **Check against examples**: Does it align with similar skills?
4. **Apply naming pattern**: Reference gets suffix, task does not
5. **Update description**: Ensure description reflects the naming category

---

## When to Optimize

### Triggers for Optimization

Run optimization when you see:

1. **File Size Issues**
   - Any reference file >500 lines
   - Files >1,000 lines (high priority)
   - Files >2,000 lines (urgent)

2. **Navigation Problems**
   - Users can't find information quickly
   - No clear path back to overview
   - Missing Guide Index or outdated

3. **DRY Violations**
   - Same content in multiple files
   - "Preserved duplicates" from earlier work
   - Conflicting information in different files

4. **Poor Organization**
   - Flat file structure with 30+ files
   - No logical grouping
   - Unclear file naming

### Pre-Optimization Checklist

Before starting optimization:

- [ ] Create tracking document (`ai_working/ddd/docs_index.txt`)
- [ ] Analyze all files >500 lines (create `phase2_split_analysis.md`)
- [ ] Identify preserved duplicates to delete
- [ ] Estimate total work (files to split, links to add)
- [ ] Back up current state (`git commit` or checkpoint)

---

## Phase 2A: Cleanup

**Goal**: Remove duplicate content before restructuring

### What to Delete

**Preserved Duplicates** - Files marked with `_preserved` or similar:
```bash
# Example from docker-engine
/references/storage/overview.md          # Original, keep
/references/storage/overview_preserved.md # Delete
```

**How to Identify**:
```bash
# Find preserved files
find /home/ufeld/.claude/skills/*/references -name "*preserved*"
find /home/ufeld/.claude/skills/*/references -name "*_old*"
find /home/ufeld/.claude/skills/*/references -name "*backup*"
```

### Process

1. **Scan for duplicates** across all skills
2. **Verify content** - ensure original has all information
3. **Delete preserved copies**
4. **Track deletions** in `docs_index.txt`

### Example Tracking Entry

```markdown
## docker-engine: Cleanup (2025-01-16)

[x] /home/ufeld/.claude/skills/docker-engine/references/storage/overview_preserved.md - DELETED
    Reason: Duplicate of overview.md (original kept)

Total: 1 file deleted, 1,413 lines removed
```

---

## Phase 2B: File Splitting

**Goal**: Split all files >500 lines into organized, manageable chunks

### Strategy Overview

**Tier-based Approach**:

- **Tier 1** (>2,000 lines): Highest priority, split into 4-5 parts
- **Tier 2** (1,000-2,000 lines): Medium priority, split into 2-3 parts
- **Tier 3** (500-1,000 lines): Lower priority, split into 2 parts

### File Splitting Patterns

#### Pattern 1: Sequential Multi-Part Split

**When to use**: Large homogeneous content (CLI references, API docs)

**Example**: `cli-utilities.md` (3,360 lines) → 7 parts

```bash
# Calculate split points
total_lines=3360
parts=7
lines_per_part=$((total_lines / parts))  # 480 lines per part

# Split into parts
for i in {1..7}; do
  start=$(( ($i - 1) * 480 + 1 ))
  end=$(( $i * 480 ))
  head -n $end "cli-utilities.md" | tail -n +$start > "cli-utilities-part${i}.md"
done
```

**Naming Convention**: `filename-part1.md`, `filename-part2.md`, etc.

**Result**:
```
cli-utilities.md (3,360 lines) DELETED
├── cli-utilities-part1.md (480 lines)
├── cli-utilities-part2.md (480 lines)
├── cli-utilities-part3.md (480 lines)
├── cli-utilities-part4.md (480 lines)
├── cli-utilities-part5.md (480 lines)
├── cli-utilities-part6.md (480 lines)
└── cli-utilities-part7.md (480 lines)
```

#### Pattern 2: Topic-Based Split

**When to use**: Content with clear topic boundaries

**Example**: `oauth.md` (1,035 lines) → 3 topic files

**Split by provider category**:
```
oauth.md (1,035 lines) DELETED
├── oauth-popular.md (345 lines)    # Google, GitHub, Facebook
├── oauth-enterprise.md (380 lines) # Azure, Okta, SAML
└── oauth-other.md (310 lines)      # Slack, Discord, Keycloak
```

**Naming Convention**: `topic-category.md`

#### Pattern 3: Hierarchical Split

**When to use**: Content with natural hierarchy (overview → details)

**Example**: `overview.md` (1,413 lines) → 3 files

```
storage/overview.md (1,413 lines) DELETED
├── overview-core.md (485 lines)      # Storage drivers, basics
├── overview-drivers.md (440 lines)   # Driver comparison
└── overview-advanced.md (488 lines)  # Advanced configurations
```

**Naming Convention**: `topic-level.md`

### Target File Sizes

**Optimal ranges**:
- **Target**: 400-500 lines (sweet spot)
- **Acceptable**: 300-500 lines
- **Maximum**: 500 lines (hard limit)
- **Minimum**: 200 lines (avoid tiny files)

### Splitting Workflow

For each file >500 lines:

1. **Read entire file** to understand structure
2. **Choose split pattern** (sequential, topic, or hierarchical)
3. **Calculate split points**:
   ```bash
   wc -l filename.md  # Get total lines
   # Divide by desired parts (aim for ~400-500 per part)
   ```
4. **Create new files** with proper headers
5. **Verify content** - no lost lines, clean splits
6. **Delete original** only after verification
7. **Track in docs_index.txt**

### Example Bash Split Script

```bash
#!/bin/bash
# Split a file into N parts of approximately equal size

file="$1"
parts="$2"

if [ -z "$file" ] || [ -z "$parts" ]; then
  echo "Usage: $0 <file> <parts>"
  exit 1
fi

total_lines=$(wc -l < "$file")
lines_per_part=$(( total_lines / parts ))

base="${file%.md}"

for i in $(seq 1 $parts); do
  start=$(( ($i - 1) * lines_per_part + 1 ))

  if [ $i -eq $parts ]; then
    # Last part gets all remaining lines
    end=$total_lines
  else
    end=$(( $i * lines_per_part ))
  fi

  output="${base}-part${i}.md"
  head -n $end "$file" | tail -n +$start > "$output"

  echo "Created $output ($(wc -l < "$output") lines)"
done

echo "Total: $total_lines lines split into $parts files"
```

**Usage**:
```bash
./split_file.sh cli-utilities.md 7
```

### Tracking Entry Example

```markdown
## supabase-development: Split cli-utilities.md (2025-01-16)

[x] /home/ufeld/.claude/skills/supabase-development/references/cli-utilities.md - DELETED (3,360 lines)
    Split into 7 sequential parts:

[x] cli-utilities-part1.md - CREATED (480 lines)
    Content: Commands supabase init through supabase db

[x] cli-utilities-part2.md - CREATED (480 lines)
    Content: Commands supabase functions through supabase gen

... (continue for all 7 parts)

Total: 3,360 lines → 3,360 lines (7 files, all <500 lines ✓)
```

---

## Phase 2C: Hierarchical Linking

**Goal**: Add backwards navigation from every reference file to SKILL.md

### Navigation Link Pattern

**Standard format**:
```markdown
[↑ Back to SKILL.md](../../SKILL.md)

---

# [Original File Title]

[Rest of content...]
```

**Key points**:
- Link goes at **very top** (line 1)
- Blank line after link
- Horizontal rule separator (`---`)
- Then existing content (unchanged)

### Path Depth Adjustment

Navigation path depends on file nesting level:

| File Location | Levels Up | Link Path |
|---------------|-----------|-----------|
| `references/file.md` | 1 | `../SKILL.md` |
| `references/subdir/file.md` | 2 | `../../SKILL.md` |
| `references/subdir/nested/file.md` | 3 | `../../../SKILL.md` |
| `references/sub/nested/deep/file.md` | 4 | `../../../../SKILL.md` |

**Rule**: Count directory levels from file to skill root, add one `../` per level.

### Examples by Skill

#### docker-engine (4 depth levels)

```markdown
# Root level (references/)
[↑ Back to SKILL.md](../SKILL.md)

# One level (references/runtime/)
[↑ Back to SKILL.md](../../SKILL.md)

# Two levels (references/storage/)
[↑ Back to SKILL.md](../../SKILL.md)

# Three levels (references/storage/drivers/)
[↑ Back to SKILL.md](../../../SKILL.md)
```

#### neo4j-cypher (nested categories)

```markdown
# Root level (references/)
[↑ Back to SKILL.md](../../SKILL.md)

# apoc/ directory
[↑ Back to SKILL.md](../../../SKILL.md)

# apoc/categories/ directory
[↑ Back to SKILL.md](../../../../SKILL.md)
```

### Workflow

For each skill:

1. **Scan all reference files** recursively:
   ```bash
   find /path/to/skill/references -name "*.md" -type f
   ```

2. **Check existing links**:
   ```bash
   head -n 1 file.md  # See if link already exists
   ```

3. **Add navigation if missing**:
   - Calculate correct path depth
   - Prepend navigation header
   - Preserve all existing content

4. **Verify links**:
   ```bash
   # Test that target exists
   cd /path/to/file
   ls ../../SKILL.md  # Should exist
   ```

### Agent Delegation

**Task description template**:

```markdown
For EACH reference file in /path/to/skill/references/:

1. Read the file to check if it has navigation link
2. If missing, add this header at the very top:
   ```
   [↑ Back to SKILL.md](../../SKILL.md)

   ---

   ```
3. Adjust path depth based on nesting:
   - references/: ../../SKILL.md
   - references/subdir/: ../../../SKILL.md
   - etc.
4. Preserve all existing content

Report: files processed, links added
```

---

## Phase 2D: Guide Index Updates

**Goal**: Update SKILL.md to list all reference files with metadata

### Guide Index Format

**Standard structure**:

```markdown
## Guide Index

### Category Name
- **path/to/file.md** - Brief description (XXX lines)
- **path/to/other.md** - Brief description (XXX lines)

### Another Category
- **another/file.md** - Description (XXX lines)
```

### Organization Patterns

#### By Subdirectory

**When to use**: Skills with clear directory structure

**Example** (docker-engine):

```markdown
## Guide Index

### Core References
- **index.md** - Overview and introduction (45 lines)
- **quickstart.md** - Getting started guide (42 lines)

### Runtime References
- **runtime/capabilities.md** - Container capabilities (485 lines)
- **runtime/namespaces.md** - Linux namespaces (325 lines)
- **runtime/cgroups.md** - Control groups (327 lines)

### Storage Overview
- **storage/overview-core.md** - Storage drivers basics (485 lines)
- **storage/overview-drivers.md** - Driver comparison (440 lines)
- **storage/overview-advanced.md** - Advanced configs (488 lines)
```

#### By Topic

**When to use**: Flat structure with logical grouping

**Example** (supabase-development):

```markdown
## Guide Index

### CLI Reference
- **cli-utilities-part1.md** - Init, login, projects (480 lines)
- **cli-utilities-part2.md** - Database commands (480 lines)
- **cli-utilities-part3.md** - Functions, migrations (480 lines)

### Edge Functions & Frameworks
- **edge-functions-part1.md** - Overview, deployment (372 lines)
- **edge-functions-part2.md** - Examples, patterns (368 lines)

### SDKs & Migration
- **sdks.md** - Client libraries overview (325 lines)
- **migration.md** - Migration from other platforms (280 lines)
```

### Metadata to Include

For each file entry:

1. **File path** (relative to references/):
   ```markdown
   - **storage/drivers/overlay.md**
   ```

2. **Brief description** (5-10 words):
   ```markdown
   - **storage/drivers/overlay.md** - OverlayFS driver configuration
   ```

3. **Line count** (for size reference):
   ```markdown
   - **storage/drivers/overlay.md** - OverlayFS driver configuration (385 lines)
   ```

### Generating Line Counts

**Bash command**:
```bash
wc -l /path/to/skill/references/**/*.md | sort -n
```

**For single file**:
```bash
wc -l file.md  # Output: 385 file.md
```

### Workflow

For each SKILL.md:

1. **Scan references/ directory**:
   ```bash
   find references/ -name "*.md" -type f | sort
   ```

2. **Get line counts**:
   ```bash
   for f in $(find references/ -name "*.md"); do
     echo "$(wc -l < "$f") $f"
   done | sort
   ```

3. **Group by category** (subdirectory or topic)

4. **Write Guide Index section** in SKILL.md:
   - Replace or update existing Guide Index
   - Use consistent formatting
   - Include all files

5. **Verify completeness**:
   ```bash
   # Count files
   find references/ -name "*.md" | wc -l
   # Count Guide Index entries
   grep -c "^- \*\*" SKILL.md
   # Should match!
   ```

---

## Automation & Agent Delegation

### Why Delegate to Agents?

**Benefits**:
- Preserves main context for coordination
- Parallel processing possible
- Specialized, focused execution
- Automatic verification

**When to delegate**:
- Phase 2C: Adding 100+ navigation links
- Phase 2D: Updating multiple SKILL.md files
- Repetitive, well-defined tasks

### Using general-purpose Agent

**Task invocation pattern**:

```markdown
Task: Add hierarchical navigation links to skill reference files

Skill: /path/to/skill

Instructions:
1. For EACH reference file:
   - Check if navigation link exists
   - Add if missing: [↑ Back to SKILL.md](../../SKILL.md)
   - Adjust path depth by nesting level
   - Preserve all content

2. Update SKILL.md Guide Index:
   - Scan all reference files
   - Get line counts
   - Group by category
   - List all files with metadata

3. Report:
   - Files processed: X
   - Links added: Y
   - Guide Index updated: Yes/No
```

### Agent Workflow

**Sequential processing** (recommended):

```bash
# Process skills one at a time
1. docker-build-compose → Agent reports → Verify
2. docker-platform → Agent reports → Verify
3. supabase-platform → Agent reports → Verify
...
```

**Parallel processing** (advanced):

```bash
# Launch multiple agents in single message
- Agent 1: docker-build-compose
- Agent 2: docker-platform
- Agent 3: supabase-platform
# Wait for all to complete
```

### Verification After Agent Work

**Quick checks**:

```bash
# 1. Count files with navigation links
grep -l "↑ Back to SKILL.md" references/**/*.md | wc -l

# 2. Count total reference files
find references/ -name "*.md" | wc -l

# Numbers should match!

# 3. Check Guide Index completeness
grep -c "^- \*\*" SKILL.md
# Should match total files
```

**Detailed verification**:

1. Spot-check 3-5 files:
   - Navigation link present?
   - Correct path depth?
   - Content unchanged?

2. Verify SKILL.md:
   - Guide Index section exists?
   - All files listed?
   - Line counts accurate?

---

## Verification & Quality Control

### Pre-Flight Checks

Before starting optimization:

- [ ] Git status clean (or committed)
- [ ] Tracking document created
- [ ] Analysis document created
- [ ] Backup/checkpoint available

### During-Work Checks

After each phase:

**Phase 2A** (Cleanup):
- [ ] All duplicates identified
- [ ] Originals verified complete
- [ ] Deletions tracked

**Phase 2B** (Splitting):
- [ ] All files <500 lines
- [ ] No lost content (line counts match)
- [ ] Naming conventions followed
- [ ] Splits tracked

**Phase 2C** (Linking):
- [ ] All files have navigation
- [ ] Path depths correct
- [ ] Links verified functional

**Phase 2D** (Indexing):
- [ ] All files in Guide Index
- [ ] Categories logical
- [ ] Metadata complete

### Post-Completion Verification

**Final checklist**:

```bash
# For each skill:

# 1. File size check
find references/ -name "*.md" -exec wc -l {} \; | awk '$1 > 500 {print}'
# Should be empty (no files >500 lines)

# 2. Navigation link check
find references/ -name "*.md" | while read f; do
  if ! head -n 1 "$f" | grep -q "Back to SKILL.md"; then
    echo "Missing navigation: $f"
  fi
done
# Should be empty (all have navigation)

# 3. Guide Index completeness
file_count=$(find references/ -name "*.md" | wc -l)
index_count=$(grep -c "^- \*\*" SKILL.md)
echo "Files: $file_count, Indexed: $index_count"
# Should match

# 4. Path depth verification (manual spot checks)
# Pick files at different depths, verify paths work
```

### Quality Metrics

**Success criteria**:

- ✅ **0 files** >500 lines
- ✅ **100%** files with navigation links
- ✅ **100%** files listed in Guide Index
- ✅ **All** links verified functional
- ✅ **All** changes tracked in docs_index.txt

---

## Lessons Learned

### What Worked Well

1. **Tier-based approach** to file splitting
   - Prioritize largest files first
   - Clear criteria for split strategies
   - Consistent ~400-500 line targets

2. **Agent delegation** for repetitive work
   - Preserved main context
   - Faster execution
   - Consistent application of patterns

3. **Comprehensive tracking** (docs_index.txt)
   - Every change documented
   - Easy to review what was done
   - Audit trail for verification

4. **Sequential multi-part splits** for homogeneous content
   - Clean, predictable naming
   - Easy to verify completeness
   - Works well for CLI references, API docs

5. **Verification at each phase**
   - Catch issues early
   - Prevent cascading problems
   - Build confidence in results

### Challenges Encountered

1. **Path depth calculations** for nested directories
   - Solution: Count levels systematically
   - Use consistent patterns per skill

2. **Agent type registration** issues
   - Created agent definition but not available
   - Solution: Use general-purpose agent with detailed instructions

3. **Assumptions about compliance**
   - Some skills thought to be compliant weren't
   - Solution: Always verify, don't assume

4. **File location changes** between sessions
   - Files moved or renamed in earlier work
   - Solution: Use `find` to verify actual structure

### Best Practices Established

1. **Always use absolute paths** in scripts
   - Don't rely on `cd` commands
   - Shell working directory can reset

2. **Verify before delete** original files
   - Ensure split files have all content
   - Check line counts match

3. **Track everything** in docs_index.txt
   - What was deleted
   - What was created
   - Why changes were made

4. **Spot-check agent work** even when delegating
   - Verify first 3-5 files manually
   - Confirms pattern is correct
   - Builds trust in automation

5. **Use consistent naming conventions**
   - `filename-part1.md` for sequential splits
   - `topic-category.md` for topic splits
   - `topic-level.md` for hierarchical splits

---

## Checklists & Templates

### Phase 2A Checklist

```markdown
## Phase 2A: Cleanup - [Skill Name]

Date: YYYY-MM-DD

### Pre-Flight
- [ ] Git status clean
- [ ] Tracking document ready

### Identify Duplicates
- [ ] Scan for *preserved* files
- [ ] Scan for *_old* files
- [ ] Scan for *backup* files
- [ ] List all duplicates found: _____ files

### Verify & Delete
For each duplicate:
- [ ] Verify original has all content
- [ ] Delete preserved copy
- [ ] Track deletion in docs_index.txt

### Complete
- [ ] All duplicates removed
- [ ] Changes tracked
- [ ] Git commit checkpoint
```

### Phase 2B Checklist

```markdown
## Phase 2B: File Splitting - [Skill Name]

Date: YYYY-MM-DD

### Pre-Flight
- [ ] Analysis document created
- [ ] Files >500 lines identified: _____ files
- [ ] Split strategies chosen

### For Each File to Split

File: _______________
Size: _____ lines
Strategy: Sequential / Topic / Hierarchical
Target: _____ parts

- [ ] Read entire file
- [ ] Choose split points
- [ ] Create new files
- [ ] Verify content (line counts match)
- [ ] Delete original
- [ ] Track in docs_index.txt

### Complete
- [ ] All files <500 lines
- [ ] All splits verified
- [ ] Changes tracked
- [ ] Git commit checkpoint
```

### Phase 2C Checklist

```markdown
## Phase 2C: Hierarchical Linking - [Skill Name]

Date: YYYY-MM-DD

### Pre-Flight
- [ ] Count total reference files: _____ files
- [ ] Identify directory structure (depth levels)

### Add Navigation Links
- [ ] Scan all reference files
- [ ] Check existing links
- [ ] Add missing navigation headers
- [ ] Adjust path depths by nesting
- [ ] Preserve all content

### Verification
- [ ] Spot-check 5 files manually
- [ ] Verify path depths correct
- [ ] Test links functional
- [ ] Count: _____ links added

### Complete
- [ ] All files have navigation
- [ ] All paths verified
- [ ] Git commit checkpoint
```

### Phase 2D Checklist

```markdown
## Phase 2D: Guide Index Update - [Skill Name]

Date: YYYY-MM-DD

### Pre-Flight
- [ ] List all reference files
- [ ] Get line counts for all files
- [ ] Decide categorization scheme

### Update Guide Index
- [ ] Open SKILL.md
- [ ] Locate Guide Index section
- [ ] Group files by category
- [ ] Add file path, description, line count
- [ ] Format consistently

### Verification
- [ ] Count files: _____ total
- [ ] Count index entries: _____ entries
- [ ] Numbers match: Yes / No
- [ ] All categories logical

### Complete
- [ ] Guide Index complete
- [ ] All files listed
- [ ] Git commit checkpoint
```

### File Split Template (Sequential)

```bash
#!/bin/bash
# Split [filename] into [N] sequential parts

original_file="FILENAME.md"
total_lines=$(wc -l < "$original_file")
parts=N
lines_per_part=$(( total_lines / parts ))

base="${original_file%.md}"

for i in $(seq 1 $parts); do
  start=$(( ($i - 1) * lines_per_part + 1 ))

  if [ $i -eq $parts ]; then
    end=$total_lines
  else
    end=$(( $i * lines_per_part ))
  fi

  output="${base}-part${i}.md"
  head -n $end "$original_file" | tail -n +$start > "$output"

  lines=$(wc -l < "$output")
  echo "✓ Created $output ($lines lines)"
done

echo ""
echo "Summary:"
echo "  Original: $total_lines lines"
echo "  Split into: $parts files"
echo "  Target per file: $lines_per_part lines"
```

### Navigation Link Template

```markdown
[↑ Back to SKILL.md](../../SKILL.md)

---

# [Original File Title Here]

[Rest of existing content unchanged...]
```

### Guide Index Template

```markdown
## Guide Index

### Category Name 1
- **path/to/file1.md** - Brief description (XXX lines)
- **path/to/file2.md** - Brief description (XXX lines)

### Category Name 2
- **another/file3.md** - Brief description (XXX lines)
- **another/file4.md** - Brief description (XXX lines)
```

### Tracking Entry Template

```markdown
## [skill-name]: [Action] (YYYY-MM-DD)

[x] /path/to/file.md - ACTION (size info)
    Details: What was done and why

[x] /path/to/new-file.md - CREATED (XXX lines)
    Content: What this file contains

Total: Summary of changes (files affected, lines changed)
Result: All files <500 lines ✓ / Guide Index updated ✓
```

---

## Statistics from This Optimization

**8 Skills Optimized**:

| Skill | Files Before | Files After | Total Lines | Status |
|-------|--------------|-------------|-------------|--------|
| docker-build-compose | 1 | 22 | 2,006 | ✓ |
| docker-platform | 2 | 23 | ~1,800 | ✓ |
| supabase-platform | 3 | 30 | ~2,400 | ✓ |
| docker-engine | 4 | 22 | 6,540 | ✓ |
| supabase-development | 8 | 30 | 13,055 | ✓ |
| neo4j-cypher | 15 | 60 | ~18,000 | ✓ |
| supabase-database | 87 | 87 | ~26,100 | ✓ |
| docker-desktop | 9 | 9 | ~900 | ✓ |
| **TOTAL** | **129** | **283** | **~70,801** | **✓** |

**Work Summary**:
- **Phase 2A**: 2 duplicates deleted
- **Phase 2B**: 10 files split → 85 new files created
- **Phase 2C**: 283 navigation links added/corrected
- **Phase 2D**: 8 SKILL.md Guide Indexes updated

**Time Investment**:
- Planning & Analysis: ~30 minutes
- Phase 2A: ~10 minutes
- Phase 2B: ~2 hours (manual splitting with verification)
- Phase 2C: ~1 hour (agent delegation with verification)
- Phase 2D: ~30 minutes (automated during Phase 2C)
- **Total**: ~4 hours for 8 skills

**Efficiency Gains**:
- Agent delegation reduced Phase 2C from ~3 hours to ~1 hour
- Tracking system enabled quick verification
- Systematic approach prevented rework

---

## Future Improvements

### Potential Enhancements

1. **Full Automation Script**
   - Input: Skill directory path
   - Output: Fully optimized skill
   - Would require sophisticated content analysis

2. **Custom Agent Registration**
   - Create persistent `skill-hierarchy-linker` agent
   - Register in Claude Code agent system
   - Simplify delegation

3. **Interactive Analysis**
   - Tool to suggest split strategies
   - Preview split results before committing
   - Automatic optimal split point detection

4. **Quality Dashboard**
   - Real-time metrics across all skills
   - File size distribution graphs
   - Navigation coverage percentage
   - Index completeness tracking

5. **Regression Prevention**
   - Pre-commit hooks to check file sizes
   - Automated tests for navigation links
   - CI/CD integration for skill validation

### Tool Ideas

```bash
# Theoretical future tools

# Auto-analyze skill health
skill-analyze /path/to/skill
# Output: Health score, issues found, recommendations

# Preview split strategies
skill-split-preview file.md
# Output: Suggested split points, size distribution

# Verify skill compliance
skill-verify /path/to/skill
# Output: Pass/fail on all criteria, detailed report

# Optimize entire skill automatically
skill-optimize /path/to/skill --auto
# Output: Optimized skill following all Phase 2 principles
```

---

## Quick Reference

### File Size Limits

- **Maximum**: 500 lines (hard limit)
- **Target**: 400-500 lines (optimal)
- **Minimum**: 200 lines (avoid tiny files)

### Navigation Paths

| Depth | Path |
|-------|------|
| 1 level | `../SKILL.md` |
| 2 levels | `../../SKILL.md` |
| 3 levels | `../../../SKILL.md` |
| 4 levels | `../../../../SKILL.md` |

### Phase Sequence

1. **Phase 2A**: Cleanup (delete duplicates)
2. **Phase 2B**: Split files >500 lines
3. **Phase 2C**: Add hierarchical links
4. **Phase 2D**: Update Guide Indexes

### Key Commands

```bash
# Count lines in file
wc -l file.md

# Find files >500 lines
find references/ -name "*.md" -exec wc -l {} \; | awk '$1 > 500 {print}'

# Check for navigation links
grep -l "Back to SKILL.md" references/**/*.md

# Count reference files
find references/ -name "*.md" | wc -l

# Count Guide Index entries
grep -c "^- \*\*" SKILL.md
```

---

## Conclusion

Skill optimization following DDD Phase 2 principles creates:

- **Better user experience** through progressive disclosure
- **Improved maintainability** with smaller, focused files
- **Clear navigation** enabling quick information access
- **Complete documentation** with comprehensive indexes

**The process is repeatable, verifiable, and automatable.**

Use this guide as your playbook for future skill optimizations.

---

**Document History**:
- Version 1.0 (2025-01-16): Initial creation based on 8-skill optimization
- Skills covered: docker-build-compose, docker-platform, supabase-platform, docker-engine, supabase-development, neo4j-cypher, supabase-database, docker-desktop
- Total files processed: 283
- Total lines documented: ~70,801
