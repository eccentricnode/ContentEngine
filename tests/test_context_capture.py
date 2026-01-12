"""Tests for context capture module."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from lib.context_capture import (
    SessionSummary,
    _extract_decisions,
    _extract_topics,
    _parse_session_file,
    read_session_history,
)


@pytest.fixture
def temp_session_dir():
    """Create a temporary directory for session files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_session_json(temp_session_dir):
    """Create a sample session JSON file."""
    session_data = {
        "sessionId": "test-session-001",
        "startTime": "2026-01-12T10:30:00Z",
        "duration": 45,
        "topics": ["Python testing", "Context capture"],
        "decisions": ["Use pytest for testing", "Implement dataclass pattern"],
        "messages": [
            {"role": "user", "content": "How do I test Python code?"},
            {
                "role": "assistant",
                "content": "We decided to use pytest because it's the standard testing framework.",
            },
        ],
    }

    file_path = temp_session_dir / "session_001.json"
    with open(file_path, "w") as f:
        json.dump(session_data, f)

    return file_path


@pytest.fixture
def sample_session_jsonl(temp_session_dir):
    """Create a sample JSONL session file."""
    session_line = json.dumps(
        {
            "sessionId": "test-session-002",
            "startTime": "2026-01-11T14:00:00Z",
            "messages": [{"role": "user", "content": "Test JSONL format"}],
        }
    )

    file_path = temp_session_dir / "session_002.jsonl"
    with open(file_path, "w") as f:
        f.write(session_line + "\n")

    return file_path


@pytest.fixture
def malformed_session_json(temp_session_dir):
    """Create a malformed JSON file."""
    file_path = temp_session_dir / "malformed.json"
    with open(file_path, "w") as f:
        f.write("{invalid json content")

    return file_path


@pytest.fixture
def minimal_session_json(temp_session_dir):
    """Create a minimal session JSON with only required fields."""
    session_data = {"sessionId": "minimal-001"}

    file_path = temp_session_dir / "minimal.json"
    with open(file_path, "w") as f:
        json.dump(session_data, f)

    return file_path


def test_read_session_history_success(sample_session_json, sample_session_jsonl, temp_session_dir):
    """Test successful reading of session history."""
    summaries = read_session_history(str(temp_session_dir))

    assert len(summaries) == 2
    assert all(isinstance(s, SessionSummary) for s in summaries)

    # Check sorting (most recent first)
    assert summaries[0].session_id == "test-session-001"
    assert summaries[1].session_id == "test-session-002"


def test_read_session_history_with_limit(
    sample_session_json, sample_session_jsonl, temp_session_dir
):
    """Test reading session history with limit parameter."""
    summaries = read_session_history(str(temp_session_dir), limit=1)

    assert len(summaries) == 1
    assert summaries[0].session_id == "test-session-001"


def test_read_session_history_empty_directory(temp_session_dir):
    """Test reading from empty directory."""
    summaries = read_session_history(str(temp_session_dir))

    assert len(summaries) == 0


def test_read_session_history_nonexistent_directory():
    """Test reading from non-existent directory."""
    with pytest.raises(FileNotFoundError):
        read_session_history("/nonexistent/path/to/sessions")


def test_read_session_history_with_malformed_file(
    sample_session_json, malformed_session_json, temp_session_dir
):
    """Test that malformed files are skipped gracefully."""
    summaries = read_session_history(str(temp_session_dir))

    # Should have 1 valid session, malformed one is skipped
    assert len(summaries) == 1
    assert summaries[0].session_id == "test-session-001"


def test_parse_session_file_standard_json(sample_session_json):
    """Test parsing a standard JSON session file."""
    summary = _parse_session_file(sample_session_json)

    assert summary is not None
    assert summary.session_id == "test-session-001"
    assert summary.date.year == 2026
    assert summary.date.month == 1
    assert summary.date.day == 12
    assert summary.duration_minutes == 45
    assert "Python testing" in summary.topics
    assert "Use pytest for testing" in summary.decisions
    assert str(sample_session_json) == summary.file_path


