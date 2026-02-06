"""Blueprint engine for content validation and framework selection.

This module provides validation logic for generated content, checking against
framework structure requirements, brand voice constraints, and platform rules.
It also provides workflow execution capabilities for multi-step content generation.
"""

from dataclasses import dataclass
from typing import Any

from lib.blueprint_loader import load_constraints, load_framework, load_workflow


@dataclass
class ValidationResult:
    """Result of content validation."""

    is_valid: bool
    violations: list[str]
    warnings: list[str]
    suggestions: list[str]
    score: float  # 0.0 to 1.0


@dataclass
class WorkflowResult:
    """Result of workflow execution."""

    workflow_name: str
    success: bool
    outputs: dict[str, Any]
    steps_completed: int
    total_steps: int
    errors: list[str]


def validate_content(
    content: str, framework_name: str, platform: str = "linkedin"
) -> ValidationResult:
    """Validate content against framework structure and constraints.

    Args:
        content: The content to validate
        framework_name: Name of framework (STF, MRS, SLA, PIF)
        platform: Target platform (default: linkedin)

    Returns:
        ValidationResult with violations, warnings, and suggestions
    """
    violations: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []

    # Load framework blueprint
    framework = load_framework(framework_name, platform)

    # Check character length
    validation_rules = framework.get("validation", {})
    min_chars = validation_rules.get("min_chars", 0)
    max_chars = validation_rules.get("max_chars", 3000)

    content_length = len(content)

    if content_length < min_chars:
        violations.append(
            f"Content too short: {content_length} chars (min: {min_chars})"
        )
    elif content_length > max_chars:
        violations.append(
            f"Content too long: {content_length} chars (max: {max_chars})"
        )

    # Check brand voice constraints
    brand_voice_violations = check_brand_voice(content)
    violations.extend(brand_voice_violations)

    # Calculate score based on violations/warnings
    total_issues = len(violations) + len(warnings)
    if total_issues == 0:
        score = 1.0
    else:
        # Violations hurt score more than warnings
        score = max(0.0, 1.0 - (len(violations) * 0.2) - (len(warnings) * 0.05))

    # Add suggestions if not perfect
    if score < 1.0:
        if content_length < min_chars:
            suggestions.append(
                f"Expand content by {min_chars - content_length} characters"
            )
        if content_length > max_chars:
            suggestions.append(
                f"Reduce content by {content_length - max_chars} characters"
            )

    is_valid = len(violations) == 0

    return ValidationResult(
        is_valid=is_valid,
        violations=violations,
        warnings=warnings,
        suggestions=suggestions,
        score=score,
    )


def check_brand_voice(content: str) -> list[str]:
    """Check content against brand voice constraints.

    Args:
        content: The content to check

    Returns:
        List of brand voice violations
    """
    violations: list[str] = []

    # Load brand voice constraints
    brand_voice = load_constraints("BrandVoice")

    # Check forbidden phrases
    forbidden_categories = brand_voice.get("forbidden_phrases", {})
    content_lower = content.lower()

    for category, phrases in forbidden_categories.items():
        for phrase in phrases:
            if phrase.lower() in content_lower:
                violations.append(
                    f"Forbidden phrase '{phrase}' (category: {category})"
                )

    # Check for red flags
    validation_flags = brand_voice.get("validation_flags", {})
    red_flags = validation_flags.get("red_flags", [])

    for flag in red_flags:
        flag_text = flag.lower()
        if flag_text in content_lower:
            violations.append(f"Red flag detected: '{flag}'")

    return violations


def select_framework(pillar: str, context: dict[str, Any] | None = None) -> str:
    """Select appropriate framework based on content pillar and context.

    Args:
        pillar: Content pillar (what_building, what_learning, sales_tech, problem_solution)
        context: Optional context data to inform selection

    Returns:
        Framework name (STF, MRS, SLA, or PIF)
    """
    # Default framework mappings based on pillar
    framework_map = {
        "what_building": "STF",  # Problem/Tried/Worked/Lesson works well for builds
        "what_learning": "MRS",  # Mistake/Realization/Shift fits learning journey
        "sales_tech": "STF",  # Sales stories benefit from STF structure
        "problem_solution": "STF",  # Problem-solving maps naturally to STF
    }

    # Get default framework for pillar
    framework = framework_map.get(pillar, "STF")

    # Context can override default (e.g., if context suggests interactive content, use PIF)
    if context:
        # If context mentions poll/question/engagement, suggest PIF
        context_str = str(context).lower()
        if any(
            keyword in context_str
            for keyword in ["poll", "question", "ask", "vote", "opinion"]
        ):
            framework = "PIF"

        # If context suggests vulnerability/mistake, suggest MRS
        if any(
            keyword in context_str
            for keyword in ["mistake", "failed", "learned", "realized", "wrong"]
        ):
            framework = "MRS"

    return framework


def execute_workflow(
    workflow_name: str, inputs: dict[str, Any]
) -> WorkflowResult:
    """Execute a multi-step workflow blueprint.

    This function loads a workflow YAML, executes each step sequentially,
    and passes outputs from step N as inputs to step N+1.

    Args:
        workflow_name: Name of workflow to execute (e.g., "SundayPowerHour")
        inputs: Initial inputs for the workflow (passed to first step)

    Returns:
        WorkflowResult with final outputs, success status, and execution metadata

    Example:
        >>> inputs = {"session_history": [...], "projects": [...]}
        >>> result = execute_workflow("SundayPowerHour", inputs)
        >>> if result.success:
        >>>     print(f"Generated {len(result.outputs['content_plans'])} plans")
    """
    errors: list[str] = []
    steps_completed = 0

    # Load workflow blueprint
    try:
        workflow = load_workflow(workflow_name)
    except Exception as e:
        return WorkflowResult(
            workflow_name=workflow_name,
            success=False,
            outputs={},
            steps_completed=0,
            total_steps=0,
            errors=[f"Failed to load workflow: {str(e)}"],
        )

    steps = workflow.get("steps", [])
    total_steps = len(steps)

    # Execute steps sequentially
    step_outputs: dict[str, Any] = inputs.copy()

    for i, step in enumerate(steps):
        step_id = step.get("id", f"step_{i}")
        step_name = step.get("name", f"Step {i + 1}")

        try:
            # For now, we're creating a placeholder execution model
            # In a real implementation, this would:
            # 1. Render the prompt template with current step_outputs
            # 2. Call LLM with the rendered prompt
            # 3. Parse LLM response into structured outputs
            # 4. Add outputs to step_outputs for next step

            # Placeholder: Mark step as executed
            step_outputs[f"{step_id}_executed"] = True
            step_outputs[f"{step_id}_name"] = step_name

            steps_completed += 1

        except Exception as e:
            errors.append(f"Step {step_id} ({step_name}) failed: {str(e)}")
            # Don't break - continue to next step
            # This allows partial workflow execution

    # Determine success
    success = steps_completed == total_steps and len(errors) == 0

    return WorkflowResult(
        workflow_name=workflow_name,
        success=success,
        outputs=step_outputs,
        steps_completed=steps_completed,
        total_steps=total_steps,
        errors=errors,
    )
