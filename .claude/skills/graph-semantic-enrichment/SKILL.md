# Graph Semantic Enrichment Skill

**Purpose**: Guide for enriching Neo4j graph nodes from SOURCE to TARGET database
**Workflow**: 3-Phasen Loop (Gather → Act → Verify)
**Safety**: SOURCE is READ-ONLY, TARGET is WRITE-ONLY

---

## ⚠️ CRITICAL: Database Separation

**NEVER WRITE TO SOURCE DATABASE**

The system uses two separate Neo4j databases:

- **SOURCE** (Test Propagation, ID: 025a2013): READ-ONLY reference data
- **TARGET** (Graph Rebuild 202511): WRITE-ONLY production graph

```
SOURCE (Test Propagation)          TARGET (Graph Rebuild 202511)
─────────────────────────          ──────────────────────────────
Access: READ-ONLY ✓                Access: WRITE-ONLY ✓
Purpose: Reference data            Purpose: Enriched production graph
You: Read for context              You: Write enriched content
```

**What you CAN do with SOURCE**:
- ✅ Read nodes via `read_source_node` tool
- ✅ Query for context understanding
- ✅ Identify properties needing enrichment

**What you CANNOT do with SOURCE**:
- ❌ Write nodes
- ❌ Update properties
- ❌ Delete anything
- ❌ Any SET, CREATE, DELETE operations

**All enriched content goes to TARGET database only.**

---

## Quick Start

### Your Mission

Transform mixed-quality SOURCE nodes into semantically rich TARGET nodes using the 3-Phasen Loop.

### Basic Workflow

```python
# 1. Claim work packages
packages = claim_packages(agent_id="Agent_A1", num_packages=2)

# 2. For each package, apply 3-Phasen Loop
for package in packages:
    # Phase 1: Gather Context (from SOURCE)
    source_data = read_source_node(package.meta_id, "concise")

    # Phase 2: Take Action (enrich and write to TARGET)
    enriched = generate_semantic_content(source_data)
    result = enrich_metaattribute(source_id=package.meta_id, properties=enriched, ...)

    # Phase 3: Verify Work (validate in TARGET)
    validation = validate_enrichment(result["target_id"])
    if validation["valid"]:
        mark_completed(result["target_id"])
    else:
        regenerate_and_retry(validation["suggestions"])
```

### Package Contents

Each package contains:
- 1 MetaAttribute (e.g., M001 "Core Cause")
- ALL its Enumerations (could be 5, 25, or 50+)
- Status tracking for progress

**CRITICAL**: When you claim a package, you get ALL Enumerations, not just 20!

---

## 3-Phasen Agent Loop

### Phase 1: Gather Context

**Purpose**: Understand what exists in SOURCE

```bash
# Read MetaAttribute
read-source-node --node-id=M001 --response-format=concise

# Returns:
{
  "id": "M001",
  "nameDe": "Kernzweck",
  "nameEn": "Core Cause",
  "definitionDe": "TBD",  # Needs enrichment
  "whatItIsDe": ["N/A"],  # Needs enrichment
  "needs_enrichment": ["definitionDe", "whatItIsDe", "whatItIsNotDe"]
}
```

**What to look for**:
- Properties with "TBD", "N/A", or template phrases
- Missing semantic content
- Incomplete lists (whatItIs with <3 items)

### Phase 2: Take Action

**Purpose**: Create enriched content in TARGET

```bash
# Enrich MetaAttribute
enrich-metaattribute \
  --source-id=M001 \
  --properties='{
    "nameDe": "Kernzweck",
    "nameEn": "Core Cause",
    "definitionDe": "Der Core Cause ist der zentrale Beweggrund...",
    "definitionEn": "The Core Cause is the fundamental reason...",
    "whatItIsDe": ["Fundamentaler Daseinszweck", "Langfristig stabil", ...],
    "whatItIsEn": ["Fundamental purpose", "Long-term stable", ...],
    "whatItIsNotDe": ["Nicht identisch mit Vision", "Nicht kurzfristig änderbar", ...],
    "whatItIsNotEn": ["Not identical to vision", "Not short-term changeable", ...],
    "brandingRelevanceDe": "Der Core Cause ist fundamental für...",
    "brandingRelevanceEn": "The Core Cause is fundamental for..."
  }' \
  --layer=foundation \
  --group=brand_core \
  --assignment-reasoning="Assigned to Foundation because it defines..." \
  --grouping-reasoning="Grouped in brand_core because it forms..."
```

**Requirements for enrichment**:
- Definitions: 200-600 chars, explain WHAT and WHY
- whatItIs/IsNot: 3-7 items each, specific characteristics
- No template phrases (see banned list in reference)
- Reasoning on edges: 200-600 chars explaining decisions

### Phase 3: Verify Work

**Purpose**: Ensure quality in TARGET

```bash
# Validate enrichment
validate-enrichment --target-id=M015

# Returns:
{
  "valid": true,
  "tier1_passed": true,  # Structural constraints
  "tier2_passed": true,  # Semantic quality
  "tier1_violations": [],
  "tier2_violations": [],
  "suggestions": []
}
```

