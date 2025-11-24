"""
Graph Semantic Enrichment Skill Package.

This package provides tools for safely migrating Neo4j graph data from a
READ-ONLY SOURCE database to a WRITE-ONLY TARGET database with semantic
enrichment and validation.

Key Components:
- models: Pydantic models and data structures
- source_db: READ-ONLY access to SOURCE database
- target_db: WRITE-ONLY access to TARGET database
- validation: Two-tier validation system
- claiming: Atomic package claiming for parallel agents
- tools: CLI wrappers for agent interaction
"""

__version__ = "1.0.0"

# Import key classes for convenience
from .models import AttributeType
from .models import BrandExampleV3
from .models import EnrichmentStatus
from .models import EnumerationPackage
from .models import EnumerationV3
from .models import FreeTextPackage
from .models import FreeTextValueV3
from .models import HelperNodeV3
from .models import IDMapping
from .models import MetaAttributeV3
from .models import Package
from .models import ValidationResult

__all__ = [
    # Enums
    "EnrichmentStatus",
    "AttributeType",
    # Models
    "MetaAttributeV3",
    "EnumerationV3",
    "FreeTextValueV3",
    "HelperNodeV3",
    "BrandExampleV3",
    # Packages
    "Package",
    "EnumerationPackage",
    "FreeTextPackage",
    # Validation
    "ValidationResult",
    # Mapping
    "IDMapping",
]
