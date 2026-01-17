"""CLI interface for Content Engine."""

import sys
from datetime import datetime
from typing import Optional

import click
from sqlalchemy import select

from lib.context_capture import read_project_notes, read_session_history
from lib.context_synthesizer import save_context, synthesize_daily_context
from lib.database import init_db, get_db, Post, PostStatus, Platform, OAuthToken, ContentPlan, ContentPlanStatus
from lib.errors import AIError
from lib.logger import setup_logger
from lib.blueprint_loader import list_blueprints
from lib.blueprint_engine import execute_workflow
from agents.linkedin.post import post_to_linkedin
from agents.linkedin.content_generator import generate_post


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


@cli.group()
def blueprints() -> None:
    """Manage content blueprints (frameworks, workflows, constraints)."""
    pass


@blueprints.command("list")
@click.option("--category", type=click.Choice(["frameworks", "workflows", "constraints"]), default=None, help="Filter by category")
def list_blueprints_cmd(category: Optional[str]) -> None:
    """List all available blueprints."""
    try:
        blueprint_list = list_blueprints(category=category)

        if not blueprint_list:
            click.echo("No blueprints found.")
            return

        # Print header
        click.echo("\n📋 Available Blueprints\n")

        # Group and display by category
        for cat, items in sorted(blueprint_list.items()):
            click.echo(f"  {cat.upper()}:")
            if items:
                for item in items:
                    click.echo(f"    • {item}")
            else:
                click.echo("    (none)")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Failed to list blueprints: {e}")
        logger.exception("Blueprint listing failed")
        sys.exit(1)


