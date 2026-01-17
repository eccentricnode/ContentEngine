"""Tests for Repurposing1to10 workflow blueprint."""

from typing import Generator
import pytest

from lib.blueprint_loader import load_workflow, clear_cache


@pytest.fixture(autouse=True)
def clear_blueprint_cache() -> Generator[None, None, None]:
    """Clear blueprint cache before each test."""
    clear_cache()
    yield
    clear_cache()


def test_repurposing_workflow_loads() -> None:
    """Test that Repurposing1to10 workflow YAML loads successfully."""
    workflow = load_workflow("Repurposing1to10")
    assert workflow is not None
    assert workflow["name"] == "Repurposing1to10"


def test_repurposing_required_fields() -> None:
    """Test that workflow has all required fields."""
    workflow = load_workflow("Repurposing1to10")

    required_fields = [
        "name",
        "description",
        "platform",
        "frequency",
        "target_output",
        "benefits",
        "steps",
        "estimated_total_duration",
        "difficulty",
        "prerequisites",
        "success_criteria",
    ]

    for field in required_fields:
        assert field in workflow, f"Missing required field: {field}"


def test_repurposing_has_five_steps() -> None:
    """Test that workflow has exactly 5 steps."""
    workflow = load_workflow("Repurposing1to10")
    assert "steps" in workflow
    assert len(workflow["steps"]) == 5


def test_repurposing_step_order() -> None:
    """Test that steps are in correct order."""
    workflow = load_workflow("Repurposing1to10")
    steps = workflow["steps"]

    expected_order = [
        "idea_extraction",
        "platform_mapping",
        "content_adaptation",
        "cross_linking",
        "validation_and_polish",
    ]

    actual_order = [step["id"] for step in steps]
    assert actual_order == expected_order


def test_repurposing_step_metadata() -> None:
    """Test that each step has required metadata."""
    workflow = load_workflow("Repurposing1to10")

    required_step_fields = [
        "id",
        "name",
        "duration_minutes",
        "description",
        "inputs",
        "outputs",
        "prompt_template",
    ]

    for step in workflow["steps"]:
        for field in required_step_fields:
            assert field in step, f"Step {step['id']} missing field: {field}"

        # Verify types
        assert isinstance(step["id"], str)
        assert isinstance(step["name"], str)
        assert isinstance(step["duration_minutes"], int)
        assert isinstance(step["inputs"], list)
        assert isinstance(step["outputs"], list)
        assert isinstance(step["prompt_template"], str)


def test_repurposing_prompt_templates_have_mustache() -> None:
    """Test that prompt templates use Mustache syntax."""
    workflow = load_workflow("Repurposing1to10")

    # Check that at least some templates have Mustache variables
    templates_with_mustache = 0
    for step in workflow["steps"]:
        template = step["prompt_template"]
        if "{{" in template and "}}" in template:
            templates_with_mustache += 1

    assert templates_with_mustache >= 3, "Expected Mustache variables in multiple templates"


def test_repurposing_benefits_structure() -> None:
    """Test that benefits section has expected structure."""
    workflow = load_workflow("Repurposing1to10")
    benefits = workflow["benefits"]

    assert "efficiency_multiplier" in benefits
    assert "explanation" in benefits
    assert "additional_benefits" in benefits
    assert isinstance(benefits["additional_benefits"], list)
    assert len(benefits["additional_benefits"]) >= 3


def test_repurposing_platform_constraints() -> None:
    """Test that platform constraints are defined."""
    workflow = load_workflow("Repurposing1to10")

    assert "platform_constraints" in workflow
    constraints = workflow["platform_constraints"]

    # Check key platforms
    assert "linkedin" in constraints
    assert "twitter" in constraints
    assert "blog" in constraints
    assert "visual" in constraints

    # Check LinkedIn constraints
    linkedin = constraints["linkedin"]
    assert "max_chars" in linkedin
    assert "optimal_chars" in linkedin
    assert linkedin["max_chars"] == 3000


