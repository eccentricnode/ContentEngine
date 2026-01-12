#!/usr/bin/env python3
"""Create demo posts for Content Engine."""

from datetime import datetime, timedelta

from lib.database import get_db, Post, Platform, PostStatus


def create_demo_posts():
    """Create sample demo posts."""
    db = get_db()

    demo_posts = [
        {
            "content": """Just shipped Content Engine in 8 hours using Claude Code.

This isn't about building faster—it's about building smarter.

AI handled the OAuth flow, database design, and HTMX integration. I focused on architecture and user experience.

The result? A production-ready LinkedIn automation system that scales with authentication.

Force multiplier: not doing everything yourself, but architecting systems that extend themselves.""",
            "status": PostStatus.DRAFT,
            "platform": Platform.LINKEDIN,
        },
        {
            "content": """The best engineering interview isn't a whiteboard session.

It's showing up with a working system.

Content Engine demonstrates:
• OAuth 2.0 implementation (LinkedIn)
• Dual-mode architecture (demo vs. authenticated)
• AI-powered content generation (Ollama)
• Modern web stack (FastAPI + HTMX 2.0)

Built in 8 hours. That's the power of AI-first development.

Interviewing for Principal Engineer roles. This is my portfolio.""",
            "status": PostStatus.SCHEDULED,
            "platform": Platform.LINKEDIN,
            "scheduled_at": datetime.utcnow() + timedelta(days=1),
        },
        {
            "content": """Most AI tools are wrappers around ChatGPT.

Content Engine is different—it's a system that builds itself.

The AI chat interface suggests content ideas.
You can draft them with one click.
The system handles posting to LinkedIn.

All running locally with Ollama. No API costs. Full control.

This is what AI-first development looks like.""",
            "status": PostStatus.DRAFT,
            "platform": Platform.LINKEDIN,
        },
        {
            "content": """Three years ago, I couldn't code.

Today, I'm interviewing for Principal Engineer roles.

The secret? Learning to build with AI as a force multiplier.

Content Engine took 8 hours to ship. Would have taken weeks without Claude Code.

The skill isn't memorizing syntax—it's architecting systems and validating output.

AI changes the game. The question is: are you playing?""",
            "status": PostStatus.POSTED,
            "platform": Platform.LINKEDIN,
            "posted_at": datetime.utcnow() - timedelta(days=2),
            "external_id": "urn:li:share:123456789",
        },
        {
            "content": """Why did I build Content Engine?

Because I'm tired of copy-pasting content across platforms.

The system:
• Generates ideas with local AI (Ollama)
• Stores drafts in a database
• Posts to LinkedIn via OAuth
• Tracks everything in one dashboard

No third-party services. No monthly fees. Just pure engineering.

Check the GitHub repo: github.com/eccentricnode/ContentEngine""",
            "status": PostStatus.DRAFT,
            "platform": Platform.LINKEDIN,
        },
    ]

    for post_data in demo_posts:
        post = Post(
            content=post_data["content"],
            platform=post_data["platform"],
            status=post_data["status"],
            user_id=None,  # Demo posts have no user
            is_demo=True,  # Mark as demo
        )

        # Add optional fields
        if "scheduled_at" in post_data:
            post.scheduled_at = post_data["scheduled_at"]
        if "posted_at" in post_data:
            post.posted_at = post_data["posted_at"]
        if "external_id" in post_data:
            post.external_id = post_data["external_id"]

        db.add(post)
        print(f"✅ Created demo post: {post.content[:50]}...")

    db.commit()
    print(f"\n🎉 Created {len(demo_posts)} demo posts successfully!")

    db.close()


if __name__ == "__main__":
    create_demo_posts()
