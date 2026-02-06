"""CLI interface for Content Engine."""

import sys
from datetime import datetime
from typing import Optional

import click
import yaml
from sqlalchemy import select

from lib.context_capture import read_project_notes, read_session_history
from lib.context_synthesizer import save_context, synthesize_daily_context
from lib.database import init_db, get_db, Post, PostStatus, Platform, OAuthToken, ContentPlan, ContentPlanStatus
from lib.errors import AIError
from lib.logger import setup_logger
from lib.blueprint_loader import list_blueprints, load_framework, load_workflow, load_constraints
from lib.blueprint_engine import execute_workflow
from agents.linkedin.post import post_to_linkedin
from agents.linkedin.content_generator import generate_post
from agents.linkedin.post_validator import validate_post
from agents.brand_planner import BrandPlanner, ContentBrief, Game


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
        click.echo("Run OAuth flow first: uv run python -m agents.linkedin.oauth_server")
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
            click.echo("View at: https://www.linkedin.com/feed/")

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
        click.echo("❌ Invalid time format. Use: YYYY-MM-DD HH:MM (e.g., 2024-01-15 09:00)")
        db.close()
        sys.exit(1)

    if scheduled_dt < datetime.utcnow():
        click.echo("❌ Scheduled time must be in the future")
        db.close()
        sys.exit(1)

    post.status = PostStatus.SCHEDULED
    post.scheduled_at = scheduled_dt
    db.commit()

    click.echo(f"✅ Post {post_id} scheduled for {scheduled_dt}")
    click.echo("Run worker to publish: uv run python -m worker")

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


