"""Tests for SLA framework blueprint."""

from lib.blueprint_loader import load_framework


def test_sla_blueprint_loads():
    """Test that SLA.yaml loads successfully."""
    blueprint = load_framework("SLA", "linkedin")

    assert blueprint is not None
    assert blueprint["name"] == "SLA"
    assert blueprint["platform"] == "linkedin"
    assert blueprint["type"] == "framework"


def test_sla_has_required_fields():
    """Test that SLA blueprint has all required fields."""
    blueprint = load_framework("SLA", "linkedin")

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


def test_sla_structure_has_three_sections():
    """Test that SLA has exactly 3 sections in correct order."""
    blueprint = load_framework("SLA", "linkedin")

    sections = blueprint["structure"]["sections"]
    assert len(sections) == 3

    # Verify section names in correct order
    section_names = [s["name"] for s in sections]
    assert section_names == ["Story", "Lesson", "Application"]


def test_sla_section_details():
    """Test that each section has description and guidelines."""
    blueprint = load_framework("SLA", "linkedin")

    sections = blueprint["structure"]["sections"]
    for section in sections:
        assert "name" in section
        assert "description" in section
        assert "guidelines" in section
        assert isinstance(section["guidelines"], list)
        assert len(section["guidelines"]) > 0


def test_sla_validation_rules():
    """Test that SLA has proper validation rules."""
    blueprint = load_framework("SLA", "linkedin")

    validation = blueprint["validation"]
    assert validation["min_sections"] == 3
    assert validation["max_sections"] == 3
    assert validation["min_chars"] == 500
    assert validation["max_chars"] == 1400
    assert "required_elements" in validation
    assert isinstance(validation["required_elements"], list)


def test_sla_compatible_pillars():
    """Test that SLA lists compatible content pillars."""
    blueprint = load_framework("SLA", "linkedin")

    pillars = blueprint["compatible_pillars"]
    assert "what_learning" in pillars
    assert "what_building" in pillars
    assert "sales_tech" in pillars


def test_sla_has_examples():
    """Test that SLA includes example posts."""
    blueprint = load_framework("SLA", "linkedin")

    examples = blueprint["examples"]
    assert len(examples) >= 2

    # Check first example structure
    example = examples[0]
    assert "title" in example
    assert "story" in example
    assert "lesson" in example
    assert "application" in example


def test_sla_best_practices_and_anti_patterns():
    """Test that SLA includes best practices and anti-patterns."""
    blueprint = load_framework("SLA", "linkedin")

    assert isinstance(blueprint["best_practices"], list)
    assert len(blueprint["best_practices"]) > 0

    assert isinstance(blueprint["anti_patterns"], list)
    assert len(blueprint["anti_patterns"]) > 0


def test_sla_voice_guidelines():
    """Test that SLA includes voice guidelines."""
    blueprint = load_framework("SLA", "linkedin")

    assert isinstance(blueprint["voice_guidelines"], list)
    assert len(blueprint["voice_guidelines"]) > 0


def test_sla_caching():
    """Test that SLA blueprint is cached after first load."""
    from lib.blueprint_loader import clear_cache

    # Clear cache first
    clear_cache()

    # First load
    blueprint1 = load_framework("SLA", "linkedin")

    # Second load should return same object (cached)
    blueprint2 = load_framework("SLA", "linkedin")

    # Should be the same object in memory
    assert blueprint1 is blueprint2


def test_sla_description_mentions_narrative():
    """Test that SLA framework emphasizes narrative teaching."""
    blueprint = load_framework("SLA", "linkedin")

    # The framework is about narrative teaching with clear takeaways
    description = blueprint["description"].lower()
    assert "narrative" in description or "story" in description
