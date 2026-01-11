---
name: test-driven-development
description: Enforces test-first development practices. Validates test coverage for new features, ensures assertions match implementation. Use when implementing features, adding functionality, or modifying core logic. Triggers on "add feature", "implement", "write code", "new endpoint".
---

# Test-Driven Development

Ensures tests are written alongside code.

## Workflow

1. **Write test first** - Define expected behavior
2. **Run test** - Verify it fails (red)
3. **Implement code** - Make test pass (green)
4. **Refactor** - Clean up while tests pass

## Coverage Requirements

| Layer | Min Coverage | Pattern |
|-------|-------------|---------|
| Core Logic | 80% | Unit tests |
| API | 70% | Integration tests |
| E2E | Key flows | Playwright |

## Test Patterns

See [TEST_PATTERNS.md](TEST_PATTERNS.md) for examples.

## Project Test Structure

```
solver_api/tests/
├── test_*.py          # Unit tests
├── integration/       # Integration tests
└── e2e/              # End-to-end tests

frontend/
├── src/**/*.test.ts   # Component tests
└── e2e/              # Playwright tests
```

## Running Tests

```bash
# All tests (909 tests)
make test

# Specific modules
uv run pytest solver_api/tests/test_signals.py -v
uv run pytest solver_api/tests/test_conversation_rag_full.py -v

# E2E
cd frontend && npx playwright test
```

## When to Use

- Implementing new features
- Fixing bugs (write test that reproduces bug first)
- Refactoring code
- Adding API endpoints