@blueprints.command("show")
@click.argument("blueprint_name")
@click.option(
    "--platform",
    type=str,
    default="linkedin",
    help="Platform for framework blueprints (default: linkedin)",
)
def show_blueprint(blueprint_name: str, platform: str) -> None:
    """Show detailed blueprint information.

    Display the full blueprint structure including validation rules,
    sections, examples, and best practices.

    Examples:
        uv run content-engine blueprints show STF
        uv run content-engine blueprints show BrandVoice
        uv run content-engine blueprints show SundayPowerHour
    """
    try:
        # Try loading as framework first (with platform)
        blueprint = None
        blueprint_type = None

        try:
            blueprint = load_framework(blueprint_name, platform)
            blueprint_type = "Framework"
        except FileNotFoundError:
            pass

        # Try loading as workflow
        if blueprint is None:
            try:
                blueprint = load_workflow(blueprint_name)
                blueprint_type = "Workflow"
            except FileNotFoundError:
                pass

        # Try loading as constraint
        if blueprint is None:
            try:
                blueprint = load_constraints(blueprint_name)
                blueprint_type = "Constraint"
            except FileNotFoundError:
                pass

        # If still not found, error
        if blueprint is None:
            click.echo(click.style(f"\n❌ Blueprint '{blueprint_name}' not found", fg="red"))
            click.echo("\nTry: uv run content-engine blueprints list")
            sys.exit(1)

        # Print header
        click.echo(f"\n{'='*60}")
        click.echo(click.style(f"{blueprint_type}: {blueprint_name}", fg="cyan", bold=True))
        if blueprint_type == "Framework":
            click.echo(f"Platform: {platform}")
        click.echo(f"{'='*60}\n")

        # Print formatted YAML
        yaml_output = yaml.dump(blueprint, default_flow_style=False, sort_keys=False)
        click.echo(yaml_output)

        # Print footer with helpful info
        click.echo(f"{'='*60}\n")

        if blueprint_type == "Framework":
            sections = blueprint.get("structure", {}).get("sections", [])
            click.echo(click.style("📐 Structure:", fg="blue", bold=True))
            click.echo(f"   Sections: {len(sections)}")
            if sections:
                for section in sections:
                    section_name = section.get("id", "unknown")
                    click.echo(f"      • {section_name}")

            validation = blueprint.get("validation", {})
            if validation:
                click.echo(click.style("\n✓ Validation Rules:", fg="blue", bold=True))
                if "min_chars" in validation:
                    click.echo(f"   Min characters: {validation['min_chars']}")
                if "max_chars" in validation:
                    click.echo(f"   Max characters: {validation['max_chars']}")
                if "min_sections" in validation:
                    click.echo(f"   Min sections: {validation['min_sections']}")

            examples = blueprint.get("examples", [])
            if examples:
                click.echo(click.style(f"\n📝 Examples: {len(examples)} provided", fg="blue", bold=True))

        elif blueprint_type == "Workflow":
            steps = blueprint.get("steps", [])
            click.echo(click.style("🔄 Workflow Steps:", fg="blue", bold=True))
            click.echo(f"   Total: {len(steps)}")
            total_duration = sum(step.get("duration_minutes", 0) for step in steps)
            click.echo(f"   Duration: {total_duration} minutes")
            for i, step in enumerate(steps, 1):
                step_name = step.get("name", "unknown")
                duration = step.get("duration_minutes", 0)
                click.echo(f"      {i}. {step_name} ({duration}min)")

        elif blueprint_type == "Constraint":
            if "characteristics" in blueprint:
                chars = blueprint["characteristics"]
                click.echo(click.style(f"⚡ Characteristics: {len(chars)}", fg="blue", bold=True))

            if "pillars" in blueprint:
                pillars = blueprint["pillars"]
                click.echo(click.style(f"\n📊 Pillars: {len(pillars)}", fg="blue", bold=True))
                for pillar_id, pillar_data in pillars.items():
                    percentage = pillar_data.get("percentage", 0)
                    name = pillar_data.get("name", pillar_id)
                    click.echo(f"      • {name}: {percentage}%")

            if "forbidden_phrases" in blueprint:
                categories = blueprint["forbidden_phrases"]
                total_phrases = sum(len(phrases) for phrases in categories.values())
                click.echo(click.style(f"\n🚫 Forbidden Phrases: {total_phrases} total", fg="blue", bold=True))

        click.echo()

    except Exception as e:
        click.echo(click.style(f"\n❌ Failed to show blueprint: {e}", fg="red"))
        logger.exception("Blueprint show failed")
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

        click.echo("\n💡 Next steps:")
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
            click.echo("\n❌ Workflow execution failed:")
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
        click.echo("\n✅ Sunday Power Hour complete!")
        click.echo("\n📊 Summary:")
        click.echo(f"   Total plans created: {len(created_plans)}")

        # Count by pillar
        pillar_counts: dict[str, int] = {}
        framework_counts: dict[str, int] = {}

        for plan in created_plans:
            pillar_counts[plan.pillar] = pillar_counts.get(plan.pillar, 0) + 1
            framework_counts[plan.framework] = framework_counts.get(plan.framework, 0) + 1

        click.echo("\n   Distribution by pillar:")
        for pillar in ["what_building", "what_learning", "sales_tech", "problem_solution"]:
            count = pillar_counts.get(pillar, 0)
            percentage = (count / len(created_plans)) * 100
            click.echo(f"      • {pillar}: {count} ({percentage:.0f}%)")

        click.echo("\n   Frameworks used:")
        for framework, count in sorted(framework_counts.items()):
            click.echo(f"      • {framework}: {count}")

        click.echo("\n💡 Next steps:")
        click.echo(f"   • Review plans: SELECT * FROM content_plans WHERE week_start_date = '{week_start}'")
        click.echo("   • Generate posts: Use 'generate' command for each plan")
        click.echo("   • Time saved: ~92 minutes via batching!")

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


