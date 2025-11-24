# ID Translation Guide

**Purpose**: SOURCE → TARGET ID mapping rules for Neo4j graph migration
**Version**: 1.0
**Last Updated**: 2025-11-24

---

## Overview

The migration from SOURCE (Test Propagation) to TARGET (Graph Rebuild 202511) involves translating from V2 hierarchical IDs to V3 hierarchieless IDs.

**Key Principle**: In V3, hierarchies exist through edges, NOT encoded in IDs.

---

## ID Format Comparison

### V2 Format (SOURCE - Hierarchical)

| Node Type | Format | Example | Parent Encoded |
|-----------|--------|---------|----------------|
| MetaAttribute | M{3-digit}{letter?} | M001, M002a | No |
| Enumeration | E-M{parent}-{seq} | E-M001-001 | Yes (M001) |
| FreeTextValue | FT-M{parent}-{seq} | FT-M002a-001 | Yes (M002a) |

### V3 Format (TARGET - Hierarchieless)

| Node Type | Format | Example | Parent Encoded |
|-----------|--------|---------|----------------|
| MetaAttribute | M{3-digit}{letter?} | M001, M002a | No (unchanged) |
| Enumeration | E-{5-digit} | E-00001 | No (edge-based) |
| FreeTextValue | FT-{5-digit} | FT-00001 | No (edge-based) |
| HelperNode | H-{5-digit} | H-00001 | No (edge-based) |
| BrandExample | BE-{5-digit} | BE-00001 | No (edge-based) |

---

## Translation Rules

### MetaAttribute Translation

**No change required** - MetaAttribute IDs remain the same:
```
SOURCE: M001 → TARGET: M001
SOURCE: M002a → TARGET: M002a
SOURCE: M015 → TARGET: M015
```

### Enumeration Translation

**Hierarchical to Sequential**:
```python
def translate_enumeration_id(source_id: str) -> str:
    """
    Translate V2 hierarchical to V3 sequential.

    Examples:
        E-M001-001 → E-00001
        E-M001-002 → E-00002
        E-M015-001 → E-00234
    """
    if source_id.startswith("E-M"):
        # Look up in mapping table
        return enumeration_id_mapping[source_id]
    return source_id  # Already V3 format
```

**Mapping Table Structure**:
```python
enumeration_id_mapping = {
    "E-M001-001": "E-00001",  # First Core Cause enum
    "E-M001-002": "E-00002",  # Second Core Cause enum
    "E-M001-003": "E-00003",  # Third Core Cause enum
    # ... continues for all 3,255 Enumerations
    "E-M259-005": "E-03255",  # Last enumeration
}
```

### FreeTextValue Translation

**Similar to Enumeration**:
```python
def translate_freetext_id(source_id: str) -> str:
    """
    Translate V2 hierarchical to V3 sequential.

    Examples:
        FT-M002a-001 → FT-00001
        FT-M002b-001 → FT-00002
    """
    if source_id.startswith("FT-M"):
        return freetext_id_mapping[source_id]
    return source_id  # Already V3 format
```

---

## Parent Relationship Recovery

Since V3 IDs don't encode parent information, relationships must be preserved through edges:

### During Migration

```python
def migrate_enumeration(source_enum, parent_meta_id):
    """
    Migrate Enumeration preserving parent relationship.
    """
    # Translate ID
    source_id = source_enum["id"]  # e.g., "E-M001-001"
    target_id = translate_enumeration_id(source_id)  # e.g., "E-00001"

    # Create node in TARGET
    target_db.create_node(
        labels=["Enumeration"],
        properties={
            "id": target_id,
            "nameDe": source_enum["nameDe"],
            # ... other properties
        }
    )

    # Create parent relationship (THIS IS CRITICAL)
    target_db.create_relationship(
        start_id=parent_meta_id,  # e.g., "M001"
        end_id=target_id,  # e.g., "E-00001"
        type="HAS_ENUMERATION"
    )

    # Store mapping for traceability
    create_id_mapping(source_id, target_id, "Enumeration")
```

### Query Parent in V3

```cypher
// Find parent of Enumeration in V3
MATCH (m:MetaAttribute)-[:HAS_ENUMERATION]->(e:Enumeration {id: "E-00001"})
RETURN m.id as parent_id  // Returns "M001"

// Find all children of MetaAttribute in V3
MATCH (m:MetaAttribute {id: "M001"})-[:HAS_ENUMERATION]->(e:Enumeration)
RETURN e.id
ORDER BY e.id
```

---

## IDMapping for Traceability

Every translated node gets an IDMapping entry for audit:

```cypher
CREATE (map:IDMapping {
    sourceId: "E-M001-001",      // Original V2 ID
    targetId: "E-00001",         // New V3 ID
    nodeType: "Enumeration",
    translationDate: datetime(),
    migrationPhase: "Phase 3"
})
```

### Query Mappings

```cypher
// Find TARGET ID for SOURCE ID
MATCH (map:IDMapping {sourceId: "E-M001-001"})
RETURN map.targetId  // Returns "E-00001"

// Find SOURCE ID for TARGET ID
MATCH (map:IDMapping {targetId: "E-00001"})
RETURN map.sourceId  // Returns "E-M001-001"

// Audit trail - all translations
MATCH (map:IDMapping)
RETURN map.nodeType, count(*) as translated_count
ORDER BY map.nodeType
```

---

## Implementation Pattern

### Step 1: Build Mapping Tables

