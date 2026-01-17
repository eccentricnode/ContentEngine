"""LinkedIn Analytics Integration

Fetches post analytics (impressions, engagement, clicks) from LinkedIn API.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass, asdict
import requests
from pathlib import Path


@dataclass
class PostMetrics:
    """Metrics for a single LinkedIn post"""
    post_id: str
    impressions: int
    likes: int
    comments: int
    shares: int
    clicks: int
    engagement_rate: float
    fetched_at: str


@dataclass
class Post:
    """LinkedIn post with content and metrics"""
    post_id: str
    posted_at: str
    blueprint_version: str
    content: str
    metrics: Optional[PostMetrics] = None


class LinkedInAnalytics:
    """Fetch and store LinkedIn post analytics"""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def get_post_analytics(self, share_urn: str) -> Optional[PostMetrics]:
        """
        Fetch analytics for a specific post.

        Args:
            share_urn: LinkedIn share URN (e.g., "urn:li:share:7412668096475369472")

        Returns:
            PostMetrics object or None if fetch fails
        """
        # Extract share ID from URN
        share_id = share_urn.split(":")[-1]

        # LinkedIn Analytics API endpoint
        # https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/organizations/share-statistics
        url = f"{self.base_url}/organizationalEntityShareStatistics"
        params = {
            "q": "share",
            "shares[0]": f"urn:li:share:{share_id}",
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Parse response
            if "elements" in data and len(data["elements"]) > 0:
                stats = data["elements"][0]

                # Extract metrics
                total_impressions = stats.get("totalShareStatistics", {}).get(
                    "impressionCount", 0
                )
                total_engagement = stats.get("totalShareStatistics", {}).get(
                    "engagement", 0
                )
                likes = stats.get("totalShareStatistics", {}).get("likeCount", 0)
                comments = stats.get("totalShareStatistics", {}).get("commentCount", 0)
                shares = stats.get("totalShareStatistics", {}).get("shareCount", 0)
                clicks = stats.get("totalShareStatistics", {}).get("clickCount", 0)

                # Calculate engagement rate
                engagement_rate = (
                    total_engagement / total_impressions if total_impressions > 0 else 0.0
                )

                return PostMetrics(
                    post_id=share_urn,
                    impressions=total_impressions,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    clicks=clicks,
                    engagement_rate=engagement_rate,
                    fetched_at=datetime.now().isoformat(),
                )

            return None

        except requests.exceptions.RequestException as e:
            print(f"Error fetching analytics for {share_urn}: {e}")
            return None

    def save_post_with_metrics(self, post: Post, filepath: Path):
        """
        Save post data with metrics to JSONL file.

        Args:
            post: Post object with metrics
            filepath: Path to posts.jsonl file
        """
        # Append to JSONL file
        with open(filepath, "a") as f:
            post_dict = asdict(post)
            # Convert metrics to dict if present
            if post.metrics:
                post_dict["metrics"] = asdict(post.metrics)
            f.write(json.dumps(post_dict) + "\n")

    def load_posts(self, filepath: Path) -> List[Post]:
        """
        Load posts from JSONL file.

        Args:
            filepath: Path to posts.jsonl file

        Returns:
            List of Post objects
        """
        posts = []

        if not filepath.exists():
            return posts

        with open(filepath, "r") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    # Reconstruct PostMetrics if present
                    metrics_data = data.get("metrics")
                    metrics = (
                        PostMetrics(**metrics_data) if metrics_data else None
                    )
                    post = Post(
                        post_id=data["post_id"],
                        posted_at=data["posted_at"],
                        blueprint_version=data["blueprint_version"],
                        content=data["content"],
                        metrics=metrics,
                    )
                    posts.append(post)

        return posts

    def update_posts_with_analytics(
        self, filepath: Path, days_back: int = 7
    ) -> int:
        """
        Update posts.jsonl with fresh analytics for recent posts.

        Args:
            filepath: Path to posts.jsonl file
            days_back: Fetch analytics for posts from last N days

        Returns:
            Number of posts updated
        """
        posts = self.load_posts(filepath)
        updated_count = 0

        # Filter posts from last N days that don't have metrics yet
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # Create temporary file for updated posts
        temp_filepath = filepath.with_suffix(".tmp")

        with open(temp_filepath, "w") as f:
            for post in posts:
                posted_date = datetime.fromisoformat(post.posted_at)

                # Fetch analytics if post is recent and missing metrics
                if posted_date >= cutoff_date and not post.metrics:
                    print(f"Fetching analytics for {post.post_id}...")
                    metrics = self.get_post_analytics(post.post_id)

                    if metrics:
                        post.metrics = metrics
                        updated_count += 1
                        print(
                            f"  ✓ Engagement: {metrics.engagement_rate:.2%} "
                            f"({metrics.likes} likes, {metrics.comments} comments)"
                        )

                # Write post (with or without updated metrics)
                post_dict = asdict(post)
                if post.metrics:
                    post_dict["metrics"] = asdict(post.metrics)
                f.write(json.dumps(post_dict) + "\n")

        # Replace original file with updated file
        temp_filepath.replace(filepath)

        return updated_count


def main():
    """CLI for testing analytics integration"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analytics.py <command> [args]")
        print("Commands:")
        print("  fetch <share_urn>       - Fetch analytics for a specific post")
        print("  update                  - Update analytics for recent posts")
        sys.exit(1)

    # Load access token from environment
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        print("Error: LINKEDIN_ACCESS_TOKEN environment variable not set")
        sys.exit(1)

    analytics = LinkedInAnalytics(access_token)
    command = sys.argv[1]

    if command == "fetch" and len(sys.argv) == 3:
        share_urn = sys.argv[2]
        metrics = analytics.get_post_analytics(share_urn)

        if metrics:
            print(f"\n✓ Analytics for {share_urn}:")
            print(f"  Impressions: {metrics.impressions:,}")
            print(f"  Likes: {metrics.likes}")
            print(f"  Comments: {metrics.comments}")
            print(f"  Shares: {metrics.shares}")
            print(f"  Clicks: {metrics.clicks}")
            print(f"  Engagement Rate: {metrics.engagement_rate:.2%}")
        else:
            print(f"✗ Failed to fetch analytics for {share_urn}")

    elif command == "update":
        posts_file = Path("data/posts.jsonl")
        posts_file.parent.mkdir(exist_ok=True)

        count = analytics.update_posts_with_analytics(posts_file, days_back=7)
        print(f"\n✓ Updated analytics for {count} posts")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