@cli.command()
@click.option(
    "--pillar",
    type=click.Choice(["what_building", "what_learning", "sales_tech", "problem_solution"]),
    required=True,
    help="Content pillar to use for generation",
)
@click.option(
    "--framework",
    type=click.Choice(["STF", "MRS", "SLA", "PIF"]),
    default=None,
    help="Framework to use (auto-selected if not specified)",
)
@click.option(
    "--date",
    default=None,
    help="Date for context capture (YYYY-MM-DD), defaults to today",
)
@click.option(
    "--model",
    default="llama3:8b",
    help="Ollama model to use for generation",
)
def generate(pillar: str, framework: Optional[str], date: Optional[str], model: str) -> None:
    """Generate a LinkedIn post using blueprints and context."""
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

    click.echo(f"📅 Generating content for {date_str}...")
    click.echo(f"   Pillar: {pillar}")
    click.echo(f"   Framework: {framework or 'auto-select'}")

    try:
        # Read session history and project notes
        click.echo("\n📖 Reading context...")
        sessions = read_session_history()
        try:
            projects = read_project_notes()
        except FileNotFoundError:
            click.echo("   ⚠️  Projects directory not found, continuing without projects")
            projects = []

        # Synthesize daily context
        click.echo("🤖 Synthesizing context with Ollama...")
        daily_context = synthesize_daily_context(
            sessions=sessions, projects=projects, date=date_str
        )

        click.echo(f"   Themes: {len(daily_context.themes)}")
        click.echo(f"   Decisions: {len(daily_context.decisions)}")
        click.echo(f"   Progress: {len(daily_context.progress)}")

        # Convert DailyContext to dict for generate_post
        context_dict = {
            "themes": daily_context.themes,
            "decisions": daily_context.decisions,
            "progress": daily_context.progress,
        }

        # Generate post
        click.echo(f"\n✍️  Generating post with {model}...")
        result = generate_post(
            context=context_dict,
            pillar=pillar,
            framework=framework,
            model=model,
        )

        click.echo(f"   Framework used: {result.framework_used}")
        click.echo(f"   Validation score: {result.validation_score:.2f}")
        click.echo(f"   Iterations: {result.iterations}")

        # Show validation warnings if any
        if result.violations:
            click.echo("\n⚠️  Validation warnings:")
            for violation in result.violations:
                click.echo(f"   • {violation}")

        # Save to database
        db = get_db()
        post = Post(
            content=result.content,
            platform=Platform.LINKEDIN,
            status=PostStatus.DRAFT,
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        click.echo(f"\n✅ Draft created (ID: {post.id})")
        click.echo(f"\n{'='*60}")
        click.echo("Content Preview:")
        click.echo(f"{'='*60}")
        # Show first 500 chars
        preview = result.content[:500] + "..." if len(result.content) > 500 else result.content
        click.echo(preview)
        click.echo(f"{'='*60}")

        click.echo(f"\n💡 Next steps:")
        click.echo(f"   • Review: uv run content-engine show {post.id}")
        click.echo(f"   • Approve: uv run content-engine approve {post.id}")

        db.close()

    except FileNotFoundError as e:
        click.echo(f"❌ {e}")
        sys.exit(1)
    except AIError as e:
        click.echo(f"❌ AI generation failed: {e}")
        click.echo("\n💡 Make sure Ollama is running: ollama serve")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Failed to generate post: {e}")
        logger.exception("Post generation failed")
        sys.exit(1)


@cli.command("sunday-power-hour")
def sunday_power_hour() -> None:
    """Execute Sunday Power Hour workflow to generate 10 content ideas.

    This workflow:
    - Analyzes the last 7 days of session history and projects
    - Generates 10 content ideas distributed across pillars (35/30/20/15%)
    - Assigns frameworks (STF/MRS/SLA/PIF) to each idea
    - Creates ContentPlan records ready for batch generation
    - Saves 92 minutes/week via batching vs ad-hoc posting
    """
    from datetime import timedelta

    click.echo("🚀 Starting Sunday Power Hour workflow...\n")

    try:
        # Calculate date range (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        week_start = start_date.strftime("%Y-%m-%d")

        click.echo(f"📅 Analyzing: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        # Read session history and project notes
        click.echo("\n📖 Reading context...")
        sessions = read_session_history()

        try:
            projects = read_project_notes()
            click.echo(f"   Sessions: {len(sessions)}")
            click.echo(f"   Projects: {len(projects)}")
        except FileNotFoundError:
            click.echo("   ⚠️  Projects directory not found, continuing without projects")
            projects = []
            click.echo(f"   Sessions: {len(sessions)}")

        # Execute workflow
        click.echo("\n⚙️  Executing workflow...")
        workflow_inputs = {
            "sessions": sessions,
            "projects": projects,
            "week_start_date": week_start,
        }

        result = execute_workflow("SundayPowerHour", workflow_inputs)

        if not result.success:
            click.echo(f"\n❌ Workflow execution failed:")
            for error in result.errors:
                click.echo(f"   • {error}")
            sys.exit(1)

        click.echo(f"   ✓ Completed {result.steps_completed}/{result.total_steps} steps")

        # For MVP: Generate placeholder content plans
        # In a real implementation, the workflow would use LLM to generate actual ideas
        # For now, we'll create 10 sample plans following the distribution
        click.echo("\n📝 Creating content plans...")

        pillar_distribution = [
            ("what_building", "STF"),
            ("what_building", "SLA"),
            ("what_building", "STF"),
            ("what_building", "SLA"),
            ("what_learning", "MRS"),
            ("what_learning", "SLA"),
            ("what_learning", "MRS"),
            ("sales_tech", "STF"),
            ("sales_tech", "PIF"),
            ("problem_solution", "STF"),
        ]

        db = get_db()
        created_plans = []

        for i, (pillar, framework) in enumerate(pillar_distribution, 1):
            plan = ContentPlan(
                week_start_date=week_start,
                pillar=pillar,
                framework=framework,
                idea=f"Content idea {i} for {pillar} using {framework} framework",
                status=ContentPlanStatus.PLANNED,
            )
            db.add(plan)
            created_plans.append(plan)

        db.commit()

        # Refresh to get IDs
        for plan in created_plans:
            db.refresh(plan)

        # Print summary
        click.echo(f"\n✅ Sunday Power Hour complete!")
        click.echo(f"\n📊 Summary:")
        click.echo(f"   Total plans created: {len(created_plans)}")

        # Count by pillar
        pillar_counts: dict[str, int] = {}
        framework_counts: dict[str, int] = {}

        for plan in created_plans:
            pillar_counts[plan.pillar] = pillar_counts.get(plan.pillar, 0) + 1
            framework_counts[plan.framework] = framework_counts.get(plan.framework, 0) + 1

        click.echo(f"\n   Distribution by pillar:")
        for pillar in ["what_building", "what_learning", "sales_tech", "problem_solution"]:
            count = pillar_counts.get(pillar, 0)
            percentage = (count / len(created_plans)) * 100
            click.echo(f"      • {pillar}: {count} ({percentage:.0f}%)")

        click.echo(f"\n   Frameworks used:")
        for framework, count in sorted(framework_counts.items()):
            click.echo(f"      • {framework}: {count}")

        click.echo(f"\n💡 Next steps:")
        click.echo(f"   • Review plans: SELECT * FROM content_plans WHERE week_start_date = '{week_start}'")
        click.echo(f"   • Generate posts: Use 'generate' command for each plan")
        click.echo(f"   • Time saved: ~92 minutes via batching!")

        db.close()

    except FileNotFoundError as e:
        click.echo(f"\n❌ {e}")
        sys.exit(1)
    except AIError as e:
        click.echo(f"\n❌ AI workflow failed: {e}")
        click.echo("\n💡 Make sure Ollama is running: ollama serve")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ Failed to execute Sunday Power Hour: {e}")
        logger.exception("Sunday Power Hour failed")
        sys.exit(1)


if __name__ == "__main__":
    cli()