def test_parse_session_file_jsonl(sample_session_jsonl):
    """Test parsing a JSONL session file."""
    summary = _parse_session_file(sample_session_jsonl)

    assert summary is not None
    assert summary.session_id == "test-session-002"
    assert summary.date.year == 2026


def test_parse_session_file_minimal(minimal_session_json):
    """Test parsing minimal session file with fallback values."""
    summary = _parse_session_file(minimal_session_json)

    assert summary is not None
    assert summary.session_id == "minimal-001"
    assert summary.duration_minutes is None
    assert summary.date is not None  # Should fallback to file mtime
    assert summary.topics == []
    assert summary.decisions == []


def test_parse_session_file_invalid_json(malformed_session_json):
    """Test parsing invalid JSON returns None."""
    summary = _parse_session_file(malformed_session_json)

    assert summary is None


def test_extract_topics_from_explicit_field():
    """Test topic extraction from explicit topics field."""
    data = {"topics": ["Topic 1", "Topic 2", "Topic 3"]}

    topics = _extract_topics(data)

    assert len(topics) == 3
    assert "Topic 1" in topics


def test_extract_topics_from_summary():
    """Test topic extraction from summary field."""
    data = {"summary": "Discussion about Python testing strategies"}

    topics = _extract_topics(data)

    assert len(topics) == 1
    assert "Discussion about Python testing strategies" in topics


def test_extract_topics_from_messages():
    """Test topic extraction from message content."""
    data = {
        "messages": [
            {"content": "First message about testing"},
            {"content": "Second message about deployment"},
            {"content": "Short"},  # Should be skipped (too short)
        ]
    }

    topics = _extract_topics(data)

    assert len(topics) >= 1
    assert any("First message about testing" in t for t in topics)


def test_extract_topics_limit():
    """Test that topic extraction limits results."""
    data = {"topics": [f"Topic {i}" for i in range(20)]}

    topics = _extract_topics(data)

    assert len(topics) == 10  # Should be limited to 10


def test_extract_decisions_from_explicit_field():
    """Test decision extraction from explicit decisions field."""
    data = {"decisions": ["Decision 1", "Decision 2"]}

    decisions = _extract_decisions(data)

    assert len(decisions) == 2
    assert "Decision 1" in decisions


def test_extract_decisions_from_messages():
    """Test decision extraction from message keywords."""
    data = {
        "messages": [
            {"content": "We decided to use Python for this project."},
            {"content": "After consideration, will implement feature X."},
            {"content": "Just a regular message without decisions."},
        ]
    }

    decisions = _extract_decisions(data)

    assert len(decisions) >= 1
    assert any("decided" in d.lower() for d in decisions)


def test_extract_decisions_limit():
    """Test that decision extraction limits results."""
    data = {
        "messages": [{"content": f"We decided on option {i}."} for i in range(10)]
    }

    decisions = _extract_decisions(data)

    assert len(decisions) == 5  # Should be limited to 5


def test_extract_decisions_no_keywords():
    """Test decision extraction with no decision keywords."""
    data = {"messages": [{"content": "Regular conversation about the weather"}]}

    decisions = _extract_decisions(data)

    assert len(decisions) == 0


def test_session_summary_dataclass():
    """Test SessionSummary dataclass creation and defaults."""
    summary = SessionSummary(
        session_id="test-001",
        date=datetime(2026, 1, 12, 10, 30),
    )

    assert summary.session_id == "test-001"
    assert summary.date.year == 2026
    assert summary.duration_minutes is None
    assert summary.topics == []
    assert summary.decisions == []
    assert summary.file_path == ""


def test_session_summary_with_all_fields():
    """Test SessionSummary with all fields populated."""
    summary = SessionSummary(
        session_id="test-002",
        date=datetime(2026, 1, 12, 10, 30),
        duration_minutes=60,
        topics=["Topic A", "Topic B"],
        decisions=["Decision X"],
        file_path="/path/to/session.json",
    )

    assert summary.duration_minutes == 60
    assert len(summary.topics) == 2
    assert len(summary.decisions) == 1
    assert summary.file_path == "/path/to/session.json"
