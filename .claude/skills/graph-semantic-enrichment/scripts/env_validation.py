"""
Environment variable validation module.

Ensures all required environment variables are set and valid before
application startup to prevent runtime failures.
"""

import logging
import os
import sys

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class EnvironmentValidator:
    """Validates required environment variables for the application."""

    # Required environment variables with descriptions
    REQUIRED_VARS = {
        # SOURCE database (Test_Propagation - READ ONLY)
        "SOURCE_NEO4J_URI": "URI for SOURCE database (Test_Propagation)",
        "SOURCE_NEO4J_USER": "Username for SOURCE database",
        "SOURCE_NEO4J_PASSWORD": "Password for SOURCE database",
        # TARGET database (Graph_Rebuild_2025_11 - WRITE ONLY)
        "TARGET_NEO4J_URI": "URI for TARGET database (Graph_Rebuild_2025_11)",
        "TARGET_NEO4J_USER": "Username for TARGET database",
        "TARGET_NEO4J_PASSWORD": "Password for TARGET database",
    }

    # Optional environment variables with defaults
    OPTIONAL_VARS = {
        "LOG_LEVEL": ("INFO", "Logging level (DEBUG, INFO, WARNING, ERROR)"),
        "MAX_PARALLEL_AGENTS": ("8", "Maximum number of parallel agents"),
        "BATCH_SIZE": ("25", "Number of items per batch"),
    }

    @classmethod
    def validate(cls, exit_on_error: bool = True) -> tuple[bool, list[str]]:
        """
        Validate all required environment variables are set.

        Args:
            exit_on_error: If True, exit the program on validation failure

        Returns:
            Tuple of (success: bool, errors: List[str])
        """
        # Load .env file if it exists
        load_dotenv()

        errors = []

        # Check required variables
        for var_name, description in cls.REQUIRED_VARS.items():
            value = os.getenv(var_name)
            if not value:
                errors.append(f"Missing required: {var_name} - {description}")
            else:
                # Validate format for specific variables
                if "URI" in var_name and not cls._validate_uri(value):
                    errors.append(f"Invalid URI format for {var_name}: {value}")

        # Set defaults for optional variables
        for var_name, (default, description) in cls.OPTIONAL_VARS.items():
            if not os.getenv(var_name):
                os.environ[var_name] = default
                logger.debug(f"Set default for {var_name}: {default}")

        # Report results
        if errors:
            logger.error("Environment validation failed:")
            for error in errors:
                logger.error(f"  • {error}")

            if exit_on_error:
                sys.exit(1)

            return False, errors
        logger.info("✅ Environment validation successful")
        cls._log_configuration()
        return True, []

    @staticmethod
    def _validate_uri(uri: str) -> bool:
        """Validate Neo4j URI format."""
        valid_prefixes = ["neo4j://", "neo4j+s://", "neo4j+ssc://", "bolt://", "bolt+s://"]
        return any(uri.startswith(prefix) for prefix in valid_prefixes)

    @classmethod
    def _log_configuration(cls):
        """Log the current configuration (with passwords masked)."""
        logger.debug("Current configuration:")

        # Log required vars (mask passwords)
        for var_name in cls.REQUIRED_VARS:
            value = os.getenv(var_name)
            if "PASSWORD" in var_name:
                display_value = "***" if value else "NOT SET"
            else:
                display_value = value or "NOT SET"
            logger.debug(f"  {var_name}: {display_value}")

        # Log optional vars
        for var_name in cls.OPTIONAL_VARS:
            value = os.getenv(var_name)
            logger.debug(f"  {var_name}: {value}")

    @classmethod
    def check_database_connectivity(cls) -> bool:
        """
        Test connections to both SOURCE and TARGET databases.

        Returns:
            True if both connections succeed, False otherwise
        """
        from neo4j import GraphDatabase
        from neo4j.exceptions import Neo4jError

        success = True

        # Test SOURCE connection
        try:
            source_driver = GraphDatabase.driver(
                os.getenv("SOURCE_NEO4J_URI"),
                auth=(os.getenv("SOURCE_NEO4J_USER"), os.getenv("SOURCE_NEO4J_PASSWORD")),
                default_access_mode="READ",
            )
            with source_driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as count LIMIT 1")
                count = result.single()["count"]
                logger.info(f"✅ SOURCE database connected (nodes: {count})")
            source_driver.close()
        except Neo4jError as e:
            logger.error(f"❌ SOURCE database connection failed: {e}")
            success = False

        # Test TARGET connection
        try:
            target_driver = GraphDatabase.driver(
                os.getenv("TARGET_NEO4J_URI"),
                auth=(os.getenv("TARGET_NEO4J_USER"), os.getenv("TARGET_NEO4J_PASSWORD")),
            )
            with target_driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as count LIMIT 1")
                count = result.single()["count"]
                logger.info(f"✅ TARGET database connected (nodes: {count})")
            target_driver.close()
        except Neo4jError as e:
            logger.error(f"❌ TARGET database connection failed: {e}")
            success = False

        return success


def validate_environment():
    """Convenience function to validate environment on import."""
    return EnvironmentValidator.validate(exit_on_error=False)


if __name__ == "__main__":
    # When run directly, validate and test connections
    logging.basicConfig(level=logging.DEBUG)

    success, errors = EnvironmentValidator.validate(exit_on_error=False)

    if success:
        print("\n🔗 Testing database connections...")
        if EnvironmentValidator.check_database_connectivity():
            print("\n✅ All systems operational!")
        else:
            print("\n⚠️ Database connectivity issues detected")
            sys.exit(1)
    else:
        print("\n❌ Environment validation failed")
        sys.exit(1)
