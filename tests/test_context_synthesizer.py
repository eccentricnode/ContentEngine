"""Tests for context synthesizer module."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lib.context_capture import ProjectNote, SessionSummary
from lib.context_synthesizer import (
    DailyContext,
    _build_context_summary,
    check_ollama_health,
    save_context,
    synthesize_daily_context,
)
from lib.errors import AIError


@pytest.fixture
def sample_sessions():
    """Create sample session summaries."""
    return [
        SessionSummary(
            session_id="session-1",
            date=datetime(2026, 1, 12, 10, 0),
            topics=["Python testing", "Context capture"],
            decisions=["Use pytest for testing"],
        ),
        SessionSummary(
            session_id="session-2",
            date=datetime(2026, 1, 12, 14, 0),
            topics=["Ollama integration"],
            decisions=["Use llama3:8b model"],
        ),
    ]


@pytest.fixture
def sample_projects():
    """Create sample project notes."""
    return [
        ProjectNote(
            project_name="Content Engine",
            last_updated=datetime(2026, 1, 12, 12, 0),
            key_insights=["FastAPI for web", "SQLite for data"],
            current_status="Phase 2 development",
        ),
        ProjectNote(
            project_name="AI Tools",
            last_updated=datetime(2026, 1, 11, 10, 0),
            key_insights=["LLM integration patterns"],
            current_status="Research phase",
        ),
    ]


@pytest.fixture
def mock_ollama_response():
    """Create a mock successful Ollama response."""
    return {
        "response": '{"themes": ["AI development", "Testing strategies"], '
        '"decisions": ["Use Ollama for synthesis"], '
        '"progress": ["Completed CE-001 and CE-002"]}'
    }


@pytest.fixture
def mock_ollama_invalid_json_response():
    """Create a mock Ollama response with invalid JSON."""
    return {"response": "This is not valid JSON at all"}


def test_daily_context_dataclass():
    """Test DailyContext dataclass creation and defaults."""
    context = DailyContext()

    assert context.themes == []
    assert context.decisions == []
    assert context.progress == []
    assert context.date == ""
    assert context.raw_data == {}


def test_daily_context_with_data():
    """Test DailyContext with populated data."""
    context = DailyContext(
        themes=["Theme 1", "Theme 2"],
        decisions=["Decision 1"],
        progress=["Progress 1", "Progress 2"],
        date="2026-01-12",
        raw_data={"sessions_count": 5, "projects_count": 3},
    )

    assert len(context.themes) == 2
    assert len(context.decisions) == 1
    assert len(context.progress) == 2
    assert context.date == "2026-01-12"
    assert context.raw_data["sessions_count"] == 5


@patch("lib.context_synthesizer.requests.get")
def test_check_ollama_health_success(mock_get):
    """Test successful Ollama health check."""
    mock_get.return_value = Mock(status_code=200)

    result = check_ollama_health()

    assert result is True
    mock_get.assert_called_once()


@patch("lib.context_synthesizer.requests.get")
def test_check_ollama_health_failure(mock_get):
    """Test failed Ollama health check."""
    mock_get.return_value = Mock(status_code=500)

    result = check_ollama_health()

    assert result is False


@patch("lib.context_synthesizer.requests.get")
def test_check_ollama_health_connection_error(mock_get):
    """Test Ollama health check with connection error."""
    mock_get.side_effect = Exception("Connection refused")

    result = check_ollama_health()

    assert result is False


@patch("lib.context_synthesizer.requests.post")
@patch("lib.context_synthesizer.requests.get")
def test_synthesize_daily_context_success(
    mock_get, mock_post, sample_sessions, sample_projects, mock_ollama_response
):
    """Test successful context synthesis."""
    mock_get.return_value = Mock(status_code=200)  # Health check
    mock_post.return_value = Mock(status_code=200, json=lambda: mock_ollama_response)

    result = synthesize_daily_context(
        sessions=sample_sessions, projects=sample_projects, date="2026-01-12"
    )

    assert isinstance(result, DailyContext)
    assert result.date == "2026-01-12"
    assert len(result.themes) == 2
    assert "AI development" in result.themes
    assert len(result.decisions) == 1
    assert len(result.progress) == 1
    assert result.raw_data["sessions_count"] == 2
    assert result.raw_data["projects_count"] == 2


@patch("lib.context_synthesizer.requests.get")
def test_synthesize_daily_context_health_check_fails(
    mock_get, sample_sessions, sample_projects
):
    """Test synthesis when Ollama health check fails."""
    mock_get.return_value = Mock(status_code=500)

    with pytest.raises(AIError) as exc_info:
        synthesize_daily_context(
            sessions=sample_sessions, projects=sample_projects, date="2026-01-12"
        )

    assert "not accessible" in str(exc_info.value)


@patch("lib.context_synthesizer.requests.post")
@patch("lib.context_synthesizer.requests.get")
def test_synthesize_daily_context_invalid_json(
    mock_get, mock_post, sample_sessions, sample_projects, mock_ollama_invalid_json_response
):
    """Test synthesis with invalid JSON response from Ollama."""
    mock_get.return_value = Mock(status_code=200)
    mock_post.return_value = Mock(
        status_code=200, json=lambda: mock_ollama_invalid_json_response
    )

    with pytest.raises(AIError) as exc_info:
        synthesize_daily_context(
            sessions=sample_sessions, projects=sample_projects, date="2026-01-12"
        )

    assert "invalid JSON" in str(exc_info.value)


@patch("lib.context_synthesizer.requests.post")
@patch("lib.context_synthesizer.requests.get")
def test_synthesize_daily_context_connection_error(
    mock_get, mock_post, sample_sessions, sample_projects
):
    """Test synthesis with connection error."""
    mock_get.return_value = Mock(status_code=200)
    mock_post.side_effect = Exception("Connection refused")

    with pytest.raises(AIError) as exc_info:
        synthesize_daily_context(
            sessions=sample_sessions, projects=sample_projects, date="2026-01-12"
        )

    assert "failed" in str(exc_info.value).lower()


@patch("lib.context_synthesizer.requests.post")
@patch("lib.context_synthesizer.requests.get")
def test_synthesize_daily_context_empty_inputs(mock_get, mock_post):
    """Test synthesis with empty sessions and projects."""
    mock_get.return_value = Mock(status_code=200)
    mock_response = {"response": '{"themes": [], "decisions": [], "progress": []}'}
    mock_post.return_value = Mock(status_code=200, json=lambda: mock_response)

    result = synthesize_daily_context(sessions=[], projects=[], date="2026-01-12")

    assert isinstance(result, DailyContext)
    assert result.themes == []
    assert result.decisions == []
    assert result.progress == []
    assert result.raw_data["sessions_count"] == 0
    assert result.raw_data["projects_count"] == 0


@patch("lib.context_synthesizer.requests.post")
@patch("lib.context_synthesizer.requests.get")
def test_synthesize_daily_context_non_list_values(mock_get, mock_post, sample_sessions):
    """Test synthesis when Ollama returns non-list values."""
    mock_get.return_value = Mock(status_code=200)
    mock_response = {
        "response": '{"themes": "single theme", "decisions": "single decision", "progress": "single progress"}'
    }
    mock_post.return_value = Mock(status_code=200, json=lambda: mock_response)

    result = synthesize_daily_context(
        sessions=sample_sessions, projects=[], date="2026-01-12"
    )

    # Should convert to lists
    assert isinstance(result.themes, list)
    assert isinstance(result.decisions, list)
    assert isinstance(result.progress, list)


@patch("lib.context_synthesizer.requests.post")
@patch("lib.context_synthesizer.requests.get")
def test_synthesize_daily_context_custom_host_model(
    mock_get, mock_post, sample_sessions, mock_ollama_response
):
    """Test synthesis with custom host and model."""
    mock_get.return_value = Mock(status_code=200)
    mock_post.return_value = Mock(status_code=200, json=lambda: mock_ollama_response)

    result = synthesize_daily_context(
        sessions=sample_sessions,
        projects=[],
        date="2026-01-12",
        host="http://custom:11434",
        model="llama3:70b",
    )

    assert isinstance(result, DailyContext)
    # Verify custom host was used in the call
    call_args = mock_post.call_args
    assert "http://custom:11434" in call_args[0][0]
    assert call_args[1]["json"]["model"] == "llama3:70b"


def test_build_context_summary_with_sessions_and_projects(
    sample_sessions, sample_projects
):
    """Test building context summary with both sessions and projects."""
    summary = _build_context_summary(sample_sessions, sample_projects)

    assert "## Sessions" in summary
    assert "## Projects" in summary
    assert "Python testing" in summary
    assert "Content Engine" in summary
    assert "FastAPI for web" in summary


def test_build_context_summary_sessions_only(sample_sessions):
    """Test building context summary with sessions only."""
    summary = _build_context_summary(sample_sessions, [])

    assert "## Sessions" in summary
    assert "Python testing" in summary


def test_build_context_summary_projects_only(sample_projects):
    """Test building context summary with projects only."""
    summary = _build_context_summary([], sample_projects)

    assert "## Projects" in summary
    assert "Content Engine" in summary


def test_build_context_summary_empty():
    """Test building context summary with no data."""
    summary = _build_context_summary([], [])

    # Should return empty or minimal structure
    assert isinstance(summary, str)


def test_build_context_summary_limits_items():
    """Test that context summary limits number of items."""
    # Create many sessions and projects
    many_sessions = [
        SessionSummary(
            session_id=f"session-{i}",
            date=datetime(2026, 1, 12, i, 0),
            topics=[f"Topic {i}"],
        )
        for i in range(20)
    ]
    many_projects = [
        ProjectNote(
            project_name=f"Project {i}",
            last_updated=datetime(2026, 1, 12, 12, 0),
            key_insights=[f"Insight {i}"],
        )
        for i in range(20)
    ]

    summary = _build_context_summary(many_sessions, many_projects)

    # Should limit to 10 sessions and 10 projects
    session_count = summary.count("### Session")
    project_count = summary.count("### Project")

    assert session_count == 10
    assert project_count == 10


def test_save_context_success():
    """Test successful context saving."""
    with tempfile.TemporaryDirectory() as tmpdir:
        context = DailyContext(
            themes=["Theme 1", "Theme 2"],
            decisions=["Decision 1"],
            progress=["Progress 1"],
            date="2026-01-12",
            raw_data={"sessions_count": 5},
        )

        file_path = save_context(context, output_dir=tmpdir)

        assert Path(file_path).exists()
        assert "2026-01-12.json" in file_path

        # Verify content
        with open(file_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data["date"] == "2026-01-12"
        assert len(saved_data["themes"]) == 2
        assert "Theme 1" in saved_data["themes"]


def test_save_context_creates_directory():
    """Test that save_context creates output directory if missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "nested" / "context"
        context = DailyContext(date="2026-01-12")

        file_path = save_context(context, output_dir=str(output_dir))

        assert Path(file_path).exists()
        assert output_dir.exists()


def test_save_context_default_directory():
    """Test save_context with default directory."""
    context = DailyContext(date="2026-01-12-test")

    try:
        file_path = save_context(context)
        assert "context/2026-01-12-test.json" in file_path
        assert Path(file_path).exists()
    finally:
        # Cleanup
        if Path(file_path).exists():
            Path(file_path).unlink()


def test_save_context_no_date():
    """Test save_context with no date in context."""
    with tempfile.TemporaryDirectory() as tmpdir:
        context = DailyContext(themes=["Test"])

        file_path = save_context(context, output_dir=tmpdir)

        assert "unknown.json" in file_path


def test_save_context_overwrites_existing():
    """Test that save_context overwrites existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        context1 = DailyContext(
            themes=["Original"], date="2026-01-12"
        )
        context2 = DailyContext(
            themes=["Updated"], date="2026-01-12"
        )

        file_path1 = save_context(context1, output_dir=tmpdir)
        file_path2 = save_context(context2, output_dir=tmpdir)

        assert file_path1 == file_path2

        # Verify updated content
        with open(file_path2, "r") as f:
            saved_data = json.load(f)

        assert "Updated" in saved_data["themes"]
        assert "Original" not in saved_data["themes"]
