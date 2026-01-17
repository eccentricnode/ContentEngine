"""Tests for STF framework blueprint."""

from lib.blueprint_loader import load_framework


def test_stf_blueprint_loads():
    """Test that STF.yaml loads successfully."""
    blueprint = load_framework("STF", "linkedin")

    assert blueprint is not None
    assert blueprint["name"] == "STF"
    assert blueprint["platform"] == "linkedin"
    assert blueprint["type"] == "framework"


def test_stf_has_required_fields():
    """Test that STF blueprint has all required fields."""
    blueprint = load_framework("STF", "linkedin")

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


def test_stf_structure_has_four_sections():
    """Test that STF has exactly 4 sections in correct order."""
    blueprint = load_framework("STF", "linkedin")

    sections = blueprint["structure"]["sections"]
    assert len(sections) == 4

    # Verify section names in correct order
    section_names = [s["name"] for s in sections]
    assert section_names == ["Problem", "Tried", "Worked", "Lesson"]


def test_stf_section_details():
    """Test that each section has description and guidelines."""
    blueprint = load_framework("STF", "linkedin")

    sections = blueprint["structure"]["sections"]
    for section in sections:
        assert "name" in section
        assert "description" in section
        assert "guidelines" in section
        assert isinstance(section["guidelines"], list)
        assert len(section["guidelines"]) > 0


def test_stf_validation_rules():
    """Test that STF has proper validation rules."""
    blueprint = load_framework("STF", "linkedin")

    validation = blueprint["validation"]
    assert validation["min_sections"] == 4
    assert validation["max_sections"] == 4
    assert validation["min_chars"] == 600
    assert validation["max_chars"] == 1500
    assert "required_elements" in validation
    assert isinstance(validation["required_elements"], list)


def test_stf_compatible_pillars():
    """Test that STF lists compatible content pillars."""
    blueprint = load_framework("STF", "linkedin")

    pillars = blueprint["compatible_pillars"]
    assert "what_building" in pillars
    assert "what_learning" in pillars
    assert "problem_solution" in pillars


def test_stf_has_examples():
    """Test that STF includes example posts."""
    blueprint = load_framework("STF", "linkedin")

    examples = blueprint["examples"]
    assert len(examples) >= 2

    # Check first example structure
    example = examples[0]
    assert "title" in example
    assert "problem" in example
    assert "tried" in example
    assert "worked" in example
    assert "lesson" in example


def test_stf_best_practices_and_anti_patterns():
    """Test that STF includes best practices and anti-patterns."""
    blueprint = load_framework("STF", "linkedin")

    assert isinstance(blueprint["best_practices"], list)
    assert len(blueprint["best_practices"]) > 0

    assert isinstance(blueprint["anti_patterns"], list)
    assert len(blueprint["anti_patterns"]) > 0


def test_stf_voice_guidelines():
    """Test that STF includes voice guidelines."""
    blueprint = load_framework("STF", "linkedin")

    assert isinstance(blueprint["voice_guidelines"], list)
    assert len(blueprint["voice_guidelines"]) > 0


def test_stf_caching():
    """Test that STF blueprint is cached after first load."""
    from lib.blueprint_loader import clear_cache

    # Clear cache first
    clear_cache()

    # First load
    blueprint1 = load_framework("STF", "linkedin")

    # Second load should return same object (cached)
    blueprint2 = load_framework("STF", "linkedin")

    # Should be the same object in memory
    assert blueprint1 is blueprint2
