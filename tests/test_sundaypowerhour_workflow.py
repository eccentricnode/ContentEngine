"""Tests for SundayPowerHour workflow blueprint."""

from lib.blueprint_loader import load_workflow


def test_workflow_loads_successfully():
    """Test that SundayPowerHour workflow loads without errors."""
    workflow = load_workflow("SundayPowerHour")
    assert workflow is not None
    assert isinstance(workflow, dict)


def test_workflow_has_required_fields():
    """Test that workflow has all required fields."""
    workflow = load_workflow("SundayPowerHour")

    # Top-level fields
    assert "name" in workflow
    assert "description" in workflow
    assert "platform" in workflow
    assert "steps" in workflow
    assert "benefits" in workflow

    # Validate values
    assert workflow["name"] == "SundayPowerHour"
    assert workflow["platform"] == "linkedin"
    assert workflow["frequency"] == "weekly"
    assert workflow["target_output"] == 10


def test_workflow_has_five_steps():
    """Test that workflow has exactly 5 steps."""
    workflow = load_workflow("SundayPowerHour")

    assert len(workflow["steps"]) == 5

    # Verify step IDs
    step_ids = [step["id"] for step in workflow["steps"]]
    expected_ids = [
        "context_mining",
        "pillar_categorization",
        "framework_selection",
        "batch_writing",
        "polish_and_schedule",
    ]
    assert step_ids == expected_ids


def test_each_step_has_required_fields():
    """Test that each step has all required fields."""
    workflow = load_workflow("SundayPowerHour")

    required_fields = ["id", "name", "duration_minutes", "description", "inputs", "outputs"]

    for step in workflow["steps"]:
        for field in required_fields:
            assert field in step, f"Step {step.get('id')} missing field: {field}"


def test_step_durations_are_valid():
    """Test that step durations are positive integers."""
    workflow = load_workflow("SundayPowerHour")

    for step in workflow["steps"]:
        duration = step["duration_minutes"]
        assert isinstance(duration, int)
        assert duration > 0
        assert duration <= 120  # Reasonable max


def test_total_duration_matches_steps():
    """Test that estimated total duration is close to sum of steps."""
    workflow = load_workflow("SundayPowerHour")

    total_from_steps = sum(step["duration_minutes"] for step in workflow["steps"])
    estimated_total = workflow["estimated_total_duration"]

    # Allow 10-minute buffer for overhead
    assert abs(total_from_steps - estimated_total) <= 10


def test_context_mining_step():
    """Test context_mining step structure."""
    workflow = load_workflow("SundayPowerHour")
    step = workflow["steps"][0]

    assert step["id"] == "context_mining"
    assert step["name"] == "Context Mining"
    assert "prompt_template" in step

    # Verify inputs
    assert "session history" in " ".join(step["inputs"]).lower()
    assert "project notes" in " ".join(step["inputs"]).lower()

    # Verify outputs
    assert len(step["outputs"]) >= 3
    assert "content ideas" in " ".join(step["outputs"]).lower()


def test_pillar_categorization_step():
    """Test pillar_categorization step structure."""
    workflow = load_workflow("SundayPowerHour")
    step = workflow["steps"][1]

    assert step["id"] == "pillar_categorization"
    assert step["name"] == "Pillar Categorization"
    assert "prompt_template" in step

    # Verify mentions content pillars
    prompt = step["prompt_template"]
    assert "what_building" in prompt
    assert "what_learning" in prompt
    assert "sales_tech" in prompt
    assert "problem_solution" in prompt


def test_framework_selection_step():
    """Test framework_selection step structure."""
    workflow = load_workflow("SundayPowerHour")
    step = workflow["steps"][2]

    assert step["id"] == "framework_selection"
    assert "Framework" in step["name"]
    assert "prompt_template" in step

    # Verify mentions all frameworks
    prompt = step["prompt_template"]
    assert "STF" in prompt
    assert "MRS" in prompt
    assert "SLA" in prompt
    assert "PIF" in prompt