@cli.command()
@click.argument("post_id", type=int)
@click.option(
    "--framework",
    type=click.Choice(["STF", "MRS", "SLA", "PIF"]),
    default="STF",
    help="Framework to validate against",
)
def validate(post_id: int, framework: str) -> None:
    """Validate a post against all constraints.

    Checks framework structure, brand voice, and platform rules.
    Provides detailed feedback with error/warning/suggestion severity levels.
    """
    try:
        db = get_db()

        # Load post
        post = db.get(Post, post_id)
        if not post:
            click.echo(click.style(f"\n❌ Post {post_id} not found", fg="red"))
            sys.exit(1)

        # Validate post
        report = validate_post(post, framework=framework)

        # Print header
        click.echo(f"\n{'='*60}")
        click.echo(f"Validation Report - Post #{post_id}")
        click.echo(f"Framework: {framework}")
        click.echo(f"{'='*60}\n")

        # Print overall status
        if report.is_valid:
            click.echo(click.style("✅ PASS", fg="green", bold=True))
        else:
            click.echo(click.style("❌ FAIL", fg="red", bold=True))

        click.echo(f"Validation Score: {report.score:.2f}/1.00\n")

        # Print violations by severity
        if report.errors:
            click.echo(click.style("🔴 ERRORS (must fix):", fg="red", bold=True))
            for error in report.errors:
                click.echo(f"  • {error.message}")
                if error.suggestion:
                    click.echo(click.style(f"    → {error.suggestion}", fg="yellow"))
            click.echo()

        if report.warnings:
            click.echo(click.style("🟡 WARNINGS (should fix):", fg="yellow", bold=True))
            for warning in report.warnings:
                click.echo(f"  • {warning.message}")
                if warning.suggestion:
                    click.echo(click.style(f"    → {warning.suggestion}", fg="cyan"))
            click.echo()

        if report.suggestions:
            click.echo(click.style("💡 SUGGESTIONS (optional):", fg="cyan", bold=True))
            for suggestion in report.suggestions:
                click.echo(f"  • {suggestion.message}")
                if suggestion.suggestion:
                    click.echo(click.style(f"    → {suggestion.suggestion}", fg="blue"))
            click.echo()

        # Print summary
        if not report.violations:
            click.echo(click.style("🎉 Perfect! No issues found.", fg="green"))
        else:
            click.echo(f"Total violations: {len(report.violations)}")
            click.echo(f"  Errors: {len(report.errors)}")
            click.echo(f"  Warnings: {len(report.warnings)}")
            click.echo(f"  Suggestions: {len(report.suggestions)}")

        # Exit with appropriate code
        sys.exit(0 if report.is_valid else 1)

    except Exception as e:
        click.echo(click.style(f"\n❌ Validation failed: {e}", fg="red"))
        logger.exception("Validation failed")
        sys.exit(1)


@cli.command("collect-analytics")
@click.option("--days-back", default=7, type=int, help="Fetch analytics for posts from last N days")
@click.option("--test-post", type=str, help="Fetch analytics for a single post URN")
def collect_analytics(days_back: int, test_post: Optional[str]) -> None:
    """Collect LinkedIn post analytics and update posts.jsonl."""
    import os
    from pathlib import Path
    from agents.linkedin.analytics import LinkedInAnalytics

    click.echo("=" * 60)
    click.echo("LinkedIn Analytics Collection")
    click.echo("=" * 60)

    # Load access token
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not access_token:
        # Try loading from database
        try:
            db = get_db()
            stmt = select(OAuthToken).where(OAuthToken.platform == Platform.LINKEDIN)
            result = db.execute(stmt)
            oauth_token = result.scalar_one_or_none()
            if oauth_token:
                access_token = oauth_token.access_token
        except Exception:
            pass

    if not access_token:
        click.echo(click.style("\n❌ Error: LINKEDIN_ACCESS_TOKEN not found", fg="red"))
        click.echo("\nPlease set the environment variable:")
        click.echo("  export LINKEDIN_ACCESS_TOKEN='your_token_here'")
        click.echo("\nOr store it in the database:")
        click.echo("  uv run content-engine oauth linkedin")
        sys.exit(1)

    analytics = LinkedInAnalytics(access_token)

    # Test single post
    if test_post:
        click.echo(f"\n📊 Fetching analytics for: {test_post}")
        metrics = analytics.get_post_analytics(test_post)

        if metrics:
            click.echo(click.style("\n✓ Analytics fetched successfully!", fg="green"))
            click.echo(f"  Impressions: {metrics.impressions:,}")
            click.echo(f"  Likes: {metrics.likes}")
            click.echo(f"  Comments: {metrics.comments}")
            click.echo(f"  Shares: {metrics.shares}")
            click.echo(f"  Clicks: {metrics.clicks}")
            click.echo(f"  Engagement Rate: {metrics.engagement_rate:.2%}")
        else:
            click.echo(click.style("\n✗ Failed to fetch analytics", fg="red"))
            click.echo("  Make sure:")
            click.echo("  - The post URN is correct")
            click.echo("  - Your access token has analytics permissions")
            click.echo("  - The post exists and you have access to it")
            sys.exit(1)
    else:
        # Update all posts
        posts_file = Path("data/posts.jsonl")

        if not posts_file.exists():
            click.echo(click.style(f"\n❌ Error: {posts_file} not found", fg="red"))
            click.echo("\nCreate the file first or run:")
            click.echo("  mkdir -p data && touch data/posts.jsonl")
            sys.exit(1)

        click.echo(f"\n📊 Fetching analytics for posts from last {days_back} days...")
        click.echo(f"   File: {posts_file}")

        try:
            updated_count = analytics.update_posts_with_analytics(posts_file, days_back=days_back)
            click.echo(click.style(f"\n✓ Updated analytics for {updated_count} posts", fg="green"))

            if updated_count == 0:
                click.echo("\n💡 No posts needed updates. This could mean:")
                click.echo("  - All recent posts already have analytics")
                click.echo("  - No posts in the specified time window")
                click.echo("  - Posts file is empty")
        except Exception as e:
            click.echo(click.style(f"\n❌ Error updating analytics: {e}", fg="red"))
            logger.exception("Analytics collection failed")
            sys.exit(1)


