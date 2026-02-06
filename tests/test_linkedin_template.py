"""Tests for LinkedInPost.hbs template."""

from lib.blueprint_loader import load_constraints, load_framework
from lib.template_renderer import render_template


def test_linkedin_template_renders_successfully() -> None:
    """Test that LinkedInPost template renders without errors."""
    # Load framework and constraints
    framework = load_framework("STF", "linkedin")
    brand_voice = load_constraints("BrandVoice")
    pillars = load_constraints("ContentPillars")

    # Prepare template context
    context_data = {
        "context": {
            "themes": ["Built blueprint system", "Added validation engine"],
            "decisions": ["Chose YAML for blueprints", "Used Mustache templates"],
            "progress": [
                "Implemented 12 user stories",
                "Created 4 framework blueprints",
            ],
        },
        "pillar_name": "What I'm Building",
        "pillar_description": pillars["pillars"]["what_building"]["description"],
        "pillar_characteristics": [
            "specific_metrics",
            "technical_depth",
            "progress_narrative",
        ],
        "framework_name": "STF",
        "framework_sections": framework["structure"]["sections"],
        "brand_voice_characteristics": [
            {"name": char["id"], "description": char.get("description", "")}
            for char in brand_voice["characteristics"]
        ],
        "forbidden_phrases": [
            phrase
            for category_phrases in brand_voice["forbidden_phrases"].values()
            for phrase in category_phrases
        ][:10],  # Limit to first 10 for template brevity
        "brand_voice_style": [
            {
                "name": style_id,
                "description": ", ".join(rules) if isinstance(rules, list) else rules,
            }
            for style_id, rules in brand_voice["style_rules"].items()
        ],
        "validation_min_chars": framework["validation"]["min_chars"],
        "validation_max_chars": framework["validation"]["max_chars"],
        "validation_min_sections": framework["validation"]["min_sections"],
    }

    # Render template
    rendered = render_template("LinkedInPost.hbs", context_data)

    # Basic assertions
    assert rendered is not None
    assert len(rendered) > 0
    assert "STF" in rendered
    assert "Austin" in rendered


def test_linkedin_template_includes_context() -> None:
    """Test that template includes context sections."""
    framework = load_framework("STF", "linkedin")

    context_data = {
        "context": {
            "themes": ["Theme 1", "Theme 2"],
            "decisions": ["Decision 1"],
            "progress": ["Progress 1"],
        },
        "pillar_name": "Test Pillar",
        "pillar_description": "Test description",
        "pillar_characteristics": ["char1"],
        "framework_name": "STF",
        "framework_sections": framework["structure"]["sections"],
        "brand_voice_characteristics": [
            {"name": "test", "description": "test desc"}
        ],
        "forbidden_phrases": ["test phrase"],
        "brand_voice_style": [{"name": "test", "description": "test"}],
        "validation_min_chars": 600,
        "validation_max_chars": 1500,
        "validation_min_sections": 4,
    }

    rendered = render_template("LinkedInPost.hbs", context_data)

    assert "Theme 1" in rendered
    assert "Theme 2" in rendered
    assert "Decision 1" in rendered
    assert "Progress 1" in rendered


def test_linkedin_template_includes_framework() -> None:
    """Test that template includes framework sections."""
    framework = load_framework("STF", "linkedin")

    context_data = {
        "context": {"themes": [], "decisions": [], "progress": []},
        "pillar_name": "Test",
        "pillar_description": "Test",
        "pillar_characteristics": [],
        "framework_name": "STF",
        "framework_sections": framework["structure"]["sections"],
        "brand_voice_characteristics": [],
        "forbidden_phrases": [],
        "brand_voice_style": [],
        "validation_min_chars": 600,
        "validation_max_chars": 1500,
        "validation_min_sections": 4,
    }

    rendered = render_template("LinkedInPost.hbs", context_data)

    # Check that all STF sections appear
    assert "Problem" in rendered
    assert "Tried" in rendered
    assert "Worked" in rendered
    assert "Lesson" in rendered


