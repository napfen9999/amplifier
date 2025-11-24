"""
FreeText Support for Graph Semantic Enrichment.

Handles:
- FreeTextValue creation and validation
- HelperNode guidance integration
- FreeText-specific enrichment workflows
- Content generation with AI assistance
"""

import logging

from models import FreeTextValueV3
from models import HelperNodeV3
from models import ValidationResult
from validation import detect_template_phrases

logger = logging.getLogger(__name__)


class FreeTextEnricher:
    """Handles FreeText attribute enrichment with HelperNode guidance."""

    def __init__(self, db_client):
        """Initialize with database client.

        Args:
            db_client: TargetDB instance for database operations
        """
        self.db = db_client

    def enrich_freetext_value(
        self,
        freetext_value: FreeTextValueV3,
        helper_node: HelperNodeV3 | None = None,
    ) -> ValidationResult:
        """Enrich a FreeTextValue with optional HelperNode guidance.

        Args:
            freetext_value: The FreeTextValue to enrich
            helper_node: Optional HelperNode providing generation guidance

        Returns:
            ValidationResult indicating success/failure
        """
        # Validate FreeText content
        result = self.validate_freetext(freetext_value, helper_node)

        if not result.valid:
            logger.warning(
                f"FreeTextValue {freetext_value.id} validation failed: "
                f"{', '.join(result.tier1_violations + result.tier2_violations)}"
            )
            return result

        # Store enriched FreeText in TARGET database
        try:
            self._write_freetext_to_target(freetext_value, helper_node)
            logger.info(f"Successfully enriched FreeTextValue {freetext_value.id}")
        except Exception as e:
            logger.error(f"Failed to write FreeTextValue {freetext_value.id}: {e}")
            result.valid = False
            result.tier1_violations.append(f"Database write failed: {str(e)}")

        return result

    def validate_freetext(
        self,
        freetext_value: FreeTextValueV3,
        helper_node: HelperNodeV3 | None = None,
    ) -> ValidationResult:
        """Validate FreeTextValue content with optional HelperNode constraints.

        Args:
            freetext_value: The FreeTextValue to validate
            helper_node: Optional HelperNode with validation criteria

        Returns:
            ValidationResult with detailed findings
        """
        result = ValidationResult(
            valid=True,
            tier1_passed=True,
            tier2_passed=True,
            tier1_violations=[],
            tier2_violations=[],
            template_phrases_found=[],
            suggestions=[],
        )

        # Tier 1: Structural validation
        self._validate_structure(freetext_value, result)

        # Tier 2: Semantic validation
        self._validate_semantics(freetext_value, result)

        # HelperNode-specific validation if provided
        if helper_node:
            self._validate_against_helper(freetext_value, helper_node, result)

        # Set overall validity
        result.tier1_passed = len(result.tier1_violations) == 0
        result.tier2_passed = len(result.tier2_violations) == 0
        result.valid = result.tier1_passed and result.tier2_passed

        return result

    def _validate_structure(self, freetext_value: FreeTextValueV3, result: ValidationResult) -> None:
        """Validate structural requirements for FreeText.

        Args:
            freetext_value: Value to validate
            result: ValidationResult to populate
        """
        # Check minimum content length
        if len(freetext_value.contentDe) < 50:
            result.tier1_violations.append(f"contentDe too short ({len(freetext_value.contentDe)} < 50 chars)")

        if len(freetext_value.contentEn) < 50:
            result.tier1_violations.append(f"contentEn too short ({len(freetext_value.contentEn)} < 50 chars)")

        # Check maximum content length
        if len(freetext_value.contentDe) > 2000:
            result.tier1_violations.append(f"contentDe too long ({len(freetext_value.contentDe)} > 2000 chars)")

        if len(freetext_value.contentEn) > 2000:
            result.tier1_violations.append(f"contentEn too long ({len(freetext_value.contentEn)} > 2000 chars)")

        # Check for placeholder content
        placeholder_patterns = ["Lorem ipsum", "TBD", "TODO", "XXX", "N/A"]
        for pattern in placeholder_patterns:
            if pattern in freetext_value.contentDe:
                result.tier1_violations.append(f"Placeholder text '{pattern}' found in contentDe")
            if pattern in freetext_value.contentEn:
                result.tier1_violations.append(f"Placeholder text '{pattern}' found in contentEn")

    def _validate_semantics(self, freetext_value: FreeTextValueV3, result: ValidationResult) -> None:
        """Validate semantic quality of FreeText content.

        Args:
            freetext_value: Value to validate
            result: ValidationResult to populate
        """
        # Check for template phrases
        template_de = detect_template_phrases(freetext_value.contentDe)
        template_en = detect_template_phrases(freetext_value.contentEn)

        if template_de:
            result.tier2_violations.append(f"Template phrases in contentDe: {', '.join(template_de)}")
            result.template_phrases_found.extend(template_de)

        if template_en:
            result.tier2_violations.append(f"Template phrases in contentEn: {', '.join(template_en)}")
            result.template_phrases_found.extend(template_en)

        # Check for consistency between languages
        # Simple check: roughly similar length (within 50% difference)
        len_ratio = len(freetext_value.contentDe) / max(len(freetext_value.contentEn), 1)
        if len_ratio < 0.5 or len_ratio > 2.0:
            result.tier2_violations.append(f"Content length mismatch between languages (ratio: {len_ratio:.2f})")
            result.suggestions.append("Ensure both language versions convey similar information")

    def _validate_against_helper(
        self,
        freetext_value: FreeTextValueV3,
        helper_node: HelperNodeV3,
        result: ValidationResult,
    ) -> None:
        """Validate FreeText against HelperNode constraints.

        Args:
            freetext_value: Value to validate
            helper_node: HelperNode with validation criteria
            result: ValidationResult to populate
        """
        # Check against structure requirements if specified
        if helper_node.structureRequirements:
            # Example: Check if required sections are present
            if "bullet points" in helper_node.structureRequirements.lower():
                if "•" not in freetext_value.contentDe and "-" not in freetext_value.contentDe:
                    result.tier2_violations.append("HelperNode requires bullet points but none found in contentDe")

            if "numbered list" in helper_node.structureRequirements.lower():
                if not any(f"{i}." in freetext_value.contentDe for i in range(1, 10)):
                    result.tier2_violations.append("HelperNode requires numbered list but none found in contentDe")

        # Check against validation criteria
        if helper_node.validationCriteria:
            # This would typically involve more sophisticated checks
            # For now, we'll do basic keyword presence checks
            criteria_keywords = ["specific", "concrete", "measurable", "clear"]
            for keyword in criteria_keywords:
                if keyword in helper_node.validationCriteria.lower():
                    # Check if content seems specific enough
                    vague_terms = ["some", "various", "certain", "etc", "and so on"]
                    vague_count = sum(1 for term in vague_terms if term in freetext_value.contentDe.lower())
                    if vague_count > 2:
                        result.tier2_violations.append(
                            f"Content contains too many vague terms ({vague_count}), violates '{keyword}' criteria"
                        )

        # Add suggestions based on HelperNode guidance
        if helper_node.generationGuidance:
            result.suggestions.append(f"Consider HelperNode guidance: {helper_node.generationGuidance[:200]}...")

    def _write_freetext_to_target(
        self,
        freetext_value: FreeTextValueV3,
        helper_node: HelperNodeV3 | None = None,
    ) -> None:
        """Write enriched FreeTextValue to TARGET database.

        Args:
            freetext_value: The FreeTextValue to write
            helper_node: Optional HelperNode to link via PROVIDES_GUIDANCE
        """
        with self.db.driver.session() as session:
            # Create FreeTextValue node
            create_query = """
            CREATE (ft:FreeTextValue {
                id: $id,
                forMetaAttribute: $forMetaAttribute,
                contentDe: $contentDe,
                contentEn: $contentEn,
                xPosition: $xPosition,
                yPosition: $yPosition
            })
            RETURN ft.id as created_id
            """

            result = session.run(
                create_query,
                id=freetext_value.id,
                forMetaAttribute=freetext_value.forMetaAttribute,
                contentDe=freetext_value.contentDe,
                contentEn=freetext_value.contentEn,
                xPosition=freetext_value.xPosition,
                yPosition=freetext_value.yPosition,
            )

            created = result.single()
            if not created:
                raise RuntimeError(f"Failed to create FreeTextValue {freetext_value.id}")

            # Create relationship to MetaAttribute
            rel_query = """
            MATCH (m:MetaAttribute {id: $meta_id}),
                  (ft:FreeTextValue {id: $ft_id})
            CREATE (m)-[:HAS_FREE_TEXT_VALUE]->(ft)
            RETURN m.id as meta_id
            """

            session.run(
                rel_query,
                meta_id=freetext_value.forMetaAttribute,
                ft_id=freetext_value.id,
            )

            # Link to HelperNode if provided
            if helper_node:
                helper_query = """
                MATCH (h:HelperNode {id: $helper_id}),
                      (ft:FreeTextValue {id: $ft_id})
                CREATE (h)-[:PROVIDES_GUIDANCE]->(ft)
                RETURN h.id as helper_id
                """

                session.run(
                    helper_query,
                    helper_id=helper_node.id,
                    ft_id=freetext_value.id,
                )

            logger.info(f"Successfully wrote FreeTextValue {freetext_value.id} to TARGET")

    def get_helper_for_metaattribute(self, meta_id: str) -> HelperNodeV3 | None:
        """Retrieve HelperNode for a MetaAttribute if it exists.

        Args:
            meta_id: MetaAttribute ID to find helper for

        Returns:
            HelperNodeV3 if found, None otherwise
        """
        with self.db.driver.session() as session:
            query = """
            MATCH (m:MetaAttribute {id: $meta_id})-[:HAS_FREE_TEXT_VALUE]->
                  ()<-[:PROVIDES_GUIDANCE]-(h:HelperNode)
            RETURN h LIMIT 1
            """

            result = session.run(query, meta_id=meta_id)
            record = result.single()

            if record:
                node = record["h"]
                return HelperNodeV3(
                    id=node.get("id"),
                    descriptionDe=node.get("descriptionDe", ""),
                    descriptionEn=node.get("descriptionEn", ""),
                    whatItIsDe=node.get("whatItIsDe", []),
                    whatItIsEn=node.get("whatItIsEn", []),
                    whatItIsNotDe=node.get("whatItIsNotDe", []),
                    whatItIsNotEn=node.get("whatItIsNotEn", []),
                    examplesDe=node.get("examplesDe", []),
                    examplesEn=node.get("examplesEn", []),
                    constraintsDe=node.get("constraintsDe", ""),
                    constraintsEn=node.get("constraintsEn", ""),
                    generationGuidance=node.get("generationGuidance", ""),
                    structureRequirements=node.get("structureRequirements", ""),
                    validationCriteria=node.get("validationCriteria", ""),
                    generationProcess=node.get("generationProcess", ""),
                    promptTemplateDe=node.get("promptTemplateDe", ""),
                    promptTemplateEn=node.get("promptTemplateEn", ""),
                )

        return None

    def generate_freetext_content(
        self,
        meta_id: str,
        helper_node: HelperNodeV3,
        context: dict[str, str],
    ) -> dict[str, str]:
        """Generate FreeText content using HelperNode guidance and context.

        This is a placeholder for AI-assisted generation.
        In production, this would call an LLM with the helper's prompt template.

        Args:
            meta_id: MetaAttribute ID this is for
            helper_node: HelperNode with generation guidance
            context: Context dictionary with brand information

        Returns:
            Dictionary with 'contentDe' and 'contentEn' keys
        """
        # Use prompt templates to generate content
        prompt_de = helper_node.promptTemplateDe
        prompt_en = helper_node.promptTemplateEn

        # Replace placeholders in prompts
        for key, value in context.items():
            prompt_de = prompt_de.replace(f"{{{key}}}", value)
            prompt_en = prompt_en.replace(f"{{{key}}}", value)

        # In production, this would call an LLM
        # For now, return a structured placeholder that follows the guidance
        content_de = (
            f"[Generated content for {meta_id} following guidance]\n"
            f"Context: {context.get('brand_name', 'Unknown Brand')}\n"
            f"Guidance applied: {helper_node.generationGuidance[:100]}..."
        )

        content_en = (
            f"[Generated content for {meta_id} following guidance]\n"
            f"Context: {context.get('brand_name', 'Unknown Brand')}\n"
            f"Guidance applied: {helper_node.generationGuidance[:100]}..."
        )

        return {
            "contentDe": content_de,
            "contentEn": content_en,
        }

    def batch_validate_freetext(self, freetext_values: list[FreeTextValueV3]) -> dict[str, ValidationResult]:
        """Validate multiple FreeTextValues in batch.

        Args:
            freetext_values: List of FreeTextValues to validate

        Returns:
            Dictionary mapping FreeTextValue ID to ValidationResult
        """
        results = {}

        for ft_value in freetext_values:
            # Try to get associated HelperNode
            helper = self.get_helper_for_metaattribute(ft_value.forMetaAttribute)

            # Validate with helper if available
            result = self.validate_freetext(ft_value, helper)
            results[ft_value.id] = result

            if result.valid:
                logger.info(f"FreeTextValue {ft_value.id} passed validation")
            else:
                logger.warning(
                    f"FreeTextValue {ft_value.id} failed validation: "
                    f"{len(result.tier1_violations)} T1, {len(result.tier2_violations)} T2 violations"
                )

        return results


