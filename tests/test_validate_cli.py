"""Tests for validate CLI command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from agents.linkedin.post_validator import Severity, ValidationReport, Violation
from cli import cli
from lib.database import Post, PostStatus, Platform


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def sample_post() -> Post:
    """Create sample post for testing."""
    return Post(
        id=1,
        content="I built a new feature today. It was challenging but I learned a lot.",
        platform=Platform.LINKEDIN,
        status=PostStatus.DRAFT,
    )


def test_validate_command_exists(runner: CliRunner) -> None:
    """Test that validate command exists."""
    result = runner.invoke(cli, ["validate", "--help"])
    assert result.exit_code == 0
    assert "Validate a post" in result.output


@patch("cli.get_db")
def test_validate_post_not_found(mock_get_db: MagicMock, runner: CliRunner) -> None:
    """Test validate command with non-existent post."""
    mock_db = MagicMock()
    mock_db.get.return_value = None
    mock_get_db.return_value = mock_db

    result = runner.invoke(cli, ["validate", "999"])
    assert result.exit_code == 1
    assert "Post 999 not found" in result.output


@patch("cli.validate_post")
@patch("cli.get_db")
def test_validate_valid_post(
    mock_get_db: MagicMock,
    mock_validate_post: MagicMock,
    runner: CliRunner,
    sample_post: Post,
) -> None:
    """Test validate command with valid post."""
    # Mock database
    mock_db = MagicMock()
    mock_db.get.return_value = sample_post
    mock_get_db.return_value = mock_db

    # Mock validation report
    mock_validate_post.return_value = ValidationReport(
        post_id=1,
        is_valid=True,
        score=1.0,
        violations=[],
    )

    result = runner.invoke(cli, ["validate", "1"])

    assert result.exit_code == 0
    assert "✅ PASS" in result.output
    assert "Validation Score: 1.00" in result.output
    assert "Perfect! No issues found" in result.output


@patch("cli.validate_post")
@patch("cli.get_db")
def test_validate_post_with_errors(
    mock_get_db: MagicMock,
    mock_validate_post: MagicMock,
    runner: CliRunner,
    sample_post: Post,
) -> None:
    """Test validate command with post that has errors."""
    # Mock database
    mock_db = MagicMock()
    mock_db.get.return_value = sample_post
    mock_get_db.return_value = mock_db

    # Mock validation report with error
    mock_validate_post.return_value = ValidationReport(
        post_id=1,
        is_valid=False,
        score=0.6,
        violations=[
            Violation(
                severity=Severity.ERROR,
                category="character_length",
                message="Content too short (50 chars, minimum 600)",
                suggestion="Add more detail and context",
            ),
        ],
    )

    result = runner.invoke(cli, ["validate", "1"])

    assert result.exit_code == 1  # Should fail with errors
    assert "❌ FAIL" in result.output
    assert "Validation Score: 0.60" in result.output
    assert "🔴 ERRORS" in result.output
    assert "Content too short" in result.output
    assert "Add more detail" in result.output


@patch("cli.validate_post")
@patch("cli.get_db")
def test_validate_post_with_warnings(
    mock_get_db: MagicMock,
    mock_validate_post: MagicMock,
    runner: CliRunner,
    sample_post: Post,
) -> None:
    """Test validate command with post that has warnings."""
    # Mock database
    mock_db = MagicMock()
    mock_db.get.return_value = sample_post
    mock_get_db.return_value = mock_db

    # Mock validation report with warning
    mock_validate_post.return_value = ValidationReport(
        post_id=1,
        is_valid=True,  # Warnings don't block validity
        score=0.85,
        violations=[
            Violation(
                severity=Severity.WARNING,
                category="platform_rules",
                message="Missing line breaks (wall of text detected)",
                suggestion="Add line breaks every 2-3 sentences",
            ),
        ],
    )

    result = runner.invoke(cli, ["validate", "1"])

    assert result.exit_code == 0  # Should pass with warnings
    assert "✅ PASS" in result.output
    assert "🟡 WARNINGS" in result.output
    assert "wall of text" in result.output


@patch("cli.validate_post")
@patch("cli.get_db")
def test_validate_post_with_suggestions(
    mock_get_db: MagicMock,
    mock_validate_post: MagicMock,
    runner: CliRunner,
    sample_post: Post,
) -> None:
    """Test validate command with post that has suggestions."""
    # Mock database
    mock_db = MagicMock()
    mock_db.get.return_value = sample_post
    mock_get_db.return_value = mock_db

    # Mock validation report with suggestion
    mock_validate_post.return_value = ValidationReport(
        post_id=1,
        is_valid=True,
        score=0.95,
        violations=[
            Violation(
                severity=Severity.SUGGESTION,
                category="engagement",
                message="Consider adding a question at the end",
                suggestion="Try: 'What's your experience with this?'",
            ),
        ],
    )

    result = runner.invoke(cli, ["validate", "1"])

    assert result.exit_code == 0
    assert "✅ PASS" in result.output
    assert "💡 SUGGESTIONS" in result.output
    assert "Consider adding a question" in result.output


@patch("cli.validate_post")
@patch("cli.get_db")
def test_validate_post_with_mixed_violations(
    mock_get_db: MagicMock,
    mock_validate_post: MagicMock,
    runner: CliRunner,
    sample_post: Post,
) -> None:
    """Test validate command with mixed violation types."""
    # Mock database
    mock_db = MagicMock()
    mock_db.get.return_value = sample_post
    mock_get_db.return_value = mock_db

    # Mock validation report with mixed violations
    mock_validate_post.return_value = ValidationReport(
        post_id=1,
        is_valid=False,
        score=0.72,
        violations=[
            Violation(
                severity=Severity.ERROR,
                category="character_length",
                message="Content too short",
                suggestion="Add more detail",
            ),
            Violation(
                severity=Severity.WARNING,
                category="brand_voice",
                message="Not written in first person",
                suggestion="Use 'I' and 'my'",
            ),
            Violation(
                severity=Severity.SUGGESTION,
                category="engagement",
                message="Could use more emojis",
                suggestion=None,
            ),
        ],
    )

    result = runner.invoke(cli, ["validate", "1"])

    assert result.exit_code == 1  # Fails due to error
    assert "❌ FAIL" in result.output
    assert "🔴 ERRORS" in result.output
    assert "🟡 WARNINGS" in result.output
    assert "💡 SUGGESTIONS" in result.output
    assert "Total violations: 3" in result.output
    assert "Errors: 1" in result.output
    assert "Warnings: 1" in result.output
    assert "Suggestions: 1" in result.output


@patch("cli.validate_post")
@patch("cli.get_db")
def test_validate_with_custom_framework(
    mock_get_db: MagicMock,
    mock_validate_post: MagicMock,
    runner: CliRunner,
    sample_post: Post,
) -> None:
    """Test validate command with custom framework."""
    # Mock database
    mock_db = MagicMock()
    mock_db.get.return_value = sample_post
    mock_get_db.return_value = mock_db

    # Mock validation report
    mock_validate_post.return_value = ValidationReport(
        post_id=1,
        is_valid=True,
        score=1.0,
        violations=[],
    )

    result = runner.invoke(cli, ["validate", "1", "--framework", "MRS"])

    assert result.exit_code == 0
    assert "Framework: MRS" in result.output
    # Verify framework was passed to validate_post
    mock_validate_post.assert_called_once()
    call_args = mock_validate_post.call_args
    assert call_args[1]["framework"] == "MRS"


@patch("cli.validate_post")
@patch("cli.get_db")
def test_validate_displays_header(
    mock_get_db: MagicMock,
    mock_validate_post: MagicMock,
    runner: CliRunner,
    sample_post: Post,
) -> None:
    """Test that validate command displays proper header."""
    # Mock database
    mock_db = MagicMock()
    mock_db.get.return_value = sample_post
    mock_get_db.return_value = mock_db

    # Mock validation report
    mock_validate_post.return_value = ValidationReport(
        post_id=1,
        is_valid=True,
        score=1.0,
        violations=[],
    )

    result = runner.invoke(cli, ["validate", "1"])

    assert result.exit_code == 0
    assert "Validation Report - Post #1" in result.output
    assert "Framework: STF" in result.output
    assert "=" in result.output  # Header divider


@patch("cli.validate_post")
@patch("cli.get_db")
def test_validate_handles_exception(
    mock_get_db: MagicMock,
    mock_validate_post: MagicMock,
    runner: CliRunner,
    sample_post: Post,
) -> None:
    """Test that validate command handles exceptions gracefully."""
    # Mock database
    mock_db = MagicMock()
    mock_db.get.return_value = sample_post
    mock_get_db.return_value = mock_db

    # Mock validate_post to raise exception
    mock_validate_post.side_effect = ValueError("Something went wrong")

    result = runner.invoke(cli, ["validate", "1"])

    assert result.exit_code == 1
    assert "Validation failed" in result.output
