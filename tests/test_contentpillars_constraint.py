"""Tests for ContentPillars constraint blueprint."""

from lib.blueprint_loader import load_constraints


def test_contentpillars_loads_successfully() -> None:
    """Test that ContentPillars constraint loads without errors."""
    constraint = load_constraints("ContentPillars")
    assert constraint is not None
    assert constraint["name"] == "ContentPillars"


def test_contentpillars_required_fields() -> None:
    """Test that ContentPillars has all required fields."""
    constraint = load_constraints("ContentPillars")

    assert "name" in constraint
    assert "type" in constraint
    assert "description" in constraint
    assert "pillars" in constraint
    assert "distribution_rules" in constraint
    assert "validation" in constraint
    assert "content_principles" in constraint
    assert "examples" in constraint

    assert constraint["type"] == "constraint"


def test_contentpillars_has_four_pillars() -> None:
    """Test that ContentPillars defines exactly 4 pillars."""
    constraint = load_constraints("ContentPillars")
    pillars = constraint["pillars"]

    assert len(pillars) == 4
    assert "what_building" in pillars
    assert "what_learning" in pillars
    assert "sales_tech" in pillars
    assert "problem_solution" in pillars


def test_contentpillars_pillar_percentages() -> None:
    """Test that pillar percentages match requirements."""
    constraint = load_constraints("ContentPillars")
    pillars = constraint["pillars"]

    assert pillars["what_building"]["percentage"] == 35
    assert pillars["what_learning"]["percentage"] == 30
    assert pillars["sales_tech"]["percentage"] == 20
    assert pillars["problem_solution"]["percentage"] == 15

    # Total should be 100%
    total = sum(p["percentage"] for p in pillars.values())
    assert total == 100


def test_contentpillars_pillar_structure() -> None:
    """Test that each pillar has required fields."""
    constraint = load_constraints("ContentPillars")
    pillars = constraint["pillars"]

    for pillar_id, pillar_data in pillars.items():
        assert "name" in pillar_data, f"Pillar {pillar_id} missing 'name'"
        assert "description" in pillar_data, f"Pillar {pillar_id} missing 'description'"
        assert "percentage" in pillar_data, f"Pillar {pillar_id} missing 'percentage'"
        assert "examples" in pillar_data, f"Pillar {pillar_id} missing 'examples'"
        assert "characteristics" in pillar_data, f"Pillar {pillar_id} missing 'characteristics'"
        assert "themes" in pillar_data, f"Pillar {pillar_id} missing 'themes'"

        # Examples should be a list with at least 2 items
        assert isinstance(pillar_data["examples"], list)
        assert len(pillar_data["examples"]) >= 2

        # Themes should be a list
        assert isinstance(pillar_data["themes"], list)
        assert len(pillar_data["themes"]) > 0


def test_contentpillars_distribution_rules() -> None:
    """Test distribution rules are defined."""
    constraint = load_constraints("ContentPillars")
    rules = constraint["distribution_rules"]

    assert "weekly_minimum" in rules
    assert "weekly_maximum" in rules
    assert "ideal_weekly" in rules
    assert "pillar_balance_window" in rules
    assert "description" in rules

    assert rules["weekly_minimum"] == 3
    assert rules["weekly_maximum"] == 7
    assert rules["ideal_weekly"] == 5
    assert rules["pillar_balance_window"] == "weekly"


def test_contentpillars_validation_rules() -> None:
    """Test validation rules are defined."""
    constraint = load_constraints("ContentPillars")
    validation = constraint["validation"]

    assert "check_pillar_balance" in validation
    assert "check_pillar_drift" in validation
    assert "min_posts_per_pillar" in validation

    # Each validation should have description and severity
    for rule_name, rule_data in validation.items():
        assert "description" in rule_data, f"Validation {rule_name} missing description"
        assert "severity" in rule_data, f"Validation {rule_name} missing severity"
        assert rule_data["severity"] in ["warning", "error"]


def test_contentpillars_content_principles() -> None:
    """Test content principles are defined."""
    constraint = load_constraints("ContentPillars")
    principles = constraint["content_principles"]

    assert isinstance(principles, list)
    assert len(principles) >= 3

    for principle in principles:
        assert "name" in principle
        assert "description" in principle


def test_contentpillars_examples() -> None:
    """Test examples section has balanced_week and poor_balance."""
    constraint = load_constraints("ContentPillars")
    examples = constraint["examples"]

    assert "balanced_week" in examples
    assert "poor_balance" in examples

    # Balanced week should have 5 posts
    balanced = examples["balanced_week"]
    assert "monday" in balanced
    assert "tuesday" in balanced
    assert "wednesday" in balanced
    assert "thursday" in balanced
    assert "friday" in balanced

    # Each day should have pillar, framework, topic
    for day_name, day_data in balanced.items():
        assert "pillar" in day_data, f"{day_name} missing pillar"
        assert "framework" in day_data, f"{day_name} missing framework"
        assert "topic" in day_data, f"{day_name} missing topic"

    # Poor balance example should show issue/consequence/fix
    poor = examples["poor_balance"]
    assert "issue" in poor
    assert "consequence" in poor
    assert "fix" in poor


def test_contentpillars_caching() -> None:
    """Test that ContentPillars constraint is cached on second load."""
    from lib.blueprint_loader import clear_cache

    # Clear cache first
    clear_cache()

    # First load - not cached
    constraint1 = load_constraints("ContentPillars")

    # Second load - should be cached (same object)
    constraint2 = load_constraints("ContentPillars")

    assert constraint1 is constraint2


def test_contentpillars_metadata() -> None:
    """Test metadata fields exist."""
    constraint = load_constraints("ContentPillars")

    assert "metadata" in constraint
    metadata = constraint["metadata"]

    assert "version" in metadata
    assert "created_at" in metadata
    assert "platform" in metadata
    assert "author" in metadata

    assert metadata["platform"] == "linkedin"
