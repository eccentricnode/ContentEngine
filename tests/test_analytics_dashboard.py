# mypy: disable-error-code="no-untyped-def"
"""Tests for scripts/analytics_dashboard.py"""

import csv
import json
from pathlib import Path
from unittest.mock import patch

from agents.linkedin.analytics import Post, PostMetrics

# Import dashboard functions
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analytics_dashboard import (
    load_posts,
    truncate_post_id,
    format_engagement_rate,
    display_dashboard,
    export_to_csv,
    main,
)


class TestLoadPosts:
    """Test load_posts function"""

    def test_load_posts_empty_file(self, tmp_path: Path):
        """Test loading from empty file"""
        posts_file = tmp_path / "posts.jsonl"
        posts_file.write_text("")

        posts = load_posts(posts_file)
        assert posts == []

    def test_load_posts_missing_file(self, tmp_path: Path):
        """Test loading from missing file"""
        posts_file = tmp_path / "nonexistent.jsonl"
        posts = load_posts(posts_file)
        assert posts == []

    def test_load_posts_without_metrics(self, tmp_path: Path):
        """Test loading posts without metrics"""
        posts_file = tmp_path / "posts.jsonl"
        posts_file.write_text(
            json.dumps({
                "post_id": "urn:li:share:123",
                "posted_at": "2026-01-01T00:00:00",
                "blueprint_version": "manual_v1",
                "content": "Test post",
                "metrics": None,
            }) + "\n"
        )

        posts = load_posts(posts_file)
        assert len(posts) == 1
        assert posts[0].post_id == "urn:li:share:123"
        assert posts[0].metrics is None

    def test_load_posts_with_metrics(self, tmp_path: Path):
        """Test loading posts with metrics"""
        posts_file = tmp_path / "posts.jsonl"
        posts_file.write_text(
            json.dumps({
                "post_id": "urn:li:share:123",
                "posted_at": "2026-01-01T00:00:00",
                "blueprint_version": "manual_v1",
                "content": "Test post",
                "metrics": {
                    "post_id": "urn:li:share:123",
                    "impressions": 1000,
                    "likes": 50,
                    "comments": 10,
                    "shares": 5,
                    "clicks": 25,
                    "engagement_rate": 0.09,
                    "fetched_at": "2026-01-02T00:00:00",
                },
            }) + "\n"
        )

        posts = load_posts(posts_file)
        assert len(posts) == 1
        assert posts[0].post_id == "urn:li:share:123"
        assert posts[0].metrics is not None
        assert posts[0].metrics.impressions == 1000
        assert posts[0].metrics.engagement_rate == 0.09

    def test_load_posts_multiple(self, tmp_path: Path):
        """Test loading multiple posts"""
        posts_file = tmp_path / "posts.jsonl"
        with open(posts_file, "w") as f:
            f.write(json.dumps({
                "post_id": "urn:li:share:123",
                "posted_at": "2026-01-01T00:00:00",
                "blueprint_version": "manual_v1",
                "content": "Post 1",
                "metrics": None,
            }) + "\n")
            f.write(json.dumps({
                "post_id": "urn:li:share:456",
                "posted_at": "2026-01-02T00:00:00",
                "blueprint_version": "manual_v1",
                "content": "Post 2",
                "metrics": {
                    "post_id": "urn:li:share:456",
                    "impressions": 500,
                    "likes": 25,
                    "comments": 5,
                    "shares": 2,
                    "clicks": 10,
                    "engagement_rate": 0.084,
                    "fetched_at": "2026-01-03T00:00:00",
                },
            }) + "\n")

        posts = load_posts(posts_file)
        assert len(posts) == 2
        assert posts[0].post_id == "urn:li:share:123"
        assert posts[1].post_id == "urn:li:share:456"


class TestTruncatePostId:
    """Test truncate_post_id function"""

    def test_truncate_short_id(self):
        """Test truncation with short ID"""
        post_id = "urn:li:share:123"
        result = truncate_post_id(post_id, 30)
        assert result == "urn:li:share:123"

    def test_truncate_long_id(self):
        """Test truncation with long ID"""
        post_id = "urn:li:share:7412668096475369472_very_long_suffix"
        result = truncate_post_id(post_id, 30)
        assert len(result) == 30
        assert result.endswith("...")
        assert result.startswith("urn:li:share:")

    def test_truncate_exact_length(self):
        """Test truncation with exact length"""
        post_id = "urn:li:share:12345678901234"  # 30 chars
        result = truncate_post_id(post_id, 30)
        assert result == post_id


class TestFormatEngagementRate:
    """Test format_engagement_rate function"""

    def test_format_zero_rate(self):
        """Test formatting zero engagement rate"""
        result = format_engagement_rate(0.0)
        assert result == "0.00%"

    def test_format_normal_rate(self):
        """Test formatting normal engagement rate"""
        result = format_engagement_rate(0.09)
        assert result == "9.00%"

    def test_format_high_rate(self):
        """Test formatting high engagement rate"""
        result = format_engagement_rate(0.15)
        assert result == "15.00%"

    def test_format_low_rate(self):
        """Test formatting low engagement rate"""
        result = format_engagement_rate(0.0123)
        assert result == "1.23%"