**If validation fails**:
```json
{
  "valid": false,
  "tier2_passed": false,
  "violations": ["Template phrase 'Ein fundamentaler Aspekt' detected"],
  "suggestions": ["Explain WHAT specifically", "Avoid generic descriptions"],
  "example": "Der Core Cause ist der zentrale Beweggrund..."
}
```

**Action on failure**: Regenerate content using suggestions, then retry Phase 2.

---

## Workflow Decision Tree

```
START
  ↓
[Claim Packages] → No packages available? → WAIT
  ↓
[Process Package]
  ↓
[Phase 1: Gather Context from SOURCE]
  ↓
Properties need enrichment? → No → Mark completed
  ↓ Yes
[Phase 2: Generate Semantic Content]
  ↓
[Write to TARGET with validation]
  ↓
Validation passed? → No → [Regenerate with feedback] → Phase 2
  ↓ Yes
[Phase 3: Mark Completed]
  ↓
More items in package? → Yes → [Process next item]
  ↓ No
[Package Complete]
  ↓
More packages? → Yes → [Claim Packages]
  ↓ No
END
```

---

## Tool Reference

### read_source_node

**Purpose**: Read node from SOURCE database
**Database**: SOURCE (READ-ONLY)

```bash
read-source-node --node-id=M001 --response-format=concise
```

**Parameters**:
- `node_id`: Node to read (e.g., "M001", "E-00042")
- `response_format`: "concise" (essential) or "detailed" (all properties)

### enrich_metaattribute

**Purpose**: Create enriched MetaAttribute in TARGET
**Database**: TARGET (WRITE-ONLY)

```bash
enrich-metaattribute \
  --source-id=M001 \
  --properties='{...}' \
  --layer=foundation \
  --group=brand_core \
  --assignment-reasoning="..." \
  --grouping-reasoning="..."
```

**Validation**: Automatic pre-write validation ensures quality

### enrich_enumeration

**Purpose**: Create enriched Enumeration in TARGET
**Database**: TARGET (WRITE-ONLY)

```bash
enrich-enumeration \
  --source-id=E-M001-001 \
  --meta-id=M015 \
  --properties='{...}'
```

**Note**: `meta-id` is the TARGET MetaAttribute ID, not SOURCE

### validate_enrichment

**Purpose**: Validate node quality in TARGET
**Database**: TARGET (READ for validation)

```bash
validate-enrichment --target-id=M015
```

**Returns**: Two-tier validation results with actionable suggestions

### claim_packages

**Purpose**: Atomically claim work packages
**Database**: TARGET (for status tracking)

```python
from claiming import PackageClaimer
claimer = PackageClaimer(target_db)
packages = claimer.claim_packages(agent_id="Agent_A1", num_packages=2)
```

**CRITICAL**: Claims ALL Enumerations in package, not limited to 20!

---

## Common Patterns

### Pattern: Processing a Complete Package

```python
# Claim package
package = claim_packages("Agent_A1", 1)[0]

# Process MetaAttribute
source_meta = read_source_node(package.meta_id, "detailed")
enriched_meta = enrich_semantically(source_meta)
meta_result = enrich_metaattribute(
    source_id=package.meta_id,
    properties=enriched_meta,
    layer="foundation",
    group="brand_core",
    assignment_reasoning="...",
    grouping_reasoning="..."
)

# Process ALL Enumerations (not just 20!)
for enum_id in package.enumeration_ids:  # Could be 50+ items
    source_enum = read_source_node(enum_id, "concise")
    enriched_enum = enrich_semantically(source_enum)
    enum_result = enrich_enumeration(
        source_id=enum_id,
        meta_id=meta_result["target_id"],
        properties=enriched_enum
    )

    # Validate each
    validation = validate_enrichment(enum_result["target_id"])
    if not validation["valid"]:
        # Regenerate and retry
        handle_validation_failure(validation)
```

### Pattern: Handling Template Phrases

```python
# Validation detects template phrase
validation = {
    "tier2_passed": False,
    "violations": ["Template phrase 'Ein fundamentaler Aspekt von' detected"],
    "suggestions": ["Explain WHAT specifically", "Explain WHY it matters"]
}

# Regenerate without template phrases
def regenerate_without_templates(original, suggestions):
    prompt = f"""
    Original definition has template phrase: {original}

    Regenerate following these guidelines:
    - {suggestions[0]}
    - {suggestions[1]}
    - Start with "Der [Concept] ist..."
    - Avoid: "Ein fundamentaler Aspekt", "Bezieht sich auf", etc.

    Generate new definition (200-600 chars):
    """
    return generate_with_ai(prompt)

new_definition = regenerate_without_templates(
    original=properties["definitionDe"],
    suggestions=validation["suggestions"]
)

# Retry with new definition
properties["definitionDe"] = new_definition
retry_result = enrich_metaattribute(source_id=..., properties=properties, ...)
```

### Pattern: Semantic Contrast (whatItIs vs whatItIsNot)

