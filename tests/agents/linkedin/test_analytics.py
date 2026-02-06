"""Tests for LinkedIn Analytics Integration

NOTE: Analytics API access blocked - LinkedIn rejected app approval.
These tests are skipped until analytics access is restored.
"""
# mypy: disable-error-code="no-untyped-def"

import json
import pytest
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import Mock, patch
import requests  # type: ignore[import-untyped]

from agents.linkedin.analytics import (
    LinkedInAnalytics,
    Post,
    PostMetrics,
)

# Skip all tests in this module - Analytics API access blocked
pytestmark = pytest.mark.skip(reason="LinkedIn Analytics API access blocked - app rejected")


@pytest.fixture
def analytics() -> LinkedInAnalytics:
    """Create LinkedInAnalytics instance with test token"""
    return LinkedInAnalytics(access_token="test_token_12345")


@pytest.fixture
def sample_post() -> Post:
    """Create sample Post object"""
    return Post(
        post_id="urn:li:share:7412668096475369472",
        posted_at="2026-01-01T10:00:00",
        blueprint_version="manual_v1",
        content="This is a test LinkedIn post about building something amazing!",
    )


@pytest.fixture
def sample_metrics() -> PostMetrics:
    """Create sample PostMetrics object"""
    return PostMetrics(
        post_id="urn:li:share:7412668096475369472",
        impressions=1500,
        likes=45,
        comments=8,
        shares=3,
        clicks=120,
        engagement_rate=0.037,
        fetched_at="2026-01-17T12:00:00",
    )


@pytest.fixture
def mock_linkedin_response() -> Dict[str, Any]:
    """Mock successful LinkedIn API response"""
    return {
        "elements": [
            {
                "totalShareStatistics": {
                    "impressionCount": 1500,
                    "engagement": 56,
                    "likeCount": 45,
                    "commentCount": 8,
                    "shareCount": 3,
                    "clickCount": 120,
                }
            }
        ]
    }


class TestLinkedInAnalyticsInit:
    """Test LinkedInAnalytics initialization"""

    def test_init_sets_access_token(self, analytics):
        """Should set access token on initialization"""
        assert analytics.access_token == "test_token_12345"

    def test_init_sets_base_url(self, analytics):
        """Should set LinkedIn API base URL"""
        assert analytics.base_url == "https://api.linkedin.com/v2"

    def test_init_sets_authorization_header(self, analytics):
        """Should set Authorization header with Bearer token"""
        assert analytics.headers["Authorization"] == "Bearer test_token_12345"

    def test_init_sets_content_type_header(self, analytics):
        """Should set Content-Type header"""
        assert analytics.headers["Content-Type"] == "application/json"


class TestGetPostAnalytics:
    """Test get_post_analytics method"""

    @patch("agents.linkedin.analytics.requests.get")
    def test_get_post_analytics_success(
        self, mock_get, analytics, mock_linkedin_response
    ):
        """Should fetch and parse analytics successfully"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = mock_linkedin_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Fetch analytics
        share_urn = "urn:li:share:7412668096475369472"
        metrics = analytics.get_post_analytics(share_urn)

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "https://api.linkedin.com/v2/organizationalEntityShareStatistics" in call_args[0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test_token_12345"
        assert call_args[1]["params"]["q"] == "share"

        # Verify metrics
        assert metrics is not None
        assert metrics.post_id == share_urn
        assert metrics.impressions == 1500
        assert metrics.likes == 45
        assert metrics.comments == 8
        assert metrics.shares == 3
        assert metrics.clicks == 120
        # engagement_rate = 56 / 1500 = 0.037333...
        assert abs(metrics.engagement_rate - 0.037333) < 0.0001
        assert metrics.fetched_at  # Should have timestamp

    @patch("agents.linkedin.analytics.requests.get")
    def test_get_post_analytics_extracts_share_id(self, mock_get, analytics):
        """Should extract share ID from URN"""
        mock_response = Mock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        analytics.get_post_analytics("urn:li:share:7412668096475369472")

        # Verify share ID in params
        call_params = mock_get.call_args[1]["params"]
        assert call_params["shares[0]"] == "urn:li:share:7412668096475369472"

    @patch("agents.linkedin.analytics.requests.get")
    def test_get_post_analytics_empty_response(self, mock_get, analytics):
        """Should return None when API returns empty elements"""
        mock_response = Mock()
        mock_response.json.return_value = {"elements": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        metrics = analytics.get_post_analytics("urn:li:share:123")

        assert metrics is None

    @patch("agents.linkedin.analytics.requests.get")
    def test_get_post_analytics_missing_elements_key(self, mock_get, analytics):
        """Should return None when response missing elements key"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": "something else"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        metrics = analytics.get_post_analytics("urn:li:share:123")

        assert metrics is None

    @patch("agents.linkedin.analytics.requests.get")
    def test_get_post_analytics_handles_request_exception(self, mock_get, analytics):
        """Should return None and print error on request exception"""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        metrics = analytics.get_post_analytics("urn:li:share:123")

        assert metrics is None

    @patch("agents.linkedin.analytics.requests.get")
    def test_get_post_analytics_handles_timeout(self, mock_get, analytics):
        """Should return None on timeout"""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        metrics = analytics.get_post_analytics("urn:li:share:123")

        assert metrics is None

    @patch("agents.linkedin.analytics.requests.get")
    def test_get_post_analytics_handles_401_unauthorized(self, mock_get, analytics):
        """Should return None on 401 Unauthorized"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized"
        )
        mock_get.return_value = mock_response

        metrics = analytics.get_post_analytics("urn:li:share:123")

        assert metrics is None

    @patch("agents.linkedin.analytics.requests.get")
    def test_get_post_analytics_zero_impressions_engagement_rate(
        self, mock_get, analytics
    ):
        """Should handle zero impressions (avoid division by zero)"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "totalShareStatistics": {
                        "impressionCount": 0,
                        "engagement": 0,
                        "likeCount": 0,
                        "commentCount": 0,
                        "shareCount": 0,
                        "clickCount": 0,
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        metrics = analytics.get_post_analytics("urn:li:share:123")

        assert metrics is not None
        assert metrics.impressions == 0
        assert metrics.engagement_rate == 0.0  # Should not raise ZeroDivisionError


