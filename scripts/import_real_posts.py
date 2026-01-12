#!/usr/bin/env python3
"""Import REAL LinkedIn posts from session data into ContentEngine database."""

from datetime import datetime
from lib.database import get_db, Post, Platform, PostStatus


def import_real_posts():
    """Import actual LinkedIn posts created during the LinkedIn agent build."""
    db = get_db()

    # The REAL posts from your LinkedIn posting agent sessions
    real_posts = [
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
            "status": PostStatus.POSTED,
            "platform": Platform.LINKEDIN,
            "posted_at": datetime(2026, 1, 2, 1, 35),  # When you actually posted it
            "external_id": "urn:li:activity:7412668096982736897",
        },
        # Add more real posts as they're discovered
    ]

    for post_data in real_posts:
        post = Post(
            content=post_data["content"],
            platform=post_data["platform"],
            status=post_data["status"],
            user_id=None,  # Demo posts have no user (Austin's content)
            is_demo=True,  # Mark as demo
        )

        # Add optional fields
        if "posted_at" in post_data:
            post.posted_at = post_data["posted_at"]
        if "external_id" in post_data:
            post.external_id = post_data["external_id"]

        db.add(post)
        print(f"✅ Imported REAL LinkedIn post: {post.content[:60]}...")

    db.commit()
    print(f"\n🎉 Imported {len(real_posts)} REAL LinkedIn posts!")
    print("These are the actual posts created during the LinkedIn agent build.")

    db.close()


if __name__ == "__main__":
    import_real_posts()
