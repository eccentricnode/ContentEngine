"""Tests for BrandVoice constraint blueprint."""

from lib.blueprint_loader import load_constraints


def test_brandvoice_constraint_loads():
    """Test that BrandVoice.yaml loads successfully."""
    blueprint = load_constraints("BrandVoice")

    assert blueprint is not None
    assert blueprint["name"] == "BrandVoice"
    assert blueprint["type"] == "constraint"
    assert blueprint["platform"] == "linkedin"


def test_brandvoice_has_required_fields():
    """Test that BrandVoice constraint has all required fields."""
    blueprint = load_constraints("BrandVoice")

    assert "name" in blueprint
    assert "type" in blueprint
    assert "description" in blueprint
    assert "platform" in blueprint
    assert "characteristics" in blueprint
    assert "forbidden_phrases" in blueprint
    assert "style_rules" in blueprint
    assert "content_principles" in blueprint
    assert "validation_flags" in blueprint


def test_brandvoice_characteristics():
    """Test that BrandVoice defines key characteristics."""
    blueprint = load_constraints("BrandVoice")

    characteristics = blueprint["characteristics"]
    assert isinstance(characteristics, list)
    assert len(characteristics) >= 5

    # Check first characteristic structure
    char = characteristics[0]
    assert "id" in char
    assert "description" in char
    assert "examples" in char
    assert "guidelines" in char


def test_brandvoice_forbidden_phrases():
    """Test that BrandVoice lists forbidden phrases."""
    blueprint = load_constraints("BrandVoice")

    forbidden = blueprint["forbidden_phrases"]
    assert "corporate_jargon" in forbidden
    assert "hustle_culture" in forbidden
    assert "empty_motivational" in forbidden
    assert "vague_business_speak" in forbidden

    # Each category should have multiple phrases
    assert isinstance(forbidden["corporate_jargon"], list)
    assert len(forbidden["corporate_jargon"]) > 0


def test_brandvoice_style_rules():
    """Test that BrandVoice defines style rules."""
    blueprint = load_constraints("BrandVoice")

    style = blueprint["style_rules"]
    assert "narrative_voice" in style
    assert "structure" in style
    assert "tone" in style
    assert "technical_communication" in style

    # Each category should have guidelines
    assert isinstance(style["narrative_voice"], list)
    assert len(style["narrative_voice"]) > 0


def test_brandvoice_content_principles():
    """Test that BrandVoice lists content principles."""
    blueprint = load_constraints("BrandVoice")

    principles = blueprint["content_principles"]
    assert isinstance(principles, list)
    assert len(principles) >= 5


def test_brandvoice_validation_flags():
    """Test that BrandVoice defines validation flags."""
    blueprint = load_constraints("BrandVoice")

    flags = blueprint["validation_flags"]
    assert "red_flags" in flags
    assert "yellow_flags" in flags
    assert "green_signals" in flags

    # Each should be a list
    assert isinstance(flags["red_flags"], list)
    assert isinstance(flags["yellow_flags"], list)
    assert isinstance(flags["green_signals"], list)


def test_brandvoice_characteristic_ids():
    """Test that key characteristics are present."""
    blueprint = load_constraints("BrandVoice")

    char_ids = [c["id"] for c in blueprint["characteristics"]]
    assert "technical_but_accessible" in char_ids
    assert "authentic" in char_ids
    assert "confident" in char_ids
    assert "builder_mindset" in char_ids
    assert "specificity_over_generic" in char_ids


def test_brandvoice_examples_structure():
    """Test that characteristics include good/bad examples."""
    blueprint = load_constraints("BrandVoice")

    # Check first characteristic has examples
    char = blueprint["characteristics"][0]
    examples = char["examples"]
    assert isinstance(examples, list)
    assert len(examples) >= 2  # At least one good and one bad example


def test_brandvoice_caching():
    """Test that BrandVoice constraint is cached after first load."""
    from lib.blueprint_loader import clear_cache

    # Clear cache first
    clear_cache()

    # First load
    blueprint1 = load_constraints("BrandVoice")

    # Second load should return same object (cached)
    blueprint2 = load_constraints("BrandVoice")

    # Should be the same object in memory
    assert blueprint1 is blueprint2