class TestSavePostWithMetrics:
    """Test save_post_with_metrics method"""

    def test_save_post_with_metrics_creates_jsonl(
        self, analytics, sample_post, sample_metrics, tmp_path
    ):
        """Should create valid JSONL file"""
        filepath = tmp_path / "posts.jsonl"
        sample_post.metrics = sample_metrics

        analytics.save_post_with_metrics(sample_post, filepath)

        assert filepath.exists()
        content = filepath.read_text()
        assert content.endswith("\n")

    def test_save_post_with_metrics_correct_format(
        self, analytics, sample_post, sample_metrics, tmp_path
    ):
        """Should write correct JSONL format"""
        filepath = tmp_path / "posts.jsonl"
        sample_post.metrics = sample_metrics

        analytics.save_post_with_metrics(sample_post, filepath)

        # Read and parse JSONL
        with open(filepath) as f:
            data = json.loads(f.read().strip())

        assert data["post_id"] == "urn:li:share:7412668096475369472"
        assert data["posted_at"] == "2026-01-01T10:00:00"
        assert data["blueprint_version"] == "manual_v1"
        assert "This is a test LinkedIn post" in data["content"]

    def test_save_post_with_metrics_includes_metrics(
        self, analytics, sample_post, sample_metrics, tmp_path
    ):
        """Should include metrics in JSONL"""
        filepath = tmp_path / "posts.jsonl"
        sample_post.metrics = sample_metrics

        analytics.save_post_with_metrics(sample_post, filepath)

        with open(filepath) as f:
            data = json.loads(f.read().strip())

        assert "metrics" in data
        assert data["metrics"]["impressions"] == 1500
        assert data["metrics"]["likes"] == 45
        assert data["metrics"]["engagement_rate"] == 0.037

    def test_save_post_without_metrics(self, analytics, sample_post, tmp_path):
        """Should save post without metrics (metrics=None)"""
        filepath = tmp_path / "posts.jsonl"

        analytics.save_post_with_metrics(sample_post, filepath)

        with open(filepath) as f:
            data = json.loads(f.read().strip())

        assert data["post_id"] == "urn:li:share:7412668096475369472"
        assert data["metrics"] is None

    def test_save_multiple_posts_appends(
        self, analytics, sample_post, sample_metrics, tmp_path
    ):
        """Should append multiple posts to JSONL"""
        filepath = tmp_path / "posts.jsonl"

        # Save first post
        sample_post.metrics = sample_metrics
        analytics.save_post_with_metrics(sample_post, filepath)

        # Save second post
        post2 = Post(
            post_id="urn:li:share:9999999999999999999",
            posted_at="2026-01-02T10:00:00",
            blueprint_version="manual_v2",
            content="Another test post",
        )
        analytics.save_post_with_metrics(post2, filepath)

        # Verify both posts saved
        lines = filepath.read_text().strip().split("\n")
        assert len(lines) == 2