```python
def generate_semantic_contrast(concept_name, concept_context):
    """Generate contrasting characteristics."""

    what_it_is = [
        "Specific characteristic 1",
        "Unique aspect 2",
        "Distinguishing feature 3",
        "Framework reference 4",
        "Measurable attribute 5"
    ]

    what_it_is_not = [
        "Not confused with similar_concept_1",
        "Not identical to related_concept_2",
        "Not merely surface_attribute_3",
        "Not short-term or changeable_4",
        "Not generic_statement_5"
    ]

    # Ensure no overlap
    assert not any(item in what_it_is_not for item in what_it_is)

    return what_it_is, what_it_is_not
```

---

## Quality Standards

### Definition Requirements

Every definition must:
1. Be 200-600 characters
2. Explain WHAT the concept is (first part)
3. Explain WHY it matters in branding (second part)
4. Be specific to this concept
5. Avoid all template phrases

**Good Example**:
```
"Der Core Cause ist der zentrale Beweggrund oder das grundlegende 'Warum'
hinter einer Marke. Er beschreibt die zugrundeliegende Motivation, aus der
heraus die Marke agiert – unabhängig von kurzfristigen Zielen."
```

### whatItIs/whatItIsNot Requirements

- **Count**: 3-7 items each
- **Length**: 15-80 characters per item
- **Specificity**: Must be unique to this concept
- **Contrast**: whatItIsNot must clarify boundaries
- **No overlap**: Items cannot appear in both lists

### Edge Property Requirements

All relationship properties must explain reasoning:

- **assignmentReasoning**: 200-600 chars, why this layer assignment
- **groupingReasoning**: 200-600 chars, why this group clustering
- **EXEMPLIFIED_BY reasoning**: 200-800 chars, how brand exemplifies
- **EXEMPLIFIED_BY context**: 200-600 chars, brand background

---

## Progressive Disclosure

For detailed information, see reference documentation:

- **[coherence_rules.md](reference/coherence_rules.md)**: Complete property standards
- **[workflow_phases.md](reference/workflow_phases.md)**: Phase 0-5 detailed workflow
- **[examples_prompts.md](reference/examples_prompts.md)**: Good/bad examples with prompts
- **[tool_guide.md](reference/tool_guide.md)**: Tool design principles
- **[id_translation.md](reference/id_translation.md)**: SOURCE→TARGET ID mapping

Load these references only when you need specific details.

---

## Error Recovery

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Template phrase detected" | Generic description used | Regenerate with specific content |
| "Definition too short" | <200 characters | Expand with WHY it matters |
| "whatItIs too generic" | Items like "Important" | Add specific characteristics |
| "Overlap detected" | Same item in Is/IsNot | Ensure mutual exclusivity |
| "SOURCE is READ-ONLY" | Attempted write to SOURCE | Use TARGET database only |

### Validation Failure Workflow

1. Read validation feedback carefully
2. Note specific violations
3. Review suggestions provided
4. Regenerate content addressing issues
5. Retry enrichment with improved content
6. Repeat until validation passes

---

## Progress Tracking

### Check Your Progress

```python
# See claimed packages
packages = get_my_claimed_packages("Agent_A1")

# Check completion status
status = get_enrichment_status()
print(f"Completed: {status['completed']}")
print(f"In Progress: {status['in_progress']}")
print(f"Failed: {status['failed']}")
print(f"Unclaimed: {status['unclaimed']}")
```

### Mark Status

```python
# After successful enrichment
mark_completed(target_id="M015", agent_id="Agent_A1")

# If unable to complete
mark_failed(
    target_id="M015",
    agent_id="Agent_A1",
    error_message="Could not generate non-template definition after 5 attempts"
)
```

---

## Best Practices

1. **Always read from SOURCE first** - Understand before enriching
2. **Check needs_enrichment list** - Focus on properties that need work
3. **Validate before committing** - Ensure quality standards met
4. **Regenerate when needed** - Don't accept template phrases
5. **Process complete packages** - Don't skip Enumerations
6. **Use concise format initially** - Save tokens during exploration
7. **Document reasoning** - Explain layer and group assignments
8. **Handle ALL Enumerations** - Package might have 50+, process them all
9. **Track your progress** - Mark completed/failed appropriately
10. **Never write to SOURCE** - It's immutable reference data

---

## Parallel Agent Safety

When working with other agents:

- **Claiming is atomic** - No race conditions
- **Packages don't overlap** - Each agent gets unique work
- **Status tracking is safe** - Database handles concurrency
- **SOURCE is read-only** - No conflicts possible
- **TARGET validates writes** - Quality maintained

You can work independently without coordination.

---

## Summary

1. **Read from SOURCE** (gather context)
2. **Enrich semantically** (generate quality content)
3. **Write to TARGET** (with validation)
4. **Verify quality** (two-tier validation)
5. **Mark complete** (or retry if needed)

Remember: SOURCE is READ-ONLY, TARGET is WRITE-ONLY, quality matters more than speed.

---

**Need help?** Check the reference documentation for detailed specifications and examples.