# Graph Migration Coherence Rules

**Purpose**: Property standards and validation rules for Neo4j V3 graph semantic enrichment
**Version**: 1.0
**Last Updated**: 2025-11-24

---

## 1. Property Standards

### 1.1 MetaAttribute Properties

All MetaAttributes require complete semantic enrichment:

| Property | Type | Length | Requirements |
|----------|------|--------|--------------|
| **nameDe/En** | STRING | 2-100 chars | Clear, unique name |
| **definitionDe/En** | STRING | 200-600 chars | Explains WHAT + WHY in branding context |
| **whatItIsDe/En** | LIST[STRING] | 3-7 items | Specific unique characteristics |
| **whatItIsNotDe/En** | LIST[STRING] | 3-7 items | Clear differentiation from similar concepts |
| **brandingRelevanceDe/En** | STRING | 200-600 chars | Strategic value + use cases |

### 1.2 Enumeration Properties

All Enumerations require semantic contrast:

| Property | Type | Length | Requirements |
|----------|------|--------|--------------|
| **nameDe/En** | STRING | 2-100 chars | Specific value name |
| **definitionDe/En** | STRING | 150-600 chars | What this value means |
| **whatItIsDe/En** | LIST[STRING] | 3-7 items | Distinguishing characteristics |
| **whatItIsNotDe/En** | LIST[STRING] | 3-7 items | Contrast with similar values |
| **examplesDe/En** | LIST[STRING] | 1-5 items | Real brand examples |

### 1.3 Edge Properties

Relationship properties provide reasoning:

| Relationship | Property | Type | Length | Purpose |
|--------------|----------|------|--------|---------|
| **HAS_ATTRIBUTE** | assignmentReasoning | STRING | 200-600 | Why MetaAttribute → Layer |
| **BELONGS_TO_GROUP** | groupingReasoning | STRING | 200-600 | Why MetaAttribute → GroupNode |
| **EXEMPLIFIED_BY** | reasoning | STRING | 200-800 | How brand exemplifies value |
| **EXEMPLIFIED_BY** | context | STRING | 200-600 | Brand background/mission |
| **EXEMPLIFIED_BY** | source | URL | Valid URL | Citation |
| **EXEMPLIFIED_BY** | retrievalDate | DATE | ISO-8601 | When retrieved |

---

## 2. Banned Template Phrases

These generic phrases indicate low-quality enrichment and must be regenerated:

### German Template Phrases

- "Ein fundamentaler Aspekt von..."
- "Ein wichtiger Bestandteil der..."
- "Beschreibt die grundlegenden..."
- "Bezieht sich auf..."
- "Umfasst alle Aspekte von..."
- "Ist relevant für..."
- "Trägt bei zu..."
- "Spielt eine Rolle bei..."
- "Hat Einfluss auf..."
- "Ist von Bedeutung für..."

### English Template Phrases

- "A fundamental aspect of..."
- "An important component of..."
- "Describes the basic..."
- "Refers to..."
- "Encompasses all aspects of..."
- "Is relevant for..."
- "Contributes to..."
- "Plays a role in..."
- "Has influence on..."
- "Is of importance for..."

### Why These Are Banned

Template phrases:
- Lack semantic specificity
- Could apply to any concept
- Don't explain WHAT or WHY
- Indicate surface-level understanding
- Reduce differentiation between concepts

---

## 3. Quality Validation Rules

### Tier 1: Structural Constraints (Neo4j enforced)

```cypher
// ID uniqueness
CREATE CONSTRAINT unique_metaattribute_id IF NOT EXISTS
ON (m:MetaAttribute) ASSERT m.id IS UNIQUE;

// Required properties
CREATE CONSTRAINT metaattribute_has_name IF NOT EXISTS
ON (m:MetaAttribute) ASSERT m.nameDe IS NOT NULL;

// Length constraints (validated before write)
WITH m.definitionDe as def
WHERE size(def) < 200 OR size(def) > 600
RETURN "definitionDe must be 200-600 characters"
```

### Tier 2: Semantic Quality Checks