```python
def build_id_mappings():
    """
    Pre-generate all ID mappings before migration.
    """
    enumeration_mapping = {}
    next_enum_id = 1

    # Query SOURCE for all Enumerations
    source_enums = source_db.query("""
        MATCH (m:MetaAttribute)-[:HAS_ENUMERATION]->(e:Enumeration)
        RETURN e.id as source_id, m.id as parent_id
        ORDER BY m.id, e.id
    """)

    for enum in source_enums:
        source_id = enum["source_id"]  # e.g., "E-M001-001"
        target_id = f"E-{next_enum_id:05d}"  # e.g., "E-00001"
        enumeration_mapping[source_id] = target_id
        next_enum_id += 1

    return enumeration_mapping
```

### Step 2: Use During Migration

```python
class IDTranslator:
    """Handles all ID translations during migration."""

    def __init__(self):
        self.enum_mapping = build_enumeration_mappings()
        self.freetext_mapping = build_freetext_mappings()

    def translate(self, source_id: str) -> str:
        """
        Translate any ID from V2 to V3 format.
        """
        # MetaAttributes unchanged
        if source_id.startswith("M"):
            return source_id

        # Enumerations
        if source_id.startswith("E-M"):
            return self.enum_mapping.get(source_id, source_id)

        # FreeTextValues
        if source_id.startswith("FT-M"):
            return self.freetext_mapping.get(source_id, source_id)

        # Unknown format - return as-is
        return source_id
```

### Step 3: Create Traceability

```python
def create_id_mapping(source_id: str, target_id: str, node_type: str):
    """
    Create IDMapping node for audit trail.
    """
    target_db.query("""
        CREATE (map:IDMapping {
            sourceId: $source_id,
            targetId: $target_id,
            nodeType: $node_type,
            translationDate: datetime(),
            migrationPhase: $phase
        })
    """, {
        "source_id": source_id,
        "target_id": target_id,
        "node_type": node_type,
        "phase": current_phase
    })
```

---

## Validation Queries

### Verify No Hierarchical IDs Remain

```cypher
// Check for old format Enumerations
MATCH (e:Enumeration)
WHERE e.id CONTAINS "E-M"
RETURN count(e) as old_format_count
// Should return 0

// Check for old format FreeTextValues
MATCH (f:FreeTextValue)
WHERE f.id CONTAINS "FT-M"
RETURN count(f) as old_format_count
// Should return 0
```

### Verify All Nodes Have Mappings

```cypher
// Count Enumerations without mappings
MATCH (e:Enumeration)
WHERE NOT EXISTS {
    MATCH (map:IDMapping {targetId: e.id, nodeType: "Enumeration"})
}
RETURN count(e) as unmapped_count
// Should return 0
```

### Verify Parent Relationships Preserved

```cypher
// Every Enumeration must have parent MetaAttribute
MATCH (e:Enumeration)
WHERE NOT EXISTS {
    MATCH (m:MetaAttribute)-[:HAS_ENUMERATION]->(e)
}
RETURN count(e) as orphaned_enumerations
// Should return 0
```

---

## Common Issues and Solutions

### Issue: Duplicate Sequential IDs

**Problem**: Two threads generate same sequential ID
**Solution**: Use atomic counter or pre-generate all mappings

```python
# Pre-generate all mappings before migration starts
all_mappings = build_complete_id_mappings()
# Then use mappings during parallel processing
```

### Issue: Missing Parent Relationship

**Problem**: Enumeration created without HAS_ENUMERATION edge
**Solution**: Always create node and relationship in same transaction

```python
def create_enumeration_with_parent(enum_props, parent_id):
    """Create Enumeration and parent relationship atomically."""
    with target_db.transaction() as tx:
        tx.run("CREATE (e:Enumeration $props)", props=enum_props)
        tx.run("""
            MATCH (m:MetaAttribute {id: $parent_id}),
                  (e:Enumeration {id: $enum_id})
            CREATE (m)-[:HAS_ENUMERATION]->(e)
        """, parent_id=parent_id, enum_id=enum_props["id"])
```

### Issue: Incorrect Mapping Lookup

**Problem**: Source ID not found in mapping table
**Solution**: Log unmapped IDs, use fallback

```python
def safe_translate(source_id: str) -> str:
    """Translate with fallback and logging."""
    if source_id in mapping:
        return mapping[source_id]
    else:
        logger.warning(f"No mapping for {source_id}, using as-is")
        return source_id  # Use source ID as fallback
```

---

## Benefits of Hierarchieless System

1. **Parallel Safety**: No ID conflicts during concurrent generation
2. **Reorganization Flexibility**: Can reassign parents without changing IDs
3. **Pure Graph Traversal**: No string parsing needed
4. **Extensibility**: Can add sub-hierarchies without ID schema changes
5. **Query Performance**: Sequential IDs improve index performance

---

## Summary

### Key Points

1. **MetaAttribute IDs unchanged** (M001 → M001)
2. **Enumeration IDs sequential** (E-M001-001 → E-00001)
3. **Parent via edges not IDs** (HAS_ENUMERATION relationship)
4. **IDMapping for traceability** (sourceId ↔ targetId)
5. **Pre-generate mappings** (avoid conflicts)
6. **Atomic operations** (node + relationship together)

### Translation Patterns

```python
# Simple translation
source_id = "E-M001-001"
target_id = translate_enumeration_id(source_id)  # "E-00001"

# With relationship preservation
create_enumeration(target_id, properties)
create_relationship(parent_id="M001", child_id=target_id, type="HAS_ENUMERATION")

# With traceability
create_id_mapping(source_id, target_id, "Enumeration")
```

---

**Remember**: V3 uses edges for hierarchy, not IDs. Every translation needs both ID mapping and relationship creation.