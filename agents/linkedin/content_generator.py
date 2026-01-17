"""Content generator using blueprint-based validation."""

from dataclasses import dataclass
from typing import Any

from agents.linkedin.post_validator import Severity, validate_post
from lib.blueprint_engine import select_framework
from lib.blueprint_loader import load_constraints, load_framework
from lib.database import Post
from lib.errors import AIError
from lib.ollama import OllamaClient
from lib.template_renderer import render_template


@dataclass
class GenerationResult:
    """Result of content generation."""

    content: str
    framework_used: str
    validation_score: float
    is_valid: bool
    iterations: int
    violations: list[str]


def generate_post(
    context: dict[str, Any],
    pillar: str,
    framework: str | None = None,
    model: str = "llama3:8b",
    max_iterations: int = 3,
) -> GenerationResult:
    """Generate LinkedIn post using blueprint-based validation.

    Args:
        context: Daily context with themes, decisions, and progress
        pillar: Content pillar (what_building, what_learning, sales_tech, problem_solution)
        framework: Framework to use (STF, MRS, SLA, PIF) or None for auto-selection
        model: Ollama model to use (default: llama3:8b)
        max_iterations: Maximum refinement attempts (default: 3)

    Returns:
        GenerationResult with generated content and validation info

    Raises:
        AIError: If content generation fails
    """
    # Auto-select framework if not specified
    if framework is None:
        framework = select_framework(pillar, context)

    # Load blueprints
    framework_blueprint = load_framework(framework, "linkedin")
    brand_voice = load_constraints("BrandVoice")
    pillars_constraint = load_constraints("ContentPillars")

    # Prepare template context
    template_context = _prepare_template_context(
        context, pillar, framework_blueprint, brand_voice, pillars_constraint
    )

    # Render prompt template
    prompt = render_template("LinkedInPost.hbs", template_context)

    # Initialize Ollama client
    ollama = OllamaClient(model=model)

    # Iterative generation with validation
    best_content = ""
    best_score = 0.0
    violations: list[str] = []

    for iteration in range(max_iterations):
        # Generate content
        try:
            if iteration == 0:
                # First attempt - use base prompt
                generated = ollama.generate_content_ideas(prompt)
            else:
                # Refinement - add violations as feedback
                refinement_prompt = (
                    f"{prompt}\n\n"
                    f"PREVIOUS ATTEMPT HAD THESE ISSUES:\n"
                    + "\n".join(f"- {v}" for v in violations)
                    + "\n\nPlease fix these issues and try again."
                )
                generated = ollama.generate_content_ideas(refinement_prompt)
        except AIError:
            if iteration == 0:
                # If first attempt fails, re-raise
                raise
            # If refinement fails, return best attempt so far
            break

        # Validate generated content using comprehensive post validator
        # Create temporary Post object for validation
        temp_post = Post(id=0, content=generated)
        validation_report = validate_post(temp_post, framework=framework)

        # Extract violation messages for feedback (errors and warnings only)
        current_violations = [
            f"{v.severity.upper()}: {v.message}"
            + (f" (Suggestion: {v.suggestion})" if v.suggestion else "")
            for v in validation_report.violations
            if v.severity in (Severity.ERROR, Severity.WARNING)
        ]

        # Track best attempt
        if validation_report.score > best_score:
            best_content = generated
            best_score = validation_report.score
            violations = current_violations

        # If valid (no errors), we're done
        if validation_report.is_valid:
            return GenerationResult(
                content=generated,
                framework_used=framework,
                validation_score=validation_report.score,
                is_valid=True,
                iterations=iteration + 1,
                violations=[],
            )

        # Update violations for next iteration
        violations = current_violations

    # Return best attempt (may not be fully valid)
    return GenerationResult(
        content=best_content,
        framework_used=framework,
        validation_score=best_score,
        is_valid=len(violations) == 0,
        iterations=max_iterations,
        violations=violations,
    )


def _prepare_template_context(
    context: dict[str, Any],
    pillar: str,
    framework_blueprint: dict[str, Any],
    brand_voice: dict[str, Any],
    pillars_constraint: dict[str, Any],
) -> dict[str, Any]:
    """Prepare context for template rendering.

    Args:
        context: Daily context data
        pillar: Content pillar ID
        framework_blueprint: Framework YAML data
        brand_voice: BrandVoice constraint data
        pillars_constraint: ContentPillars constraint data

    Returns:
        Template context dict
    """
    # Get pillar data
    pillar_data = pillars_constraint["pillars"][pillar]

    # Extract framework sections
    framework_sections = framework_blueprint["structure"]["sections"]

    # Extract brand voice data
    brand_characteristics = [
        {"name": char["id"], "description": char.get("description", "")}
        for char in brand_voice["characteristics"]
    ]

    # Flatten forbidden phrases from all categories
    forbidden_phrases = [
        phrase
        for category_phrases in brand_voice["forbidden_phrases"].values()
        for phrase in category_phrases
    ][:15]  # Limit to first 15 for prompt brevity

    # Extract style rules
    brand_style = [
        {
            "name": style_id,
            "description": ", ".join(rules) if isinstance(rules, list) else rules,
        }
        for style_id, rules in brand_voice["style_rules"].items()
    ]

    # Get validation rules
    validation_rules = framework_blueprint.get("validation", {})

    return {
        "context": {
            "themes": context.get("themes", []),
            "decisions": context.get("decisions", []),
            "progress": context.get("progress", []),
        },
        "pillar_name": pillar_data["name"],
        "pillar_description": pillar_data["description"],
        "pillar_characteristics": [
            f"{list(char.keys())[0]}: {list(char.values())[0]}"
            for char in pillar_data.get("characteristics", [])
        ],
        "framework_name": framework_blueprint["name"],
        "framework_sections": framework_sections,
        "brand_voice_characteristics": brand_characteristics,
        "forbidden_phrases": forbidden_phrases,
        "brand_voice_style": brand_style,
        "validation_min_chars": validation_rules.get("min_chars", 0),
        "validation_max_chars": validation_rules.get("max_chars", 3000),
        "validation_min_sections": validation_rules.get("min_sections", 1),
    }
