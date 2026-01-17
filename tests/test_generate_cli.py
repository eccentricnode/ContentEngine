"""Tests for generate CLI command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli import cli
from agents.linkedin.content_generator import GenerationResult
from lib.context_synthesizer import DailyContext


@pytest.fixture
def runner():
    """Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_daily_context():
    """Sample daily context."""
    return DailyContext(
        themes=["Building Content Engine", "Learning RAG systems"],
        decisions=["Use blueprint-based validation", "Implement iterative refinement"],
        progress=["Completed Phase 2", "Started Phase 3"],
        date="2026-01-17",
    )


@pytest.fixture
def mock_generation_result():
    """Sample generation result."""
    return GenerationResult(
        content="Test LinkedIn post content that follows STF framework...",
        framework_used="STF",
        validation_score=0.95,
        is_valid=True,
        iterations=1,
        violations=[],
    )


def test_generate_requires_pillar(runner):
    """Test that generate command requires --pillar option."""
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code != 0
    assert "Missing option '--pillar'" in result.output or "Error" in result.output


def test_generate_valid_pillar_choices(runner):
    """Test that generate command only accepts valid pillars."""
    result = runner.invoke(cli, ["generate", "--pillar", "invalid_pillar"])
    assert result.exit_code != 0
    assert "Invalid value" in result.output or "invalid choice" in result.output.lower()


def test_generate_valid_framework_choices(runner):
    """Test that generate command only accepts valid frameworks."""
    result = runner.invoke(
        cli, ["generate", "--pillar", "what_building", "--framework", "INVALID"]
    )
    assert result.exit_code != 0
    assert "Invalid value" in result.output or "invalid choice" in result.output.lower()


@patch("cli.read_session_history")
@patch("cli.read_project_notes")
@patch("cli.synthesize_daily_context")
@patch("cli.generate_post")
@patch("cli.get_db")
def test_generate_success_with_auto_framework(
    mock_get_db,
    mock_generate_post,
    mock_synthesize,
    mock_read_projects,
    mock_read_sessions,
    runner,
    mock_daily_context,
    mock_generation_result,
):
    """Test successful generation with auto-selected framework."""
    # Setup mocks
    mock_read_sessions.return_value = []
    mock_read_projects.return_value = []
    mock_synthesize.return_value = mock_daily_context
    mock_generate_post.return_value = mock_generation_result

    # Mock database
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.refresh = MagicMock(side_effect=lambda p: setattr(p, "id", 42))
    mock_get_db.return_value = mock_db

    # Run command
    result = runner.invoke(cli, ["generate", "--pillar", "what_building"])

    # Assertions
    assert result.exit_code == 0
    assert "Draft created (ID: 42)" in result.output
    assert "Framework used: STF" in result.output
    assert "Validation score: 0.95" in result.output
    assert "Test LinkedIn post content" in result.output

    # Verify generate_post was called correctly
    mock_generate_post.assert_called_once()
    call_args = mock_generate_post.call_args
    assert call_args[1]["pillar"] == "what_building"
    assert call_args[1]["framework"] is None  # Auto-select
    assert call_args[1]["model"] == "llama3:8b"


@patch("cli.read_session_history")
@patch("cli.read_project_notes")
@patch("cli.synthesize_daily_context")
@patch("cli.generate_post")
@patch("cli.get_db")
def test_generate_success_with_specific_framework(
    mock_get_db,
    mock_generate_post,
    mock_synthesize,
    mock_read_projects,
    mock_read_sessions,
    runner,
    mock_daily_context,
):
    """Test successful generation with specified framework."""
    # Setup mocks
    mock_read_sessions.return_value = []
    mock_read_projects.return_value = []
    mock_synthesize.return_value = mock_daily_context

    mock_result = GenerationResult(
        content="MRS framework post...",
        framework_used="MRS",
        validation_score=0.88,
        is_valid=True,
        iterations=2,
        violations=[],
    )
    mock_generate_post.return_value = mock_result

    # Mock database
    mock_db = MagicMock()
    mock_db.refresh = MagicMock(side_effect=lambda p: setattr(p, "id", 99))
    mock_get_db.return_value = mock_db

    # Run command with specified framework
    result = runner.invoke(
        cli, ["generate", "--pillar", "what_learning", "--framework", "MRS"]
    )

    # Assertions
    assert result.exit_code == 0
    assert "Draft created (ID: 99)" in result.output
    assert "Framework used: MRS" in result.output

    # Verify generate_post received MRS framework
    call_args = mock_generate_post.call_args
    assert call_args[1]["framework"] == "MRS"


