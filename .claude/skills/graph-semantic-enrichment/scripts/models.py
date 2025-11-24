"""
Pydantic models and data structures for graph semantic enrichment.

This module defines the core data structures that all other modules use.
Following the "bricks and studs" philosophy, these models are the connection
points (studs) that allow modules (bricks) to work together.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

# Enums


class EnrichmentStatus(str, Enum):
    """Status tracking for enrichment workflow."""

    UNCLAIMED = "unclaimed"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AttributeType(str, Enum):
    """Type of attribute content."""

    ENUMERATION = "enumeration"
    FREE_TEXT = "free_text"
    MIXED = "mixed"


# Base Models


class EnrichableNode(BaseModel):
    """Base model for nodes that can be enriched."""

    model_config = ConfigDict(
        # Allow Neo4j datetime objects
        arbitrary_types_allowed=True,
        # Validate on assignment
        validate_assignment=True,
    )

    id: str = Field(..., description="Unique identifier")
    enrichment_status: EnrichmentStatus = Field(
        default=EnrichmentStatus.UNCLAIMED, description="Current enrichment status"
    )
    claimed_at: datetime | None = Field(default=None, description="When the node was claimed for enrichment")
    claimed_by: str | None = Field(default=None, description="Agent ID that claimed this node")
    completed_at: datetime | None = Field(default=None, description="When enrichment was completed")
    error_message: str | None = Field(default=None, description="Error message if enrichment failed")


# Node Models


class MetaAttributeV3(EnrichableNode):
    """V3 Schema MetaAttribute with semantic properties."""

    nameDe: str = Field(..., min_length=3, max_length=100)
    nameEn: str = Field(..., min_length=3, max_length=100)

    definitionDe: str = Field(..., min_length=200, max_length=600)
    definitionEn: str = Field(..., min_length=200, max_length=600)

    whatItIsDe: list[str] = Field(..., description="3-7 bullet points describing what it is")
    whatItIsEn: list[str] = Field(..., description="3-7 bullet points describing what it is")

    whatItIsNotDe: list[str] = Field(..., description="2-5 bullet points describing what it is not")
    whatItIsNotEn: list[str] = Field(..., description="2-5 bullet points describing what it is not")

    brandingRelevanceDe: str | None = Field(None, min_length=100, max_length=400)
    brandingRelevanceEn: str | None = Field(None, min_length=100, max_length=400)

    scope: str = Field(..., pattern="^(primary_scope|secondary_scope)$")
    attributeType: AttributeType = Field(...)

    # Visualization properties
    xPosition: float | None = Field(None, ge=-1000, le=1000)
    yPosition: float | None = Field(None, ge=-1000, le=1000)

    @field_validator("whatItIsDe", "whatItIsEn")
    @classmethod
    def validate_what_it_is(cls, v: list[str]) -> list[str]:
        """Ensure correct number of bullet points and each is substantial."""
        if len(v) < 3 or len(v) > 7:
            raise ValueError(f"Must have 3-7 bullet points, got {len(v)}")
        for item in v:
            if len(item) < 20:
                raise ValueError(f"Bullet point too short: {item}")
            if len(item) > 200:
                raise ValueError(f"Bullet point too long: {item}")
        return v

    @field_validator("whatItIsNotDe", "whatItIsNotEn")
    @classmethod
    def validate_what_it_is_not(cls, v: list[str]) -> list[str]:
        """Ensure correct number of bullet points for what it is not."""
        if len(v) < 2 or len(v) > 5:
            raise ValueError(f"Must have 2-5 bullet points, got {len(v)}")
        for item in v:
            if len(item) < 20:
                raise ValueError(f"Bullet point too short: {item}")
            if len(item) > 200:
                raise ValueError(f"Bullet point too long: {item}")
        return v

    @field_validator("definitionDe", "definitionEn")
    @classmethod
    def validate_definition(cls, v: str) -> str:
        """Check for template phrases."""
        template_phrases = [
            "Ein fundamentaler Aspekt",
            "A fundamental aspect",
            "Dies umfasst",
            "This encompasses",
            "TBD",
            "N/A",
            "TODO",
        ]
        for phrase in template_phrases:
            if phrase.lower() in v.lower():
                raise ValueError(f"Template phrase detected: {phrase}")
        return v


class EnumerationV3(BaseModel):
    """V3 Schema Enumeration with semantic contrast."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    id: str = Field(..., pattern="^E-\\d{5}$")  # E-00001 format
    forMetaAttribute: str = Field(..., description="Parent MetaAttribute ID")

    nameDe: str = Field(..., min_length=3, max_length=100)
    nameEn: str = Field(..., min_length=3, max_length=100)

    whatItIsDe: str = Field(..., min_length=50, max_length=300)
    whatItIsEn: str = Field(..., min_length=50, max_length=300)

    whatItIsNotDe: str = Field(..., min_length=50, max_length=300)
    whatItIsNotEn: str = Field(..., min_length=50, max_length=300)

    examplesDe: str | None = Field(None, min_length=100, max_length=400)
    examplesEn: str | None = Field(None, min_length=100, max_length=400)

    # Visualization properties
    xPosition: float | None = Field(None, ge=-1000, le=1000)
    yPosition: float | None = Field(None, ge=-1000, le=1000)

    @field_validator("whatItIsDe", "whatItIsEn", "whatItIsNotDe", "whatItIsNotEn")
    @classmethod
    def validate_semantic_content(cls, v: str) -> str:
        """Ensure semantic content is substantial."""
        if v.strip().upper() in ["TBD", "N/A", "TODO", "NA"]:
            raise ValueError(f"Placeholder content not allowed: {v}")
        return v


