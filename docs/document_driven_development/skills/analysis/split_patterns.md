# Phase 2 Split Analysis

**Goal**: Split all files >500 lines and add hierarchical linking

**Total Scope**: 36 files across 6 skills (~57K lines to split)

---

## Summary by Skill

| Skill | Files >500 | Total Lines | Status |
|-------|------------|-------------|--------|
| supabase-database | 0 | 0 | ✅ Already compliant |
| docker-desktop | 0 | 0 | ✅ Already compliant |
| docker-build-compose | 1 | 2,286 | ⚠️ Needs work |
| docker-platform | 3 | 5,123 | ⚠️ Needs work |
| supabase-platform | 3 | 2,512 | ⚠️ Needs work |
| docker-engine | 5 | 9,760 | ⚠️ Needs work |
| supabase-development | 9 | 16,907 | ⚠️ Needs work |
| neo4j-cypher | 15 | 19,575 | ⚠️ Needs work |

---

## Priority Order (Largest First)

### TIER 1: MASSIVE FILES (>2,000 lines)

#### 1. docker-engine/storage.md (6,004 lines)
**RECOMMENDATION**: DELETE - This is a preserved file from original split
**Reason**: Content already split into storage/overview.md and subdirectory files
**Action**: Remove after verifying content is in split files

#### 2. supabase-development/management-api.md (5,640 lines)
**Strategy**: Split by API category
**Suggested splits**:
- Database API (~1,400 lines)
- Projects API (~1,400 lines)
- Organizations API (~1,200 lines)
- Secrets API (~800 lines)
- SSL Certificates API (~840 lines)

#### 3. docker-platform/scout.md (3,670 lines)
**RECOMMENDATION**: DELETE or merge into scout/ subdirectory
**Reason**: Content likely duplicated in scout/ subdirectory (8 files exist)
**Action**: Verify duplication, then remove

#### 4. supabase-development/cli-utilities.md (3,360 lines)
**Strategy**: Split by command category
**Suggested splits**:
- Gen commands (~800 lines)
- Migration commands (~800 lines)
- Testing commands (~600 lines)
- Link/Unlink commands (~600 lines)
- Secrets commands (~560 lines)

#### 5. neo4j-cypher/apoc/node-relationship-ops.md (2,462 lines)
**Strategy**: Split by operation type
**Suggested splits**:
- Node operations (~1,000 lines)
- Relationship operations (~800 lines)
- Path operations (~662 lines)

#### 6. docker-build-compose/other.md (2,286 lines)
**Strategy**: Categorize and split
**Action**: Review content, create proper categories

---

### TIER 2: LARGE FILES (1,000-2,000 lines)

#### 7. neo4j-cypher/apoc/import-export.md (1,484 lines)
**Strategy**: Split by format
- JSON import/export (~500 lines)
- CSV import/export (~400 lines)
- GraphML import/export (~300 lines)
- Cypher import/export (~284 lines)

#### 8. neo4j-cypher/other.md (1,473 lines)
**Action**: Categorize uncategorized content

#### 9. neo4j-cypher/apoc/collections.md (1,403 lines)
**Strategy**: Split by operation type
- List operations (~500 lines)
- Set operations (~450 lines)
- Pair operations (~453 lines)

#### 10. docker-engine/storage/overview.md (1,413 lines)
**Strategy**: Split into sections
- Storage concepts (~400 lines)
- Driver comparison (~400 lines)
- Troubleshooting (~400 lines)
- Best practices (~213 lines)

#### 11. supabase-development/cli-database.md (1,342 lines)
**Strategy**: Split by database operation
- Migrations (~500 lines)
- Functions (~400 lines)
- Types (~442 lines)

#### 12. neo4j-cypher/apoc/utilities.md (1,321 lines)
**Strategy**: Split by utility type
- Conversion utilities (~500 lines)
- Validation utilities (~400 lines)
- System utilities (~421 lines)

#### 13. docker-engine/storage/drivers/btrfs.md (1,230 lines)
**Strategy**: Split into sections
- Configuration (~400 lines)
- Operations (~400 lines)
- Troubleshooting (~430 lines)

#### 14. neo4j-cypher/apoc/text-processing.md (1,155 lines)
**Strategy**: Split by function category
- String manipulation (~400 lines)
- Regular expressions (~400 lines)
- Formatting (~355 lines)

#### 15. neo4j-cypher/apoc/graph-operations.md (1,124 lines)
**Strategy**: Split by operation type
- Graph analysis (~400 lines)
- Graph traversal (~400 lines)
- Graph transformation (~324 lines)

#### 16. neo4j-cypher/apoc/graph-algorithms.md (1,041 lines)
**Strategy**: Split by algorithm category
- Pathfinding (~400 lines)
- Centrality (~300 lines)
- Community detection (~341 lines)

#### 17. supabase-platform/auth/providers/oauth.md (1,035 lines)
**Strategy**: Split by provider
- Google/GitHub/Apple (~400 lines)
- Microsoft/Azure (~300 lines)
- Other providers (~335 lines)

---

### TIER 3: MEDIUM FILES (500-1,000 lines)

18. supabase-development/self-hosting-storage.md (997 lines)
19. supabase-development/self-hosting-auth.md (911 lines)
20. neo4j-cypher/apoc/meta-schema.md (935 lines)
21. neo4j-cypher/apoc/map-operations.md (933 lines)
22. supabase-platform/storage.md (898 lines)
23. supabase-development/edge_functions.md (761 lines)
24. supabase-development/cli-core.md (748 lines)
25. supabase-development/frameworks.md (739 lines)
26. docker-platform/scout/cli-reference.md (794 lines)
27. supabase-development/self-hosting-analytics.md (696 lines)
28. docker-platform/hub/general.md (659 lines)
29. neo4j-cypher/apoc/math-number.md (663 lines)
30. docker-engine/storage/drivers/overlay.md (591 lines)
31. supabase-platform/billing-usage.md (579 lines)
32. neo4j-cypher/querying.md (572 lines)
33. neo4j-cypher/apoc/aggregation.md (526 lines)
34. neo4j-cypher/apoc/data-conversion.md (525 lines)
35. neo4j-cypher/functions.md (523 lines)
36. docker-engine/storage/drivers/zfs.md (522 lines)
37. neo4j-cypher/optimization.md (513 lines)

**Strategy for Tier 3**: Most can be split in half or thirds

---

## Execution Strategy

### Phase 2A: Cleanup (DELETE preserved files)
1. Delete docker-engine/storage.md (preserved duplicate)
2. Delete docker-platform/scout.md (preserved duplicate)
3. Verify content exists in split files first

### Phase 2B: Split Files by Priority
1. **Tier 1** (7 files, ~24K lines) - Largest files first
2. **Tier 2** (11 files, ~17K lines) - Large files
3. **Tier 3** (18 files, ~11K lines) - Medium files

### Phase 2C: Add Hierarchical Linking
- Add "↑ Back to SKILL.md" links to all reference files
- Add "↑ Back to [parent]" links for nested files
- Update SKILL.md files with tree structure notation

### Phase 2D: Update Documentation
- Update all SKILL.md Guide Index sections
- Update docs_index.txt with all changes
- Verify all links work

---

## Notes

- **supabase-database** and **docker-desktop** are already Phase 2 compliant
- Focus on structure-first: understand content before splitting
- Target: ~400-500 lines per split file
- Preserve all examples and code blocks intact
- Add hierarchical navigation after splits complete