@patch("cli.read_session_history")
@patch("cli.read_project_notes")
@patch("cli.synthesize_daily_context")
@patch("cli.generate_post")
@patch("cli.get_db")
def test_generate_with_custom_date(
    mock_get_db,
    mock_generate_post,
    mock_synthesize,
    mock_read_projects,
    mock_read_sessions,
    runner,
    mock_daily_context,
    mock_generation_result,
):
    """Test generation with custom date."""
    # Setup mocks
    mock_read_sessions.return_value = []
    mock_read_projects.return_value = []
    mock_synthesize.return_value = mock_daily_context
    mock_generate_post.return_value = mock_generation_result

    # Mock database
    mock_db = MagicMock()
    mock_db.refresh = MagicMock(side_effect=lambda p: setattr(p, "id", 1))
    mock_get_db.return_value = mock_db

    # Run with custom date
    result = runner.invoke(
        cli, ["generate", "--pillar", "what_building", "--date", "2026-01-15"]
    )

    # Assertions
    assert result.exit_code == 0
    assert "Generating content for 2026-01-15" in result.output

    # Verify synthesize_daily_context received correct date
    call_args = mock_synthesize.call_args
    assert call_args[1]["date"] == "2026-01-15"


@patch("cli.read_session_history")
@patch("cli.read_project_notes")
@patch("cli.synthesize_daily_context")
@patch("cli.generate_post")
@patch("cli.get_db")
def test_generate_with_custom_model(
    mock_get_db,
    mock_generate_post,
    mock_synthesize,
    mock_read_projects,
    mock_read_sessions,
    runner,
    mock_daily_context,
    mock_generation_result,
):
    """Test generation with custom model."""
    # Setup mocks
    mock_read_sessions.return_value = []
    mock_read_projects.return_value = []
    mock_synthesize.return_value = mock_daily_context
    mock_generate_post.return_value = mock_generation_result

    # Mock database
    mock_db = MagicMock()
    mock_db.refresh = MagicMock(side_effect=lambda p: setattr(p, "id", 1))
    mock_get_db.return_value = mock_db

    # Run with custom model
    result = runner.invoke(
        cli, ["generate", "--pillar", "what_building", "--model", "llama2:13b"]
    )

    # Assertions
    assert result.exit_code == 0
    assert "Generating post with llama2:13b" in result.output

    # Verify generate_post received custom model
    call_args = mock_generate_post.call_args
    assert call_args[1]["model"] == "llama2:13b"


@patch("cli.read_session_history")
@patch("cli.read_project_notes")
@patch("cli.synthesize_daily_context")
@patch("cli.generate_post")
@patch("cli.get_db")
def test_generate_shows_validation_warnings(
    mock_get_db,
    mock_generate_post,
    mock_synthesize,
    mock_read_projects,
    mock_read_sessions,
    runner,
    mock_daily_context,
):
    """Test that validation warnings are displayed."""
    # Setup mocks
    mock_read_sessions.return_value = []
    mock_read_projects.return_value = []
    mock_synthesize.return_value = mock_daily_context

    # Result with violations
    mock_result = GenerationResult(
        content="Post with issues...",
        framework_used="STF",
        validation_score=0.65,
        is_valid=False,
        iterations=3,
        violations=["Content too short (450 chars, min 600)", "Missing Problem section"],
    )
    mock_generate_post.return_value = mock_result

    # Mock database
    mock_db = MagicMock()
    mock_db.refresh = MagicMock(side_effect=lambda p: setattr(p, "id", 1))
    mock_get_db.return_value = mock_db

    # Run command
    result = runner.invoke(cli, ["generate", "--pillar", "what_building"])

    # Assertions
    assert result.exit_code == 0
    assert "Validation warnings:" in result.output
    assert "Content too short" in result.output
    assert "Missing Problem section" in result.output


@patch("cli.read_session_history")
def test_generate_handles_missing_sessions(mock_read_sessions, runner):
    """Test error handling when session history not found."""
    mock_read_sessions.side_effect = FileNotFoundError("Session history not found")

    result = runner.invoke(cli, ["generate", "--pillar", "what_building"])

    assert result.exit_code != 0
    assert "Session history not found" in result.output


