"""Tests for PIF framework blueprint."""

from lib.blueprint_loader import load_framework


def test_pif_blueprint_loads():
    """Test that PIF.yaml loads successfully."""
    blueprint = load_framework("PIF", "linkedin")

    assert blueprint is not None
    assert blueprint["name"] == "PIF"
    assert blueprint["platform"] == "linkedin"
    assert blueprint["type"] == "framework"


def test_pif_has_required_fields():
    """Test that PIF blueprint has all required fields."""
    blueprint = load_framework("PIF", "linkedin")

    # Top-level fields
    assert "name" in blueprint
    assert "platform" in blueprint
    assert "description" in blueprint
    assert "type" in blueprint
    assert "structure" in blueprint
    assert "validation" in blueprint
    assert "compatible_pillars" in blueprint
    assert "examples" in blueprint
    assert "best_practices" in blueprint
    assert "anti_patterns" in blueprint
    assert "voice_guidelines" in blueprint
    assert "engagement_tactics" in blueprint


def test_pif_structure_has_four_sections():
    """Test that PIF has exactly 4 sections in correct order."""
    blueprint = load_framework("PIF", "linkedin")

    sections = blueprint["structure"]["sections"]
    assert len(sections) == 4

    # Verify section names in correct order
    section_names = [s["name"] for s in sections]
    assert section_names == ["Hook", "Interactive_Element", "Context", "Call_to_Action"]


def test_pif_section_details():
    """Test that each section has description and guidelines."""
    blueprint = load_framework("PIF", "linkedin")

    sections = blueprint["structure"]["sections"]
    for section in sections:
        assert "name" in section
        assert "description" in section
        assert "guidelines" in section
        assert isinstance(section["guidelines"], list)
        assert len(section["guidelines"]) > 0


def test_pif_validation_rules():
    """Test that PIF has proper validation rules."""
    blueprint = load_framework("PIF", "linkedin")

    validation = blueprint["validation"]
    assert validation["min_sections"] == 4
    assert validation["max_sections"] == 4
    assert validation["min_chars"] == 300
    assert validation["max_chars"] == 1000
    assert "required_elements" in validation
    assert isinstance(validation["required_elements"], list)


def test_pif_compatible_pillars():
    """Test that PIF lists compatible content pillars."""
    blueprint = load_framework("PIF", "linkedin")

    pillars = blueprint["compatible_pillars"]
    # PIF is compatible with all pillars
    assert "what_building" in pillars
    assert "what_learning" in pillars
    assert "sales_tech" in pillars
    assert "problem_solution" in pillars


def test_pif_has_examples():
    """Test that PIF includes example posts."""
    blueprint = load_framework("PIF", "linkedin")

    examples = blueprint["examples"]
    assert len(examples) >= 3

    # Check first example structure
    example = examples[0]
    assert "title" in example
    assert "hook" in example
    assert "interactive_element" in example
    assert "context" in example
    assert "call_to_action" in example


def test_pif_best_practices_and_anti_patterns():
    """Test that PIF includes best practices and anti-patterns."""
    blueprint = load_framework("PIF", "linkedin")

    assert isinstance(blueprint["best_practices"], list)
    assert len(blueprint["best_practices"]) > 0

    assert isinstance(blueprint["anti_patterns"], list)
    assert len(blueprint["anti_patterns"]) > 0


def test_pif_voice_guidelines():
    """Test that PIF includes voice guidelines."""
    blueprint = load_framework("PIF", "linkedin")

    assert isinstance(blueprint["voice_guidelines"], list)
    assert len(blueprint["voice_guidelines"]) > 0


def test_pif_engagement_tactics():
    """Test that PIF includes engagement tactics."""
    blueprint = load_framework("PIF", "linkedin")

    assert "engagement_tactics" in blueprint
    assert isinstance(blueprint["engagement_tactics"], list)
    assert len(blueprint["engagement_tactics"]) > 0


def test_pif_caching():
    """Test that PIF blueprint is cached after first load."""
    from lib.blueprint_loader import clear_cache

    # Clear cache first
    clear_cache()

    # First load
    blueprint1 = load_framework("PIF", "linkedin")

    # Second load should return same object (cached)
    blueprint2 = load_framework("PIF", "linkedin")

    # Should be the same object in memory
    assert blueprint1 is blueprint2


def test_pif_description_mentions_engagement():
    """Test that PIF framework emphasizes engagement and participation."""
    blueprint = load_framework("PIF", "linkedin")

    # The framework is about engagement and interaction
    description = blueprint["description"].lower()
    assert "engagement" in description or "interactive" in description or "participation" in description
