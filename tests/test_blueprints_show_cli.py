"""Tests for blueprints show CLI command."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cli import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def sample_framework() -> dict:
    """Sample framework blueprint."""
    return {
        "name": "STF",
        "platform": "linkedin",
        "description": "Storytelling Framework",
        "structure": {
            "sections": [
                {"id": "Problem", "description": "The challenge"},
                {"id": "Tried", "description": "What you attempted"},
                {"id": "Worked", "description": "What succeeded"},
                {"id": "Lesson", "description": "Key takeaway"},
            ]
        },
        "validation": {
            "min_chars": 600,
            "max_chars": 1500,
            "min_sections": 4,
        },
        "examples": [
            {"content": "Example 1"},
            {"content": "Example 2"},
        ],
    }


@pytest.fixture
def sample_workflow() -> dict:
    """Sample workflow blueprint."""
    return {
        "name": "SundayPowerHour",
        "description": "Weekly batching workflow",
        "platform": "linkedin",
        "steps": [
            {"id": "step1", "name": "Context Mining", "duration_minutes": 15},
            {"id": "step2", "name": "Categorization", "duration_minutes": 10},
            {"id": "step3", "name": "Framework Selection", "duration_minutes": 5},
        ],
    }


@pytest.fixture
def sample_constraint() -> dict:
    """Sample constraint blueprint."""
    return {
        "name": "BrandVoice",
        "type": "constraint",
        "characteristics": [
            {"id": "technical", "description": "Technical but accessible"},
            {"id": "authentic", "description": "Authentic voice"},
        ],
        "forbidden_phrases": {
            "corporate_jargon": ["leverage synergy", "disrupt"],
            "hustle_culture": ["rise and grind", "crush it"],
        },
    }


@pytest.fixture
def sample_pillars_constraint() -> dict:
    """Sample ContentPillars constraint blueprint."""
    return {
        "name": "ContentPillars",
        "type": "constraint",
        "pillars": {
            "what_building": {
                "name": "What I'm Building",
                "percentage": 35,
            },
            "what_learning": {
                "name": "What I'm Learning",
                "percentage": 30,
            },
        },
    }


def test_show_command_exists(runner: CliRunner) -> None:
    """Test that blueprints show command exists."""
    result = runner.invoke(cli, ["blueprints", "show", "--help"])
    assert result.exit_code == 0
    assert "Show detailed blueprint information" in result.output


def test_show_blueprint_not_found(runner: CliRunner) -> None:
    """Test show command with non-existent blueprint."""
    result = runner.invoke(cli, ["blueprints", "show", "NONEXISTENT"])
    assert result.exit_code == 1
    assert "Blueprint 'NONEXISTENT' not found" in result.output
    assert "blueprints list" in result.output


@patch("cli.load_framework")
def test_show_framework_blueprint(
    mock_load_framework, runner: CliRunner, sample_framework: dict
) -> None:
    """Test showing a framework blueprint."""
    mock_load_framework.return_value = sample_framework

    result = runner.invoke(cli, ["blueprints", "show", "STF"])

    assert result.exit_code == 0
    assert "Framework: STF" in result.output
    assert "Platform: linkedin" in result.output
    assert "Storytelling Framework" in result.output
    assert "📐 Structure:" in result.output
    assert "Sections: 4" in result.output
    assert "Problem" in result.output
    assert "✓ Validation Rules:" in result.output
    assert "Min characters: 600" in result.output
    assert "Max characters: 1500" in result.output
    assert "📝 Examples: 2 provided" in result.output


@patch("cli.load_framework")
@patch("cli.load_workflow")
def test_show_workflow_blueprint(
    mock_load_workflow, mock_load_framework, runner: CliRunner, sample_workflow: dict
) -> None:
    """Test showing a workflow blueprint."""
    mock_load_framework.side_effect = FileNotFoundError
    mock_load_workflow.return_value = sample_workflow

    result = runner.invoke(cli, ["blueprints", "show", "SundayPowerHour"])

    assert result.exit_code == 0
    assert "Workflow: SundayPowerHour" in result.output
    assert "Weekly batching workflow" in result.output
    assert "🔄 Workflow Steps:" in result.output
    assert "Total: 3" in result.output
    assert "Duration: 30 minutes" in result.output
    assert "1. Context Mining (15min)" in result.output
    assert "2. Categorization (10min)" in result.output


@patch("cli.load_framework")
@patch("cli.load_workflow")
@patch("cli.load_constraints")
def test_show_constraint_blueprint(
    mock_load_constraints,
    mock_load_workflow,
    mock_load_framework,
    runner: CliRunner,
    sample_constraint: dict,
) -> None:
    """Test showing a constraint blueprint."""
    mock_load_framework.side_effect = FileNotFoundError
    mock_load_workflow.side_effect = FileNotFoundError
    mock_load_constraints.return_value = sample_constraint

    result = runner.invoke(cli, ["blueprints", "show", "BrandVoice"])

    assert result.exit_code == 0
    assert "Constraint: BrandVoice" in result.output
    assert "⚡ Characteristics: 2" in result.output
    assert "🚫 Forbidden Phrases: 4 total" in result.output


@patch("cli.load_framework")
@patch("cli.load_workflow")
@patch("cli.load_constraints")
def test_show_pillars_constraint(
    mock_load_constraints,
    mock_load_workflow,
    mock_load_framework,
    runner: CliRunner,
    sample_pillars_constraint: dict,
) -> None:
    """Test showing ContentPillars constraint."""
    mock_load_framework.side_effect = FileNotFoundError
    mock_load_workflow.side_effect = FileNotFoundError
    mock_load_constraints.return_value = sample_pillars_constraint

    result = runner.invoke(cli, ["blueprints", "show", "ContentPillars"])

    assert result.exit_code == 0
    assert "Constraint: ContentPillars" in result.output
    assert "📊 Pillars: 2" in result.output
    assert "What I'm Building: 35%" in result.output
    assert "What I'm Learning: 30%" in result.output


@patch("cli.load_framework")
def test_show_with_custom_platform(
    mock_load_framework, runner: CliRunner, sample_framework: dict
) -> None:
    """Test show command with custom platform."""
    mock_load_framework.return_value = sample_framework

    result = runner.invoke(cli, ["blueprints", "show", "STF", "--platform", "twitter"])

    assert result.exit_code == 0
    assert "Framework: STF" in result.output
    mock_load_framework.assert_called_once_with("STF", "twitter")


@patch("cli.load_framework")
def test_show_displays_yaml(
    mock_load_framework, runner: CliRunner, sample_framework: dict
) -> None:
    """Test that show command displays YAML content."""
    mock_load_framework.return_value = sample_framework

    result = runner.invoke(cli, ["blueprints", "show", "STF"])

    assert result.exit_code == 0
    # Check for YAML-formatted content
    assert "name: STF" in result.output
    assert "platform: linkedin" in result.output
    assert "min_chars: 600" in result.output


@patch("cli.load_framework")
def test_show_handles_exception(mock_load_framework, runner: CliRunner) -> None:
    """Test that show command handles exceptions gracefully."""
    mock_load_framework.side_effect = ValueError("Something went wrong")

    result = runner.invoke(cli, ["blueprints", "show", "STF"])

    assert result.exit_code == 1
    assert "Failed to show blueprint" in result.output
