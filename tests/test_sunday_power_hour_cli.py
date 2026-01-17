"""Tests for sunday-power-hour CLI command."""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli import cli
from lib.database import ContentPlan, ContentPlanStatus
from lib.blueprint_engine import WorkflowResult


@pytest.fixture
def runner() -> CliRunner:
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_sessions() -> list[dict[str, Any]]:
    """Mock session history data."""
    return [
        {
            "date": "2026-01-16",
            "topics": ["Implemented blueprint system", "Fixed validation bugs"],
        },
        {
            "date": "2026-01-15",
            "topics": ["Created workflow YAML files", "Added CLI commands"],
        },
    ]


@pytest.fixture
def mock_projects() -> list[dict[str, str]]:
    """Mock project notes data."""
    return [
        {"name": "Content Engine", "status": "active"},
        {"name": "Sales RPG", "status": "planning"},
    ]


@pytest.fixture
def mock_workflow_result() -> WorkflowResult:
    """Mock successful workflow execution result."""
    return WorkflowResult(
        workflow_name="SundayPowerHour",
        success=True,
        outputs={
            "context_mining_executed": True,
            "pillar_categorization_executed": True,
            "framework_selection_executed": True,
            "batch_writing_executed": True,
            "polish_and_schedule_executed": True,
        },
        steps_completed=5,
        total_steps=5,
        errors=[],
    )


def test_sunday_power_hour_success(runner: Any, mock_sessions: Any, mock_projects: Any, mock_workflow_result: Any, tmp_path: Any) -> None:
    """Test successful Sunday Power Hour execution."""
    with patch("cli.read_session_history") as mock_read_sessions, \
         patch("cli.read_project_notes") as mock_read_projects, \
         patch("cli.execute_workflow") as mock_execute_workflow, \
         patch("cli.get_db") as mock_get_db:

        # Mock data sources
        mock_read_sessions.return_value = mock_sessions
        mock_read_projects.return_value = mock_projects
        mock_execute_workflow.return_value = mock_workflow_result

        # Mock database
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Track created plans
        created_plans = []
        plan_id = 1

        def add_plan(plan: ContentPlan) -> None:
            nonlocal plan_id
            created_plans.append(plan)
            # Simulate ID assignment on refresh
            plan.id = plan_id
            plan_id += 1

        mock_db.add.side_effect = add_plan
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda plan: None  # ID already set in add_plan

        # Run command
        result = runner.invoke(cli, ["sunday-power-hour"])

        # Assertions
        assert result.exit_code == 0
        assert "🚀 Starting Sunday Power Hour workflow" in result.output
        assert "✅ Sunday Power Hour complete!" in result.output
        assert "Total plans created: 10" in result.output

        # Verify workflow was called
        mock_execute_workflow.assert_called_once()
        call_args = mock_execute_workflow.call_args
        assert call_args[0][0] == "SundayPowerHour"
        assert "sessions" in call_args[0][1]
        assert "projects" in call_args[0][1]
        assert "week_start_date" in call_args[0][1]

        # Verify 10 plans created
        assert len(created_plans) == 10

        # Verify pillar distribution (35/30/20/15%)
        pillar_counts: dict[str, int] = {}
        for plan in created_plans:
            pillar_counts[plan.pillar] = pillar_counts.get(plan.pillar, 0) + 1

        assert pillar_counts["what_building"] == 4  # 40% (closest to 35%)
        assert pillar_counts["what_learning"] == 3  # 30%
        assert pillar_counts["sales_tech"] == 2     # 20%
        assert pillar_counts["problem_solution"] == 1  # 10% (closest to 15%)

        # Verify all plans have PLANNED status
        for plan in created_plans:
            assert plan.status == ContentPlanStatus.PLANNED

        # Verify output includes distribution
        assert "what_building: 4 (40%)" in result.output
        assert "what_learning: 3 (30%)" in result.output
        assert "sales_tech: 2 (20%)" in result.output
        assert "problem_solution: 1 (10%)" in result.output