def test_linkedin_template_includes_brand_voice() -> None:
    """Test that template includes brand voice constraints."""
    framework = load_framework("STF", "linkedin")

    context_data = {
        "context": {"themes": [], "decisions": [], "progress": []},
        "pillar_name": "Test",
        "pillar_description": "Test",
        "pillar_characteristics": [],
        "framework_name": "STF",
        "framework_sections": framework["structure"]["sections"],
        "brand_voice_characteristics": [
            {
                "name": "technical_but_accessible",
                "description": "Balance technical depth with clarity",
            }
        ],
        "forbidden_phrases": ["leverage synergies", "disrupt"],
        "brand_voice_style": [
            {"name": "narrative_voice", "description": "First-person storytelling"}
        ],
        "validation_min_chars": 600,
        "validation_max_chars": 1500,
        "validation_min_sections": 4,
    }

    rendered = render_template("LinkedInPost.hbs", context_data)

    assert "technical_but_accessible" in rendered
    assert "leverage synergies" in rendered
    assert "disrupt" in rendered
    assert "narrative_voice" in rendered


def test_linkedin_template_includes_validation_requirements() -> None:
    """Test that template includes validation requirements."""
    framework = load_framework("STF", "linkedin")

    context_data = {
        "context": {"themes": [], "decisions": [], "progress": []},
        "pillar_name": "Test",
        "pillar_description": "Test",
        "pillar_characteristics": [],
        "framework_name": "STF",
        "framework_sections": framework["structure"]["sections"],
        "brand_voice_characteristics": [],
        "forbidden_phrases": [],
        "brand_voice_style": [],
        "validation_min_chars": 600,
        "validation_max_chars": 1500,
        "validation_min_sections": 4,
    }

    rendered = render_template("LinkedInPost.hbs", context_data)

    assert "600" in rendered
    assert "1500" in rendered
    assert "4" in rendered or "four" in rendered.lower()


def test_linkedin_template_with_mrs_framework() -> None:
    """Test template works with MRS framework."""
    framework = load_framework("MRS", "linkedin")

    context_data = {
        "context": {"themes": ["Learning mistake"], "decisions": [], "progress": []},
        "pillar_name": "What I'm Learning",
        "pillar_description": "Document learning journey",
        "pillar_characteristics": ["depth_over_breadth"],
        "framework_name": "MRS",
        "framework_sections": framework["structure"]["sections"],
        "brand_voice_characteristics": [],
        "forbidden_phrases": [],
        "brand_voice_style": [],
        "validation_min_chars": 500,
        "validation_max_chars": 1300,
        "validation_min_sections": 3,
    }

    rendered = render_template("LinkedInPost.hbs", context_data)

    assert "MRS" in rendered
    assert "Mistake" in rendered
    assert "Realization" in rendered
    assert "Shift" in rendered


def test_linkedin_template_with_pif_framework() -> None:
    """Test template works with PIF framework."""
    framework = load_framework("PIF", "linkedin")

    context_data = {
        "context": {"themes": ["Poll question"], "decisions": [], "progress": []},
        "pillar_name": "Test",
        "pillar_description": "Test",
        "pillar_characteristics": [],
        "framework_name": "PIF",
        "framework_sections": framework["structure"]["sections"],
        "brand_voice_characteristics": [],
        "forbidden_phrases": [],
        "brand_voice_style": [],
        "validation_min_chars": 300,
        "validation_max_chars": 1000,
        "validation_min_sections": 4,
    }

    rendered = render_template("LinkedInPost.hbs", context_data)

    assert "PIF" in rendered
    assert "Hook" in rendered
    assert "Interactive_Element" in rendered or "Interactive" in rendered


def test_linkedin_template_empty_context() -> None:
    """Test template handles empty context gracefully."""
    framework = load_framework("STF", "linkedin")

    context_data = {
        "context": {"themes": [], "decisions": [], "progress": []},
        "pillar_name": "Test",
        "pillar_description": "Test",
        "pillar_characteristics": [],
        "framework_name": "STF",
        "framework_sections": framework["structure"]["sections"],
        "brand_voice_characteristics": [],
        "forbidden_phrases": [],
        "brand_voice_style": [],
        "validation_min_chars": 600,
        "validation_max_chars": 1500,
        "validation_min_sections": 4,
    }

    # Should render without errors even with empty lists
    rendered = render_template("LinkedInPost.hbs", context_data)
    assert rendered is not None
    assert "STF" in rendered
