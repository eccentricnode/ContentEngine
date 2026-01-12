"""CLI interface for Content Engine."""

import sys
from datetime import datetime
from typing import Optional

import click
from sqlalchemy import select

from lib.context_capture import read_project_notes, read_session_history
from lib.context_synthesizer import save_context, synthesize_daily_context
from lib.database import init_db, get_db, Post, PostStatus, Platform, OAuthToken
from lib.errors import AIError
from lib.logger import setup_logger
from agents.linkedin.post import post_to_linkedin


logger = setup_logger(__name__)


@click.group()
def cli() -> None:
    """Content Engine - AI-powered content posting system."""
    init_db()


@cli.command()
@click.argument("content")
@click.option("--platform", type=click.Choice(["linkedin", "twitter", "blog"]), default="linkedin")
def draft(content: str, platform: str) -> None:
    """Create a new draft post."""
    db = get_db()

    post = Post(
        content=content,
        platform=Platform(platform),
        status=PostStatus.DRAFT,
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    click.echo(f"✅ Draft created (ID: {post.id})")
    click.echo(f"Platform: {post.platform.value}")
    click.echo(f"Content: {post.content[:100]}..." if len(post.content) > 100 else f"Content: {post.content}")

    db.close()


@cli.command()
@click.option("--status", type=click.Choice(["draft", "approved", "scheduled", "posted", "failed", "rejected"]))
@click.option("--platform", type=click.Choice(["linkedin", "twitter", "blog"]))
@click.option("--limit", type=int, default=10)
def list(status: Optional[str], platform: Optional[str], limit: int) -> None:
    """List posts."""
    db = get_db()

    query = select(Post).order_by(Post.created_at.desc()).limit(limit)

    if status:
        query = query.where(Post.status == PostStatus(status))
    if platform:
        query = query.where(Post.platform == Platform(platform))

    posts = db.execute(query).scalars().all()

    if not posts:
        click.echo("No posts found.")
        db.close()
        return

    click.echo(f"\n{'ID':<5} {'Platform':<10} {'Status':<12} {'Created':<20} {'Content':<50}")
    click.echo("=" * 100)

    for post in posts:
        content_preview = post.content[:47] + "..." if len(post.content) > 50 else post.content
        created = post.created_at.strftime("%Y-%m-%d %H:%M")
        click.echo(f"{post.id:<5} {post.platform.value:<10} {post.status.value:<12} {created:<20} {content_preview:<50}")

    db.close()


@cli.command()
@click.argument("post_id", type=int)
def show(post_id: int) -> None:
    """Show full post details."""
    db = get_db()

    post = db.get(Post, post_id)

    if not post:
        click.echo(f"❌ Post {post_id} not found")
        db.close()
        sys.exit(1)

    click.echo(f"\n{'='*60}")
    click.echo(f"Post ID: {post.id}")
    click.echo(f"Platform: {post.platform.value}")
    click.echo(f"Status: {post.status.value}")
    click.echo(f"Created: {post.created_at}")
    click.echo(f"Updated: {post.updated_at}")

    if post.scheduled_at:
        click.echo(f"Scheduled: {post.scheduled_at}")
    if post.posted_at:
        click.echo(f"Posted: {post.posted_at}")
    if post.external_id:
        click.echo(f"External ID: {post.external_id}")
    if post.error_message:
        click.echo(f"Error: {post.error_message}")

    click.echo(f"\nContent:\n{post.content}")
    click.echo(f"{'='*60}\n")

    db.close()


@cli.command()
@click.argument("post_id", type=int)
@click.option("--dry-run", is_flag=True, help="Test without actually posting")
def approve(post_id: int, dry_run: bool) -> None:
    """Approve a draft and post immediately."""
    db = get_db()

    post = db.get(Post, post_id)

    if not post:
        click.echo(f"❌ Post {post_id} not found")
        db.close()
        sys.exit(1)

    if post.status != PostStatus.DRAFT:
        click.echo(f"❌ Post must be in DRAFT status (currently: {post.status.value})")
        db.close()
        sys.exit(1)

    # Get OAuth token
    token_query = select(OAuthToken).where(OAuthToken.platform == post.platform)
    oauth_token = db.execute(token_query).scalar_one_or_none()

    if not oauth_token:
        click.echo(f"❌ No OAuth token found for {post.platform.value}")
        click.echo(f"Run OAuth flow first: uv run python -m agents.linkedin.oauth_server")
        db.close()
        sys.exit(1)

    click.echo(f"📤 Posting to {post.platform.value}...")

    try:
        if post.platform == Platform.LINKEDIN:
            external_id = post_to_linkedin(
                content=post.content,
                access_token=oauth_token.access_token,
                user_sub=oauth_token.user_sub or "",
                dry_run=dry_run,
            )

            post.status = PostStatus.POSTED
            post.posted_at = datetime.utcnow()
            post.external_id = external_id

        else:
            click.echo(f"❌ Platform {post.platform.value} not yet supported")
            db.close()
            sys.exit(1)

        db.commit()
        click.echo(f"\n✅ Post {post_id} published successfully!")

        if not dry_run and post.platform == Platform.LINKEDIN:
            click.echo(f"View at: https://www.linkedin.com/feed/")

    except Exception as e:
        post.status = PostStatus.FAILED
        post.error_message = str(e)
        db.commit()
        click.echo(f"❌ Failed to post: {e}")
        db.close()
        sys.exit(1)

    db.close()


@cli.command()
@click.argument("post_id", type=int)
@click.argument("scheduled_time")
def schedule(post_id: int, scheduled_time: str) -> None:
    """
    Schedule a draft for later posting.

    TIME format: YYYY-MM-DD HH:MM (e.g., 2024-01-15 09:00)
    """
    db = get_db()

    post = db.get(Post, post_id)

    if not post:
        click.echo(f"❌ Post {post_id} not found")
        db.close()
        sys.exit(1)

    if post.status != PostStatus.DRAFT:
        click.echo(f"❌ Post must be in DRAFT status (currently: {post.status.value})")
        db.close()
        sys.exit(1)

    try:
        scheduled_dt = datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M")
    except ValueError:
        click.echo(f"❌ Invalid time format. Use: YYYY-MM-DD HH:MM (e.g., 2024-01-15 09:00)")
        db.close()
        sys.exit(1)

    if scheduled_dt < datetime.utcnow():
        click.echo(f"❌ Scheduled time must be in the future")
        db.close()
        sys.exit(1)

    post.status = PostStatus.SCHEDULED
    post.scheduled_at = scheduled_dt
    db.commit()

    click.echo(f"✅ Post {post_id} scheduled for {scheduled_dt}")
    click.echo(f"Run worker to publish: uv run python -m worker")

    db.close()


@cli.command()
@click.argument("post_id", type=int)
def reject(post_id: int) -> None:
    """Reject a draft post."""
    db = get_db()

    post = db.get(Post, post_id)

    if not post:
        click.echo(f"❌ Post {post_id} not found")
        db.close()
        sys.exit(1)

    post.status = PostStatus.REJECTED
    db.commit()

    click.echo(f"✅ Post {post_id} rejected")
    db.close()


@cli.command("capture-context")
@click.option("--date", help="Date to capture context for (YYYY-MM-DD), defaults to today")
@click.option("--sessions-dir", help="Custom session history directory")
@click.option("--projects-dir", help="Custom projects directory")
@click.option("--output-dir", default="context", help="Output directory for context files")
def capture_context(
    date: Optional[str],
    sessions_dir: Optional[str],
    projects_dir: Optional[str],
    output_dir: str,
) -> None:
    """
    Capture daily context from sessions and projects.

    Reads PAI session history and project notes, synthesizes with local LLM,
    and saves structured context to JSON file.
    """
    # Determine date
    if date:
        try:
            context_date = datetime.strptime(date, "%Y-%m-%d")
            date_str = date
        except ValueError:
            click.echo("❌ Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        context_date = datetime.now()
        date_str = context_date.strftime("%Y-%m-%d")

    click.echo(f"📅 Capturing context for {date_str}...")

    try:
        # Read session history
        click.echo("📖 Reading session history...")
        sessions = read_session_history(sessions_dir)
        click.echo(f"   Found {len(sessions)} sessions")

        # Read project notes
        click.echo("📁 Reading project notes...")
        try:
            projects = read_project_notes(projects_dir)
            click.echo(f"   Found {len(projects)} projects")
        except FileNotFoundError:
            click.echo("   ⚠️  Projects directory not found, continuing without projects")
            projects = []

        # Synthesize with LLM
        click.echo("🤖 Synthesizing with Ollama...")
        daily_context = synthesize_daily_context(
            sessions=sessions, projects=projects, date=date_str
        )

        # Save to file
        click.echo("💾 Saving context...")
        file_path = save_context(daily_context, output_dir)

        # Print summary
        click.echo("\n✅ Context captured successfully!")
        click.echo(f"   Sessions: {len(sessions)}")
        click.echo(f"   Projects: {len(projects)}")
        click.echo(f"   Themes: {len(daily_context.themes)}")
        click.echo(f"   Decisions: {len(daily_context.decisions)}")
        click.echo(f"   Progress: {len(daily_context.progress)}")
        click.echo(f"\n📄 Saved to: {file_path}")

        # Show themes preview
        if daily_context.themes:
            click.echo("\n🔍 Key themes:")
            for theme in daily_context.themes[:3]:
                click.echo(f"   • {theme}")

    except FileNotFoundError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)
    except AIError as e:
        click.echo(f"❌ AI synthesis failed: {e}")
        click.echo("\n💡 Make sure Ollama is running: ollama serve")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Failed to capture context: {e}")
        logger.exception("Context capture failed")
        sys.exit(1)


if __name__ == "__main__":
    cli()
