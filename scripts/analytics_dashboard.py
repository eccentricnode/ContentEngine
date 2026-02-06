#!/usr/bin/env python3
"""LinkedIn Analytics Dashboard

Displays analytics summary for posts in data/posts.jsonl.

Usage:
    python scripts/analytics_dashboard.py
    python scripts/analytics_dashboard.py --export-csv results.csv
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.linkedin.analytics import Post, PostMetrics


def load_posts(posts_file: Path) -> List[Post]:
    """Load posts from JSONL file."""
    posts: List[Post] = []

    if not posts_file.exists():
        return posts

    with open(posts_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            data = json.loads(line)

            # Parse metrics if present
            metrics = None
            if data.get("metrics"):
                metrics = PostMetrics(**data["metrics"])

            post = Post(
                post_id=data["post_id"],
                posted_at=data["posted_at"],
                blueprint_version=data["blueprint_version"],
                content=data["content"],
                metrics=metrics,
            )
            posts.append(post)

    return posts


def truncate_post_id(post_id: str, max_length: int = 30) -> str:
    """Truncate post ID for display."""
    if len(post_id) <= max_length:
        return post_id
    return post_id[:max_length - 3] + "..."


def format_engagement_rate(rate: float) -> str:
    """Format engagement rate as percentage."""
    return f"{rate * 100:.2f}%"


def display_dashboard(posts: List[Post]) -> None:
    """Display analytics dashboard in terminal."""
    print("\n" + "=" * 100)
    print("LinkedIn Analytics Dashboard".center(100))
    print("=" * 100 + "\n")

    if not posts:
        print("No posts found in data/posts.jsonl")
        return

    # Filter posts with metrics
    posts_with_metrics = [p for p in posts if p.metrics]

    if not posts_with_metrics:
        print(f"Found {len(posts)} posts, but none have analytics data yet.")
        print("\nRun: uv run content-engine collect-analytics")
        return

    # Display header
    print(f"{'Post ID':<32} {'Date':<12} {'Engagement':<12} {'Likes':<8} {'Comments':<10}")
    print("-" * 100)

    # Display each post
    total_engagement = 0.0
    post_count = 0

    best_post: Optional[Post] = None
    worst_post: Optional[Post] = None

    for post in posts_with_metrics:
        if not post.metrics:
            continue

        post_id_short = truncate_post_id(post.post_id, 30)
        date_short = post.posted_at[:10]  # YYYY-MM-DD
        engagement = format_engagement_rate(post.metrics.engagement_rate)

        print(f"{post_id_short:<32} {date_short:<12} {engagement:<12} {post.metrics.likes:<8} {post.metrics.comments:<10}")

        # Track stats
        total_engagement += post.metrics.engagement_rate
        post_count += 1

        # Track best/worst
        if best_post is None or (post.metrics.engagement_rate > best_post.metrics.engagement_rate):  # type: ignore
            best_post = post

        if worst_post is None or (post.metrics.engagement_rate < worst_post.metrics.engagement_rate):  # type: ignore
            worst_post = post

    # Display summary
    print("-" * 100)
    print("\nSummary:")
    print(f"  Total posts: {len(posts)}")
    print(f"  Posts with analytics: {post_count}")

    if post_count > 0:
        avg_engagement = total_engagement / post_count
        print(f"  Average engagement rate: {format_engagement_rate(avg_engagement)}")

        if best_post and best_post.metrics:
            print("\n  Best performing post:")
            print(f"    ID: {truncate_post_id(best_post.post_id, 50)}")
            print(f"    Engagement: {format_engagement_rate(best_post.metrics.engagement_rate)}")
            print(f"    Likes: {best_post.metrics.likes}, Comments: {best_post.metrics.comments}")

        if worst_post and worst_post.metrics:
            print("\n  Worst performing post:")
            print(f"    ID: {truncate_post_id(worst_post.post_id, 50)}")
            print(f"    Engagement: {format_engagement_rate(worst_post.metrics.engagement_rate)}")
            print(f"    Likes: {worst_post.metrics.likes}, Comments: {worst_post.metrics.comments}")

    print("\n" + "=" * 100 + "\n")


def export_to_csv(posts: List[Post], output_file: Path) -> None:
    """Export analytics to CSV file."""
    posts_with_metrics = [p for p in posts if p.metrics]

    if not posts_with_metrics:
        print("No posts with metrics to export")
        return

    with open(output_file, "w", newline="") as f:
        fieldnames = [
            "post_id",
            "posted_at",
            "blueprint_version",
            "impressions",
            "likes",
            "comments",
            "shares",
            "clicks",
            "engagement_rate",
            "fetched_at",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for post in posts_with_metrics:
            if not post.metrics:
                continue

            row = {
                "post_id": post.post_id,
                "posted_at": post.posted_at,
                "blueprint_version": post.blueprint_version,
                "impressions": post.metrics.impressions,
                "likes": post.metrics.likes,
                "comments": post.metrics.comments,
                "shares": post.metrics.shares,
                "clicks": post.metrics.clicks,
                "engagement_rate": post.metrics.engagement_rate,
                "fetched_at": post.metrics.fetched_at,
            }
            writer.writerow(row)

    print(f"\nExported {len(posts_with_metrics)} posts to {output_file}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Display LinkedIn analytics dashboard"
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        help="Export results to CSV file",
        metavar="FILE",
    )

    args = parser.parse_args()

    # Load posts
    posts_file = Path("data/posts.jsonl")
    posts = load_posts(posts_file)

    # Display dashboard
    display_dashboard(posts)

    # Export if requested
    if args.export_csv:
        output_file = Path(args.export_csv)
        export_to_csv(posts, output_file)


if __name__ == "__main__":
    main()
