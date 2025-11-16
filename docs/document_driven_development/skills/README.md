# Claude Code Skills Optimization

Documentation for optimizing Claude Code skills using DDD Phase 2 principles.

## Contents

### [Optimization Guide](./OPTIMIZATION_GUIDE.md)

Complete guide for optimizing existing Claude Code skills:
- **Phase 2A**: Cleanup (remove duplicates and backups)
- **Phase 2B**: File Splitting (all files <500 lines)
- **Phase 2C**: Hierarchical Linking (navigation to SKILL.md)
- **Phase 2D**: Guide Index Updates (complete file listings)
- **Skill Naming Strategy**: Reference vs Task-oriented naming

Based on optimization of 8 skills (283 files processed).

### Analysis

- [Split Patterns](./analysis/split_patterns.md) - File splitting patterns and strategies

### Examples

- [Neo4j Cypher Split](./examples/neo4j_cypher_split.md) - Example of splitting large reference files

## Key Concepts

### Reference vs Task-Oriented Skills

**Reference Skills** (`-reference` suffix):
- Primary purpose: Look up syntax, APIs, configuration
- Content: >70% documentation and specifications
- Examples: `neo4j-cypher-reference`, `docker-platform-reference`

**Task-Oriented Skills** (no suffix):
- Primary purpose: Accomplish goals and workflows
- Content: >70% tutorials and guides
- Examples: `neo4j-application-dev`, `docker-build-compose`

See [Optimization Guide](./OPTIMIZATION_GUIDE.md#skill-naming-strategy) for detailed decision framework.

## Progressive Disclosure

Skills follow a three-tier loading pattern:

```
SKILL.md (Overview, ~200 lines)
    ↓
Category Files (Organized topics, ~400 lines)
    ↓
Detailed Examples (Specific implementations, ~300 lines)
```

**Why 500 lines?**
- Fits comfortably in LLM context windows
- Easy to navigate and understand
- Forces modular organization
- Enables effective progressive disclosure

## Related Documentation

- [DDD Overview](../overview.md) - Document-Driven Development methodology
- [DDD Phases](../phases/) - Complete DDD phase documentation
- [Claude Code Skills](https://code.claude.com/docs/en/skills) - Official Claude Code skills documentation