class TestLoadPosts:
    """Test load_posts method"""

    def test_load_posts_empty_file(self, analytics, tmp_path):
        """Should return empty list for non-existent file"""
        filepath = tmp_path / "nonexistent.jsonl"

        posts = analytics.load_posts(filepath)

        assert posts == []

    def test_load_posts_single_post(
        self, analytics, sample_post, sample_metrics, tmp_path
    ):
        """Should load single post from JSONL"""
        filepath = tmp_path / "posts.jsonl"
        sample_post.metrics = sample_metrics
        analytics.save_post_with_metrics(sample_post, filepath)

        posts = analytics.load_posts(filepath)

        assert len(posts) == 1
        assert posts[0].post_id == "urn:li:share:7412668096475369472"
        assert posts[0].content == sample_post.content
        assert posts[0].metrics is not None
        assert posts[0].metrics.impressions == 1500

    def test_load_posts_multiple_posts(
        self, analytics, sample_post, sample_metrics, tmp_path
    ):
        """Should load multiple posts from JSONL"""
        filepath = tmp_path / "posts.jsonl"

        # Save two posts
        sample_post.metrics = sample_metrics
        analytics.save_post_with_metrics(sample_post, filepath)

        post2 = Post(
            post_id="urn:li:share:9999999999999999999",
            posted_at="2026-01-02T10:00:00",
            blueprint_version="manual_v2",
            content="Another test post",
        )
        analytics.save_post_with_metrics(post2, filepath)

        posts = analytics.load_posts(filepath)

        assert len(posts) == 2
        assert posts[0].post_id == "urn:li:share:7412668096475369472"
        assert posts[1].post_id == "urn:li:share:9999999999999999999"

    def test_load_posts_without_metrics(self, analytics, sample_post, tmp_path):
        """Should load post without metrics (metrics=None)"""
        filepath = tmp_path / "posts.jsonl"
        analytics.save_post_with_metrics(sample_post, filepath)

        posts = analytics.load_posts(filepath)

        assert len(posts) == 1
        assert posts[0].metrics is None

    def test_load_posts_skips_empty_lines(self, analytics, tmp_path):
        """Should skip empty lines in JSONL"""
        filepath = tmp_path / "posts.jsonl"

        # Write JSONL with empty lines
        with open(filepath, "w") as f:
            f.write('{"post_id": "urn:li:share:123", "posted_at": "2026-01-01", "blueprint_version": "v1", "content": "test"}\n')
            f.write("\n")  # Empty line
            f.write('{"post_id": "urn:li:share:456", "posted_at": "2026-01-02", "blueprint_version": "v1", "content": "test2"}\n')

        posts = analytics.load_posts(filepath)

        assert len(posts) == 2