class TestDisplayDashboard:
    """Test display_dashboard function"""

    def test_display_no_posts(self, capsys):
        """Test display with no posts"""
        display_dashboard([])
        captured = capsys.readouterr()
        assert "No posts found" in captured.out

    def test_display_posts_without_metrics(self, capsys):
        """Test display with posts but no metrics"""
        posts = [
            Post(
                post_id="urn:li:share:123",
                posted_at="2026-01-01T00:00:00",
                blueprint_version="manual_v1",
                content="Test",
                metrics=None,
            )
        ]
        display_dashboard(posts)
        captured = capsys.readouterr()
        assert "Found 1 posts, but none have analytics data yet" in captured.out
        assert "collect-analytics" in captured.out

    def test_display_posts_with_metrics(self, capsys):
        """Test display with posts with metrics"""
        metrics = PostMetrics(
            post_id="urn:li:share:123",
            impressions=1000,
            likes=50,
            comments=10,
            shares=5,
            clicks=25,
            engagement_rate=0.09,
            fetched_at="2026-01-02T00:00:00",
        )
        posts = [
            Post(
                post_id="urn:li:share:123",
                posted_at="2026-01-01T00:00:00",
                blueprint_version="manual_v1",
                content="Test",
                metrics=metrics,
            )
        ]
        display_dashboard(posts)
        captured = capsys.readouterr()

        # Check table headers
        assert "Post ID" in captured.out
        assert "Date" in captured.out
        assert "Engagement" in captured.out
        assert "Likes" in captured.out
        assert "Comments" in captured.out

        # Check data
        assert "2026-01-01" in captured.out
        assert "9.00%" in captured.out
        assert "50" in captured.out
        assert "10" in captured.out

        # Check summary
        assert "Summary:" in captured.out
        assert "Total posts: 1" in captured.out
        assert "Posts with analytics: 1" in captured.out
        assert "Average engagement rate: 9.00%" in captured.out

    def test_display_best_worst_posts(self, capsys):
        """Test display shows best and worst performing posts"""
        posts = [
            Post(
                post_id="urn:li:share:123",
                posted_at="2026-01-01T00:00:00",
                blueprint_version="manual_v1",
                content="Low engagement",
                metrics=PostMetrics(
                    post_id="urn:li:share:123",
                    impressions=1000,
                    likes=20,
                    comments=2,
                    shares=0,
                    clicks=5,
                    engagement_rate=0.027,
                    fetched_at="2026-01-02T00:00:00",
                ),
            ),
            Post(
                post_id="urn:li:share:456",
                posted_at="2026-01-02T00:00:00",
                blueprint_version="manual_v1",
                content="High engagement",
                metrics=PostMetrics(
                    post_id="urn:li:share:456",
                    impressions=1000,
                    likes=150,
                    comments=30,
                    shares=10,
                    clicks=50,
                    engagement_rate=0.24,
                    fetched_at="2026-01-03T00:00:00",
                ),
            ),
        ]
        display_dashboard(posts)
        captured = capsys.readouterr()

        # Check best/worst sections
        assert "Best performing post" in captured.out
        assert "Worst performing post" in captured.out
        assert "24.00%" in captured.out  # Best engagement
        assert "2.70%" in captured.out  # Worst engagement

    def test_display_average_engagement(self, capsys):
        """Test display calculates average engagement correctly"""
        posts = [
            Post(
                post_id="urn:li:share:1",
                posted_at="2026-01-01T00:00:00",
                blueprint_version="manual_v1",
                content="Post 1",
                metrics=PostMetrics(
                    post_id="urn:li:share:1",
                    impressions=1000,
                    likes=50,
                    comments=10,
                    shares=5,
                    clicks=25,
                    engagement_rate=0.09,
                    fetched_at="2026-01-02T00:00:00",
                ),
            ),
            Post(
                post_id="urn:li:share:2",
                posted_at="2026-01-02T00:00:00",
                blueprint_version="manual_v1",
                content="Post 2",
                metrics=PostMetrics(
                    post_id="urn:li:share:2",
                    impressions=1000,
                    likes=70,
                    comments=15,
                    shares=8,
                    clicks=30,
                    engagement_rate=0.123,
                    fetched_at="2026-01-03T00:00:00",
                ),
            ),
        ]
        display_dashboard(posts)
        captured = capsys.readouterr()

        # Average should be (0.09 + 0.123) / 2 = 0.1065 = 10.65%
        assert "Average engagement rate: 10.65%" in captured.out


