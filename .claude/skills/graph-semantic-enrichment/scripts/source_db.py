"""
SourceDB module - READ-ONLY access to Test Propagation database.

This module provides read-only operations for the SOURCE database,
ensuring data integrity and preventing accidental modifications.
"""

import logging
import os
from typing import Any
from typing import Literal

from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class SourceDB:
    """
    READ-ONLY access to Test Propagation database (SOURCE).

    CRITICAL: This database must remain immutable. All operations are
    strictly read-only to preserve the source data integrity.
    """

    def __init__(self):
        """Initialize connection to SOURCE database with READ-ONLY enforcement."""
        # Get credentials from environment
        self.uri = os.getenv("SOURCE_NEO4J_URI", "neo4j+s://025a2013.databases.neo4j.io")
        user = os.getenv("SOURCE_NEO4J_USER", "neo4j")
        password = os.getenv("SOURCE_NEO4J_PASSWORD")

        if not password:
            raise ValueError("SOURCE_NEO4J_PASSWORD environment variable not set")

        # Create driver with readonly flag for safety
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(user, password),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_acquisition_timeout=30,
            # Additional safety: default_access_mode ensures all sessions are READ by default
            default_access_mode="READ",
        )

        logger.info(f"Connected to SOURCE database (READ-ONLY): {self.uri}")

    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()
            logger.info("SOURCE database connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def _execute_read_query(self, query: str, parameters: dict | None = None) -> list[dict]:
        """
        Execute a read-only query on the SOURCE database.

        Args:
            query: Cypher query (must be read-only)
            parameters: Query parameters

        Returns:
            List of result dictionaries

        Raises:
            PermissionError: If query attempts to modify data
            Neo4jError: If query execution fails
        """
        # Safety check: Ensure query is read-only
        forbidden_keywords = ["CREATE", "DELETE", "SET", "REMOVE", "MERGE", "DETACH"]
        query_upper = query.upper()
        for keyword in forbidden_keywords:
            if keyword in query_upper:
                raise PermissionError(f"SOURCE database is READ-ONLY. Query contains forbidden keyword: {keyword}")

        try:
            with self.driver.session(default_access_mode="READ") as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        except Neo4jError as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def read_node(
        self, node_id: str, response_format: Literal["concise", "detailed"] = "concise"
    ) -> dict[str, Any] | None:
        """
        Read a node from the SOURCE database.

        Args:
            node_id: Node identifier (e.g., "M001", "E-00042")
            response_format:
                - "concise": Only essential properties (saves tokens)
                - "detailed": All properties + metadata

        Returns:
            Node data dictionary or None if not found
        """
        # Determine node type based on ID pattern
        if node_id.startswith("M"):
            label = "MetaAttribute"
        elif node_id.startswith("E-"):
            label = "Enumeration"
        elif node_id.startswith("H-"):
            label = "HelperNode"
        elif node_id.startswith("FT-"):
            label = "FreeTextValue"
        else:
            # Try GroupNode or Layer
            label = None

        if label:
            query = f"""
            MATCH (n:{label} {{id: $node_id}})
            RETURN n
            """
        else:
            # Generic search across all node types
            query = """
            MATCH (n {id: $node_id})
            RETURN n
            """

        results = self._execute_read_query(query, {"node_id": node_id})

        if not results:
            logger.warning(f"Node not found: {node_id}")
            return None

        node_data = dict(results[0]["n"])

        # Format response based on requested level
        if response_format == "concise":
            # Return only essential properties
            essential_props = ["id", "nameDe", "nameEn", "forMetaAttribute"]
            return {k: v for k, v in node_data.items() if k in essential_props or v is not None}
        # Return all properties
        return node_data

    def read_enumerations(self, meta_attribute_id: str, limit: int = 20) -> dict[str, Any]:
        """
        Read Enumerations for a MetaAttribute (PREVIEW ONLY, not for claiming).

        CRITICAL DISTINCTION:
        - THIS METHOD: Shows max 20 Enumerations (token-efficient preview for agent context)
        - CLAIMING METHOD: PackageClaimer.claim_packages() claims ALL Enumerations (no limit!)
        - WHY BOTH: Agents need preview to understand context, but claiming MUST be complete

        Args:
            meta_attribute_id: MetaAttribute identifier (e.g., "M001")
            limit: Max results for preview (default 20)

        Returns:
            Dictionary with enumerations list and truncation info
        """
        query = """
        MATCH (m:MetaAttribute {id: $meta_id})-[:HAS_ENUMERATION]->(e:Enumeration)
        RETURN e
        ORDER BY e.id
        LIMIT $limit
        """

        results = self._execute_read_query(
            query,
            {"meta_id": meta_attribute_id, "limit": limit + 1},  # Get one extra to check truncation
        )

        enumerations = [dict(r["e"]) for r in results[:limit]]
        truncated = len(results) > limit

        response = {"enumerations": enumerations, "truncated": truncated, "count": len(enumerations)}

        if truncated:
            response["message"] = (
                f"Showing first {limit} results. This is PREVIEW only. Package claiming includes ALL Enumerations."
            )

        return response

    def check_enrichment_needs(self, node_id: str) -> dict[str, Any]:
        """
        Analyze a node to determine what needs enrichment.

        Args:
            node_id: Node identifier

        Returns:
            Dictionary with enrichment analysis
        """
        node_data = self.read_node(node_id, response_format="detailed")

        if not node_data:
            return {"error": f"Node {node_id} not found"}

        needs_enrichment = []
        has_template_phrases = []

        # Check for TBD/N/A values
        for key, value in node_data.items():
            if value in ["TBD", "N/A", None, ""]:
                needs_enrichment.append(key)
            elif isinstance(value, str):
                # Check for template phrases
                template_indicators = [
                    "Ein fundamentaler Aspekt",
                    "Dies umfasst",
                    "Ein wichtiger Bestandteil",
                    "Zentrale Komponente",
                ]
                if any(phrase in value for phrase in template_indicators):
                    has_template_phrases.append(key)

        return {
            "node_id": node_id,
            "needs_enrichment": needs_enrichment,
            "has_template_phrases": has_template_phrases,
            "ready_for_enrichment": len(needs_enrichment) > 0 or len(has_template_phrases) > 0,
        }

    def get_relationships(self, node_id: str) -> dict[str, list[dict]]:
        """
        Get all relationships for a node.

        Args:
            node_id: Node identifier

        Returns:
            Dictionary with incoming and outgoing relationships
        """
        query = """
        MATCH (n {id: $node_id})
        OPTIONAL MATCH (n)-[r_out]->(target)
        OPTIONAL MATCH (source)-[r_in]->(n)
        RETURN
            collect(DISTINCT {
                type: type(r_out),
                target_id: target.id,
                properties: properties(r_out)
            }) as outgoing,
            collect(DISTINCT {
                type: type(r_in),
                source_id: source.id,
                properties: properties(r_in)
            }) as incoming
        """

        results = self._execute_read_query(query, {"node_id": node_id})

        if not results:
            return {"incoming": [], "outgoing": []}

        result = results[0]

        # Filter out null relationships
        outgoing = [r for r in result.get("outgoing", []) if r["type"] is not None]
        incoming = [r for r in result.get("incoming", []) if r["type"] is not None]

        return {"incoming": incoming, "outgoing": outgoing}

    def count_nodes_by_status(self) -> dict[str, int]:
        """
        Count nodes by enrichment_status (for progress tracking).

        Returns:
            Dictionary with status counts
        """
        query = """
        MATCH (n)
        WHERE n.enrichment_status IS NOT NULL
        RETURN n.enrichment_status as status, count(n) as count
        ORDER BY status
        """

        results = self._execute_read_query(query)

        status_counts = {r["status"]: r["count"] for r in results}

        # Add zero counts for missing statuses
        all_statuses = ["unclaimed", "claimed", "in_progress", "completed", "failed"]
        for status in all_statuses:
            if status not in status_counts:
                status_counts[status] = 0

        return status_counts

    # Safety method to prevent writes
    def write(self, *args, **kwargs):
        """
        Raises error - writes are not permitted on SOURCE database.

        Raises:
            PermissionError: Always (SOURCE is READ-ONLY)
        """
        raise PermissionError(
            "SOURCE database (Test Propagation) is READ-ONLY. No modifications allowed to preserve data integrity."
        )

    def create(self, *args, **kwargs):
        """Alias for write - raises PermissionError."""
        self.write()

    def update(self, *args, **kwargs):
        """Alias for write - raises PermissionError."""
        self.write()

    def delete(self, *args, **kwargs):
        """Alias for write - raises PermissionError."""
        self.write()
