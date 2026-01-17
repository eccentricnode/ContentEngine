"""Tests for collect-analytics CLI command."""
# mypy: disable-error-code="no-untyped-def"

from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from cli import cli
from agents.linkedin.analytics import PostMetrics


def test_collect_analytics_command_exists():
    """Test that collect-analytics command exists and has help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["collect-analytics", "--help"])
    assert result.exit_code == 0
    assert "Collect LinkedIn post analytics" in result.output
    assert "--days-back" in result.output
    assert "--test-post" in result.output


def test_collect_analytics_missing_token_env_and_db():
    """Test error when LINKEDIN_ACCESS_TOKEN is missing from both env and DB."""
    runner = CliRunner()

    with patch("os.getenv", return_value=None), \
         patch("cli.get_db") as mock_db:
        # Mock database to return None for OAuth token
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_db.return_value = mock_session

        result = runner.invoke(cli, ["collect-analytics"])

        assert result.exit_code == 1
        assert "❌ Error: LINKEDIN_ACCESS_TOKEN not found" in result.output
        assert "export LINKEDIN_ACCESS_TOKEN" in result.output


def test_collect_analytics_loads_token_from_env():
    """Test that command loads access token from environment variable."""
    runner = CliRunner()

    with patch("os.getenv", return_value="test_token_from_env"), \
         patch("agents.linkedin.analytics.LinkedInAnalytics") as mock_analytics_class, \
         runner.isolated_filesystem():

        # Create empty posts.jsonl
        Path("data").mkdir()
        Path("data/posts.jsonl").write_text("")

        mock_analytics = MagicMock()
        mock_analytics.update_posts_with_analytics.return_value = 0
        mock_analytics_class.return_value = mock_analytics

        result = runner.invoke(cli, ["collect-analytics"])

        # Verify LinkedInAnalytics was instantiated with env token
        mock_analytics_class.assert_called_once_with("test_token_from_env")
        assert result.exit_code == 0


def test_collect_analytics_loads_token_from_database():
    """Test that command loads access token from database if env var missing."""
    runner = CliRunner()

    with patch("os.getenv", return_value=None), \
         patch("cli.get_db") as mock_db, \
         patch("agents.linkedin.analytics.LinkedInAnalytics") as mock_analytics_class, \
         runner.isolated_filesystem():

        # Mock database to return OAuth token
        mock_token = MagicMock()
        mock_token.access_token = "test_token_from_db"
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_token
        mock_db.return_value = mock_session

        # Create empty posts.jsonl
        Path("data").mkdir()
        Path("data/posts.jsonl").write_text("")

        mock_analytics = MagicMock()
        mock_analytics.update_posts_with_analytics.return_value = 0
        mock_analytics_class.return_value = mock_analytics

        result = runner.invoke(cli, ["collect-analytics"])

        # Verify LinkedInAnalytics was instantiated with DB token
        mock_analytics_class.assert_called_once_with("test_token_from_db")
        assert result.exit_code == 0


def test_collect_analytics_test_post_success():
    """Test fetching analytics for a single test post."""
    runner = CliRunner()
    test_urn = "urn:li:share:7412668096475369472"

    with patch("os.getenv", return_value="test_token"), \
         patch("agents.linkedin.analytics.LinkedInAnalytics") as mock_analytics_class:

        mock_analytics = MagicMock()
        mock_metrics = PostMetrics(
            post_id=test_urn,
            impressions=1000,
            likes=50,
            comments=10,
            shares=5,
            clicks=25,
            engagement_rate=0.09,
            fetched_at="2026-01-17T12:00:00"
        )
        mock_analytics.get_post_analytics.return_value = mock_metrics
        mock_analytics_class.return_value = mock_analytics

        result = runner.invoke(cli, ["collect-analytics", "--test-post", test_urn])

        assert result.exit_code == 0
        assert "Fetching analytics for" in result.output
        assert "Impressions: 1,000" in result.output
        assert "Likes: 50" in result.output
        assert "Comments: 10" in result.output
        assert "Shares: 5" in result.output
        assert "Clicks: 25" in result.output
        assert "Engagement Rate: 9.00%" in result.output
        mock_analytics.get_post_analytics.assert_called_once_with(test_urn)


def test_collect_analytics_test_post_failure():
    """Test error handling when fetching single post fails."""
    runner = CliRunner()
    test_urn = "urn:li:share:invalid"

    with patch("os.getenv", return_value="test_token"), \
         patch("agents.linkedin.analytics.LinkedInAnalytics") as mock_analytics_class:

        mock_analytics = MagicMock()
        mock_analytics.get_post_analytics.return_value = None
        mock_analytics_class.return_value = mock_analytics

        result = runner.invoke(cli, ["collect-analytics", "--test-post", test_urn])

        assert result.exit_code == 1
        assert "✗ Failed to fetch analytics" in result.output
        assert "Make sure:" in result.output


def test_collect_analytics_missing_posts_file():
    """Test error when posts.jsonl file doesn't exist."""
    runner = CliRunner()

    with patch("os.getenv", return_value="test_token"), \
         runner.isolated_filesystem():

        result = runner.invoke(cli, ["collect-analytics"])

        assert result.exit_code == 1
        assert "❌ Error: data/posts.jsonl not found" in result.output
        assert "mkdir -p data" in result.output