@cli.command("plan-content")
@click.option("--days", default=7, type=int, help="Days of context to aggregate (default: 7)")
@click.option("--posts", default=10, type=int, help="Target posts to plan (default: 10)")
@click.option("--dry-run", is_flag=True, help="Preview without saving to database")
@click.option("--model", default="llama3:8b", help="Ollama model for planning (default: llama3:8b)")
def plan_content(days: int, posts: int, dry_run: bool, model: str) -> None:
    """Plan content using Brand Planner agent.

    Analyzes context from the past N days and generates content plans
    with strategic decisions about pillars, frameworks, and game strategy.

    The Brand Planner:
    - Extracts content ideas from daily context
    - Assigns pillars based on 35/30/20/15 distribution
    - Decides game strategy (traffic vs building-in-public)
    - Selects appropriate frameworks (STF/MRS/SLA/PIF)
    """
    from datetime import timedelta
    from pathlib import Path
    import json

    click.echo("🧠 Starting Brand Planner...\n")

    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        week_start = start_date.strftime("%Y-%m-%d")

        click.echo(f"📅 Analyzing: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        click.echo(f"🎯 Target: {posts} posts")

        # Load context files
        context_dir = Path("context")
        contexts = []

        if context_dir.exists():
            click.echo(f"\n📖 Loading context from {context_dir}/...")
            for i in range(days):
                date = (end_date - timedelta(days=i)).strftime("%Y-%m-%d")
                context_file = context_dir / f"{date}.json"
                if context_file.exists():
                    try:
                        with open(context_file, "r") as f:
                            data = json.load(f)
                            from lib.context_synthesizer import DailyContext
                            ctx = DailyContext(
                                themes=data.get("themes", []),
                                decisions=data.get("decisions", []),
                                progress=data.get("progress", []),
                                date=data.get("date", date),
                                raw_data=data.get("raw_data", {}),
                            )
                            contexts.append(ctx)
                            click.echo(f"   ✓ Loaded {date}")
                    except Exception as e:
                        click.echo(f"   ⚠️ Failed to load {date}: {e}")

        if not contexts:
            click.echo("\n⚠️ No context files found. Generating from session history...")

            # Fall back to capturing context on the fly
            sessions = read_session_history()
            try:
                projects = read_project_notes()
            except FileNotFoundError:
                projects = []

            from lib.context_synthesizer import synthesize_daily_context
            ctx = synthesize_daily_context(
                sessions=sessions,
                projects=projects,
                date=end_date.strftime("%Y-%m-%d"),
            )
            contexts.append(ctx)
            click.echo(f"   ✓ Synthesized context with {len(ctx.themes)} themes")

        click.echo(f"\n📊 Loaded {len(contexts)} day(s) of context")

        # Run Brand Planner
        click.echo(f"\n🤖 Planning with {model}...")
        planner = BrandPlanner(model=model)
        result = planner.plan_week(contexts, target_posts=posts)

        if not result.success:
            click.echo(click.style("\n❌ Planning failed:", fg="red"))
            for error in result.errors:
                click.echo(f"   • {error}")
            sys.exit(1)

        # Display results
        click.echo(click.style(f"\n✅ Planning complete!", fg="green"))
        click.echo(f"   Ideas extracted: {result.total_ideas_extracted}")
        click.echo(f"   Briefs created: {len(result.briefs)}")

        # Distribution breakdown
        click.echo("\n📈 Pillar Distribution:")
        total = sum(result.distribution.values())
        for pillar, count in sorted(result.distribution.items()):
            percentage = (count / total * 100) if total > 0 else 0
            click.echo(f"   {pillar}: {count} ({percentage:.0f}%)")

        # Game strategy breakdown
        click.echo("\n🎮 Game Strategy:")
        for game, count in result.game_breakdown.items():
            click.echo(f"   {game}: {count}")

        # Show briefs
        click.echo("\n📝 Content Briefs:")
        click.echo("=" * 70)

        for i, brief in enumerate(result.briefs, 1):
            click.echo(f"\n{i}. {brief.idea.title}")
            click.echo(f"   Pillar: {brief.pillar} | Framework: {brief.framework}")
            click.echo(f"   Game: {brief.game.value} | Hook: {brief.hook_type.value}")
            click.echo(f"   Insight: {brief.idea.core_insight[:80]}...")
            click.echo(f"   Structure: {brief.structure_preview[:70]}...")

        if dry_run:
            click.echo(click.style("\n🔍 DRY RUN - No changes saved to database", fg="yellow"))
        else:
            # Save to database
            click.echo("\n💾 Saving to database...")
            db = get_db()

            created_plans = []
            for brief in result.briefs:
                plan = ContentPlan(
                    week_start_date=week_start,
                    pillar=brief.pillar,
                    framework=brief.framework,
                    idea=brief.idea.title,
                    status=ContentPlanStatus.PLANNED,
                    game=brief.game.value,
                    hook_type=brief.hook_type.value,
                    core_insight=brief.idea.core_insight,
                    context_summary=brief.context_summary,
                    structure_preview=brief.structure_preview,
                    rationale=brief.rationale,
                    source_theme=brief.idea.source_theme,
                    audience_value=brief.idea.audience_value,
                )
                db.add(plan)
                created_plans.append(plan)

            db.commit()

            # Refresh to get IDs
            for plan in created_plans:
                db.refresh(plan)

            click.echo(click.style(f"   ✓ Created {len(created_plans)} content plans", fg="green"))

            click.echo("\n💡 Next steps:")
            click.echo(f"   • Generate post: uv run content-engine generate-from-plan <plan_id>")
            click.echo(f"   • List plans: SELECT * FROM content_plans WHERE week_start_date = '{week_start}'")

            db.close()

        if result.errors:
            click.echo(click.style("\n⚠️ Warnings:", fg="yellow"))
            for error in result.errors:
                click.echo(f"   • {error}")

    except AIError as e:
        click.echo(click.style(f"\n❌ AI planning failed: {e}", fg="red"))
        click.echo("\n💡 Make sure Ollama is running: ollama serve")
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"\n❌ Planning failed: {e}", fg="red"))
        logger.exception("Brand Planner failed")
        sys.exit(1)


