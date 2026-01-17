"""Tests for workflow execution in blueprint_engine."""

from typing import Any

from lib.blueprint_engine import execute_workflow, WorkflowResult


def test_execute_workflow_loads_workflow() -> None:
    """Test that execute_workflow loads a workflow blueprint."""
    inputs = {"test_input": "value"}
    result = execute_workflow("SundayPowerHour", inputs)

    assert isinstance(result, WorkflowResult)
    assert result.workflow_name == "SundayPowerHour"


def test_execute_workflow_success() -> None:
    """Test successful workflow execution."""
    inputs = {"session_history": ["session1", "session2"], "projects": ["project1"]}
    result = execute_workflow("SundayPowerHour", inputs)

    assert result.success is True
    assert result.steps_completed == result.total_steps
    assert len(result.errors) == 0


def test_execute_workflow_total_steps() -> None:
    """Test that total_steps matches workflow definition."""
    inputs: dict[str, Any] = {}
    result = execute_workflow("SundayPowerHour", inputs)

    # SundayPowerHour has 5 steps
    assert result.total_steps == 5
    assert result.steps_completed == 5


def test_execute_workflow_outputs_include_inputs() -> None:
    """Test that workflow outputs include initial inputs."""
    inputs = {"session_history": ["session1"], "projects": ["project1"]}
    result = execute_workflow("SundayPowerHour", inputs)

    assert "session_history" in result.outputs
    assert "projects" in result.outputs
    assert result.outputs["session_history"] == ["session1"]
    assert result.outputs["projects"] == ["project1"]


def test_execute_workflow_step_execution_tracking() -> None:
    """Test that each step execution is tracked in outputs."""
    inputs: dict[str, Any] = {}
    result = execute_workflow("SundayPowerHour", inputs)

    # Check that each step is marked as executed
    expected_steps = [
        "context_mining",
        "pillar_categorization",
        "framework_selection",
        "batch_writing",
        "polish_and_schedule",
    ]

    for step_id in expected_steps:
        assert f"{step_id}_executed" in result.outputs
        assert result.outputs[f"{step_id}_executed"] is True
        assert f"{step_id}_name" in result.outputs


def test_execute_workflow_invalid_name() -> None:
    """Test handling of invalid workflow name."""
    inputs: dict[str, Any] = {}
    result = execute_workflow("NonExistentWorkflow", inputs)

    assert result.success is False
    assert result.steps_completed == 0
    assert result.total_steps == 0
    assert len(result.errors) > 0
    assert "Failed to load workflow" in result.errors[0]


def test_execute_workflow_repurposing() -> None:
    """Test executing Repurposing1to10 workflow."""
    inputs = {"source_content": "Test content about AI agents"}
    result = execute_workflow("Repurposing1to10", inputs)

    assert result.success is True
    assert result.workflow_name == "Repurposing1to10"
    assert result.total_steps == 5  # Repurposing has 5 steps


def test_execute_workflow_empty_inputs() -> None:
    """Test workflow execution with empty inputs."""
    inputs: dict[str, Any] = {}
    result = execute_workflow("SundayPowerHour", inputs)

    # Should still succeed (steps don't fail, just execute)
    assert result.success is True
    assert result.steps_completed == result.total_steps


def test_workflow_result_dataclass() -> None:
    """Test WorkflowResult dataclass structure."""
    result = WorkflowResult(
        workflow_name="TestWorkflow",
        success=True,
        outputs={"key": "value"},
        steps_completed=3,
        total_steps=5,
        errors=[],
    )

    assert result.workflow_name == "TestWorkflow"
    assert result.success is True
    assert result.outputs == {"key": "value"}
    assert result.steps_completed == 3
    assert result.total_steps == 5
    assert result.errors == []


def test_workflow_result_with_errors() -> None:
    """Test WorkflowResult with errors."""
    errors = ["Error 1", "Error 2"]
    result = WorkflowResult(
        workflow_name="TestWorkflow",
        success=False,
        outputs={},
        steps_completed=2,
        total_steps=5,
        errors=errors,
    )

    assert result.success is False
    assert len(result.errors) == 2
    assert "Error 1" in result.errors
    assert "Error 2" in result.errors


def test_execute_workflow_sequential_execution() -> None:
    """Test that steps execute sequentially and outputs accumulate."""
    inputs = {"initial": "data"}
    result = execute_workflow("SundayPowerHour", inputs)

    # Outputs should accumulate across steps
    assert "initial" in result.outputs
    assert "context_mining_executed" in result.outputs
    assert "pillar_categorization_executed" in result.outputs
    assert "framework_selection_executed" in result.outputs
    assert "batch_writing_executed" in result.outputs
    assert "polish_and_schedule_executed" in result.outputs


def test_execute_workflow_step_names() -> None:
    """Test that step names are captured in outputs."""
    inputs: dict[str, Any] = {}
    result = execute_workflow("SundayPowerHour", inputs)

    assert result.outputs["context_mining_name"] == "Context Mining"
    assert result.outputs["pillar_categorization_name"] == "Pillar Categorization"
    assert result.outputs["framework_selection_name"] == "Framework Selection"
    assert result.outputs["batch_writing_name"] == "Batch Writing"
    assert result.outputs["polish_and_schedule_name"] == "Polish & Schedule"