def test_sunday_power_hour_missing_projects(runner: Any, mock_sessions: Any, mock_workflow_result: Any) -> None:
    """Test Sunday Power Hour with missing projects directory."""
    with patch("cli.read_session_history") as mock_read_sessions, \
         patch("cli.read_project_notes") as mock_read_projects, \
         patch("cli.execute_workflow") as mock_execute_workflow, \
         patch("cli.get_db") as mock_get_db:

        mock_read_sessions.return_value = mock_sessions
        mock_read_projects.side_effect = FileNotFoundError("Projects directory not found")
        mock_execute_workflow.return_value = mock_workflow_result

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda plan: setattr(plan, "id", 1)

        result = runner.invoke(cli, ["sunday-power-hour"])

        assert result.exit_code == 0
        assert "⚠️  Projects directory not found" in result.output
        assert "✅ Sunday Power Hour complete!" in result.output

        # Verify workflow called without projects
        call_args = mock_execute_workflow.call_args
        assert call_args[0][1]["projects"] == []


def test_sunday_power_hour_missing_sessions(runner: Any) -> None:
    """Test Sunday Power Hour with missing session history."""
    with patch("cli.read_session_history") as mock_read_sessions:
        mock_read_sessions.side_effect = FileNotFoundError("Session history not found")

        result = runner.invoke(cli, ["sunday-power-hour"])

        assert result.exit_code == 1
        assert "Session history not found" in result.output


def test_sunday_power_hour_workflow_failure(runner: Any, mock_sessions: Any, mock_projects: Any) -> None:
    """Test Sunday Power Hour with workflow execution failure."""
    with patch("cli.read_session_history") as mock_read_sessions, \
         patch("cli.read_project_notes") as mock_read_projects, \
         patch("cli.execute_workflow") as mock_execute_workflow:

        mock_read_sessions.return_value = mock_sessions
        mock_read_projects.return_value = mock_projects

        # Mock workflow failure
        mock_execute_workflow.return_value = WorkflowResult(
            workflow_name="SundayPowerHour",
            success=False,
            outputs={},
            steps_completed=2,
            total_steps=5,
            errors=["Step failed: context_mining error", "Step failed: LLM timeout"],
        )

        result = runner.invoke(cli, ["sunday-power-hour"])

        assert result.exit_code == 1
        assert "❌ Workflow execution failed" in result.output
        assert "context_mining error" in result.output
        assert "LLM timeout" in result.output


def test_sunday_power_hour_database_plans(runner: Any, mock_sessions: Any, mock_projects: Any, mock_workflow_result: Any) -> None:
    """Test that ContentPlan records have correct fields."""
    with patch("cli.read_session_history") as mock_read_sessions, \
         patch("cli.read_project_notes") as mock_read_projects, \
         patch("cli.execute_workflow") as mock_execute_workflow, \
         patch("cli.get_db") as mock_get_db:

        mock_read_sessions.return_value = mock_sessions
        mock_read_projects.return_value = mock_projects
        mock_execute_workflow.return_value = mock_workflow_result

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        created_plans = []

        def add_plan(plan: ContentPlan) -> None:
            created_plans.append(plan)

        mock_db.add.side_effect = add_plan
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda plan: setattr(plan, "id", len(created_plans))

        result = runner.invoke(cli, ["sunday-power-hour"])

        assert result.exit_code == 0

        # Verify all plans have required fields
        for plan in created_plans:
            assert isinstance(plan, ContentPlan)
            assert plan.week_start_date is not None
            assert plan.pillar in ["what_building", "what_learning", "sales_tech", "problem_solution"]
            assert plan.framework in ["STF", "MRS", "SLA", "PIF"]
            assert plan.idea is not None
            assert plan.status == ContentPlanStatus.PLANNED
            assert plan.post_id is None  # Not yet generated


def test_sunday_power_hour_week_start_date(runner: Any, mock_sessions: Any, mock_projects: Any, mock_workflow_result: Any) -> None:
    """Test that week_start_date is calculated correctly."""
    with patch("cli.read_session_history") as mock_read_sessions, \
         patch("cli.read_project_notes") as mock_read_projects, \
         patch("cli.execute_workflow") as mock_execute_workflow, \
         patch("cli.get_db") as mock_get_db:

        mock_read_sessions.return_value = mock_sessions
        mock_read_projects.return_value = mock_projects
        mock_execute_workflow.return_value = mock_workflow_result

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        created_plans = []
        mock_db.add.side_effect = lambda plan: created_plans.append(plan)
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda plan: setattr(plan, "id", 1)

        # Run command
        result = runner.invoke(cli, ["sunday-power-hour"])

        assert result.exit_code == 0

        # Calculate expected week_start_date (7 days ago)
        expected_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        # Verify all plans have same week_start_date
        for plan in created_plans:
            assert plan.week_start_date == expected_date


