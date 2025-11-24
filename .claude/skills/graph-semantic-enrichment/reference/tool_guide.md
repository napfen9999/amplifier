# Tool Design Guide

**Purpose**: Tool usage patterns and design principles for the Graph Semantic Enrichment Skills System
**Based on**: "Building Agents with Claude Agent SDK" and "Writing Tools for Agents" (Anthropic)

---

## Tool Usage Patterns

The Graph Semantic Enrichment system provides purpose-specific tools that follow Anthropic's design principles for agent-friendly interfaces.

### Available Tools

#### 1. read_source_node

**Purpose**: Read node from SOURCE database (Test Propagation) for context gathering

```bash
read-source-node --node-id=M001 --response-format=concise
```

**Parameters**:
- `node_id`: Node ID to read (e.g., "M001", "E-00042")
- `response_format`: "concise" (essential only) or "detailed" (all properties)

**Returns**: Node properties with needs_enrichment indicators

#### 2. enrich_metaattribute

**Purpose**: Create enriched MetaAttribute in TARGET database with relationships

```bash
enrich-metaattribute \
  --source-id=M001 \
  --properties='{"nameDe": "...", "definitionDe": "...", ...}' \
  --layer=foundation \
  --group=brand_core \
  --assignment-reasoning="..." \
  --grouping-reasoning="..."
```

**Safety**: Pre-write validation, atomic transactions, traceability

#### 3. enrich_enumeration

**Purpose**: Create enriched Enumeration in TARGET database

```bash
enrich-enumeration \
  --source-id=E-00042 \
  --meta-id=M015 \
  --properties='{"nameDe": "...", "definitionDe": "...", ...}'
```

#### 4. validate_enrichment

**Purpose**: Two-tier validation of enriched nodes

```bash
validate-enrichment --target-id=M015
```

**Returns**: Validation results with tier1 (constraints) and tier2 (semantic quality)

#### 5. claim_packages

**Purpose**: Atomically claim work packages

```python
from claiming import PackageClaimer
claimer = PackageClaimer(target_db)
packages = claimer.claim_packages(agent_id="A1", num_packages=2)
```

**Critical**: Claims ALL Enumerations in package, not limited to 20!

---

## Design Principles

### 1. Consolidate Related Operations

**Don't**: Generic operations
```bash
write-node --type=metaattribute --properties='{...}'  # Too generic
```

**Do**: Purpose-specific tools
```bash
enrich-metaattribute --source-id=M001 --properties='{...}' --layer=foundation  # Clear purpose
```

**Why**: Tools represent primary actions, reducing cognitive load for agents.

### 2. Token Efficiency (Response Format Control)

Tools expose response_format parameters to control output size:

```python
def read_source_node(
    node_id: str,
    response_format: Literal["concise", "detailed"] = "concise"
) -> dict:
    """
    Read node from SOURCE with format control.

    Args:
        response_format:
            - "concise": Only essential properties (saves tokens)
            - "detailed": All properties + metadata
    """
    if response_format == "concise":
        return {"id": ..., "nameDe": ..., "nameEn": ...}  # Essential only
    else:
        return {"id": ..., "nameDe": ..., ..., "metadata": {...}}  # Everything
```

**Why**: Agents have limited context. Avoid forcing them to process irrelevant data.

### 3. Helpful Error Messages (Not Just Codes)

**Don't**: Opaque errors
```python
return {"status": "error", "code": "E001"}  # What does E001 mean?
```

**Do**: Actionable guidance
```python
return {
    "status": "error",
    "message": "definitionDe too short (120 chars). Must be 200-600 chars.",
    "suggestion": "Add explanation of WHAT this concept is and WHY it matters in branding.",
    "example": "Der Core Cause ist der zentrale Beweggrund..."
}
```

**Why**: Agents can self-correct with clear instructions.

### 4. Natural Language Names (Not Cryptic IDs)

**Don't**: Technical internals
```python
return {"uuid": "a3d5f...", "mime_type": "application/json"}
```

**Do**: Semantic identifiers
```python
return {"id": "M015", "name": "Markenpersönlichkeit", "type": "MetaAttribute"}
```

**Why**: Natural language names significantly improve precision and reduce hallucinations.

### 5. Pagination & Filtering (With Sensible Defaults)

**Pattern**: Built-in limits with guidance

```python
def read_enumerations(
    meta_attribute_id: str,
    limit: int = 20  # Sensible default
) -> dict:
    """Read Enumerations for MetaAttribute (max 20 by default for preview)."""
    results = query_database(meta_attribute_id, limit)

    if len(results) == limit:
        return {
            "enumerations": results,
            "truncated": True,
            "message": "Showing first 20 results. This is PREVIEW only. Package claiming includes ALL Enumerations."
        }
    return {"enumerations": results, "truncated": False}
```

**Critical Distinction**:
- **Preview** (read_enumerations): Shows max 20 for agent context
- **Claiming** (claim_packages): Claims ALL Enumerations, no limit!

---

## 3-Phasen Agent Loop Integration

Tools are designed to support the three-phase workflow:

### Phase 1: Gather Context

```python
# Agent uses: read_source_node (concise format)
source_data = read_source_node(node_id="M001", response_format="concise")

# Agent understands:
# - What properties exist in SOURCE
# - What needs enrichment (TBD, N/A detected)
# - What ID translation needed (M001 → M015?)
```

### Phase 2: Take Action