class FreeTextClaimer:
    """Handles claiming of FreeText packages for parallel processing."""

    def __init__(self, db_client):
        """Initialize with database client.

        Args:
            db_client: TargetDB instance for database operations
        """
        self.db = db_client

    def claim_freetext_packages(self, agent_id: str, num_packages: int = 2) -> list[dict]:
        """Claim FreeText MetaAttributes for enrichment.

        Args:
            agent_id: Unique identifier for the agent
            num_packages: Number of packages to claim

        Returns:
            List of claimed FreeText packages
        """
        claimed = []

        with self.db.driver.session() as session:
            # Find unclaimed FreeText MetaAttributes
            query = """
            MATCH (m:MetaAttribute {attributeType: 'FREITEXT'})
            WHERE m.enrichment_status = 'unclaimed'
            WITH m LIMIT $limit
            SET m.enrichment_status = 'claimed',
                m.claimed_at = datetime(),
                m.claimed_by = $agent_id
            RETURN m.id as meta_id, m.claimed_at as claimed_at
            """

            result = session.run(
                query,
                limit=num_packages,
                agent_id=agent_id,
            )

            for record in result:
                # Get associated HelperNode if exists
                helper_query = """
                MATCH (m:MetaAttribute {id: $meta_id})-[:HAS_FREE_TEXT_VALUE]->
                      ()<-[:PROVIDES_GUIDANCE]-(h:HelperNode)
                RETURN h.id as helper_id
                LIMIT 1
                """

                helper_result = session.run(
                    helper_query,
                    meta_id=record["meta_id"],
                )
                helper_record = helper_result.single()

                package = {
                    "meta_id": record["meta_id"],
                    "type": "freetext",
                    "claimed_at": record["claimed_at"],
                    "agent_id": agent_id,
                    "helper_id": helper_record["helper_id"] if helper_record else None,
                }

                claimed.append(package)

        logger.info(f"Agent {agent_id} claimed {len(claimed)} FreeText packages")
        return claimed
