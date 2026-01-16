#!/usr/bin/env python3
"""Database schema migration: Add user_id and is_demo columns to posts.

This script:
1. Backs up all existing posts from the old schema
2. Deletes the old database
3. Creates new database with updated schema (User, Session, ChatMessage, updated Post)
4. Restores all posts as demo posts (is_demo=True, user_id=NULL)
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

from lib.database import init_db, get_db, Post, Platform, PostStatus

# Paths
DB_PATH = Path(__file__).parent.parent / "content.db"
BACKUP_PATH = Path(__file__).parent.parent / "posts_backup.json"


def backup_existing_posts():
    """Backup existing posts from old schema."""
    print("📦 Backing up existing posts...")

    if not DB_PATH.exists():
        print("No existing database found. Starting fresh.")
        return []

    # Connect directly with sqlite3 to read old schema
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM posts")
        posts = cursor.fetchall()

        # Convert to list of dicts
        posts_data = []
        for post in posts:
            posts_data.append({
                "id": post["id"],
                "content": post["content"],
                "platform": post["platform"],
                "status": post["status"],
                "created_at": post["created_at"],
                "updated_at": post["updated_at"],
                "scheduled_at": post["scheduled_at"],
                "posted_at": post["posted_at"],
                "external_id": post["external_id"],
                "error_message": post["error_message"],
            })

        print(f"  Found {len(posts_data)} posts to backup")

        # Save to JSON
        with open(BACKUP_PATH, "w") as f:
            json.dump(posts_data, f, indent=2, default=str)

        print(f"  ✅ Saved backup to {BACKUP_PATH}")

        conn.close()
        return posts_data

    except sqlite3.OperationalError as e:
        print(f"  Error reading database: {e}")
        conn.close()
        return []


def recreate_database():
    """Delete old database and create new one with updated schema."""
    print("\n🔧 Recreating database with new schema...")

    # Delete old database
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("  Deleted old database")

    # Create new database with updated schema
    init_db()
    print("  ✅ Created new database with updated schema (User, Session, ChatMessage, Post)")


def restore_posts_as_demo(posts_data):
    """Restore posts as demo posts."""
    if not posts_data:
        print("\n📭 No posts to restore")
        return

    print(f"\n📥 Restoring {len(posts_data)} posts as demo posts...")

    db = get_db()

    for post_data in posts_data:
        # Handle case sensitivity for enums (old DB might have uppercase)
        platform_value = post_data["platform"].lower()
        status_value = post_data["status"].lower()

        post = Post(
            content=post_data["content"],
            platform=Platform(platform_value),
            status=PostStatus(status_value),
            user_id=None,  # Demo posts have no user
            is_demo=True,  # Mark as demo
            external_id=post_data.get("external_id"),
            error_message=post_data.get("error_message"),
        )

        # Preserve timestamps if they exist
        if post_data.get("created_at"):
            post.created_at = datetime.fromisoformat(post_data["created_at"].replace("Z", "+00:00"))
        if post_data.get("updated_at"):
            post.updated_at = datetime.fromisoformat(post_data["updated_at"].replace("Z", "+00:00"))
        if post_data.get("scheduled_at"):
            post.scheduled_at = datetime.fromisoformat(post_data["scheduled_at"].replace("Z", "+00:00"))
        if post_data.get("posted_at"):
            post.posted_at = datetime.fromisoformat(post_data["posted_at"].replace("Z", "+00:00"))

        db.add(post)
        print(f"  - Restored Post: {post.content[:50]}...")

    db.commit()
    print(f"  ✅ Restored {len(posts_data)} posts as demo posts")

    db.close()


def main():
    """Run the migration."""
    import warnings
    warnings.warn(
        "This script is deprecated. Use Alembic migrations instead:\n"
        "  uv run alembic upgrade head\n"
        "See DATABASE.md for migration guide.",
        DeprecationWarning
    )

    print("\n" + "="*60)
    print("⚠️  WARNING: This migration script is DEPRECATED")
    print("="*60)
    print("Use Alembic instead: uv run alembic upgrade head")
    print("See DATABASE.md and MIGRATION_GUIDE.md for details")
    print("="*60 + "\n")

    proceed = input("Continue anyway? [y/N]: ")
    if proceed.lower() != 'y':
        print("Aborted.")
        return

    print("\n" + "="*60)
    print("Database Schema Migration")
    print("Adding user_id and is_demo columns to posts table")
    print("="*60 + "\n")

    # Step 1: Backup existing posts
    posts_data = backup_existing_posts()

    # Step 2: Recreate database with new schema
    recreate_database()

    # Step 3: Restore posts as demo posts
    restore_posts_as_demo(posts_data)

    print("\n" + "="*60)
    print("✅ Migration complete!")
    print("="*60)
    print(f"\nBackup saved to: {BACKUP_PATH}")
    print(f"Database recreated at: {DB_PATH}")
    print(f"All {len(posts_data)} posts restored as demo posts")
    print("\nDemo mode users will now see these posts.")
    print("Authenticated users will see only their own posts.")


if __name__ == "__main__":
    main()
