"""
Validation module - Two-tier validation for enriched nodes.

Tier 1: Structural constraints (required fields, character limits)
Tier 2: Semantic quality (template phrases, coherence)
"""

from models import EnumerationV3
from models import MetaAttributeV3
from models import ValidationResult

# Template phrases to detect and flag
TEMPLATE_PHRASES = [
    "Ein fundamentaler Aspekt",
    "Dies umfasst",
    "Ein wichtiger Bestandteil",
    "Zentrale Komponente",
    "Ein zentraler Aspekt",
    "Dies bezieht sich auf",
    "Ein wesentlicher Teil",
    "Eine wichtige Dimension",
    "Dies betrifft",
    "Ein grundlegender Baustein",
]


def detect_template_phrases(text: str) -> list[str]:
    """
    Detect template phrases in text.

    Args:
        text: Text to check

    Returns:
        List of detected template phrases
    """
    if not text:
        return []

    detected = []
    for phrase in TEMPLATE_PHRASES:
        if phrase in text:
            detected.append(phrase)
    return detected


def validate_metaattribute(meta_attr: MetaAttributeV3) -> ValidationResult:
    """
    Validate a MetaAttribute with two-tier validation.

    Args:
        meta_attr: MetaAttribute to validate

    Returns:
        ValidationResult with detailed feedback
    """
    tier1_violations = []
    tier2_violations = []

    # Tier 1: Structural constraints

    # Check required fields
    if not meta_attr.nameDe or len(meta_attr.nameDe) < 3:
        tier1_violations.append("nameDe must be at least 3 characters")

    if not meta_attr.nameEn or len(meta_attr.nameEn) < 3:
        tier1_violations.append("nameEn must be at least 3 characters")

    # Check definition lengths
    if not meta_attr.definitionDe or len(meta_attr.definitionDe) < 200:
        tier1_violations.append("definitionDe must be at least 200 characters")
    elif len(meta_attr.definitionDe) > 600:
        tier1_violations.append("definitionDe must not exceed 600 characters")

    if not meta_attr.definitionEn or len(meta_attr.definitionEn) < 200:
        tier1_violations.append("definitionEn must be at least 200 characters")
    elif len(meta_attr.definitionEn) > 600:
        tier1_violations.append("definitionEn must not exceed 600 characters")

    # Check list field counts
    if not meta_attr.whatItIsDe or len(meta_attr.whatItIsDe) < 3:
        tier1_violations.append("whatItIsDe must have at least 3 items")
    elif len(meta_attr.whatItIsDe) > 7:
        tier1_violations.append("whatItIsDe must not exceed 7 items")

    if not meta_attr.whatItIsEn or len(meta_attr.whatItIsEn) < 3:
        tier1_violations.append("whatItIsEn must have at least 3 items")
    elif len(meta_attr.whatItIsEn) > 7:
        tier1_violations.append("whatItIsEn must not exceed 7 items")

    if not meta_attr.whatItIsNotDe or len(meta_attr.whatItIsNotDe) < 2:
        tier1_violations.append("whatItIsNotDe must have at least 2 items")
    elif len(meta_attr.whatItIsNotDe) > 5:
        tier1_violations.append("whatItIsNotDe must not exceed 5 items")

    if not meta_attr.whatItIsNotEn or len(meta_attr.whatItIsNotEn) < 2:
        tier1_violations.append("whatItIsNotEn must have at least 2 items")
    elif len(meta_attr.whatItIsNotEn) > 5:
        tier1_violations.append("whatItIsNotEn must not exceed 5 items")

    # Check optional field lengths if present
    if meta_attr.brandingRelevanceDe:
        if len(meta_attr.brandingRelevanceDe) < 200:
            tier1_violations.append("brandingRelevanceDe must be at least 200 characters")
        elif len(meta_attr.brandingRelevanceDe) > 600:
            tier1_violations.append("brandingRelevanceDe must not exceed 600 characters")

    if meta_attr.brandingRelevanceEn:
        if len(meta_attr.brandingRelevanceEn) < 200:
            tier1_violations.append("brandingRelevanceEn must be at least 200 characters")
        elif len(meta_attr.brandingRelevanceEn) > 600:
            tier1_violations.append("brandingRelevanceEn must not exceed 600 characters")

    # Tier 2: Semantic quality

    # Check for template phrases
    if meta_attr.definitionDe:
        detected = detect_template_phrases(meta_attr.definitionDe)
        if detected:
            tier2_violations.append(f"definitionDe contains template phrases: {', '.join(detected)}")

    if meta_attr.definitionEn:
        # Check for English template phrases (translated versions)
        english_templates = ["A fundamental aspect", "This includes", "An important component", "Central component"]
        for phrase in english_templates:
            if phrase in meta_attr.definitionEn:
                tier2_violations.append(f"definitionEn contains template phrase: {phrase}")

    # Check for generic content
    if meta_attr.whatItIsDe:
        for item in meta_attr.whatItIsDe:
            if len(item) < 20:  # Too short to be meaningful
                tier2_violations.append(f"whatItIsDe item too generic: '{item}'")

    if meta_attr.whatItIsEn:
        for item in meta_attr.whatItIsEn:
            if len(item) < 20:  # Too short to be meaningful
                tier2_violations.append(f"whatItIsEn item too generic: '{item}'")

    # Check for "TBD" or "N/A" values
    for field_name, field_value in meta_attr.model_dump().items():
        if isinstance(field_value, str) and field_value in ["TBD", "N/A", "TODO"]:
            tier2_violations.append(f"{field_name} contains placeholder value: {field_value}")

    # Determine pass/fail
    tier1_passed = len(tier1_violations) == 0
    tier2_passed = len(tier2_violations) == 0
    overall_passed = tier1_passed and tier2_passed

    return ValidationResult(
        valid=overall_passed,
        tier1_passed=tier1_passed,
        tier2_passed=tier2_passed,
        tier1_violations=tier1_violations,
        tier2_violations=tier2_violations,
    )


