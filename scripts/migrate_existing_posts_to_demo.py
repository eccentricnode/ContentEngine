#!/usr/bin/env python3
"""Migration: Convert existing posts to demo posts.

This migration takes all existing posts in the database (created during testing)
and marks them as demo posts that will be visible to unauthenticated users.
"""

from lib.database import get_db, Post

def migrate():
    """Convert all existing posts to demo posts."""
    db = get_db()

    # Find all posts that don't have a user_id (existing posts from testing)
    existing_posts = db.query(Post).filter(Post.user_id is None).all()

    print(f"Found {len(existing_posts)} existing posts to migrate")

    if len(existing_posts) == 0:
        print("No posts to migrate. Database is empty.")
        db.close()
        return

    # Mark them all as demo posts
    for post in existing_posts:
        post.is_demo = True
        print(f"  - Migrated Post #{post.id}: {post.content[:50]}...")

    db.commit()
    print(f"\n✅ Successfully migrated {len(existing_posts)} posts to demo mode")
    print("These posts will now be visible to all users in demo mode.")

    db.close()

if __name__ == "__main__":
    migrate()