def test_batch_writing_step():
    """Test batch_writing step structure."""
    workflow = load_workflow("SundayPowerHour")
    step = workflow["steps"][3]

    assert step["id"] == "batch_writing"
    assert step["duration_minutes"] >= 45  # Longest step
    assert "prompt_template" in step
    assert "process" in step

    # Verify process steps
    process = step["process"]
    assert isinstance(process, list)
    assert len(process) >= 4


def test_polish_and_schedule_step():
    """Test polish_and_schedule step structure."""
    workflow = load_workflow("SundayPowerHour")
    step = workflow["steps"][4]

    assert step["id"] == "polish_and_schedule"
    assert "prompt_template" in step

    # Verify outputs include schedule
    outputs_str = " ".join(step["outputs"]).lower()
    assert "schedule" in outputs_str or "polish" in outputs_str


def test_benefits_documented():
    """Test that batching benefits are documented."""
    workflow = load_workflow("SundayPowerHour")

    benefits = workflow["benefits"]
    assert "context_switching_savings" in benefits
    assert benefits["context_switching_savings"] == "92 minutes per week"
    assert "explanation" in benefits
    assert "additional_benefits" in benefits

    # Verify additional benefits list
    assert isinstance(benefits["additional_benefits"], list)
    assert len(benefits["additional_benefits"]) >= 3


def test_prerequisites_defined():
    """Test that prerequisites are clearly defined."""
    workflow = load_workflow("SundayPowerHour")

    assert "prerequisites" in workflow
    prereqs = workflow["prerequisites"]
    assert isinstance(prereqs, list)
    assert len(prereqs) >= 2

    # Check for key prerequisites
    prereqs_str = " ".join(prereqs).lower()
    assert "session" in prereqs_str or "history" in prereqs_str
    assert "ollama" in prereqs_str


def test_success_criteria_defined():
    """Test that success criteria are defined."""
    workflow = load_workflow("SundayPowerHour")

    assert "success_criteria" in workflow
    criteria = workflow["success_criteria"]
    assert isinstance(criteria, list)
    assert len(criteria) >= 3

    # Verify mentions 10 posts
    criteria_str = " ".join(criteria).lower()
    assert "10" in criteria_str and "post" in criteria_str


def test_example_output_structure():
    """Test that example output is provided."""
    workflow = load_workflow("SundayPowerHour")

    assert "example_output" in workflow
    example = workflow["example_output"]

    # Verify key output metrics
    assert "posts_generated" in example
    assert example["posts_generated"] == 10

    assert "distribution" in example
    distribution = example["distribution"]
    total_posts = sum(distribution.values())
    assert total_posts == 10

    assert "average_validation_score" in example
    assert 0.0 <= example["average_validation_score"] <= 1.0


def test_step_prompt_templates_are_mustache():
    """Test that prompt templates use Mustache syntax."""
    workflow = load_workflow("SundayPowerHour")

    for step in workflow["steps"]:
        if "prompt_template" in step:
            template = step["prompt_template"]
            # Should contain Mustache variables
            assert "{{" in template and "}}" in template


def test_workflow_caching():
    """Test that workflow is cached on second load."""
    # First load
    workflow1 = load_workflow("SundayPowerHour")

    # Second load (should be from cache)
    workflow2 = load_workflow("SundayPowerHour")

    # Should be same object reference due to caching
    assert workflow1 is workflow2


def test_workflow_metadata():
    """Test workflow metadata fields."""
    workflow = load_workflow("SundayPowerHour")

    assert "estimated_total_duration" in workflow
    assert workflow["estimated_total_duration"] > 0

    assert "difficulty" in workflow
    assert workflow["difficulty"] in ["beginner", "intermediate", "advanced"]

    assert "frequency" in workflow
    assert workflow["frequency"] == "weekly"


def test_pillar_distribution_percentages():
    """Test that example output matches pillar distribution targets."""
    workflow = load_workflow("SundayPowerHour")

    distribution = workflow["example_output"]["distribution"]

    # Verify approximate percentages (±5%)
    assert 3 <= distribution["what_building"] <= 4  # 35%
    assert 2 <= distribution["what_learning"] <= 3  # 30%
    assert 2 <= distribution["sales_tech"] <= 2  # 20%
    assert 1 <= distribution["problem_solution"] <= 2  # 15%