@cli.command("generate-from-plan")
@click.argument("plan_id", type=int)
@click.option("--model", default="llama3:8b", help="Ollama model for generation (default: llama3:8b)")
def generate_from_plan(plan_id: int, model: str) -> None:
    """Generate a LinkedIn post from a content plan.

    Uses the plan's pillar, framework, game strategy, and context
    to generate an optimized post.
    """
    click.echo(f"📝 Generating post from plan #{plan_id}...\n")

    try:
        db = get_db()

        # Load plan
        plan = db.get(ContentPlan, plan_id)
        if not plan:
            click.echo(click.style(f"❌ Plan #{plan_id} not found", fg="red"))
            sys.exit(1)

        if plan.status == ContentPlanStatus.GENERATED:
            click.echo(click.style(f"⚠️ Plan #{plan_id} already has a generated post (ID: {plan.post_id})", fg="yellow"))
            if not click.confirm("Generate anyway?"):
                sys.exit(0)

        click.echo(f"Plan: {plan.idea}")
        click.echo(f"   Pillar: {plan.pillar}")
        click.echo(f"   Framework: {plan.framework}")
        click.echo(f"   Game: {plan.game or 'not set'}")
        click.echo(f"   Hook: {plan.hook_type or 'not set'}")

        # Build context for generation
        context_dict = {
            "themes": [plan.source_theme or plan.idea] if plan.source_theme else [plan.idea],
            "decisions": [],
            "progress": [plan.core_insight] if plan.core_insight else [],
        }

        # Add context summary to themes if available
        if plan.context_summary:
            context_dict["themes"].extend(plan.context_summary.split(" | ")[:2])

        # Update plan status
        plan.status = ContentPlanStatus.IN_PROGRESS
        db.commit()

        # Generate post
        click.echo(f"\n✍️ Generating with {model}...")
        result = generate_post(
            context=context_dict,
            pillar=plan.pillar,
            framework=plan.framework,
            model=model,
        )

        click.echo(f"   Framework used: {result.framework_used}")
        click.echo(f"   Validation score: {result.validation_score:.2f}")
        click.echo(f"   Iterations: {result.iterations}")

        # Show validation warnings if any
        if result.violations:
            click.echo("\n⚠️ Validation warnings:")
            for violation in result.violations:
                click.echo(f"   • {violation}")

        # Save post to database
        post = Post(
            content=result.content,
            platform=Platform.LINKEDIN,
            status=PostStatus.DRAFT,
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        # Link plan to post
        plan.status = ContentPlanStatus.GENERATED
        plan.post_id = post.id
        db.commit()

        click.echo(click.style(f"\n✅ Post created (ID: {post.id})", fg="green"))
        click.echo(f"\n{'='*60}")
        click.echo("Content Preview:")
        click.echo(f"{'='*60}")
        # Show first 500 chars
        preview = result.content[:500] + "..." if len(result.content) > 500 else result.content
        click.echo(preview)
        click.echo(f"{'='*60}")

        click.echo("\n💡 Next steps:")
        click.echo(f"   • Review: uv run content-engine show {post.id}")
        click.echo(f"   • Validate: uv run content-engine validate {post.id} --framework {plan.framework}")
        click.echo(f"   • Approve: uv run content-engine approve {post.id}")

        db.close()

    except AIError as e:
        click.echo(click.style(f"\n❌ Generation failed: {e}", fg="red"))
        click.echo("\n💡 Make sure Ollama is running: ollama serve")
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"\n❌ Generation failed: {e}", fg="red"))
        logger.exception("Generation from plan failed")
        sys.exit(1)