@patch("cli.read_session_history")
@patch("cli.read_project_notes")
@patch("cli.synthesize_daily_context")
def test_generate_handles_ai_error(
    mock_synthesize, mock_read_projects, mock_read_sessions, runner
):
    """Test error handling when AI synthesis fails."""
    from lib.errors import AIError

    mock_read_sessions.return_value = []
    mock_read_projects.return_value = []
    mock_synthesize.side_effect = AIError("Ollama connection failed")

    result = runner.invoke(cli, ["generate", "--pillar", "what_building"])

    assert result.exit_code != 0
    assert "AI generation failed" in result.output
    assert "Make sure Ollama is running" in result.output


@patch("cli.read_session_history")
@patch("cli.read_project_notes")
def test_generate_handles_missing_projects_gracefully(
    mock_read_projects, mock_read_sessions, runner
):
    """Test that missing projects directory is handled gracefully."""
    mock_read_sessions.return_value = []
    mock_read_projects.side_effect = FileNotFoundError("Projects directory not found")

    # Should continue without projects (not fail)
    # Will fail later at synthesize_daily_context, but we're testing the projects handling
    with patch("cli.synthesize_daily_context") as mock_synthesize:
        mock_synthesize.side_effect = Exception("Test stopped")

        result = runner.invoke(cli, ["generate", "--pillar", "what_building"])

        # Should show warning about missing projects
        assert "Projects directory not found, continuing without projects" in result.output


def test_generate_invalid_date_format(runner):
    """Test error handling for invalid date format."""
    result = runner.invoke(
        cli, ["generate", "--pillar", "what_building", "--date", "invalid-date"]
    )

    assert result.exit_code != 0
    assert "Invalid date format" in result.output or "does not match" in result.output


@patch("cli.read_session_history")
@patch("cli.read_project_notes")
@patch("cli.synthesize_daily_context")
@patch("cli.generate_post")
@patch("cli.get_db")
def test_generate_saves_post_correctly(
    mock_get_db,
    mock_generate_post,
    mock_synthesize,
    mock_read_projects,
    mock_read_sessions,
    runner,
    mock_daily_context,
    mock_generation_result,
):
    """Test that generated post is saved to database correctly."""
    # Setup mocks
    mock_read_sessions.return_value = []
    mock_read_projects.return_value = []
    mock_synthesize.return_value = mock_daily_context
    mock_generate_post.return_value = mock_generation_result

    # Mock database
    mock_db = MagicMock()
    mock_post_obj = None

    def capture_post(post):
        nonlocal mock_post_obj
        mock_post_obj = post

    mock_db.add = MagicMock(side_effect=capture_post)
    mock_db.refresh = MagicMock(side_effect=lambda p: setattr(p, "id", 123))
    mock_get_db.return_value = mock_db

    # Run command
    result = runner.invoke(cli, ["generate", "--pillar", "what_building"])

    # Assertions
    assert result.exit_code == 0

    # Verify Post object was created with correct attributes
    assert mock_post_obj is not None
    assert mock_post_obj.content == "Test LinkedIn post content that follows STF framework..."
    from lib.database import Platform, PostStatus

    assert mock_post_obj.platform == Platform.LINKEDIN
    assert mock_post_obj.status == PostStatus.DRAFT

    # Verify database operations
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@patch("cli.read_session_history")
@patch("cli.read_project_notes")
@patch("cli.synthesize_daily_context")
@patch("cli.generate_post")
@patch("cli.get_db")
def test_generate_displays_next_steps(
    mock_get_db,
    mock_generate_post,
    mock_synthesize,
    mock_read_projects,
    mock_read_sessions,
    runner,
    mock_daily_context,
    mock_generation_result,
):
    """Test that next steps are displayed to user."""
    # Setup mocks
    mock_read_sessions.return_value = []
    mock_read_projects.return_value = []
    mock_synthesize.return_value = mock_daily_context
    mock_generate_post.return_value = mock_generation_result

    # Mock database
    mock_db = MagicMock()
    mock_db.refresh = MagicMock(side_effect=lambda p: setattr(p, "id", 456))
    mock_get_db.return_value = mock_db

    # Run command
    result = runner.invoke(cli, ["generate", "--pillar", "what_building"])

    # Assertions
    assert result.exit_code == 0
    assert "Next steps:" in result.output
    assert "Review: uv run content-engine show 456" in result.output
    assert "Approve: uv run content-engine approve 456" in result.output