```python
# Agent enriches semantically (AI work)
enriched = {
    "nameDe": source_data["nameDe"],  # Preserve name
    "definitionDe": "Der Core Cause ist...",  # NEW semantic content
    "whatItIsDe": ["Item1", "Item2", "Item3"],
    ...
}

# Agent calls tool: enrich_metaattribute
result = enrich_metaattribute(
    source_id="M001",
    enriched_properties=enriched,
    layer_id="foundation",
    assignment_reasoning="MetaAttribute M001 assigned to Foundation because..."
)
```

### Phase 3: Verify Work

```python
# Tool automatically validates BEFORE write (built-in)
# Agent verifies AFTER write
validation = validate_enrichment(target_id=result["target_id"])

if not validation["valid"]:
    # Agent regenerates content
    # Retry Phase 2
else:
    # Agent marks completed
    mark_completed(target_id=result["target_id"])
```

---

## Common Patterns

### Pattern: Handling Template Phrases

When validation detects template phrases:

```python
# Tool returns helpful error
{
    "status": "error",
    "tier2_passed": False,
    "violations": ["Template phrase 'Ein fundamentaler Aspekt von' detected"],
    "suggestion": "Explain WHAT this concept is specifically and WHY it matters",
    "example": "Der Core Cause ist der zentrale Beweggrund..."
}

# Agent regenerates without template phrase
enriched_v2 = {
    "definitionDe": "Der Core Cause ist der zentrale Beweggrund..."  # Specific
}
```

### Pattern: Package-Based Workflow

```python
# 1. Claim packages atomically
packages = claimer.claim_packages("Agent_A1", num_packages=2)

# 2. Process each package
for package in packages:
    # Process MetaAttribute
    source_data = read_source_node(package.meta_id, "detailed")
    enriched = enrich_semantically(source_data)
    result = enrich_metaattribute(...)

    # Process ALL Enumerations (not just 20!)
    for enum_id in package.enumeration_ids:
        source_enum = read_source_node(enum_id, "concise")
        enriched_enum = enrich_semantically(source_enum)
        result = enrich_enumeration(...)
```

### Pattern: SOURCE/TARGET Separation

```python
# SOURCE operations (READ-ONLY)
source_db = SourceDB(SOURCE_URI, auth)
data = source_db.read_node("M001")  # ✅ Allowed
# source_db.write(...) → PermissionError  # ❌ Not allowed

# TARGET operations (WRITE-ONLY)
target_db = TargetDB(TARGET_URI, auth)
result = target_db.enrich_metaattribute(...)  # ✅ Allowed
# Direct reads discouraged (use validate_node instead)
```

---

## Error Handling Guidelines

### Always Include

1. **What went wrong**: Clear description
2. **Why it matters**: Impact explanation
3. **How to fix**: Actionable steps
4. **Example**: Concrete illustration

### Example Error Response

```python
{
    "status": "error",
    "message": "definitionDe contains template phrase",
    "details": "Found 'Ein fundamentaler Aspekt von' which is generic",
    "impact": "Template phrases reduce semantic quality",
    "suggestion": "Explain WHAT specifically and WHY it matters",
    "example": "Der Core Cause ist der zentrale Beweggrund oder das grundlegende 'Warum'...",
    "retry": True
}
```

---

## Performance Considerations

### Token Optimization

- Use `response_format="concise"` for initial reads
- Only use `"detailed"` when full properties needed
- Pagination prevents overwhelming responses
- Progressive disclosure in documentation

### Database Efficiency

- Atomic transactions reduce round trips
- Batch validation where possible
- Connection pooling in database classes
- Cached compatibility scores (future optimization)

---

## Testing Your Tools

### Unit Test Pattern

```python
def test_tool_with_helpful_error():
    """Verify tool provides actionable guidance."""
    result = enrich_metaattribute(
        properties={"definitionDe": "Too short"},  # Invalid
        ...
    )

    assert result["status"] == "error"
    assert "200-600 chars" in result["message"]  # Specific requirement
    assert len(result["suggestions"]) > 0  # Has suggestions
    assert "example" in result  # Includes example
```

### Integration Test Pattern

```python
@pytest.mark.integration
def test_full_3_phase_loop():
    """Test complete agent workflow."""
    # Phase 1: Gather
    source_data = read_source_node("M001", "concise")

    # Phase 2: Act
    result = enrich_metaattribute(...)

    # Phase 3: Verify
    validation = validate_enrichment(result["target_id"])

    assert validation["valid"] is True
```

---

## Tool Documentation Template

When documenting new tools, include:

```markdown
## Tool: [tool_name]

**Purpose**: [What problem it solves]
**Database**: SOURCE (READ-ONLY) | TARGET (WRITE-ONLY)
**Safety**: [Validation, transactions, etc.]

### Parameters
- `param1`: [type] - [description]
- `param2`: [type] - [description]

### Returns
```json
{
  "field1": "description",
  "field2": "description"
}
```

### Error Responses
- [Error condition]: [What agent should do]

### Example Usage
```bash
[example command]
```
```

---

## Key Takeaways

1. **Consolidate operations** into purpose-specific tools
2. **Control token usage** with response formats
3. **Provide helpful errors** with actionable guidance
4. **Use natural language** for clarity
5. **Set sensible defaults** with override options
6. **Support the 3-Phasen Loop** workflow
7. **Maintain SOURCE/TARGET separation** strictly
8. **Include examples** in error messages
9. **Test for helpfulness** not just correctness
10. **Document clearly** with examples

---

**Remember**: Tools are the primary interface for agents. Make them intuitive, helpful, and safe.