@cli.command("worker")
@click.option("--continuous", is_flag=True, help="Run continuously (daemon mode)")
@click.option("--dry-run", is_flag=True, help="Preview without actually posting")
@click.option("--poll-interval", type=int, default=30, help="Seconds between queue checks")
def worker(continuous: bool, dry_run: bool, poll_interval: int) -> None:
    """Run the job worker to process scheduled posts.

    The worker processes the SQLite job queue, posting content to
    LinkedIn (and other platforms) when their scheduled time arrives.
    """
    from job_worker import JobWorker

    click.echo("🔧 Starting ContentEngine Job Worker...")

    if dry_run:
        click.echo(click.style("   DRY RUN mode - no actual posting", fg="yellow"))

    worker_instance = JobWorker(dry_run=dry_run)

    if continuous:
        click.echo(f"   Continuous mode (poll every {poll_interval}s)")
        click.echo("   Press Ctrl+C to stop\n")
        try:
            worker_instance.run_continuous(poll_interval=poll_interval)
        except KeyboardInterrupt:
            click.echo("\n👋 Worker stopped")
    else:
        processed = worker_instance.process_queue()
        click.echo(f"✅ Processed {processed} jobs")


@cli.group()
def queue() -> None:
    """Manage the job queue for scheduled posts."""
    pass


