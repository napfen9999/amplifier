"""
TargetDB module - WRITE-ONLY access to Graph Rebuild 202511 database.

This module provides write operations for the TARGET database,
including validation, enrichment, and status tracking.
"""

import logging
import os
from typing import Any

from dotenv import load_dotenv
from models import EnrichmentStatus
from models import EnumerationV3
from models import MetaAttributeV3
from models import ValidationResult
from neo4j import GraphDatabase
from neo4j import Transaction
from neo4j.exceptions import Neo4jError
from validation import validate_enumeration
from validation import validate_metaattribute

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class TargetDB:
    """
    WRITE-ONLY access to Graph Rebuild 202511 database (TARGET).

    This database receives validated, enriched nodes from the migration.
    Pre-write validation ensures data quality before committing.
    """

    def __init__(self):
        """Initialize connection to TARGET database."""
        # Get credentials from environment
        self.uri = os.getenv("TARGET_NEO4J_URI")
        user = os.getenv("TARGET_NEO4J_USER", "neo4j")
        password = os.getenv("TARGET_NEO4J_PASSWORD")

        if not self.uri:
            raise ValueError("TARGET_NEO4J_URI environment variable not set")
        if not password:
            raise ValueError("TARGET_NEO4J_PASSWORD environment variable not set")

        # Create driver for write operations
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(user, password),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_acquisition_timeout=30,
        )

        logger.info(f"Connected to TARGET database (WRITE-ONLY): {self.uri}")

    def close(self):
        """Close the database connection."""
        if self.driver:
            self.driver.close()
            logger.info("TARGET database connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def _execute_write_transaction(self, tx_func, **kwargs):
        """
        Execute a write transaction on the TARGET database.

        Args:
            tx_func: Transaction function to execute
            **kwargs: Arguments to pass to transaction function

        Returns:
            Transaction result

        Raises:
            Neo4jError: If transaction fails
        """
        try:
            with self.driver.session() as session:
                return session.execute_write(tx_func, **kwargs)
        except Neo4jError as e:
            logger.error(f"Write transaction failed: {e}")
            raise

    def enrich_metaattribute(
        self,
        source_id: str,
        enriched_properties: dict[str, Any],
        layer_id: str,
        group_id: str,
        assignment_reasoning: str,
        grouping_reasoning: str,
    ) -> dict[str, Any]:
        """
        Create enriched MetaAttribute in TARGET with relationships.

        Safety: Validates properties BEFORE writing.
        Atomicity: Node + relationships in single transaction.
        Traceability: Stores source_id for audit trail.

        Args:
            source_id: Original ID from SOURCE database
            enriched_properties: Enriched semantic properties
            layer_id: Layer assignment (foundation/strategy/identity/expression)
            group_id: GroupNode assignment
            assignment_reasoning: Why assigned to this layer (200-600 chars)
            grouping_reasoning: Why grouped here (200-600 chars)

        Returns:
            Dictionary with target_id and status

        Raises:
            ValidationError: If properties fail validation
            Neo4jError: If database write fails
        """
        # Create Pydantic model for validation
        try:
            meta_attr = MetaAttributeV3(
                id=source_id,  # Will be updated if translation needed
                **enriched_properties,
                enrichment_status=EnrichmentStatus.COMPLETED,
            )
        except Exception as e:
            return {"status": "error", "message": f"Property validation failed: {str(e)}", "source_id": source_id}

        # Run semantic validation
        validation_result = validate_metaattribute(meta_attr)
        if not validation_result.overall_passed:
            return {
                "status": "error",
                "message": "Semantic validation failed",
                "violations": validation_result.tier1_violations + validation_result.tier2_violations,
                "source_id": source_id,
            }

        # Transaction function for atomic write
        def create_metaattribute_tx(tx: Transaction, **params):
            # Create MetaAttribute node
            create_node_query = """
            CREATE (m:MetaAttribute {
                id: $target_id,
                source_id: $source_id,
                nameDe: $nameDe,
                nameEn: $nameEn,
                definitionDe: $definitionDe,
                definitionEn: $definitionEn,
                whatItIsDe: $whatItIsDe,
                whatItIsEn: $whatItIsEn,
                whatItIsNotDe: $whatItIsNotDe,
                whatItIsNotEn: $whatItIsNotEn,
                examplesDe: $examplesDe,
                examplesEn: $examplesEn,
                brandingRelevanceDe: $brandingRelevanceDe,
                brandingRelevanceEn: $brandingRelevanceEn,
                enrichment_status: $enrichment_status,
                completed_at: datetime(),
                scope: $scope,
                attributeType: $attributeType
            })
            RETURN m.id as target_id
            """

            # Determine target_id (may differ from source_id if translation needed)
            target_id = params.get("target_id", params["source_id"])

            node_result = tx.run(
                create_node_query,
                {
                    "target_id": target_id,
                    "source_id": params["source_id"],
                    "nameDe": params["nameDe"],
                    "nameEn": params["nameEn"],
                    "definitionDe": params["definitionDe"],
                    "definitionEn": params["definitionEn"],
                    "whatItIsDe": params["whatItIsDe"],
                    "whatItIsEn": params["whatItIsEn"],
                    "whatItIsNotDe": params["whatItIsNotDe"],
                    "whatItIsNotEn": params["whatItIsNotEn"],
                    "examplesDe": params.get("examplesDe"),
                    "examplesEn": params.get("examplesEn"),
                    "brandingRelevanceDe": params.get("brandingRelevanceDe"),
                    "brandingRelevanceEn": params.get("brandingRelevanceEn"),
                    "enrichment_status": EnrichmentStatus.COMPLETED.value,
                    "scope": params.get("scope", "primary_scope"),
                    "attributeType": params.get("attributeType", "single_choice"),
                },
            ).single()

            created_id = node_result["target_id"]

            # Create HAS_ATTRIBUTE relationship to Layer
            layer_rel_query = """
            MATCH (l:Layer {id: $layer_id})
            MATCH (m:MetaAttribute {id: $target_id})
            CREATE (l)-[:HAS_ATTRIBUTE {assignmentReasoning: $reasoning}]->(m)
            """
            tx.run(
                layer_rel_query,
                {"layer_id": params["layer_id"], "target_id": created_id, "reasoning": params["assignment_reasoning"]},
            )

            # Create BELONGS_TO_GROUP relationship to GroupNode
            group_rel_query = """
            MATCH (g:GroupNode {id: $group_id})
            MATCH (m:MetaAttribute {id: $target_id})
            CREATE (m)-[:BELONGS_TO_GROUP {groupingReasoning: $reasoning}]->(g)
            """
            tx.run(
                group_rel_query,
                {"group_id": params["group_id"], "target_id": created_id, "reasoning": params["grouping_reasoning"]},
            )

            # Create IDMapping for traceability
            mapping_query = """
            CREATE (map:IDMapping {
                sourceId: $source_id,
                targetId: $target_id,
                nodeType: 'MetaAttribute',
                mappedAt: datetime()
            })
            """
            tx.run(mapping_query, {"source_id": params["source_id"], "target_id": created_id})

            return created_id

        # Execute transaction
        try:
            target_id = self._execute_write_transaction(
                create_metaattribute_tx,
                source_id=source_id,
                target_id=source_id,  # Default to same ID unless translation needed
                nameDe=meta_attr.nameDe,
                nameEn=meta_attr.nameEn,
                definitionDe=meta_attr.definitionDe,
                definitionEn=meta_attr.definitionEn,
                whatItIsDe=meta_attr.whatItIsDe,
                whatItIsEn=meta_attr.whatItIsEn,
                whatItIsNotDe=meta_attr.whatItIsNotDe,
                whatItIsNotEn=meta_attr.whatItIsNotEn,
                examplesDe=enriched_properties.get("examplesDe"),
                examplesEn=enriched_properties.get("examplesEn"),
                brandingRelevanceDe=meta_attr.brandingRelevanceDe,
                brandingRelevanceEn=meta_attr.brandingRelevanceEn,
                scope=enriched_properties.get("scope", "primary_scope"),
                attributeType=enriched_properties.get("attributeType", "single_choice"),
                layer_id=layer_id,
                group_id=group_id,
                assignment_reasoning=assignment_reasoning,
                grouping_reasoning=grouping_reasoning,
            )

            logger.info(f"Successfully created MetaAttribute: {target_id}")
            return {
                "status": "success",
                "target_id": target_id,
                "source_id": source_id,
                "message": f"MetaAttribute {target_id} created successfully",
            }

        except Neo4jError as e:
            logger.error(f"Failed to create MetaAttribute: {e}")
            return {"status": "error", "message": f"Database write failed: {str(e)}", "source_id": source_id}

    def enrich_enumeration(
        self, source_id: str, meta_attribute_id: str, enriched_properties: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create enriched Enumeration in TARGET.

        Args:
            source_id: Original ID from SOURCE database
            meta_attribute_id: Parent MetaAttribute ID
            enriched_properties: Enriched semantic properties

        Returns:
            Dictionary with target_id and status
        """
        # Create Pydantic model for validation
        try:
            enumeration = EnumerationV3(id=source_id, forMetaAttribute=meta_attribute_id, **enriched_properties)
        except Exception as e:
            return {"status": "error", "message": f"Property validation failed: {str(e)}", "source_id": source_id}

        # Run semantic validation
        validation_result = validate_enumeration(enumeration)
        if not validation_result.overall_passed:
            return {
                "status": "error",
                "message": "Semantic validation failed",
                "violations": validation_result.tier1_violations + validation_result.tier2_violations,
                "source_id": source_id,
            }

        # Transaction function for atomic write
        def create_enumeration_tx(tx: Transaction, **params):
            # Create Enumeration node
            create_query = """
            CREATE (e:Enumeration {
                id: $target_id,
                source_id: $source_id,
                forMetaAttribute: $meta_id,
                nameDe: $nameDe,
                nameEn: $nameEn,
                whatItIsDe: $whatItIsDe,
                whatItIsEn: $whatItIsEn,
                whatItIsNotDe: $whatItIsNotDe,
                whatItIsNotEn: $whatItIsNotEn,
                examplesDe: $examplesDe,
                examplesEn: $examplesEn
            })
            RETURN e.id as target_id
            """

            result = tx.run(
                create_query,
                {
                    "target_id": params["target_id"],
                    "source_id": params["source_id"],
                    "meta_id": params["meta_attribute_id"],
                    "nameDe": params["nameDe"],
                    "nameEn": params["nameEn"],
                    "whatItIsDe": params["whatItIsDe"],
                    "whatItIsEn": params["whatItIsEn"],
                    "whatItIsNotDe": params["whatItIsNotDe"],
                    "whatItIsNotEn": params["whatItIsNotEn"],
                    "examplesDe": params.get("examplesDe"),
                    "examplesEn": params.get("examplesEn"),
                },
            ).single()

            created_id = result["target_id"]

            # Create HAS_ENUMERATION relationship
            rel_query = """
            MATCH (m:MetaAttribute {id: $meta_id})
            MATCH (e:Enumeration {id: $enum_id})
            CREATE (m)-[:HAS_ENUMERATION]->(e)
            """
            tx.run(rel_query, {"meta_id": params["meta_attribute_id"], "enum_id": created_id})

            # Create IDMapping
            mapping_query = """
            CREATE (map:IDMapping {
                sourceId: $source_id,
                targetId: $target_id,
                nodeType: 'Enumeration',
                mappedAt: datetime()
            })
            """
            tx.run(mapping_query, {"source_id": params["source_id"], "target_id": created_id})

            return created_id

        # Execute transaction
        try:
            target_id = self._execute_write_transaction(
                create_enumeration_tx,
                source_id=source_id,
                target_id=source_id,  # Default to same ID
                meta_attribute_id=meta_attribute_id,
                nameDe=enumeration.nameDe,
                nameEn=enumeration.nameEn,
                whatItIsDe=enumeration.whatItIsDe,
                whatItIsEn=enumeration.whatItIsEn,
                whatItIsNotDe=enumeration.whatItIsNotDe,
                whatItIsNotEn=enumeration.whatItIsNotEn,
                examplesDe=enumeration.examplesDe,
                examplesEn=enumeration.examplesEn,
            )

            logger.info(f"Successfully created Enumeration: {target_id}")
            return {
                "status": "success",
                "target_id": target_id,
                "source_id": source_id,
                "message": f"Enumeration {target_id} created successfully",
            }

        except Neo4jError as e:
            logger.error(f"Failed to create Enumeration: {e}")
            return {"status": "error", "message": f"Database write failed: {str(e)}", "source_id": source_id}

    def validate_node(self, target_id: str) -> ValidationResult:
        """
        Validate an enriched node AFTER it has been written.

        Post-write validation for semantic quality checks.

        Args:
            target_id: Node ID in TARGET database

        Returns:
            ValidationResult with detailed feedback
        """
        # Query the node from TARGET
        query = """
        MATCH (n {id: $target_id})
        RETURN n, labels(n) as labels
        """

        try:
            with self.driver.session() as session:
                result = session.run(query, {"target_id": target_id}).single()

                if not result:
                    return ValidationResult(
                        valid=False,
                        tier1_passed=False,
                        tier2_passed=True,
                        tier1_violations=["Node not found in TARGET database"],
                        tier2_violations=[],
                    )

                node_data = dict(result["n"])
                labels = result["labels"]

                # Determine node type and validate accordingly
                if "MetaAttribute" in labels:
                    meta_attr = MetaAttributeV3(**node_data)
                    return validate_metaattribute(meta_attr)
                if "Enumeration" in labels:
                    enumeration = EnumerationV3(**node_data)
                    return validate_enumeration(enumeration)
                return ValidationResult(
                    valid=False,
                    tier1_passed=False,
                    tier2_passed=True,
                    tier1_violations=[f"Unknown node type: {labels}"],
                    tier2_violations=[],
                )

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return ValidationResult(
                valid=False,
                tier1_passed=False,
                tier2_passed=True,
                tier1_violations=[f"Validation error: {str(e)}"],
                tier2_violations=[],
            )

    def mark_completed(
        self, target_id: str, enrichment_status: EnrichmentStatus = EnrichmentStatus.COMPLETED
    ) -> dict[str, Any]:
        """
        Mark a node as completed in TARGET database.

        Args:
            target_id: Node ID in TARGET
            enrichment_status: Status to set (default COMPLETED)

        Returns:
            Status dictionary
        """
        query = """
        MATCH (n {id: $target_id})
        SET n.enrichment_status = $status,
            n.completed_at = datetime()
        RETURN n.id as id
        """

        try:
            with self.driver.session() as session:
                result = session.run(query, {"target_id": target_id, "status": enrichment_status.value}).single()

                if result:
                    logger.info(f"Marked {target_id} as {enrichment_status.value}")
                    return {"status": "success", "target_id": target_id, "enrichment_status": enrichment_status.value}
                return {"status": "error", "message": f"Node {target_id} not found"}

        except Neo4jError as e:
            logger.error(f"Failed to mark completed: {e}")
            return {"status": "error", "message": f"Database update failed: {str(e)}"}

    def mark_failed(self, target_id: str, error_message: str) -> dict[str, Any]:
        """
        Mark a node as failed with error details.

        Args:
            target_id: Node ID in TARGET
            error_message: Error description

        Returns:
            Status dictionary
        """
        query = """
        MATCH (n {id: $target_id})
        SET n.enrichment_status = 'failed',
            n.error_message = $error_message,
            n.failed_at = datetime()
        RETURN n.id as id
        """

        try:
            with self.driver.session() as session:
                result = session.run(query, {"target_id": target_id, "error_message": error_message}).single()

                if result:
                    logger.warning(f"Marked {target_id} as failed: {error_message}")
                    return {
                        "status": "success",
                        "target_id": target_id,
                        "enrichment_status": "failed",
                        "error_message": error_message,
                    }
                return {"status": "error", "message": f"Node {target_id} not found"}

        except Neo4jError as e:
            logger.error(f"Failed to mark as failed: {e}")
            return {"status": "error", "message": f"Database update failed: {str(e)}"}

    def get_enrichment_progress(self) -> dict[str, Any]:
        """
        Get overall enrichment progress statistics.

        Returns:
            Dictionary with progress metrics
        """
        query = """
        MATCH (n)
        WHERE n.enrichment_status IS NOT NULL
        RETURN n.enrichment_status as status, count(n) as count
        ORDER BY status
        """

        try:
            with self.driver.session() as session:
                results = session.run(query).data()

                status_counts = {r["status"]: r["count"] for r in results}

                # Calculate totals
                total = sum(status_counts.values())
                completed = status_counts.get("completed", 0)
                failed = status_counts.get("failed", 0)
                in_progress = status_counts.get("in_progress", 0) + status_counts.get("claimed", 0)

                return {
                    "total_nodes": total,
                    "completed": completed,
                    "failed": failed,
                    "in_progress": in_progress,
                    "completion_percentage": round((completed / total * 100) if total > 0 else 0, 2),
                    "status_breakdown": status_counts,
                }

        except Neo4jError as e:
            logger.error(f"Failed to get progress: {e}")
            return {"error": f"Failed to retrieve progress: {str(e)}"}
