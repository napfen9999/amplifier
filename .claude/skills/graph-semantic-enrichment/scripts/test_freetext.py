#!/usr/bin/env python3
"""
Test script for FreeText Support (freetext.py)

This script verifies:
1. FreeTextValue validation works correctly
2. HelperNode guidance is applied
3. Template phrase detection in FreeText
4. FreeText claiming for parallel agents
5. Content generation with HelperNode
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
    """Test that all FreeText modules can be imported."""
    logger.info("=" * 60)
    logger.info("Testing imports...")

    try:
        from models import FreeTextValueV3
        from models import HelperNodeV3
        from models import ValidationResult

        logger.info("✅ FreeText models imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import models: {e}")
        return False

    try:
        from freetext import FreeTextClaimer
        from freetext import FreeTextEnricher

        logger.info("✅ FreeText classes imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import freetext classes: {e}")
        return False

    return True


def test_freetext_validation():
    """Test FreeTextValue validation."""
    logger.info("=" * 60)
    logger.info("Testing FreeText validation...")

    from freetext import FreeTextEnricher
    from models import FreeTextValueV3

    # Create mock database
    mock_db = MagicMock()
    enricher = FreeTextEnricher(mock_db)

    # Test 1: Valid FreeText
    valid_freetext = FreeTextValueV3(
        id="FT-00001",
        forMetaAttribute="M001",
        contentDe="Dies ist ein ausführlicher Text über die Markenidentität, der mindestens 50 Zeichen lang ist und keine Template-Phrasen enthält.",
        contentEn="This is a detailed text about brand identity that is at least 50 characters long and contains no template phrases.",
        xPosition=100.0,
        yPosition=200.0,
    )

    result = enricher.validate_freetext(valid_freetext)
    if result.valid:
        logger.info("✅ Valid FreeText correctly accepted")
    else:
        logger.error(f"❌ Valid FreeText rejected: {result.tier1_violations + result.tier2_violations}")
        return False

    # Test 2: FreeText too short
    # Use model_construct to bypass Pydantic validation for test purposes
    short_freetext = FreeTextValueV3.model_construct(
        id="FT-00002",
        forMetaAttribute="M001",
        contentDe="Zu kurz",
        contentEn="Too short",
        xPosition=100.0,
        yPosition=200.0,
    )

    result = enricher.validate_freetext(short_freetext)
    if not result.valid and "too short" in str(result.tier1_violations):
        logger.info("✅ Short FreeText correctly rejected")
    else:
        logger.error("❌ Short FreeText should have been rejected")
        return False

    # Test 3: FreeText with template phrases
    # Use model_construct to ensure test runs even with template phrases
    template_freetext = FreeTextValueV3.model_construct(
        id="FT-00003",
        forMetaAttribute="M001",
        contentDe="Ein fundamentaler Aspekt der Markenidentität ist die konsistente Kommunikation. Dies umfasst alle wichtigen Elemente.",
        contentEn="A fundamental aspect of brand identity is consistent communication. This encompasses all important elements.",
        xPosition=100.0,
        yPosition=200.0,
    )

    result = enricher.validate_freetext(template_freetext)
    if not result.valid and len(result.template_phrases_found) > 0:
        logger.info(f"✅ Template phrases detected: {result.template_phrases_found}")
    else:
        logger.error("❌ Template phrases should have been detected")
        return False

    # Test 4: FreeText with placeholder content
    # Use model_construct to bypass validation for testing
    placeholder_freetext = FreeTextValueV3.model_construct(
        id="FT-00004",
        forMetaAttribute="M001",
        contentDe="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor.",
        contentEn="TODO: Add English translation of the brand message here when available.",
        xPosition=100.0,
        yPosition=200.0,
    )

    result = enricher.validate_freetext(placeholder_freetext)
    if not result.valid and any("Lorem ipsum" in v or "TODO" in v for v in result.tier1_violations):
        logger.info("✅ Placeholder content correctly detected")
    else:
        logger.error("❌ Placeholder content should have been detected")
        return False

    return True


def test_helper_node_validation():
    """Test FreeText validation with HelperNode constraints."""
    logger.info("=" * 60)
    logger.info("Testing HelperNode validation...")

    from freetext import FreeTextEnricher
    from models import FreeTextValueV3
    from models import HelperNodeV3

    # Create mock database
    mock_db = MagicMock()
    enricher = FreeTextEnricher(mock_db)

    # Create HelperNode with bullet point requirement
    # Use model_construct to bypass validation for test purposes
    helper = HelperNodeV3.model_construct(
        id="H-00001",
        descriptionDe="Leitfaden für Markenmission",
        descriptionEn="Guide for brand mission",
        whatItIsDe=["Strukturierter Leitfaden", "Klare Anweisungen"],
        whatItIsEn=["Structured guide", "Clear instructions"],
        whatItIsNotDe=["Vage Beschreibung"],
        whatItIsNotEn=["Vague description"],
        examplesDe="• Punkt 1\n• Punkt 2",  # Changed to string
        examplesEn="• Point 1\n• Point 2",  # Changed to string
        constraintsDe="Muss Aufzählungspunkte enthalten",
        constraintsEn="Must contain bullet points",
        generationGuidance="Create structured content with bullet points",
        structureRequirements="Must include bullet points for clarity",
        validationCriteria="Content must be specific and measurable",
        generationProcess="1. Identify key points 2. Structure as bullets",
        promptTemplateDe="Erstellen Sie eine Markenmission mit Aufzählungspunkten",
        promptTemplateEn="Create a brand mission with bullet points",
    )

    # Test 1: FreeText without required bullet points
    no_bullets = FreeTextValueV3(
        id="FT-00005",
        forMetaAttribute="M001",
        contentDe="Dies ist ein Text ohne Aufzählungspunkte, der die Anforderungen nicht erfüllt.",
        contentEn="This is text without bullet points that doesn't meet the requirements.",
        xPosition=100.0,
        yPosition=200.0,
    )

    result = enricher.validate_freetext(no_bullets, helper)
    if not result.valid and any("bullet points" in v for v in result.tier2_violations):
        logger.info("✅ Missing bullet points correctly detected")
    else:
        logger.error("❌ Should have detected missing bullet points")
        return False

    # Test 2: FreeText with required bullet points
    with_bullets = FreeTextValueV3(
        id="FT-00006",
        forMetaAttribute="M001",
        contentDe="Unsere Markenmission:\n• Innovation fördern\n• Qualität liefern\n• Kunden begeistern",
        contentEn="Our brand mission:\n• Foster innovation\n• Deliver quality\n• Delight customers",
        xPosition=100.0,
        yPosition=200.0,
    )

    result = enricher.validate_freetext(with_bullets, helper)
    if result.valid or not any("bullet points" in v for v in result.tier2_violations):
        logger.info("✅ Bullet points correctly accepted")
    else:
        logger.error("❌ Valid bullet points rejected")
        return False

    # Test 3: FreeText with vague terms (violates "specific" criteria)
    vague_content = FreeTextValueV3(
        id="FT-00007",
        forMetaAttribute="M001",
        contentDe="• Do various things with some products\n• Achieve certain goals etc\n• Work on various areas and so on",
        contentEn="• Do various things with some products\n• Achieve certain goals etc\n• Work on various areas and so on",
        xPosition=100.0,
        yPosition=200.0,
    )

    result = enricher.validate_freetext(vague_content, helper)
    if not result.valid and any("vague terms" in v for v in result.tier2_violations):
        logger.info("✅ Vague content correctly detected")
    else:
        logger.error("❌ Should have detected vague content")
        return False

    return True


def test_freetext_claiming():
    """Test FreeText package claiming for parallel agents."""
    logger.info("=" * 60)
    logger.info("Testing FreeText claiming...")

    from freetext import FreeTextClaimer

    # Create mock database
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_db.driver.session.return_value.__exit__ = MagicMock(return_value=None)

    # Mock query results
    claim_records = [
        {"meta_id": "M010", "claimed_at": datetime.now()},
        {"meta_id": "M011", "claimed_at": datetime.now()},
    ]

    mock_run = MagicMock()
    mock_run.__iter__ = lambda self: iter(claim_records)
    mock_session.run.return_value = mock_run

    # Test claiming
    claimer = FreeTextClaimer(mock_db)
    packages = claimer.claim_freetext_packages("Agent_F1", num_packages=2)

    if len(packages) == 2:
        logger.info(f"✅ Successfully claimed {len(packages)} FreeText packages")
        if all(p["type"] == "freetext" for p in packages):
            logger.info("✅ All packages marked as 'freetext' type")
        else:
            logger.error("❌ Package types incorrect")
            return False
    else:
        logger.error(f"❌ Expected 2 packages, got {len(packages)}")
        return False

    return True


def test_content_generation():
    """Test FreeText content generation with HelperNode."""
    logger.info("=" * 60)
    logger.info("Testing content generation...")

    from freetext import FreeTextEnricher
    from models import HelperNodeV3

    # Create mock database
    mock_db = MagicMock()
    enricher = FreeTextEnricher(mock_db)

    # Create HelperNode with prompt templates
    # Use model_construct to bypass validation for test purposes
    helper = HelperNodeV3.model_construct(
        id="H-00002",
        descriptionDe="Generator für Markenvision",
        descriptionEn="Brand vision generator",
        whatItIsDe=["Visionsgenerator"],
        whatItIsEn=["Vision generator"],
        whatItIsNotDe=["Zufälliger Text"],
        whatItIsNotEn=["Random text"],
        examplesDe="Beispiel Vision",  # Changed to string
        examplesEn="Example vision",  # Changed to string
        constraintsDe="Muss inspirierend sein",
        constraintsEn="Must be inspiring",
        generationGuidance="Create inspiring vision statement",
        structureRequirements="Single paragraph",
        validationCriteria="Must be forward-looking",
        generationProcess="Analyze brand values, project future",
        promptTemplateDe="Erstelle eine Vision für {brand_name} im Bereich {industry}",
        promptTemplateEn="Create a vision for {brand_name} in {industry}",
    )

    # Test content generation
    context = {
        "brand_name": "TestBrand",
        "industry": "Technology",
    }

    content = enricher.generate_freetext_content("M012", helper, context)

    if "contentDe" in content and "contentEn" in content:
        logger.info("✅ Content generated with both languages")
        if "TestBrand" in content["contentEn"]:
            logger.info("✅ Context variables replaced in content")
        else:
            logger.error("❌ Context not properly applied")
            return False
    else:
        logger.error("❌ Content generation failed")
        return False

    return True


def test_batch_validation():
    """Test batch validation of multiple FreeTextValues."""
    logger.info("=" * 60)
    logger.info("Testing batch validation...")

    from freetext import FreeTextEnricher
    from models import FreeTextValueV3

    # Create mock database
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_db.driver.session.return_value.__exit__ = MagicMock(return_value=None)

    # Mock get_helper_for_metaattribute to return None
    mock_session.run.return_value.single.return_value = None

    enricher = FreeTextEnricher(mock_db)

    # Create test FreeTextValues
    freetext_values = [
        FreeTextValueV3(
            id="FT-00008",
            forMetaAttribute="M001",
            contentDe="Gültiger Text mit mehr als 50 Zeichen für die Validierung.",
            contentEn="Valid text with more than 50 characters for validation.",
            xPosition=100.0,
            yPosition=200.0,
        ),
        FreeTextValueV3.model_construct(  # Use model_construct for invalid test case
            id="FT-00009",
            forMetaAttribute="M002",
            contentDe="Zu kurz",  # Invalid
            contentEn="Too short",  # Invalid
            xPosition=100.0,
            yPosition=200.0,
        ),
        FreeTextValueV3(
            id="FT-00010",
            forMetaAttribute="M003",
            contentDe="Ein fundamentaler Aspekt der Markenidentität mit mehr als 50 Zeichen.",  # Template phrase
            contentEn="A fundamental aspect of brand identity with more than 50 characters.",
            xPosition=100.0,
            yPosition=200.0,
        ),
    ]

    results = enricher.batch_validate_freetext(freetext_values)

    if len(results) == 3:
        logger.info(f"✅ Batch validation returned {len(results)} results")

        # Check individual results
        if results["FT-00008"].valid:
            logger.info("✅ Valid FreeText passed in batch")
        else:
            logger.error("❌ Valid FreeText failed in batch")
            return False

        if not results["FT-00009"].valid:
            logger.info("✅ Invalid FreeText caught in batch")
        else:
            logger.error("❌ Invalid FreeText not caught in batch")
            return False

        if not results["FT-00010"].valid and len(results["FT-00010"].template_phrases_found) > 0:
            logger.info("✅ Template phrases detected in batch")
        else:
            logger.error("❌ Template phrases not detected in batch")
            return False
    else:
        logger.error(f"❌ Expected 3 results, got {len(results)}")
        return False

    return True


def main():
    """Run all FreeText tests."""
    logger.info("=" * 60)
    logger.info("TESTING FREETEXT SUPPORT")
    logger.info("=" * 60)

    all_passed = True

    # Test 1: Imports
    if not test_imports():
        all_passed = False

    # Test 2: FreeText validation
    if not test_freetext_validation():
        all_passed = False

    # Test 3: HelperNode validation
    if not test_helper_node_validation():
        all_passed = False

    # Test 4: FreeText claiming
    if not test_freetext_claiming():
        all_passed = False

    # Test 5: Content generation
    if not test_content_generation():
        all_passed = False

    # Test 6: Batch validation
    if not test_batch_validation():
        all_passed = False

    # Summary
    logger.info("=" * 60)
    if all_passed:
        logger.info("✅ ALL FREETEXT TESTS PASSED!")
        logger.info("✅ FreeTextValue validation works")
        logger.info("✅ HelperNode guidance applied")
        logger.info("✅ Template phrase detection in FreeText")
        logger.info("✅ FreeText claiming for parallel agents")
        logger.info("✅ Content generation with HelperNode")
        logger.info("✅ Batch validation operational")
    else:
        logger.error("❌ SOME FREETEXT TESTS FAILED - Please review the output above")
    logger.info("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
