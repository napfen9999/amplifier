---
name: documentation-validator
description: Validates code changes against documentation contracts, ensures schema compliance and API consistency. Use when implementing features, updating APIs, modifying data structures, or making breaking changes. Triggers on "implement", "add endpoint", "change schema", "update API".
---

# Documentation Validator

Validates that code changes align with project documentation.

## Quick Start

Before making code changes, check:
1. API changes → `docs/api/openapi.json`
2. Schema changes → `ai_context/DATA_MODEL.md`
3. Contract changes → `docs/architecture/CONTRACTS.md`

## Key Documentation Files

| File | Purpose |
|------|---------|
| `docs/api/openapi.json` | API endpoints (19 endpoints) |
| `ai_context/DATA_MODEL.md` | PostgreSQL + Neo4j + Redis schema |
| `docs/architecture/CONTRACTS.md` | API contracts, embedding specs |
| `docs/architecture/modules/signal_extraction.md` | Signal pipeline spec |
| `docs/architecture/modules/memory_system.md` | 4-Layer memory spec |
| `docs/architecture/modules/traceability.md` | Why-Path spec |

## Validation Rules

See [VALIDATION_RULES.md](VALIDATION_RULES.md) for complete checklist.

## Automated Validation

Run validation script:
```bash
python .claude/skills/documentation-validator/scripts/validate_docs.py
```

## When to Use

- Adding new API endpoints → Check openapi.json
- Changing database schema → Check DATA_MODEL.md
- Modifying signal extraction → Check signal_extraction.md
- Updating memory system → Check memory_system.md