```python
def validate_semantic_quality(properties: dict) -> ValidationResult:
    """Check semantic quality beyond structural constraints."""

    violations = []

    # Check for template phrases
    for phrase in BANNED_PHRASES_DE:
        if phrase in properties.get("definitionDe", ""):
            violations.append(f"Template phrase '{phrase}' detected")

    # Check for meaningful contrast
    what_it_is = properties.get("whatItIsDe", [])
    what_it_is_not = properties.get("whatItIsNotDe", [])

    if any(item in what_it_is_not for item in what_it_is):
        violations.append("whatItIs and whatItIsNot cannot overlap")

    # Check for specific vs generic
    if len([item for item in what_it_is if len(item) < 15]) > 2:
        violations.append("whatItIs items too generic (< 15 chars)")

    return ValidationResult(
        tier2_passed=len(violations) == 0,
        tier2_violations=violations
    )
```

---

## 4. Node Count Requirements

### Primary Scope (WHO WE ARE)

| Layer | MetaAttributes | Enumerations | GroupNodes |
|-------|---------------|--------------|------------|
| Foundation | 34 | ~500 | 6 |
| Strategy | 28 | ~450 | 6 |
| Identity | 32 | ~480 | 6 |
| Expression | 28 | ~448 | 6 |
| **Total** | **122** | **1,878** | **24** |

### Secondary Scope (HOW WE EXECUTE)

| Layer | MetaAttributes | Enumerations | GroupNodes |
|-------|---------------|--------------|------------|
| All | 137 | 1,377 | 24 |

**Grand Total**: 259 MetaAttributes, 3,255 Enumerations, 48 GroupNodes

---

## 5. ID Translation Rules

### 5.1 Hierarchieless ID System (V3)

**Old V2 Format** (hierarchical):
```
E-M001-001  // First Enumeration of MetaAttribute M001
E-M001-002  // Second Enumeration of MetaAttribute M001
```

**New V3 Format** (hierarchieless):
```
E-00001  // Sequential, no parent encoding
E-00042  // Relationship via HAS_ENUMERATION edge
```

### 5.2 ID Format Specifications

| Node Type | Format | Example | Range |
|-----------|--------|---------|-------|
| **MetaAttribute** | M{3-digit}{letter?} | M001, M002a | M001-M259 |
| **Enumeration** | E-{5-digit} | E-00001 | E-00001 to E-03255 |
| **FreeTextValue** | FT-{5-digit} | FT-00001 | FT-00001 to FT-99999 |
| **HelperNode** | H-{5-digit} | H-00001 | H-00001 to H-00008 |
| **BrandExample** | BE-{5-digit} | BE-00001 | BE-00001 to BE-99999 |
| **GroupNode** | snake_case | brand_core | N/A |
| **Layer** | snake_case | foundation | N/A |

### 5.3 Translation During Migration

```python
def translate_enumeration_id(old_id: str) -> str:
    """
    Translate V2 hierarchical ID to V3 sequential.

    Examples:
        E-M001-001 → E-00001
        E-M015-003 → E-00234
    """
    # Maintain mapping table during migration
    return id_mapping.get(old_id, generate_next_sequential_id())

def preserve_traceability(source_id: str, target_id: str):
    """Create IDMapping node for audit trail."""
    query = """
    CREATE (m:IDMapping {
        sourceId: $source_id,
        targetId: $target_id,
        nodeType: $type,
        translationDate: datetime(),
        migrationPhase: 'Phase 4'
    })
    """
    target_db.write(query, {
        "source_id": source_id,
        "target_id": target_id,
        "type": detect_node_type(source_id)
    })
```

---

## 6. Semantic Enrichment Requirements

### Definition Structure

Every definition must:
1. **Explain WHAT** the concept is (first sentence)
2. **Explain WHY** it matters in branding (second sentence)
3. **Provide context** or framework reference (if applicable)
4. **Be specific** to this concept (not generic)

**Good Example**:
```
"Der Core Cause ist der zentrale Beweggrund oder das grundlegende 'Warum'
hinter einer Marke. Er beschreibt die zugrundeliegende Motivation, aus der
heraus die Marke agiert – unabhängig von kurzfristigen Zielen. Der Core
Cause bezeichnet den fundamentalen, übergeordneten Daseinszweck jenseits
von Gewinnerzielung."
```

**Bad Example** (template phrase):
```
"Ein fundamentaler Aspekt von Markenstrategie, der beschreibt die
Kernelemente der Marke."
```

### whatItIs/whatItIsNot Contrast

Must provide semantic differentiation:

**Good whatItIs**:
- "Fundamentaler Daseinszweck jenseits von Gewinnerzielung"
- "Übergeordnetes 'Warum' nach Simon Sinek's Golden Circle"
- "Langfristig stabil (nicht kurzfristig änderbar)"