class FreeTextValueV3(BaseModel):
    """V3 Schema FreeTextValue for user-generated content."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    id: str = Field(..., pattern="^FT-\\d{5}$")  # FT-00001 format
    forMetaAttribute: str = Field(..., description="Parent MetaAttribute ID")

    contentDe: str = Field(..., min_length=50, max_length=1000)
    contentEn: str = Field(..., min_length=50, max_length=1000)

    # Visualization properties
    xPosition: float | None = Field(None, ge=-1000, le=1000)
    yPosition: float | None = Field(None, ge=-1000, le=1000)


class HelperNodeV3(BaseModel):
    """V3 Schema HelperNode for generation guidance."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    id: str = Field(..., pattern="^H-\\d{5}$")  # H-00001 format

    descriptionDe: str = Field(..., min_length=100, max_length=500)
    descriptionEn: str = Field(..., min_length=100, max_length=500)

    whatItIsDe: list[str] = Field(..., description="3-7 bullet points describing what it is")
    whatItIsEn: list[str] = Field(..., description="3-7 bullet points describing what it is")

    whatItIsNotDe: list[str] = Field(..., description="2-5 bullet points describing what it is not")
    whatItIsNotEn: list[str] = Field(..., description="2-5 bullet points describing what it is not")

    examplesDe: str = Field(..., min_length=200, max_length=800)
    examplesEn: str = Field(..., min_length=200, max_length=800)

    constraintsDe: str = Field(..., min_length=100, max_length=400)
    constraintsEn: str = Field(..., min_length=100, max_length=400)

    generationGuidance: str = Field(..., min_length=200, max_length=800)
    structureRequirements: str = Field(..., min_length=100, max_length=400)
    validationCriteria: str = Field(..., min_length=100, max_length=400)
    generationProcess: str = Field(..., min_length=200, max_length=600)

    promptTemplateDe: str | None = Field(None, min_length=200, max_length=1000)
    promptTemplateEn: str | None = Field(None, min_length=200, max_length=1000)

    @field_validator("whatItIsDe", "whatItIsEn")
    @classmethod
    def validate_what_it_is(cls, v: list[str]) -> list[str]:
        """Ensure correct number of bullet points and each is substantial."""
        if len(v) < 3 or len(v) > 7:
            raise ValueError(f"Must have 3-7 bullet points, got {len(v)}")
        for item in v:
            if len(item) < 20:
                raise ValueError(f"Bullet point too short: {item}")
            if len(item) > 200:
                raise ValueError(f"Bullet point too long: {item}")
        return v

    @field_validator("whatItIsNotDe", "whatItIsNotEn")
    @classmethod
    def validate_what_it_is_not(cls, v: list[str]) -> list[str]:
        """Ensure correct number of bullet points for what it is not."""
        if len(v) < 2 or len(v) > 5:
            raise ValueError(f"Must have 2-5 bullet points, got {len(v)}")
        for item in v:
            if len(item) < 20:
                raise ValueError(f"Bullet point too short: {item}")
            if len(item) > 200:
                raise ValueError(f"Bullet point too long: {item}")
        return v


