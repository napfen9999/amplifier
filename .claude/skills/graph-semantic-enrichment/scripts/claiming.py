"""
Claiming System for atomic package-based work allocation.

CRITICAL Requirements:
1. Atomic claiming of MetaAttribute + ALL its children
2. Support for 8 parallel agents without conflicts
3. ALL Enumerations must be included (not limited to 20)
4. Thread-safe operations
5. Track agent ownership and timing

V3 Architecture:
- Package = MetaAttribute + ALL Enumerations (atomic unit)
- No partial claiming (all or nothing)
- Agent owns entire package during enrichment
"""

import logging

from models import EnumerationPackage
from models import FreeTextPackage

logger = logging.getLogger(__name__)


class PackageClaimer:
    """Manages atomic claiming of enrichment packages for parallel agents."""

    def __init__(self, db_client):
        """Initialize with database client.

        Args:
            db_client: TargetDB instance for database operations
        """
        self.db = db_client

    def claim_packages(self, agent_id: str, num_packages: int = 2) -> list:
        """Claim unclaimed packages atomically for an agent.

        CRITICAL: Claims ALL Enumerations for each MetaAttribute (no 20-item limit)

        Args:
            agent_id: Unique identifier for the agent claiming work
            num_packages: Number of packages to claim (default 2)

        Returns:
            List of claimed packages (EnumerationPackage or FreeTextPackage)
        """
        claimed = []

        with self.db.driver.session() as session:
            for _ in range(num_packages):
                package = self._claim_single_package(session, agent_id)
                if package:
                    claimed.append(package)
                else:
                    break  # No more unclaimed packages

        logger.info(f"Agent {agent_id} claimed {len(claimed)} packages")
        return claimed

    def _claim_single_package(self, session, agent_id: str) -> object | None:
        """Claim a single unclaimed package atomically.

        Args:
            session: Neo4j session for transaction
            agent_id: Agent claiming the package

        Returns:
            EnumerationPackage, FreeTextPackage, or None if nothing to claim
        """

        def claim_transaction(tx):
            """Transaction to atomically claim a package."""

            # Find first unclaimed MetaAttribute and claim it atomically
            # CRITICAL: This uses a single atomic operation to prevent race conditions
            # The WHERE clause in the SET ensures only truly unclaimed nodes are updated
            claim_query = """
            MATCH (m:MetaAttribute)
            WHERE m.enrichment_status = 'unclaimed'
            WITH m
            ORDER BY m.id  // Deterministic ordering to reduce contention
            LIMIT 1
            // Atomic check-and-set: only update if still unclaimed
            SET m.enrichment_status = CASE
                    WHEN m.enrichment_status = 'unclaimed' THEN 'claimed'
                    ELSE m.enrichment_status
                END,
                m.claimed_at = CASE
                    WHEN m.enrichment_status = 'unclaimed' THEN datetime()
                    ELSE m.claimed_at
                END,
                m.claimed_by = CASE
                    WHEN m.enrichment_status = 'unclaimed' THEN $agent_id
                    ELSE m.claimed_by
                END
            WITH m
            WHERE m.claimed_by = $agent_id  // Only return if we successfully claimed it
            RETURN m.id as meta_id,
                   m.attributeType as attribute_type,
                   m.claimed_at as claimed_at
            """

            result = tx.run(claim_query, agent_id=agent_id)
            record = result.single()

            if not record:
                return None  # No unclaimed MetaAttributes

            meta_id = record["meta_id"]
            attribute_type = record["attribute_type"]
            claimed_at = record["claimed_at"]

            # Get ALL associated child nodes based on type
            if attribute_type == "ENUMERATION":
                # Get ALL Enumerations (not limited to 20!)
                enum_query = """
                MATCH (m:MetaAttribute {id: $meta_id})-[:HAS_ENUMERATION]->(e:Enumeration)
                RETURN e.id as enum_id
                ORDER BY e.id
                """
                enum_result = tx.run(enum_query, meta_id=meta_id)
                enum_ids = [r["enum_id"] for r in enum_result]

                # Log if package is large
                if len(enum_ids) > 20:
                    logger.info(f"Large package: {meta_id} has {len(enum_ids)} Enumerations (ALL included)")

                return EnumerationPackage(
                    meta_id=meta_id,
                    type="enumeration",
                    claimed_at=claimed_at,
                    agent_id=agent_id,
                    enumeration_ids=enum_ids,
                )

            if attribute_type == "FREITEXT":
                # Get FreeTextValues and optional HelperNode
                freetext_query = """
                MATCH (m:MetaAttribute {id: $meta_id})-[:HAS_FREE_TEXT_VALUE]->(ft:FreeTextValue)
                OPTIONAL MATCH (ft)<-[:PROVIDES_GUIDANCE]-(h:HelperNode)
                RETURN ft.id as freetext_id, h.id as helper_id
                """
                freetext_result = tx.run(freetext_query, meta_id=meta_id)

                freetext_ids = []
                helper_id = None

                for record in freetext_result:
                    freetext_ids.append(record["freetext_id"])
                    if record["helper_id"]:
                        helper_id = record["helper_id"]

                return FreeTextPackage(
                    meta_id=meta_id,
                    type="freetext",
                    claimed_at=claimed_at,
                    agent_id=agent_id,
                    freetext_ids=freetext_ids,
                    helper_id=helper_id,
                )

            # Hybrid or unknown type - return just MetaAttribute
            logger.warning(f"Unknown attribute type '{attribute_type}' for {meta_id}")
            return EnumerationPackage(
                meta_id=meta_id, type="unknown", claimed_at=claimed_at, agent_id=agent_id, enumeration_ids=[]
            )

        # Execute transaction
        return session.execute_write(claim_transaction)

    def mark_completed(self, meta_id: str, agent_id: str) -> bool:
        """Mark a package as completed.

        Args:
            meta_id: MetaAttribute ID of the completed package
            agent_id: Agent that completed the work

        Returns:
            True if successfully marked, False otherwise
        """
        with self.db.driver.session() as session:
            query = """
            MATCH (m:MetaAttribute {id: $meta_id, claimed_by: $agent_id})
            WHERE m.enrichment_status = 'claimed'
               OR m.enrichment_status = 'in_progress'
            SET m.enrichment_status = 'completed',
                m.completed_at = datetime()
            RETURN m.id
            """
            result = session.run(query, meta_id=meta_id, agent_id=agent_id)
            return result.single() is not None

    def mark_failed(self, meta_id: str, agent_id: str, error_message: str) -> bool:
        """Mark a package as failed.

        Args:
            meta_id: MetaAttribute ID of the failed package
            agent_id: Agent that encountered the failure
            error_message: Description of what went wrong

        Returns:
            True if successfully marked, False otherwise
        """
        with self.db.driver.session() as session:
            query = """
            MATCH (m:MetaAttribute {id: $meta_id, claimed_by: $agent_id})
            WHERE m.enrichment_status = 'claimed'
               OR m.enrichment_status = 'in_progress'
            SET m.enrichment_status = 'failed',
                m.completed_at = datetime(),
                m.error_message = $error_message
            RETURN m.id
            """
            result = session.run(
                query,
                meta_id=meta_id,
                agent_id=agent_id,
                error_message=error_message[:500],  # Limit error message length
            )
            return result.single() is not None

    def update_progress(self, meta_id: str, agent_id: str) -> bool:
        """Update package status to in_progress.

        Args:
            meta_id: MetaAttribute ID being worked on
            agent_id: Agent doing the work

        Returns:
            True if successfully updated, False otherwise
        """
        with self.db.driver.session() as session:
            query = """
            MATCH (m:MetaAttribute {id: $meta_id, claimed_by: $agent_id})
            WHERE m.enrichment_status = 'claimed'
            SET m.enrichment_status = 'in_progress'
            RETURN m.id
            """
            result = session.run(query, meta_id=meta_id, agent_id=agent_id)
            return result.single() is not None

    def get_agent_packages(self, agent_id: str) -> list:
        """Get all packages currently owned by an agent.

        Args:
            agent_id: Agent to query

        Returns:
            List of MetaAttribute IDs owned by the agent
        """
        with self.db.driver.session() as session:
            query = """
            MATCH (m:MetaAttribute {claimed_by: $agent_id})
            WHERE m.enrichment_status IN ['claimed', 'in_progress']
            RETURN m.id as meta_id, m.enrichment_status as status
            ORDER BY m.claimed_at
            """
            result = session.run(query, agent_id=agent_id)
            return [dict(r) for r in result]

    def get_enrichment_stats(self) -> dict:
        """Get overall enrichment statistics.

        Returns:
            Dictionary with counts by status
        """
        with self.db.driver.session() as session:
            query = """
            MATCH (m:MetaAttribute)
            RETURN m.enrichment_status as status, count(m) as count
            ORDER BY status
            """
            result = session.run(query)

            stats = {}
            for record in result:
                stats[record["status"]] = record["count"]

            # Calculate completion percentage
            total = sum(stats.values())
            completed = stats.get("completed", 0)
            stats["completion_percentage"] = (completed / total * 100) if total > 0 else 0
            stats["total"] = total

            return stats

    def reset_abandoned_claims(self, timeout_hours: int = 2) -> int:
        """Reset claims that have been abandoned (no progress for N hours).

        Args:
            timeout_hours: Hours after which to consider a claim abandoned

        Returns:
            Number of claims reset
        """
        with self.db.driver.session() as session:
            query = """
            MATCH (m:MetaAttribute)
            WHERE m.enrichment_status IN ['claimed', 'in_progress']
              AND m.claimed_at < datetime() - duration({hours: $timeout_hours})
            SET m.enrichment_status = 'unclaimed',
                m.claimed_at = null,
                m.claimed_by = null,
                m.error_message = 'Claim timeout - reset for retry'
            RETURN count(m) as reset_count
            """
            result = session.run(query, timeout_hours=timeout_hours)
            count = result.single()["reset_count"]

            if count > 0:
                logger.info(f"Reset {count} abandoned claims (>{timeout_hours}h old)")

            return count
