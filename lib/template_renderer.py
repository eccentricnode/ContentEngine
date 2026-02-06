"""Template renderer for Content Engine.

Renders Handlebars templates with context data for LLM prompts.
"""

from pathlib import Path
from typing import Any, cast
import chevron  # type: ignore[import-untyped]


def get_templates_dir() -> Path:
    """Get the templates directory path.

    Returns:
        Path to blueprints/templates directory
    """
    # Get project root (parent of lib/)
    project_root = Path(__file__).parent.parent
    return project_root / "blueprints" / "templates"


def render_template(template_name: str, context: dict[str, Any]) -> str:
    """Render a Handlebars template with the given context.

    Args:
        template_name: Template filename (e.g., "LinkedInPost.hbs")
        context: Dictionary of variables to substitute in template

    Returns:
        Rendered template as string

    Raises:
        FileNotFoundError: If template file doesn't exist
        ValueError: If template rendering fails
    """
    templates_dir = get_templates_dir()
    template_path = templates_dir / template_name

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    try:
        with open(template_path, 'r') as f:
            template_content = f.read()

        rendered = cast(str, chevron.render(template_content, context))
        return rendered
    except Exception as e:
        raise ValueError(f"Failed to render template {template_name}: {e}") from e


def render_template_string(template_string: str, context: dict[str, Any]) -> str:
    """Render a Handlebars template string with the given context.

    Args:
        template_string: Handlebars template as string
        context: Dictionary of variables to substitute in template

    Returns:
        Rendered template as string

    Raises:
        ValueError: If template rendering fails
    """
    try:
        rendered = cast(str, chevron.render(template_string, context))
        return rendered
    except Exception as e:
        raise ValueError(f"Failed to render template string: {e}") from e
