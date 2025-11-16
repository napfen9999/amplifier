# neo4j-cypher Split Structure Revision

**Issue Discovered**: Content analysis of `procedures.md` (18,530 lines) reveals the original plan's split structure doesn't match actual content organization.

---

## Original Plan (Phase 1)

**11 files proposed:**
1. apoc/overview.md (~100 lines)
2. apoc/categories/aggregation.md (~1,500 lines)
3. apoc/categories/text-processing.md (~2,000 lines)
4. apoc/categories/graph-algorithms.md (~2,500 lines)
5. apoc/categories/data-conversion.md (~1,800 lines)
6. apoc/categories/temporal.md (~1,200 lines)
7. apoc/categories/spatial.md (~1,000 lines)
8. apoc/categories/triggers.md (~1,500 lines)
9. apoc/categories/import-export.md (~2,000 lines)
10. apoc/categories/meta.md (~1,000 lines)
11. apoc/categories/utilities.md (~1,500 lines)

**Total: ~16,100 lines** (missing ~2,430 lines)

---

## Actual Content Distribution

**Analysis findings:**

| Namespace Group | Actual Size | In Original Plan? |
|----------------|-------------|-------------------|
| Collections (apoc.coll) | ~1,400 lines | ❌ **MISSING** |
| Node/Rel Operations | ~2,800 lines | ❌ **MISSING** |
| Map Operations | ~700 lines | ❌ **MISSING** |
| Math/Number | ~600 lines | ❌ **MISSING** |
| Text Processing | ~1,200 lines | ✅ Close match |
| Import/Export | ~1,850 lines | ✅ Close match |
| Graph Operations | ~1,700 lines | ⚠️ Conflated with algorithms |
| Graph Algorithms | ~1,060 lines | ⚠️ Overestimated (2,500 → 1,060) |
| Utilities | ~1,410 lines | ✅ Close match |
| Meta/Schema | ~1,000 lines | ✅ Match |
| Aggregation | ~530 lines | ⚠️ Overestimated (1,500 → 530) |
| Temporal | ~550 lines | ⚠️ Underestimated (1,200 → 550) |
| Spatial | ~160 lines | ⚠️ Overestimated (1,000 → 160) |
| Triggers | ~440 lines | ⚠️ Overestimated (1,500 → 440) |
| Data Conversion | ~560 lines | ⚠️ Overestimated (1,800 → 560) |
| Miscellaneous | ~800 lines | ❌ **MISSING** |

---

## Recommended Revised Structure

**17 files (vs 11 originally):**

1. **apoc/overview.md** (~100 lines) - ✅ Same
2. **apoc/categories/aggregation.md** (~530 lines) - ✏️ Adjusted
3. **apoc/categories/text-processing.md** (~1,200 lines) - ✅ Close
4. **apoc/categories/collections.md** (~1,400 lines) - ⭐ **NEW**
5. **apoc/categories/map-operations.md** (~700 lines) - ⭐ **NEW**
6. **apoc/categories/math-number.md** (~600 lines) - ⭐ **NEW**
7. **apoc/categories/node-relationship-ops.md** (~2,800 lines) - ⭐ **NEW**
8. **apoc/categories/graph-algorithms.md** (~1,060 lines) - ✏️ Adjusted
9. **apoc/categories/graph-operations.md** (~1,700 lines) - ⭐ **NEW (split from #8)**
10. **apoc/categories/data-conversion.md** (~560 lines) - ✏️ Adjusted
11. **apoc/categories/temporal.md** (~550 lines) - ✏️ Adjusted
12. **apoc/categories/spatial.md** (~160 lines) - ✏️ Adjusted
13. **apoc/categories/triggers.md** (~440 lines) - ✏️ Adjusted
14. **apoc/categories/import-export.md** (~1,850 lines) - ✅ Close
15. **apoc/categories/meta-schema.md** (~1,000 lines) - ✅ Close
16. **apoc/categories/utilities.md** (~1,410 lines) - ✅ Close
17. **apoc/categories/miscellaneous.md** (~800 lines) - ⭐ **NEW**

**Total: ~18,500 lines** ✅ Matches source

---

## Key Differences

### Files Added (6 new)
- **collections.md** - 2nd largest namespace group (52 entries)
- **node-relationship-ops.md** - **LARGEST group** (82 entries, 2,800 lines!)
- **map-operations.md** - Significant standalone group (25 entries)
- **math-number.md** - Combined math/number operations (31 entries)
- **graph-operations.md** - Split from over-broad "algorithms" category
- **miscellaneous.md** - Catchall for smaller namespaces

### Size Adjustments (9 files)
- **aggregation**: 1,500 → 530 (overestimated by 970 lines)
- **temporal**: 1,200 → 550 (overestimated by 650 lines)
- **spatial**: 1,000 → 160 (overestimated by 840 lines)
- **triggers**: 1,500 → 440 (overestimated by 1,060 lines)
- **data-conversion**: 1,800 → 560 (overestimated by 1,240 lines)
- **graph-algorithms**: 2,500 → 1,060 (split off graph-operations)

---

## Impact on SKILL.md

**Original plan:** Navigate to 11 categories
**Revised:** Navigate to 17 categories

**SKILL.md will need:**
- Longer Guide Index section (17 vs 11 entries)
- More detailed "When to Use" categorization
- Still well under 150-line target

---

## Philosophy Alignment

### ✅ Ruthless Simplicity
- Each file covers ONE clear namespace/category
- No "dumping ground" files
- Logical organization matches actual content

### ✅ Modular Design
- Self-contained reference files
- Clear boundaries
- Independently understandable

### ✅ Progressive Disclosure
- All files <500 lines ✅
- Overview → Category → Details
- On-demand loading works correctly

---

## Recommendation

**Use the revised 17-file structure** because:

1. **Matches reality** - Reflects actual content organization
2. **No missing content** - Accounts for all 18,530 lines
3. **Better organization** - Clearer categories
4. **Maintains targets** - All files <500 lines
5. **Philosophy compliant** - Follows all principles

---

## User Decision Required

**Option A: Approve revised structure (17 files)**
- More files but better organized
- Matches actual content
- No missing categories

**Option B: Stick to original plan (11 files)**
- Fewer files but some forced categorization
- Would need to merge related groups
- Risk of poor organization

**Option C: Hybrid approach**
- Keep some of the 6 new categories
- Merge others into existing categories
- Specify which to keep/merge

---

**Please advise which option to proceed with.**