class TestUpdatePostsWithAnalytics:
    """Test update_posts_with_analytics method"""

    @patch("agents.linkedin.analytics.LinkedInAnalytics.get_post_analytics")
    def test_update_posts_fetches_analytics(
        self, mock_get_analytics, analytics, sample_post, sample_metrics, tmp_path
    ):
        """Should fetch analytics for recent posts without metrics"""
        filepath = tmp_path / "posts.jsonl"

        # Create post from yesterday (within 7 days)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        sample_post.posted_at = yesterday
        analytics.save_post_with_metrics(sample_post, filepath)

        # Mock analytics fetch
        mock_get_analytics.return_value = sample_metrics

        # Update analytics
        count = analytics.update_posts_with_analytics(filepath, days_back=7)

        # Verify analytics were fetched
        mock_get_analytics.assert_called_once_with(sample_post.post_id)
        assert count == 1

    @patch("agents.linkedin.analytics.LinkedInAnalytics.get_post_analytics")
    def test_update_posts_updates_file(
        self, mock_get_analytics, analytics, sample_post, sample_metrics, tmp_path
    ):
        """Should update JSONL file with fetched metrics"""
        filepath = tmp_path / "posts.jsonl"

        # Create recent post without metrics
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        sample_post.posted_at = yesterday
        analytics.save_post_with_metrics(sample_post, filepath)

        # Mock analytics fetch
        mock_get_analytics.return_value = sample_metrics

        # Update analytics
        analytics.update_posts_with_analytics(filepath, days_back=7)

        # Load posts and verify metrics added
        posts = analytics.load_posts(filepath)
        assert len(posts) == 1
        assert posts[0].metrics is not None
        assert posts[0].metrics.impressions == 1500

    @patch("agents.linkedin.analytics.LinkedInAnalytics.get_post_analytics")
    def test_update_posts_skips_old_posts(
        self, mock_get_analytics, analytics, sample_post, tmp_path
    ):
        """Should skip posts older than days_back"""
        filepath = tmp_path / "posts.jsonl"

        # Create post from 10 days ago (outside 7-day window)
        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        sample_post.posted_at = old_date
        analytics.save_post_with_metrics(sample_post, filepath)

        # Update analytics (7 days back)
        count = analytics.update_posts_with_analytics(filepath, days_back=7)

        # Should not fetch analytics for old post
        mock_get_analytics.assert_not_called()
        assert count == 0

    @patch("agents.linkedin.analytics.LinkedInAnalytics.get_post_analytics")
    def test_update_posts_skips_posts_with_existing_metrics(
        self, mock_get_analytics, analytics, sample_post, sample_metrics, tmp_path
    ):
        """Should skip posts that already have metrics"""
        filepath = tmp_path / "posts.jsonl"

        # Create recent post WITH metrics
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        sample_post.posted_at = yesterday
        sample_post.metrics = sample_metrics
        analytics.save_post_with_metrics(sample_post, filepath)

        # Update analytics
        count = analytics.update_posts_with_analytics(filepath, days_back=7)

        # Should not fetch analytics (already has metrics)
        mock_get_analytics.assert_not_called()
        assert count == 0

    @patch("agents.linkedin.analytics.LinkedInAnalytics.get_post_analytics")
    def test_update_posts_handles_fetch_failure(
        self, mock_get_analytics, analytics, sample_post, tmp_path
    ):
        """Should handle analytics fetch failure gracefully"""
        filepath = tmp_path / "posts.jsonl"

        # Create recent post without metrics
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        sample_post.posted_at = yesterday
        analytics.save_post_with_metrics(sample_post, filepath)

        # Mock analytics fetch failure
        mock_get_analytics.return_value = None

        # Update analytics
        count = analytics.update_posts_with_analytics(filepath, days_back=7)

        # Should handle failure and return 0
        assert count == 0

        # Post should still exist in file (without metrics)
        posts = analytics.load_posts(filepath)
        assert len(posts) == 1
        assert posts[0].metrics is None

    @patch("agents.linkedin.analytics.LinkedInAnalytics.get_post_analytics")
    def test_update_posts_mixed_scenario(
        self, mock_get_analytics, analytics, sample_metrics, tmp_path
    ):
        """Should handle mix of recent/old posts with/without metrics"""
        filepath = tmp_path / "posts.jsonl"

        # Post 1: Recent, no metrics (should fetch)
        post1 = Post(
            post_id="urn:li:share:111",
            posted_at=(datetime.now() - timedelta(days=1)).isoformat(),
            blueprint_version="v1",
            content="Recent post",
        )
        analytics.save_post_with_metrics(post1, filepath)

        # Post 2: Old, no metrics (should skip)
        post2 = Post(
            post_id="urn:li:share:222",
            posted_at=(datetime.now() - timedelta(days=10)).isoformat(),
            blueprint_version="v1",
            content="Old post",
        )
        analytics.save_post_with_metrics(post2, filepath)

        # Post 3: Recent, has metrics (should skip)
        post3 = Post(
            post_id="urn:li:share:333",
            posted_at=(datetime.now() - timedelta(days=2)).isoformat(),
            blueprint_version="v1",
            content="Recent post with metrics",
            metrics=sample_metrics,
        )
        analytics.save_post_with_metrics(post3, filepath)

        # Mock analytics fetch
        mock_get_analytics.return_value = sample_metrics

        # Update analytics
        count = analytics.update_posts_with_analytics(filepath, days_back=7)

        # Should only fetch for post1
        assert mock_get_analytics.call_count == 1
        assert count == 1

        # Verify all posts preserved
        posts = analytics.load_posts(filepath)
        assert len(posts) == 3


class TestPostMetricsDataclass:
    """Test PostMetrics dataclass"""

    def test_post_metrics_creation(self):
        """Should create PostMetrics with all fields"""
        metrics = PostMetrics(
            post_id="urn:li:share:123",
            impressions=1000,
            likes=50,
            comments=10,
            shares=5,
            clicks=100,
            engagement_rate=0.05,
            fetched_at="2026-01-17T12:00:00",
        )

        assert metrics.post_id == "urn:li:share:123"
        assert metrics.impressions == 1000
        assert metrics.engagement_rate == 0.05


class TestPostDataclass:
    """Test Post dataclass"""

    def test_post_creation_without_metrics(self):
        """Should create Post without metrics"""
        post = Post(
            post_id="urn:li:share:123",
            posted_at="2026-01-01",
            blueprint_version="v1",
            content="Test content",
        )

        assert post.post_id == "urn:li:share:123"
        assert post.metrics is None

    def test_post_creation_with_metrics(self, sample_metrics):
        """Should create Post with metrics"""
        post = Post(
            post_id="urn:li:share:123",
            posted_at="2026-01-01",
            blueprint_version="v1",
            content="Test content",
            metrics=sample_metrics,
        )

        assert post.metrics is not None
        assert post.metrics.impressions == 1500