class TestExportToCsv:
    """Test export_to_csv function"""

    def test_export_no_metrics(self, tmp_path: Path, capsys):
        """Test export with no metrics"""
        posts = [
            Post(
                post_id="urn:li:share:123",
                posted_at="2026-01-01T00:00:00",
                blueprint_version="manual_v1",
                content="Test",
                metrics=None,
            )
        ]
        output_file = tmp_path / "output.csv"
        export_to_csv(posts, output_file)

        captured = capsys.readouterr()
        assert "No posts with metrics to export" in captured.out
        assert not output_file.exists()

    def test_export_with_metrics(self, tmp_path: Path, capsys):
        """Test export with metrics"""
        metrics = PostMetrics(
            post_id="urn:li:share:123",
            impressions=1000,
            likes=50,
            comments=10,
            shares=5,
            clicks=25,
            engagement_rate=0.09,
            fetched_at="2026-01-02T00:00:00",
        )
        posts = [
            Post(
                post_id="urn:li:share:123",
                posted_at="2026-01-01T00:00:00",
                blueprint_version="manual_v1",
                content="Test",
                metrics=metrics,
            )
        ]
        output_file = tmp_path / "output.csv"
        export_to_csv(posts, output_file)

        captured = capsys.readouterr()
        assert f"Exported 1 posts to {output_file}" in captured.out
        assert output_file.exists()

        # Verify CSV content
        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["post_id"] == "urn:li:share:123"
            assert rows[0]["impressions"] == "1000"
            assert rows[0]["likes"] == "50"
            assert rows[0]["comments"] == "10"
            assert rows[0]["engagement_rate"] == "0.09"

    def test_export_multiple_posts(self, tmp_path: Path):
        """Test export with multiple posts"""
        posts = [
            Post(
                post_id="urn:li:share:123",
                posted_at="2026-01-01T00:00:00",
                blueprint_version="manual_v1",
                content="Post 1",
                metrics=PostMetrics(
                    post_id="urn:li:share:123",
                    impressions=1000,
                    likes=50,
                    comments=10,
                    shares=5,
                    clicks=25,
                    engagement_rate=0.09,
                    fetched_at="2026-01-02T00:00:00",
                ),
            ),
            Post(
                post_id="urn:li:share:456",
                posted_at="2026-01-02T00:00:00",
                blueprint_version="manual_v1",
                content="Post 2",
                metrics=PostMetrics(
                    post_id="urn:li:share:456",
                    impressions=500,
                    likes=25,
                    comments=5,
                    shares=2,
                    clicks=10,
                    engagement_rate=0.084,
                    fetched_at="2026-01-03T00:00:00",
                ),
            ),
        ]
        output_file = tmp_path / "output.csv"
        export_to_csv(posts, output_file)

        # Verify CSV has both rows
        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["post_id"] == "urn:li:share:123"
            assert rows[1]["post_id"] == "urn:li:share:456"

    def test_export_csv_headers(self, tmp_path: Path):
        """Test CSV export has correct headers"""
        posts = [
            Post(
                post_id="urn:li:share:123",
                posted_at="2026-01-01T00:00:00",
                blueprint_version="manual_v1",
                content="Test",
                metrics=PostMetrics(
                    post_id="urn:li:share:123",
                    impressions=1000,
                    likes=50,
                    comments=10,
                    shares=5,
                    clicks=25,
                    engagement_rate=0.09,
                    fetched_at="2026-01-02T00:00:00",
                ),
            )
        ]
        output_file = tmp_path / "output.csv"
        export_to_csv(posts, output_file)

        # Verify headers
        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            assert headers is not None
            assert "post_id" in headers
            assert "posted_at" in headers
            assert "blueprint_version" in headers
            assert "impressions" in headers
            assert "likes" in headers
            assert "comments" in headers
            assert "shares" in headers
            assert "clicks" in headers
            assert "engagement_rate" in headers
            assert "fetched_at" in headers


class TestMain:
    """Test main function"""

    @patch("analytics_dashboard.load_posts")
    @patch("analytics_dashboard.display_dashboard")
    def test_main_default(self, mock_display, mock_load):
        """Test main with default args"""
        mock_load.return_value = []

        with patch("sys.argv", ["analytics_dashboard.py"]):
            main()

        mock_load.assert_called_once()
        mock_display.assert_called_once()

    @patch("analytics_dashboard.load_posts")
    @patch("analytics_dashboard.display_dashboard")
    @patch("analytics_dashboard.export_to_csv")
    def test_main_with_export(self, mock_export, mock_display, mock_load):
        """Test main with --export-csv flag"""
        mock_load.return_value = []

        with patch("sys.argv", ["analytics_dashboard.py", "--export-csv", "output.csv"]):
            main()

        mock_load.assert_called_once()
        mock_display.assert_called_once()
        mock_export.assert_called_once()

    @patch("analytics_dashboard.load_posts")
    @patch("analytics_dashboard.display_dashboard")
    @patch("analytics_dashboard.export_to_csv")
    def test_main_export_receives_correct_path(self, mock_export, mock_display, mock_load):
        """Test main passes correct path to export"""
        mock_load.return_value = []

        with patch("sys.argv", ["analytics_dashboard.py", "--export-csv", "results.csv"]):
            main()

        # Check that export was called with Path object
        call_args = mock_export.call_args
        assert call_args is not None
        assert str(call_args[0][1]) == "results.csv"