def validate_enumeration(enumeration: EnumerationV3) -> ValidationResult:
    """
    Validate an Enumeration with two-tier validation.

    Args:
        enumeration: Enumeration to validate

    Returns:
        ValidationResult with detailed feedback
    """
    tier1_violations = []
    tier2_violations = []

    # Tier 1: Structural constraints

    # Check required fields
    if not enumeration.nameDe or len(enumeration.nameDe) < 3:
        tier1_violations.append("nameDe must be at least 3 characters")

    if not enumeration.nameEn or len(enumeration.nameEn) < 3:
        tier1_violations.append("nameEn must be at least 3 characters")

    # Check whatItIs lists
    if not enumeration.whatItIsDe or len(enumeration.whatItIsDe) < 2:
        tier1_violations.append("whatItIsDe must have at least 2 items")
    elif len(enumeration.whatItIsDe) > 5:
        tier1_violations.append("whatItIsDe must not exceed 5 items")

    if not enumeration.whatItIsEn or len(enumeration.whatItIsEn) < 2:
        tier1_violations.append("whatItIsEn must have at least 2 items")
    elif len(enumeration.whatItIsEn) > 5:
        tier1_violations.append("whatItIsEn must not exceed 5 items")

    # Check whatItIsNot lists
    if not enumeration.whatItIsNotDe or len(enumeration.whatItIsNotDe) < 2:
        tier1_violations.append("whatItIsNotDe must have at least 2 items")
    elif len(enumeration.whatItIsNotDe) > 5:
        tier1_violations.append("whatItIsNotDe must not exceed 5 items")

    if not enumeration.whatItIsNotEn or len(enumeration.whatItIsNotEn) < 2:
        tier1_violations.append("whatItIsNotEn must have at least 2 items")
    elif len(enumeration.whatItIsNotEn) > 5:
        tier1_violations.append("whatItIsNotEn must not exceed 5 items")

    # Check forMetaAttribute reference
    if not enumeration.forMetaAttribute:
        tier1_violations.append("forMetaAttribute reference is required")

    # Tier 2: Semantic quality

    # Check for meaningful contrast between whatItIs and whatItIsNot
    if enumeration.whatItIsDe and enumeration.whatItIsNotDe:
        # Check if there's actual differentiation
        is_items = set(" ".join(enumeration.whatItIsDe).lower().split())
        is_not_items = set(" ".join(enumeration.whatItIsNotDe).lower().split())

        overlap = is_items & is_not_items
        if len(overlap) > len(is_items) * 0.3:  # More than 30% overlap
            tier2_violations.append("whatItIs and whatItIsNot lack sufficient contrast (German)")

    if enumeration.whatItIsEn and enumeration.whatItIsNotEn:
        # Check English contrast
        is_items = set(" ".join(enumeration.whatItIsEn).lower().split())
        is_not_items = set(" ".join(enumeration.whatItIsNotEn).lower().split())

        overlap = is_items & is_not_items
        if len(overlap) > len(is_items) * 0.3:  # More than 30% overlap
            tier2_violations.append("whatItIs and whatItIsNot lack sufficient contrast (English)")

    # Check for generic content
    generic_terms = ["thing", "stuff", "something", "anything", "ding", "sache", "etwas"]

    if enumeration.whatItIsDe:
        for item in enumeration.whatItIsDe:
            if any(term in item.lower() for term in generic_terms):
                tier2_violations.append(f"whatItIsDe contains generic term: '{item}'")

    if enumeration.whatItIsEn:
        for item in enumeration.whatItIsEn:
            if any(term in item.lower() for term in generic_terms[:4]):  # English terms only
                tier2_violations.append(f"whatItIsEn contains generic term: '{item}'")

    # Check for placeholder values
    for field_name, field_value in enumeration.model_dump().items():
        if isinstance(field_value, str) and field_value in ["TBD", "N/A", "TODO"]:
            tier2_violations.append(f"{field_name} contains placeholder value: {field_value}")

    # Determine pass/fail
    tier1_passed = len(tier1_violations) == 0
    tier2_passed = len(tier2_violations) == 0
    overall_passed = tier1_passed and tier2_passed

    return ValidationResult(
        valid=overall_passed,
        tier1_passed=tier1_passed,
        tier2_passed=tier2_passed,
        tier1_violations=tier1_violations,
        tier2_violations=tier2_violations,
    )


def validate_semantic_coherence(
    german_def: str, english_def: str, german_what: list[str], english_what: list[str]
) -> list[str]:
    """
    Check semantic coherence between definition and whatItIs properties.

    Args:
        german_def: German definition
        english_def: English definition
        german_what: German whatItIs list
        english_what: English whatItIs list

    Returns:
        List of coherence violations
    """
    violations = []

    # Check if whatItIs items relate to definition
    if german_def and german_what:
        def_words = set(german_def.lower().split())
        what_words = set(" ".join(german_what).lower().split())

        # Should have some overlap (at least 10% of words)
        overlap = def_words & what_words
        if len(overlap) < len(what_words) * 0.1:
            violations.append("German whatItIs items don't relate to definition")

    if english_def and english_what:
        def_words = set(english_def.lower().split())
        what_words = set(" ".join(english_what).lower().split())

        # Should have some overlap (at least 10% of words)
        overlap = def_words & what_words
        if len(overlap) < len(what_words) * 0.1:
            violations.append("English whatItIs items don't relate to definition")

    # Check if German and English are consistent (not translations but similar concepts)
    if german_what and english_what:
        if abs(len(german_what) - len(english_what)) > 2:
            violations.append("German and English whatItIs lists have very different lengths")

    return violations
