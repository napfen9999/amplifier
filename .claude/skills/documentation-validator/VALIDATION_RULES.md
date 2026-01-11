# Validation Rules

Complete checklist for validating code against documentation.

## API Changes

Before adding or modifying API endpoints:

- [ ] Check `docs/api/openapi.json` for existing endpoints
- [ ] Verify Pydantic models in `solver_api/src/models/`
- [ ] Check `docs/architecture/CONTRACTS.md` for API contracts
- [ ] Update openapi.json after changes: `curl http://localhost:8001/openapi.json > docs/api/openapi.json`

## Database Schema Changes

Before modifying database schema:

- [ ] Check `ai_context/DATA_MODEL.md` for current schema
- [ ] Verify migration in `solver_api/migrations/`
- [ ] Check PostgreSQL tables in Supabase
- [ ] Check Neo4j nodes/edges if graph-related

### PostgreSQL Tables (15)

| Table | Purpose |
|-------|---------|
| sessions | Interview sessions |
| turns | Turn metadata |
| messages | User/Assistant messages |
| processed_signals | Signal → Enum matching |
| solver_seeds | Solver input |
| solver_deltas | Solver effect |
| conflict_records | Active conflicts |
| ... | See DATA_MODEL.md |

### Neo4j Nodes (7)

| Node | Count |
|------|-------|
| MetaAttribute | 43 |
| Enumeration | 847 |
| Layer | 4 |
| Brand | 5 |
| FreetextHelper | 4 |
| ... | See DATA_MODEL.md |

## Business Logic Changes

Before modifying core logic:

- [ ] Check `docs/architecture/modules/signal_extraction.md` for signal pipeline
- [ ] Check `docs/architecture/modules/memory_system.md` for 4-layer memory
- [ ] Check `docs/architecture/modules/traceability.md` for why-path
- [ ] Check `docs/solver/SOLVER_V5_GUIDE.md` for solver logic

## Embedding/AI Changes

- [ ] Embedding model: `voyage-3.5-lite` (1024-dim)
- [ ] Signal extraction model: Haiku 4.5
- [ ] Generation model: Sonnet 4.5
- [ ] Check `docs/architecture/CONTRACTS.md` for specs

## ADR Reference

Check Architecture Decision Records before making architectural changes:

| ADR | Topic |
|-----|-------|
| ADR-001 | Unified Embedding Dimensions |
| ADR-002 | Haiku Signal Extraction |
| ADR-003 | Redis State Management |
| ADR-004 | Four-Layer Memory |
| ADR-005 | H-PHASED Solver |
