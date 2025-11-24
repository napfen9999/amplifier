#!/usr/bin/env python3
"""
CLI Tools for Graph Semantic Enrichment System.

Provides command-line interfaces for:
- Status monitoring
- Manual enrichment operations
- Data validation
- Progress tracking
- System health checks
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from claiming import PackageClaimer
from models import EnumerationV3
from models import MetaAttributeV3
from source_db import SourceDB
from target_db import TargetDB
from validation import validate_enumeration
from validation import validate_metaattribute

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def status_command(args):
    """Show enrichment status and statistics."""
    logger.info("Fetching enrichment status...")

    try:
        target_db = TargetDB()
        claimer = PackageClaimer(target_db)

        stats = claimer.get_enrichment_stats()

        print("\n" + "=" * 60)
        print("📊 ENRICHMENT STATUS")
        print("=" * 60)

        print(f"\nTotal MetaAttributes: {stats['total']}")
        print(f"Completion: {stats['completion_percentage']:.1f}%")
        print("\nBreakdown by status:")

        for status in ["unclaimed", "claimed", "in_progress", "completed", "failed"]:
            count = stats.get(status, 0)
            percentage = (count / stats["total"] * 100) if stats["total"] > 0 else 0

            # Status emoji
            emoji = {"unclaimed": "⬜", "claimed": "🟨", "in_progress": "🟦", "completed": "✅", "failed": "❌"}.get(
                status, "❓"
            )

            bar = "█" * int(percentage / 2)
            print(f"  {emoji} {status:12s}: {count:4d} ({percentage:5.1f}%) {bar}")

        print("=" * 60)

        target_db.close()

    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        return 1

    return 0


def validate_command(args):
    """Validate a specific MetaAttribute or Enumeration."""
    logger.info(f"Validating {args.type} with ID {args.id}...")

    try:
        source_db = SourceDB()

        if args.type == "meta":
            # Fetch MetaAttribute from source
            query = """
            MATCH (m:MetaAttribute {id: $id})
            RETURN m
            """
            result = source_db._execute_read_query(query, id=args.id)

            if not result:
                logger.error(f"MetaAttribute {args.id} not found")
                return 1

            node = result[0]["m"]

            # Create model instance
            meta = MetaAttributeV3(
                id=node.get("id"),
                nameDe=node.get("nameDe", "Unknown"),
                nameEn=node.get("nameEn", "Unknown"),
                definitionDe=node.get("definitionDe", "N/A" * 100),
                definitionEn=node.get("definitionEn", "N/A" * 100),
                whatItIsDe=node.get("whatItIsDe", ["N/A"] * 3),
                whatItIsEn=node.get("whatItIsEn", ["N/A"] * 3),
                whatItIsNotDe=node.get("whatItIsNotDe", ["N/A"] * 2),
                whatItIsNotEn=node.get("whatItIsNotEn", ["N/A"] * 2),
                brandingRelevanceDe=node.get("brandingRelevanceDe", "N/A" * 50),
                brandingRelevanceEn=node.get("brandingRelevanceEn", "N/A" * 50),
                attributeType=node.get("attributeType", "ENUMERATION"),
                xPosition=node.get("xPosition", 0.0),
                yPosition=node.get("yPosition", 0.0),
            )

            # Validate
            result = validate_metaattribute(meta)

        elif args.type == "enum":
            # Fetch Enumeration from source
            query = """
            MATCH (e:Enumeration {id: $id})
            RETURN e
            """
            result = source_db._execute_read_query(query, id=args.id)

            if not result:
                logger.error(f"Enumeration {args.id} not found")
                return 1

            node = result[0]["e"]

            # Create model instance
            enum = EnumerationV3(
                id=node.get("id"),
                forMetaAttribute=node.get("forMetaAttribute", "M999"),
                nameDe=node.get("nameDe", "Unknown"),
                nameEn=node.get("nameEn", "Unknown"),
                whatItIsDe=node.get("whatItIsDe", "N/A" * 10),
                whatItIsEn=node.get("whatItIsEn", "N/A" * 10),
                whatItIsNotDe=node.get("whatItIsNotDe", "N/A" * 10),
                whatItIsNotEn=node.get("whatItIsNotEn", "N/A" * 10),
                examplesDe=node.get("examplesDe", ["N/A"]),
                examplesEn=node.get("examplesEn", ["N/A"]),
                xPosition=node.get("xPosition", 0.0),
                yPosition=node.get("yPosition", 0.0),
            )

            # Validate
            result = validate_enumeration(enum)

        else:
            logger.error(f"Unknown type: {args.type}")
            return 1

        # Display results
        print("\n" + "=" * 60)
        print(f"🔍 VALIDATION RESULTS for {args.type} {args.id}")
        print("=" * 60)

        if result.valid:
            print("\n✅ VALID - All checks passed!")
        else:
            print("\n❌ INVALID - Issues found:")

            if result.tier1_violations:
                print("\n📋 Tier 1 (Structural) Violations:")
                for v in result.tier1_violations:
                    print(f"  • {v}")

            if result.tier2_violations:
                print("\n📝 Tier 2 (Semantic) Violations:")
                for v in result.tier2_violations:
                    print(f"  • {v}")

            if result.template_phrases_found:
                print("\n⚠️ Template Phrases Detected:")
                for p in result.template_phrases_found:
                    print(f"  • {p}")

            if result.suggestions:
                print("\n💡 Suggestions:")
                for s in result.suggestions:
                    print(f"  • {s}")

        print("=" * 60)

        source_db.close()

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 1

    return 0


def claim_command(args):
    """Manually claim packages for an agent."""
    logger.info(f"Claiming {args.num} packages for agent {args.agent}...")

    try:
        target_db = TargetDB()
        claimer = PackageClaimer(target_db)

        packages = claimer.claim_packages(args.agent, args.num)

        print("\n" + "=" * 60)
        print(f"📦 CLAIMED PACKAGES for {args.agent}")
        print("=" * 60)

        if packages:
            for pkg in packages:
                print(f"\n📋 Package: {pkg.meta_id}")
                print(f"   Type: {pkg.type}")
                print(f"   Claimed at: {pkg.claimed_at}")

                if hasattr(pkg, "enumeration_ids"):
                    count = len(pkg.enumeration_ids)
                    print(f"   Enumerations: {count}")
                    if count > 20:
                        print(f"   ⚠️ Large package with {count} items (ALL included)")

                if hasattr(pkg, "freetext_ids"):
                    print(f"   FreeText Values: {len(pkg.freetext_ids)}")

                if hasattr(pkg, "helper_id") and pkg.helper_id:
                    print(f"   Helper Node: {pkg.helper_id}")
        else:
            print("\n⚠️ No unclaimed packages available")

        print("=" * 60)

        target_db.close()

    except Exception as e:
        logger.error(f"Claiming failed: {e}")
        return 1

    return 0


def reset_command(args):
    """Reset abandoned claims."""
    logger.info(f"Resetting claims older than {args.hours} hours...")

    try:
        target_db = TargetDB()
        claimer = PackageClaimer(target_db)

        count = claimer.reset_abandoned_claims(timeout_hours=args.hours)

        print("\n" + "=" * 60)
        print("🔄 RESET ABANDONED CLAIMS")
        print("=" * 60)

        if count > 0:
            print(f"\n✅ Reset {count} abandoned claims")
            print(f"   (Claims older than {args.hours} hours)")
        else:
            print("\n✓ No abandoned claims to reset")

        print("=" * 60)

        target_db.close()

    except Exception as e:
        logger.error(f"Reset failed: {e}")
        return 1

    return 0


def agent_status_command(args):
    """Show status for a specific agent."""
    logger.info(f"Getting status for agent {args.agent}...")

    try:
        target_db = TargetDB()
        claimer = PackageClaimer(target_db)

        packages = claimer.get_agent_packages(args.agent)

        print("\n" + "=" * 60)
        print(f"🤖 AGENT STATUS: {args.agent}")
        print("=" * 60)

        if packages:
            print(f"\nActive packages: {len(packages)}")
            print("\nPackage details:")

            for pkg in packages:
                status_emoji = "🟨" if pkg["status"] == "claimed" else "🟦"
                print(f"  {status_emoji} {pkg['meta_id']:10s} - {pkg['status']}")
        else:
            print("\n✓ No active packages for this agent")

        print("=" * 60)

        target_db.close()

    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        return 1

    return 0


def health_command(args):
    """Check system health and connectivity."""
    logger.info("Checking system health...")

    print("\n" + "=" * 60)
    print("🏥 SYSTEM HEALTH CHECK")
    print("=" * 60)

    health_status = []

    # Check SOURCE database
    try:
        source_db = SourceDB()
        query = "MATCH (n) RETURN count(n) as count LIMIT 1"
        result = source_db._execute_read_query(query)
        source_db.close()
        health_status.append(("SOURCE Database", "✅ Connected", True))
    except Exception as e:
        health_status.append(("SOURCE Database", f"❌ {str(e)[:50]}", False))

    # Check TARGET database
    try:
        target_db = TargetDB()
        with target_db.driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()
        target_db.close()
        health_status.append(("TARGET Database", "✅ Connected", True))
    except Exception as e:
        health_status.append(("TARGET Database", f"❌ {str(e)[:50]}", False))

    # Check environment variables
    env_vars = {
        "SOURCE_NEO4J_URI": os.environ.get("SOURCE_NEO4J_URI"),
        "SOURCE_NEO4J_USER": os.environ.get("SOURCE_NEO4J_USER"),
        "SOURCE_NEO4J_PASSWORD": "***" if os.environ.get("SOURCE_NEO4J_PASSWORD") else None,
        "TARGET_NEO4J_URI": os.environ.get("TARGET_NEO4J_URI"),
        "TARGET_NEO4J_USER": os.environ.get("TARGET_NEO4J_USER"),
        "TARGET_NEO4J_PASSWORD": "***" if os.environ.get("TARGET_NEO4J_PASSWORD") else None,
    }

    env_ok = all(v is not None for v in env_vars.values())
    status = "✅ All set" if env_ok else "⚠️ Some missing"
    health_status.append(("Environment Variables", status, env_ok))

    # Display results
    print("\nComponent Status:")
    for component, status, ok in health_status:
        print(f"  {component:20s}: {status}")

    if not env_ok:
        print("\nEnvironment Variables:")
        for var, value in env_vars.items():
            status = "✅" if value else "❌"
            display_value = value if value else "NOT SET"
            print(f"  {status} {var:25s}: {display_value}")

    # Overall status
    all_ok = all(ok for _, _, ok in health_status)
    print("\nOverall Status: " + ("✅ HEALTHY" if all_ok else "⚠️ ISSUES DETECTED"))

    print("=" * 60)

    return 0 if all_ok else 1


def main():
    """Main entry point for CLI tools."""
    parser = argparse.ArgumentParser(
        description="Graph Semantic Enrichment CLI Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools.py status                  # Show enrichment status
  python tools.py validate meta M001      # Validate a MetaAttribute
  python tools.py claim -a Agent_A1 -n 2  # Claim 2 packages
  python tools.py reset --hours 4         # Reset claims older than 4 hours
  python tools.py agent -a Agent_A1       # Show agent status
  python tools.py health                  # Check system health
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    subparsers.add_parser("status", help="Show enrichment status")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a node")
    validate_parser.add_argument("type", choices=["meta", "enum"], help="Node type")
    validate_parser.add_argument("id", help="Node ID to validate")

    # Claim command
    claim_parser = subparsers.add_parser("claim", help="Manually claim packages")
    claim_parser.add_argument("-a", "--agent", required=True, help="Agent ID")
    claim_parser.add_argument("-n", "--num", type=int, default=2, help="Number of packages")

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset abandoned claims")
    reset_parser.add_argument("--hours", type=int, default=2, help="Timeout in hours")

    # Agent status command
    agent_parser = subparsers.add_parser("agent", help="Show agent status")
    agent_parser.add_argument("-a", "--agent", required=True, help="Agent ID")

    # Health check command
    subparsers.add_parser("health", help="Check system health")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Route to appropriate command
    commands = {
        "status": status_command,
        "validate": validate_command,
        "claim": claim_command,
        "reset": reset_command,
        "agent": agent_status_command,
        "health": health_command,
    }

    command_func = commands.get(args.command)
    if command_func:
        return command_func(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
