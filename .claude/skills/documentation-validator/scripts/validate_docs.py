#!/usr/bin/env python3
"""
Documentation Validator Script

Validates that code and documentation are in sync.
Run: python .claude/skills/documentation-validator/scripts/validate_docs.py
"""

import json
import sys
from pathlib import Path


def check_openapi_exists() -> tuple[bool, str]:
    """Check if openapi.json exists and is valid."""
    openapi_path = Path("docs/api/openapi.json")
    if not openapi_path.exists():
        return False, "docs/api/openapi.json not found"

    try:
        with open(openapi_path) as f:
            data = json.load(f)

        paths = data.get("paths", {})
        if not paths:
            return False, "openapi.json has no paths defined"

        return True, f"openapi.json valid ({len(paths)} endpoints)"
    except json.JSONDecodeError as e:
        return False, f"openapi.json invalid JSON: {e}"


def check_data_model_exists() -> tuple[bool, str]:
    """Check if DATA_MODEL.md exists."""
    path = Path("ai_context/DATA_MODEL.md")
    if not path.exists():
        return False, "ai_context/DATA_MODEL.md not found"

    content = path.read_text()
    if "PostgreSQL" not in content:
        return False, "DATA_MODEL.md missing PostgreSQL section"
    if "Neo4j" not in content:
        return False, "DATA_MODEL.md missing Neo4j section"

    return True, "DATA_MODEL.md valid"


def check_contracts_exists() -> tuple[bool, str]:
    """Check if CONTRACTS.md exists."""
    path = Path("docs/architecture/CONTRACTS.md")
    if not path.exists():
        return False, "docs/architecture/CONTRACTS.md not found"

    content = path.read_text()
    if "voyage-3.5-lite" not in content and "voyage-3-large" not in content:
        return False, "CONTRACTS.md missing embedding model spec"

    return True, "CONTRACTS.md valid"


def check_module_specs() -> tuple[bool, str]:
    """Check if module specs exist."""
    modules = [
        "docs/architecture/modules/signal_extraction.md",
        "docs/architecture/modules/memory_system.md",
        "docs/architecture/modules/traceability.md",
    ]

    missing = []
    for module in modules:
        if not Path(module).exists():
            missing.append(module)

    if missing:
        return False, f"Missing module specs: {', '.join(missing)}"

    return True, "All module specs present"


def check_adrs() -> tuple[bool, str]:
    """Check if ADRs exist."""
    adr_dir = Path("docs/architecture/decisions")
    if not adr_dir.exists():
        return False, "docs/architecture/decisions/ not found"

    adrs = list(adr_dir.glob("ADR-*.md"))
    if len(adrs) < 5:
        return False, f"Only {len(adrs)} ADRs found (expected 5)"

    return True, f"{len(adrs)} ADRs found"


def main():
    """Run all validation checks."""
    print("=" * 60)
    print("Documentation Validation")
    print("=" * 60)
    print()

    checks = [
        ("OpenAPI Spec", check_openapi_exists),
        ("Data Model", check_data_model_exists),
        ("Contracts", check_contracts_exists),
        ("Module Specs", check_module_specs),
        ("ADRs", check_adrs),
    ]

    all_passed = True
    for name, check_func in checks:
        passed, message = check_func()
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}: {message}")
        if not passed:
            all_passed = False

    print()
    print("=" * 60)
    if all_passed:
        print("All checks passed!")
        sys.exit(0)
    else:
        print("Some checks failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
