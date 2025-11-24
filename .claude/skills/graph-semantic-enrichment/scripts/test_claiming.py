#!/usr/bin/env python3
"""
Test script for Claiming System (claiming.py)

This script verifies:
1. Atomic package claiming works correctly
2. ALL Enumerations are claimed (not limited to 20)
3. Package status transitions work
4. Agent ownership is tracked correctly
5. Stats and monitoring functions work
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all modules can be imported."""
    logger.info("=" * 60)
    logger.info("Testing imports...")

    try:
        from models import EnumerationPackage
        from models import FreeTextPackage

        logger.info("✅ Models imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import models: {e}")
        return False

    try:
        from claiming import PackageClaimer

        logger.info("✅ PackageClaimer imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import PackageClaimer: {e}")
        return False

    return True


def test_package_claiming():
    """Test atomic package claiming functionality."""
    logger.info("=" * 60)
    logger.info("Testing package claiming...")

    from claiming import PackageClaimer
    from models import EnumerationPackage

    # Create mock database client
    mock_db = MagicMock()
    mock_driver = MagicMock()
    mock_db.driver = mock_driver

    # Create mock session
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_driver.session.return_value.__exit__ = MagicMock(return_value=None)

    # Test claiming with 35 Enumerations (more than 20)
    def mock_transaction(tx_func):
        # Mock transaction that returns a large package
        mock_tx = MagicMock()

        # First query result (claim MetaAttribute)
        claim_result = MagicMock()
        claim_record = {"meta_id": "M001", "attribute_type": "ENUMERATION", "claimed_at": datetime.now()}
        claim_result.single.return_value = claim_record

        # Second query result (get ALL Enumerations)
        enum_ids = [f"E-{i:05d}" for i in range(1, 36)]  # 35 Enumerations
        enum_records = [{"enum_id": eid} for eid in enum_ids]

        # Setup mock to return different results for different queries
        def run_side_effect(query, **kwargs):
            if "SET m.enrichment_status" in query:
                return claim_result
            if "HAS_ENUMERATION" in query:
                enum_result = MagicMock()
                enum_result.__iter__ = lambda self: iter(enum_records)
                return enum_result
            return MagicMock()

        mock_tx.run = MagicMock(side_effect=run_side_effect)

        # Execute the transaction function
        result = tx_func(mock_tx)

        # Verify it's an EnumerationPackage with ALL 35 enums
        if isinstance(result, EnumerationPackage):
            if len(result.enumeration_ids) == 35:
                logger.info("✅ Claimed package with ALL 35 Enumerations (not limited to 20)")
            else:
                logger.error(f"❌ Package has {len(result.enumeration_ids)} Enumerations, expected 35")
                return None
        else:
            logger.error(f"❌ Expected EnumerationPackage, got {type(result)}")
            return None

        return result

    mock_session.execute_write = MagicMock(side_effect=mock_transaction)

    # Create claimer and test
    claimer = PackageClaimer(mock_db)
    packages = claimer.claim_packages("Agent_A1", num_packages=1)

    if len(packages) == 1:
        logger.info("✅ Successfully claimed 1 package")
        package = packages[0]
        if len(package.enumeration_ids) == 35:
            logger.info("✅ Package includes ALL 35 Enumerations")
        else:
            logger.error(f"❌ Package has wrong number of Enumerations: {len(package.enumeration_ids)}")
            return False
    else:
        logger.error(f"❌ Expected 1 package, got {len(packages)}")
        return False

    return True


def test_status_transitions():
    """Test package status transition methods."""
    logger.info("=" * 60)
    logger.info("Testing status transitions...")

    from claiming import PackageClaimer

    # Create mock database
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_db.driver.session.return_value.__exit__ = MagicMock(return_value=None)

    claimer = PackageClaimer(mock_db)

    # Test mark_completed
    mock_result = MagicMock()
    mock_result.single.return_value = {"id": "M001"}
    mock_session.run.return_value = mock_result

    success = claimer.mark_completed("M001", "Agent_A1")
    if success:
        logger.info("✅ mark_completed() works correctly")
    else:
        logger.error("❌ mark_completed() failed")
        return False

    # Test mark_failed
    success = claimer.mark_failed("M001", "Agent_A1", "Test error")
    if success:
        logger.info("✅ mark_failed() works correctly")
    else:
        logger.error("❌ mark_failed() failed")
        return False

    # Test update_progress
    success = claimer.update_progress("M001", "Agent_A1")
    if success:
        logger.info("✅ update_progress() works correctly")
    else:
        logger.error("❌ update_progress() failed")
        return False

    return True


def test_monitoring_functions():
    """Test stats and monitoring functionality."""
    logger.info("=" * 60)
    logger.info("Testing monitoring functions...")

    from claiming import PackageClaimer

    # Create mock database
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_db.driver.session.return_value.__exit__ = MagicMock(return_value=None)

    claimer = PackageClaimer(mock_db)

    # Test get_agent_packages
    mock_result = MagicMock()
    mock_records = [{"meta_id": "M001", "status": "claimed"}, {"meta_id": "M002", "status": "in_progress"}]
    mock_result.__iter__ = lambda self: iter(mock_records)
    mock_session.run.return_value = mock_result

    packages = claimer.get_agent_packages("Agent_A1")
    if len(packages) == 2:
        logger.info("✅ get_agent_packages() returns correct data")
    else:
        logger.error(f"❌ get_agent_packages() returned {len(packages)} items, expected 2")
        return False

    # Test get_enrichment_stats
    stats_records = [
        {"status": "unclaimed", "count": 100},
        {"status": "claimed", "count": 20},
        {"status": "completed", "count": 80},
    ]
    mock_result.__iter__ = lambda self: iter(stats_records)
    mock_session.run.return_value = mock_result

    stats = claimer.get_enrichment_stats()
    if stats["total"] == 200 and stats["completion_percentage"] == 40.0:
        logger.info("✅ get_enrichment_stats() calculates correctly")
    else:
        logger.error(f"❌ get_enrichment_stats() incorrect: {stats}")
        return False

    # Test reset_abandoned_claims
    reset_result = MagicMock()
    reset_result.single.return_value = {"reset_count": 5}
    mock_session.run.return_value = reset_result

    count = claimer.reset_abandoned_claims(timeout_hours=2)
    if count == 5:
        logger.info("✅ reset_abandoned_claims() works correctly")
    else:
        logger.error(f"❌ reset_abandoned_claims() returned {count}, expected 5")
        return False

    return True


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("TESTING CLAIMING SYSTEM")
    logger.info("=" * 60)

    all_passed = True

    # Test 1: Imports
    if not test_imports():
        all_passed = False

    # Test 2: Package claiming
    if not test_package_claiming():
        all_passed = False

    # Test 3: Status transitions
    if not test_status_transitions():
        all_passed = False

    # Test 4: Monitoring functions
    if not test_monitoring_functions():
        all_passed = False

    # Summary
    logger.info("=" * 60)
    if all_passed:
        logger.info("✅ ALL TESTS PASSED - Claiming System is working correctly!")
        logger.info("✅ Atomic package claiming works")
        logger.info("✅ ALL Enumerations are claimed (not limited to 20)")
        logger.info("✅ Status transitions work correctly")
        logger.info("✅ Monitoring functions work correctly")
    else:
        logger.error("❌ SOME TESTS FAILED - Please review the output above")
    logger.info("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