class BrandExampleV3(BaseModel):
    """V3 Schema BrandExample for real-world examples."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    id: str = Field(..., pattern="^BE-\\d{5}$")  # BE-00001 format
    brandName: str = Field(..., min_length=2, max_length=100)
    industry: str = Field(..., min_length=3, max_length=100)
    foundedYear: int | None = Field(None, ge=1800, le=2025)
    url: str | None = Field(None, pattern="^https?://.*")


# Package Dataclasses for Claiming


@dataclass
class Package:
    """Base package for atomic claiming."""

    meta_id: str
    type: str  # "enumeration" or "freetext"
    claimed_at: datetime
    agent_id: str


@dataclass
class EnumerationPackage(Package):
    """Package containing MetaAttribute and ALL its Enumerations."""

    enumeration_ids: list[str]  # ALL Enumerations, not limited to 20!

    def __post_init__(self):
        self.type = "enumeration"
        # Log if package is large
        if len(self.enumeration_ids) > 20:
            print(f"Large package: {self.meta_id} has {len(self.enumeration_ids)} Enumerations")


@dataclass
class FreeTextPackage(Package):
    """Package containing MetaAttribute and its FreeTextValues."""

    freetext_ids: list[str]
    helper_id: str | None = None

    def __post_init__(self):
        self.type = "freetext"


# Validation Results


class ValidationResult(BaseModel):
    """Result of two-tier validation."""

    valid: bool = Field(..., description="Overall validation result")

    # Tier 1: Structural constraints
    tier1_passed: bool = Field(default=True)
    tier1_violations: list[str] = Field(default_factory=list)

    # Tier 2: Semantic quality
    tier2_passed: bool = Field(default=True)
    tier2_violations: list[str] = Field(default_factory=list)

    # Suggestions for improvement
    suggestions: list[str] = Field(default_factory=list)

    # Template phrases detected
    template_phrases_found: list[str] = Field(default_factory=list)

    @property
    def overall_passed(self) -> bool:
        """Check if both tiers passed."""
        return self.tier1_passed and self.tier2_passed

    def add_tier1_violation(self, message: str) -> None:
        """Add a structural violation."""
        self.tier1_violations.append(message)
        self.tier1_passed = False
        self.valid = False

    def add_tier2_violation(self, message: str) -> None:
        """Add a semantic violation."""
        self.tier2_violations.append(message)
        self.tier2_passed = False
        self.valid = False

    def add_template_phrase(self, phrase: str) -> None:
        """Record a template phrase detection."""
        self.template_phrases_found.append(phrase)
        self.add_tier2_violation(f"Template phrase detected: {phrase}")

    def add_suggestion(self, suggestion: str) -> None:
        """Add improvement suggestion."""
        self.suggestions.append(suggestion)


# ID Translation


@dataclass
class IDMapping:
    """Maps SOURCE IDs to TARGET IDs."""

    source_id: str
    target_id: str
    node_type: str  # "MetaAttribute", "Enumeration", etc.
    translation_date: datetime
    migration_phase: str = "Phase 4"