**Good whatItIsNot**:
- "Nicht identisch mit Vision oder Mission Statement"
- "Nicht primär auf Gewinnmaximierung ausgerichtet"
- "Nicht oberflächliches Marketing-Versprechen"

**Bad (too generic)**:
- whatItIs: "Wichtig für die Marke"
- whatItIsNot: "Nicht unwichtig"

---

## 7. Language Consistency

### German vs English Properties

Properties must be **semantically equivalent** but culturally appropriate:

**German Style**:
- More philosophical, formal tone
- Compound words acceptable
- Abstract concepts common
- Example: "Daseinszweck", "zugrundeliegend"

**English Style**:
- More action-oriented, direct
- Shorter sentences preferred
- Pragmatic vocabulary
- Example: "purpose", "fundamental"

**Semantic Equivalence Required**:
```python
assert meaning(definitionDe) == meaning(definitionEn)
assert len(whatItIsDe) == len(whatItIsEn)
assert concepts(whatItIsNotDe) == concepts(whatItIsNotEn)
```

---

## 8. Brand Example Requirements

### EXEMPLIFIED_BY Relationships

Only create if:
1. Real brand can be identified
2. Concrete evidence exists
3. Source URL available
4. Multiple dimensions of exemplification

**Good Example**:
```cypher
(:Enumeration {nameDe: "Umweltschutz"})-[:EXEMPLIFIED_BY {
    reasoning: "Patagonia exemplifies 'Environmental Protection' through
               concrete actions: 1% for the Planet donations ($140M since
               1985), Worn Wear repair program, political advocacy,
               transparent supply chain reporting.",
    context: "Founded by Yvon Chouinard with mission 'We're in business
             to save our home planet'. 2022: ownership transferred to
             environmental trust.",
    source: "https://www.patagonia.com/our-footprint/",
    retrievalDate: date("2025-11-24")
}]->(:BrandExample {brandName: "Patagonia"})
```

**Bad Example** (vague):
```
reasoning: "Patagonia cares about the environment"  // Too vague
source: "General knowledge"  // Not verifiable
```

---

## 9. Validation Workflow

### Pre-Write Validation

```python
def validate_before_write(properties: dict) -> ValidationResult:
    """Run both tiers before database write."""

    # Tier 1: Structural constraints
    try:
        validated = MetaAttributeV3(**properties)
    except ValidationError as e:
        return ValidationResult(
            tier1_passed=False,
            tier1_violations=e.errors()
        )

    # Tier 2: Semantic quality
    semantic_result = validate_semantic_quality(properties)

    return ValidationResult(
        overall_passed=tier1_passed and semantic_result.tier2_passed,
        tier1_passed=True,
        tier2_passed=semantic_result.tier2_passed,
        tier2_violations=semantic_result.violations
    )
```

### Post-Write Verification

```cypher
// Verify all properties populated
MATCH (m:MetaAttribute {id: $target_id})
WHERE m.definitionDe IS NULL
   OR size(m.definitionDe) < 200
   OR m.whatItIsDe IS NULL
   OR size(m.whatItIsDe) < 3
RETURN m.id as incomplete_node

// Verify relationships created
MATCH (m:MetaAttribute {id: $target_id})
WHERE NOT (m)<-[:HAS_ATTRIBUTE]-(:Layer)
   OR NOT (m)-[:BELONGS_TO_GROUP]->(:GroupNode)
RETURN m.id as missing_relationships
```

---

## 10. Progress Tracking

### Enrichment Status Workflow

```
unclaimed → claimed → in_progress → completed/failed
```

```cypher
// Track progress
MATCH (m:MetaAttribute)
RETURN m.enrichment_status as status, count(m) as count
ORDER BY status

// Find failed nodes for review
MATCH (m:MetaAttribute {enrichment_status: 'failed'})
RETURN m.id, m.error_message
ORDER BY m.claimed_at DESC
```

---

## Key Principles

1. **No template phrases** - Every property must be specific
2. **Semantic contrast required** - whatItIs ≠ whatItIsNot
3. **Reasoning on edges** - Relationships carry metadata
4. **Hierarchieless IDs** - Structure via edges, not IDs
5. **Two-tier validation** - Structure + semantic quality
6. **Helpful errors** - Actionable guidance for fixes
7. **SOURCE immutable** - Never write to Test Propagation
8. **TARGET validated** - Only write quality content
9. **Complete enrichment** - All properties populated
10. **Traceability preserved** - IDMapping for audit

---

**Remember**: Quality over speed. Better to regenerate content multiple times than commit template phrases.