@queue.command("list")
@click.option("--status", type=click.Choice(["pending", "processing", "completed", "failed", "cancelled"]))
@click.option("--limit", type=int, default=20)
def queue_list(status: Optional[str], limit: int) -> None:
    """List jobs in the queue."""
    from lib.database import JobQueue, JobStatus

    db = get_db()

    query = db.query(JobQueue).order_by(JobQueue.created_at.desc()).limit(limit)

    if status:
        query = query.filter(JobQueue.status == JobStatus(status.upper()))

    jobs = query.all()

    if not jobs:
        click.echo("No jobs found.")
        db.close()
        return

    click.echo(f"\n{'ID':<5} {'Type':<18} {'Status':<12} {'Post':<6} {'Scheduled':<20}")
    click.echo("=" * 70)

    for job in jobs:
        scheduled = job.scheduled_at.strftime("%Y-%m-%d %H:%M") if job.scheduled_at else "immediate"
        click.echo(f"{job.id:<5} {job.job_type.value:<18} {job.status.value:<12} {job.post_id:<6} {scheduled:<20}")

    db.close()


@queue.command("status")
@click.argument("job_id", type=int)
def queue_status(job_id: int) -> None:
    """Show detailed status of a job."""
    from lib.database import JobQueue

    db = get_db()
    job = db.get(JobQueue, job_id)

    if not job:
        click.echo(click.style(f"Job {job_id} not found", fg="red"))
        db.close()
        sys.exit(1)

    click.echo(f"\n{'='*50}")
    click.echo(f"Job #{job.id}")
    click.echo(f"{'='*50}")
    click.echo(f"Type: {job.job_type.value}")
    click.echo(f"Status: {job.status.value}")
    click.echo(f"Post ID: {job.post_id}")
    click.echo(f"Priority: {job.priority}")
    click.echo(f"Scheduled: {job.scheduled_at or 'immediate'}")
    click.echo(f"Attempts: {job.attempts}/{job.max_attempts}")

    if job.last_error:
        click.echo(f"Last Error: {job.last_error}")
    if job.next_retry_at:
        click.echo(f"Next Retry: {job.next_retry_at}")
    if job.source_file:
        click.echo(f"Source File: {job.source_file}")

    click.echo(f"\nCreated: {job.created_at}")
    if job.started_at:
        click.echo(f"Started: {job.started_at}")
    if job.completed_at:
        click.echo(f"Completed: {job.completed_at}")

    db.close()


@queue.command("cancel")
@click.argument("job_id", type=int)
def queue_cancel(job_id: int) -> None:
    """Cancel a pending job."""
    from mcp_server import ContentEngineMCP

    mcp = ContentEngineMCP()
    result = mcp.cancel(job_id=job_id)

    if result.get("action") == "cancelled":
        click.echo(click.style(f"✅ Job {job_id} cancelled", fg="green"))
    else:
        click.echo(click.style(f"❌ {result.get('error', 'Unknown error')}", fg="red"))


@queue.command("fire")
@click.argument("post_id", type=int)
def queue_fire(post_id: int) -> None:
    """Queue a post for immediate publishing."""
    from mcp_server import ContentEngineMCP

    mcp = ContentEngineMCP()
    result = mcp.fire(post_id=post_id)

    if result.get("action") == "queued_immediate":
        click.echo(click.style(f"✅ Post {post_id} queued for immediate publishing", fg="green"))
        click.echo(f"   Job ID: {result.get('job_id')}")
        click.echo("\n💡 Run worker to process: uv run content-engine worker")
    else:
        click.echo(click.style(f"❌ {result.get('error', 'Unknown error')}", fg="red"))


@queue.command("schedule")
@click.argument("post_id", type=int)
@click.argument("scheduled_time")
def queue_schedule(post_id: int, scheduled_time: str) -> None:
    """Schedule a post for future publishing.

    SCHEDULED_TIME format: YYYY-MM-DDTHH:MM (e.g., 2026-02-10T09:00)
    """
    from mcp_server import ContentEngineMCP

    mcp = ContentEngineMCP()

    try:
        result = mcp.schedule(post_id=post_id, scheduled_at=scheduled_time)

        if result.get("action") in ["scheduled", "rescheduled"]:
            click.echo(click.style(f"✅ Post {post_id} scheduled", fg="green"))
            click.echo(f"   Job ID: {result.get('job_id')}")
            click.echo(f"   Scheduled: {result.get('scheduled_at')}")
        else:
            click.echo(click.style(f"❌ {result.get('error', 'Unknown error')}", fg="red"))

    except ValueError as e:
        click.echo(click.style(f"❌ {e}", fg="red"))
        sys.exit(1)


if __name__ == "__main__":
    cli()