def test_repurposing_templates_by_pillar() -> None:
    """Test that repurposing templates are defined for all pillars."""
    workflow = load_workflow("Repurposing1to10")

    assert "repurposing_templates" in workflow
    templates = workflow["repurposing_templates"]

    # All 4 content pillars should have templates
    assert "what_building" in templates
    assert "what_learning" in templates
    assert "sales_tech" in templates
    assert "problem_solution" in templates

    # Each pillar should have format recommendations
    for pillar, config in templates.items():
        assert "primary_formats" in config
        assert "secondary_formats" in config
        assert "emphasis" in config
        assert isinstance(config["primary_formats"], list)
        assert len(config["primary_formats"]) >= 2


def test_repurposing_prerequisites() -> None:
    """Test that prerequisites are defined."""
    workflow = load_workflow("Repurposing1to10")
    prerequisites = workflow["prerequisites"]

    assert isinstance(prerequisites, list)
    assert len(prerequisites) >= 2


def test_repurposing_success_criteria() -> None:
    """Test that success criteria are defined."""
    workflow = load_workflow("Repurposing1to10")
    criteria = workflow["success_criteria"]

    assert isinstance(criteria, list)
    assert len(criteria) >= 3


def test_repurposing_example_output() -> None:
    """Test that example output is provided."""
    workflow = load_workflow("Repurposing1to10")

    assert "example_output" in workflow
    example = workflow["example_output"]

    assert "core_idea" in example
    assert "pieces_created" in example
    assert example["pieces_created"] == 10
    assert "distribution" in example
    assert "publishing_timeline" in example


def test_repurposing_metadata() -> None:
    """Test metadata fields."""
    workflow = load_workflow("Repurposing1to10")

    assert workflow["platform"] == "multi_platform"
    assert workflow["frequency"] == "on_demand"
    assert workflow["target_output"] == 10
    assert workflow["difficulty"] == "advanced"
    assert isinstance(workflow["estimated_total_duration"], int)


def test_repurposing_step_durations_sum() -> None:
    """Test that step durations roughly match total duration."""
    workflow = load_workflow("Repurposing1to10")

    steps_total = sum(step["duration_minutes"] for step in workflow["steps"])
    estimated_total = workflow["estimated_total_duration"]

    # Allow some variance for overhead/transitions
    assert abs(steps_total - estimated_total) <= 10, \
        f"Steps sum to {steps_total} but total is {estimated_total}"


def test_repurposing_content_adaptation_has_process() -> None:
    """Test that content_adaptation step has process field."""
    workflow = load_workflow("Repurposing1to10")

    # Find content_adaptation step
    content_adaptation = next(
        step for step in workflow["steps"]
        if step["id"] == "content_adaptation"
    )

    assert "process" in content_adaptation
    assert isinstance(content_adaptation["process"], list)
    assert len(content_adaptation["process"]) >= 3


def test_repurposing_description() -> None:
    """Test that description explains the workflow."""
    workflow = load_workflow("Repurposing1to10")

    description = workflow["description"]
    assert "one core idea" in description.lower() or "1" in description
    assert "10" in description
    assert "content" in description.lower()


def test_repurposing_caches_correctly() -> None:
    """Test that workflow is cached after first load."""
    # First load
    workflow1 = load_workflow("Repurposing1to10")

    # Second load (should be cached)
    workflow2 = load_workflow("Repurposing1to10")

    # Should be the same object reference
    assert workflow1 is workflow2


def test_repurposing_cross_linking_step() -> None:
    """Test cross-linking step has appropriate fields."""
    workflow = load_workflow("Repurposing1to10")

    cross_linking = next(
        step for step in workflow["steps"]
        if step["id"] == "cross_linking"
    )

    # Should focus on cross-promotion strategy
    assert "cross-promotion" in cross_linking["description"].lower() or \
           "cross-linking" in cross_linking["description"].lower()

    # Outputs should include linking strategy
    outputs = " ".join(cross_linking["outputs"]).lower()
    assert "cross" in outputs or "link" in outputs or "promotion" in outputs
