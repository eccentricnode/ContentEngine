#!/usr/bin/env python3
"""
Import all REAL LinkedIn posts that Austin created with Jeff into the database as demo posts.

This script extracts actual posts from:
1. The existing Content Engine database
2. Session history files from Claude Code sessions
3. LinkedIn API dry-run outputs

All posts are imported as demo posts (is_demo=True, user_id=None) for demonstration purposes.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.database import get_db, Post, PostStatus, Platform, init_db


# All REAL posts found in session data
REAL_POSTS = [
    {
        "content": """Happy New Year! 🎉

I'm excited about what's ahead. Despite all of last year's challenges, I feel like there's still so much opportunity.

2025 was a year of building and learning:

→ Dove deep into AI systems and how they help develop applications
→ Got hands-on building everything from the ground up
→ Started some really cool projects like Sales RPG and other tools
→ Learned a ton about sales and generated over $110k in revenue — with no prior experience

All of these experiences have been huge for my growth. I can't wait to see what else is possible in 2026!

What are you most excited about this year?""",
        "platform": "LINKEDIN",
        "status": "POSTED",
        "external_id": "urn:li:activity:7412668096982736897",
        "posted_at": "2026-01-02T01:40:00",  # Approximate timestamp from session data
        "notes": "First post created with Content Engine - New Year reflection post"
    },
]


def import_posts():
    """Import all real posts into the database as demo posts."""
    # Initialize database
    init_db()

    db = get_db()

    print(f"Importing {len(REAL_POSTS)} real posts as demo posts...\n")

    imported_count = 0
    skipped_count = 0

    for post_data in REAL_POSTS:
        # Check if post already exists (by external_id or exact content match)
        external_id = post_data.get("external_id")
        content = post_data["content"]

        existing_post = None
        if external_id:
            existing_post = db.query(Post).filter(
                Post.external_id == external_id
            ).first()

        if not existing_post:
            existing_post = db.query(Post).filter(
                Post.content == content,
                Post.is_demo
            ).first()

        if existing_post:
            print(f"⏭️  Skipping (already exists): {content[:80]}...")
            skipped_count += 1
            continue

        # Create new demo post
        platform = Platform[post_data.get("platform", "LINKEDIN").upper()]
        status = PostStatus[post_data.get("status", "POSTED").upper()]

        post = Post(
            content=content,
            platform=platform,
            status=status,
            external_id=external_id,
            is_demo=True,  # Mark as demo post
            user_id=None,   # No user association
            created_at=datetime.fromisoformat(post_data.get("posted_at", datetime.utcnow().isoformat())),
            posted_at=datetime.fromisoformat(post_data["posted_at"]) if post_data.get("posted_at") else None,
        )

        db.add(post)
        db.commit()

        print(f"✅ Imported: {content[:80]}...")
        if post_data.get("notes"):
            print(f"   Notes: {post_data['notes']}")
        print()

        imported_count += 1

    db.close()

    print("="*80)
    print("✅ Import complete!")
    print(f"   Imported: {imported_count} posts")
    print(f"   Skipped: {skipped_count} posts (already exist)")
    print(f"   Total: {len(REAL_POSTS)} posts")
    print("="*80)


if __name__ == "__main__":
    import_posts()