def test_sunday_power_hour_framework_distribution(runner: Any, mock_sessions: Any, mock_projects: Any, mock_workflow_result: Any) -> None:
    """Test that frameworks are distributed appropriately."""
    with patch("cli.read_session_history") as mock_read_sessions, \
         patch("cli.read_project_notes") as mock_read_projects, \
         patch("cli.execute_workflow") as mock_execute_workflow, \
         patch("cli.get_db") as mock_get_db:

        mock_read_sessions.return_value = mock_sessions
        mock_read_projects.return_value = mock_projects
        mock_execute_workflow.return_value = mock_workflow_result

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        created_plans = []
        mock_db.add.side_effect = lambda plan: created_plans.append(plan)
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda plan: setattr(plan, "id", 1)

        result = runner.invoke(cli, ["sunday-power-hour"])

        assert result.exit_code == 0

        # Count framework usage
        framework_counts: dict[str, int] = {}
        for plan in created_plans:
            framework_counts[plan.framework] = framework_counts.get(plan.framework, 0) + 1

        # Verify all 4 frameworks used
        assert "STF" in framework_counts
        assert "MRS" in framework_counts
        assert "SLA" in framework_counts
        assert "PIF" in framework_counts

        # STF should be most common (default for building/sales/problem-solving)
        assert framework_counts["STF"] >= 3


def test_sunday_power_hour_output_summary(runner: Any, mock_sessions: Any, mock_projects: Any, mock_workflow_result: Any) -> None:
    """Test that output includes comprehensive summary."""
    with patch("cli.read_session_history") as mock_read_sessions, \
         patch("cli.read_project_notes") as mock_read_projects, \
         patch("cli.execute_workflow") as mock_execute_workflow, \
         patch("cli.get_db") as mock_get_db:

        mock_read_sessions.return_value = mock_sessions
        mock_read_projects.return_value = mock_projects
        mock_execute_workflow.return_value = mock_workflow_result

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda plan: setattr(plan, "id", 1)

        result = runner.invoke(cli, ["sunday-power-hour"])

        assert result.exit_code == 0

        # Verify summary sections present
        assert "📊 Summary:" in result.output
        assert "Distribution by pillar:" in result.output
        assert "Frameworks used:" in result.output
        assert "💡 Next steps:" in result.output
        assert "Time saved: ~92 minutes via batching!" in result.output


def test_sunday_power_hour_next_steps(runner: Any, mock_sessions: Any, mock_projects: Any, mock_workflow_result: Any) -> None:
    """Test that next steps guide user correctly."""
    with patch("cli.read_session_history") as mock_read_sessions, \
         patch("cli.read_project_notes") as mock_read_projects, \
         patch("cli.execute_workflow") as mock_execute_workflow, \
         patch("cli.get_db") as mock_get_db:

        mock_read_sessions.return_value = mock_sessions
        mock_read_projects.return_value = mock_projects
        mock_execute_workflow.return_value = mock_workflow_result

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.side_effect = lambda plan: setattr(plan, "id", 1)

        result = runner.invoke(cli, ["sunday-power-hour"])

        assert result.exit_code == 0

        # Verify next steps instructions
        assert "Review plans:" in result.output
        assert "Generate posts:" in result.output
        assert "SELECT * FROM content_plans" in result.output


def test_sunday_power_hour_help(runner: Any) -> None:
    """Test sunday-power-hour --help output."""
    result = runner.invoke(cli, ["sunday-power-hour", "--help"])

    assert result.exit_code == 0
    assert "Execute Sunday Power Hour workflow" in result.output
    assert "10 content ideas" in result.output
    assert "92 minutes" in result.output