def test_collect_analytics_update_posts_success():
    """Test successful analytics update for posts."""
    runner = CliRunner()

    with patch("os.getenv", return_value="test_token"), \
         patch("agents.linkedin.analytics.LinkedInAnalytics") as mock_analytics_class, \
         runner.isolated_filesystem():

        # Create posts.jsonl
        Path("data").mkdir()
        Path("data/posts.jsonl").write_text("")

        mock_analytics = MagicMock()
        mock_analytics.update_posts_with_analytics.return_value = 3
        mock_analytics_class.return_value = mock_analytics

        result = runner.invoke(cli, ["collect-analytics", "--days-back", "7"])

        assert result.exit_code == 0
        assert "Fetching analytics for posts from last 7 days" in result.output
        assert "✓ Updated analytics for 3 posts" in result.output
        mock_analytics.update_posts_with_analytics.assert_called_once()


def test_collect_analytics_update_posts_zero_updates():
    """Test when no posts need updates."""
    runner = CliRunner()

    with patch("os.getenv", return_value="test_token"), \
         patch("agents.linkedin.analytics.LinkedInAnalytics") as mock_analytics_class, \
         runner.isolated_filesystem():

        # Create posts.jsonl
        Path("data").mkdir()
        Path("data/posts.jsonl").write_text("")

        mock_analytics = MagicMock()
        mock_analytics.update_posts_with_analytics.return_value = 0
        mock_analytics_class.return_value = mock_analytics

        result = runner.invoke(cli, ["collect-analytics"])

        assert result.exit_code == 0
        assert "✓ Updated analytics for 0 posts" in result.output
        assert "No posts needed updates" in result.output
        assert "All recent posts already have analytics" in result.output


def test_collect_analytics_custom_days_back():
    """Test custom --days-back flag."""
    runner = CliRunner()

    with patch("os.getenv", return_value="test_token"), \
         patch("agents.linkedin.analytics.LinkedInAnalytics") as mock_analytics_class, \
         runner.isolated_filesystem():

        # Create posts.jsonl
        Path("data").mkdir()
        Path("data/posts.jsonl").write_text("")

        mock_analytics = MagicMock()
        mock_analytics.update_posts_with_analytics.return_value = 5
        mock_analytics_class.return_value = mock_analytics

        result = runner.invoke(cli, ["collect-analytics", "--days-back", "14"])

        assert result.exit_code == 0
        assert "Fetching analytics for posts from last 14 days" in result.output
        assert "✓ Updated analytics for 5 posts" in result.output
        # Verify days_back parameter was passed
        mock_analytics.update_posts_with_analytics.assert_called_once()
        call_args = mock_analytics.update_posts_with_analytics.call_args
        assert call_args[1]["days_back"] == 14


def test_collect_analytics_update_exception_handling():
    """Test exception handling during analytics update."""
    runner = CliRunner()

    with patch("os.getenv", return_value="test_token"), \
         patch("agents.linkedin.analytics.LinkedInAnalytics") as mock_analytics_class, \
         runner.isolated_filesystem():

        # Create posts.jsonl
        Path("data").mkdir()
        Path("data/posts.jsonl").write_text("")

        mock_analytics = MagicMock()
        mock_analytics.update_posts_with_analytics.side_effect = Exception("API error")
        mock_analytics_class.return_value = mock_analytics

        result = runner.invoke(cli, ["collect-analytics"])

        assert result.exit_code == 1
        assert "❌ Error updating analytics: API error" in result.output


def test_collect_analytics_header_display():
    """Test that command displays proper header."""
    runner = CliRunner()

    with patch("os.getenv", return_value="test_token"), \
         patch("agents.linkedin.analytics.LinkedInAnalytics") as mock_analytics_class, \
         runner.isolated_filesystem():

        # Create posts.jsonl
        Path("data").mkdir()
        Path("data/posts.jsonl").write_text("")

        mock_analytics = MagicMock()
        mock_analytics.update_posts_with_analytics.return_value = 0
        mock_analytics_class.return_value = mock_analytics

        result = runner.invoke(cli, ["collect-analytics"])

        assert "=" * 60 in result.output
        assert "LinkedIn Analytics Collection" in result.output
