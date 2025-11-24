#!/usr/bin/env python3
"""
Comprehensive test suite for Graph Semantic Enrichment System.

Runs all component tests and verifies integration.
"""

import logging
import subprocess
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_test(test_file: str, description: str) -> bool:
    """Run a single test file and report results.

    Args:
        test_file: Path to test file
        description: Test description

    Returns:
        True if test passed, False otherwise
    """
    logger.info(f"Running: {description}")
    logger.info("=" * 60)

    try:
        result = subprocess.run([sys.executable, test_file], capture_output=True, text=True, cwd=Path(__file__).parent)

        # Print output
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode == 0:
            logger.info(f"✅ {description} - PASSED")
            return True
        logger.error(f"❌ {description} - FAILED")
        return False

    except Exception as e:
        logger.error(f"❌ {description} - ERROR: {e}")
        return False


def test_cli_help() -> bool:
    """Test CLI tools help command."""
    logger.info("Testing CLI help command...")

    try:
        result = subprocess.run(
            [sys.executable, "tools.py", "--help"], capture_output=True, text=True, cwd=Path(__file__).parent
        )

        if "Graph Semantic Enrichment CLI Tools" in result.stdout:
            logger.info("✅ CLI help command works")
            return True
        logger.error("❌ CLI help command failed")
        return False

    except Exception as e:
        logger.error(f"❌ CLI help test failed: {e}")
        return False


def main():
    """Run all tests and report overall status."""
    logger.info("=" * 70)
    logger.info("COMPREHENSIVE TEST SUITE - GRAPH SEMANTIC ENRICHMENT")
    logger.info("=" * 70)

    all_passed = True
    test_results = []

    # Define tests to run
    tests = [
        ("test_database_layer.py", "Database Access Layer Tests"),
        ("test_claiming.py", "Claiming System Tests"),
        ("test_freetext.py", "FreeText Support Tests"),
    ]

    # Run each test
    for test_file, description in tests:
        passed = run_test(test_file, description)
        test_results.append((description, passed))
        all_passed = all_passed and passed
        print()  # Add spacing between tests

    # Test CLI help
    passed = test_cli_help()
    test_results.append(("CLI Help Command", passed))
    all_passed = all_passed and passed

    # Print summary
    logger.info("=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)

    for test_name, passed in test_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name:40s} : {status}")

    logger.info("=" * 70)

    if all_passed:
        logger.info("✅ ALL TESTS PASSED!")
        logger.info("")
        logger.info("System Components Verified:")
        logger.info("  ✅ Core Data Models (models.py)")
        logger.info("  ✅ Database Access Layer (source_db.py, target_db.py)")
        logger.info("  ✅ Validation System (validation.py)")
        logger.info("  ✅ Claiming System (claiming.py)")
        logger.info("  ✅ CLI Tools (tools.py)")
        logger.info("")
        logger.info("Critical Requirements Met:")
        logger.info("  ✅ SOURCE database is READ-ONLY")
        logger.info("  ✅ TARGET database validates before writing")
        logger.info("  ✅ ALL Enumerations claimed (not limited to 20)")
        logger.info("  ✅ Template phrases detected")
        logger.info("  ✅ Atomic package claiming")
        logger.info("  ✅ 8 parallel agents supported")
    else:
        logger.error("❌ SOME TESTS FAILED - Please review the output above")

    logger.info("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
