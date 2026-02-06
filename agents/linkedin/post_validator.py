"""Comprehensive post validation for LinkedIn content.

This module provides validation against all constraints: framework structure,
brand voice guidelines, and platform-specific rules.
"""

from dataclasses import dataclass
from enum import Enum

from lib.blueprint_loader import load_constraints, load_framework
from lib.database import Post


class Severity(str, Enum):
    """Validation severity levels."""

    ERROR = "error"  # Must fix before posting
    WARNING = "warning"  # Should fix, but not blocking
    SUGGESTION = "suggestion"  # Optional improvement


@dataclass
class Violation:
    """A single validation violation."""

    severity: Severity
    category: str  # e.g., "character_length", "brand_voice", "platform_rules"
    message: str
    suggestion: str | None = None  # How to fix it


@dataclass
class ValidationReport:
    """Comprehensive validation report for a post."""

    post_id: int
    is_valid: bool  # True if no ERROR-level violations
    score: float  # 0.0 to 1.0
    violations: list[Violation]

    @property
    def errors(self) -> list[Violation]:
        """Get only ERROR-level violations."""
        return [v for v in self.violations if v.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Violation]:
        """Get only WARNING-level violations."""
        return [v for v in self.violations if v.severity == Severity.WARNING]

    @property
    def suggestions(self) -> list[Violation]:
        """Get only SUGGESTION-level violations."""
        return [v for v in self.violations if v.severity == Severity.SUGGESTION]


def validate_post(post: Post, framework: str = "STF") -> ValidationReport:
    """Validate a post against all constraints.

    This function performs comprehensive validation:
    1. Framework structure (character limits, section requirements)
    2. Brand voice (forbidden phrases, style guidelines)
    3. Platform rules (LinkedIn-specific formatting and limits)

    Args:
        post: The Post object to validate
        framework: Framework to validate against (default: STF)

    Returns:
        ValidationReport with all violations categorized by severity

    Example:
        >>> report = validate_post(post, framework="STF")
        >>> if not report.is_valid:
        ...     for error in report.errors:
        ...         print(f"ERROR: {error.message}")
        >>> print(f"Validation score: {report.score:.2f}")
    """
    violations: list[Violation] = []

    # 1. Validate framework structure
    violations.extend(_validate_framework_structure(post.content, framework))  # type: ignore[arg-type]

    # 2. Validate brand voice
    violations.extend(_validate_brand_voice(post.content))  # type: ignore[arg-type]

    # 3. Validate platform rules (LinkedIn)
    violations.extend(_validate_platform_rules(post.content, "linkedin"))  # type: ignore[arg-type]

    # Calculate score
    score = _calculate_score(violations)

    # Determine validity (no ERROR-level violations)
    is_valid = all(v.severity != Severity.ERROR for v in violations)

    return ValidationReport(
        post_id=post.id,  # type: ignore[arg-type]
        is_valid=is_valid,
        score=score,
        violations=violations,
    )


def _validate_framework_structure(content: str, framework_name: str) -> list[Violation]:
    """Validate content against framework structure requirements.

    Args:
        content: Post content to validate
        framework_name: Framework name (STF, MRS, SLA, PIF)

    Returns:
        List of violations related to framework structure
    """
    violations: list[Violation] = []

    # Load framework blueprint
    framework = load_framework(framework_name, "linkedin")
    validation_rules = framework.get("validation", {})

    # Check character length
    min_chars = validation_rules.get("min_chars", 0)
    max_chars = validation_rules.get("max_chars", 3000)
    content_length = len(content)

    if content_length < min_chars:
        violations.append(
            Violation(
                severity=Severity.ERROR,
                category="character_length",
                message=f"Content too short: {content_length} chars (minimum: {min_chars})",
                suggestion=f"Add approximately {min_chars - content_length} more characters to meet minimum length",
            )
        )
    elif content_length > max_chars:
        violations.append(
            Violation(
                severity=Severity.ERROR,
                category="character_length",
                message=f"Content too long: {content_length} chars (maximum: {max_chars})",
                suggestion=f"Remove approximately {content_length - max_chars} characters",
            )
        )

    # Check section count (if specified)
    min_sections = validation_rules.get("min_sections", 0)
    if min_sections > 0:
        # Count sections by double line breaks (common pattern)
        sections = [s.strip() for s in content.split("\n\n") if s.strip()]
        section_count = len(sections)

        if section_count < min_sections:
            violations.append(
                Violation(
                    severity=Severity.WARNING,
                    category="structure",
                    message=f"Expected {min_sections} sections, found {section_count}",
                    suggestion=f"Consider structuring content with {min_sections} distinct sections using double line breaks",
                )
            )

    return violations


def _validate_brand_voice(content: str) -> list[Violation]:
    """Validate content against brand voice constraints.

    Args:
        content: Post content to validate

    Returns:
        List of violations related to brand voice
    """
    violations: list[Violation] = []

    # Load brand voice constraints
    brand_voice = load_constraints("BrandVoice")

    # Check forbidden phrases
    forbidden_categories = brand_voice.get("forbidden_phrases", {})
    content_lower = content.lower()

    for category, phrases in forbidden_categories.items():
        for phrase in phrases:
            if phrase.lower() in content_lower:
                violations.append(
                    Violation(
                        severity=Severity.ERROR,
                        category="brand_voice",
                        message=f"Forbidden phrase detected: '{phrase}' (type: {category})",
                        suggestion=f"Remove or rephrase this {category.replace('_', ' ')} expression",
                    )
                )

    # Check validation flags
    validation_flags = brand_voice.get("validation_flags", {})

    # Red flags (ERROR)
    red_flags = validation_flags.get("red_flags", [])
    for flag in red_flags:
        if flag.lower() in content_lower:
            violations.append(
                Violation(
                    severity=Severity.ERROR,
                    category="brand_voice",
                    message=f"Red flag detected: '{flag}'",
                    suggestion="Rewrite this section to be more specific and authentic",
                )
            )

    # Yellow flags (WARNING)
    yellow_flags = validation_flags.get("yellow_flags", [])
    for flag in yellow_flags:
        if flag.lower() in content_lower:
            violations.append(
                Violation(
                    severity=Severity.WARNING,
                    category="brand_voice",
                    message=f"Yellow flag detected: '{flag}'",
                    suggestion="Consider rewording for more authenticity",
                )
            )

    # Check style guidelines
    style_rules = brand_voice.get("style_rules", {})

    # Check narrative voice (should use "I" for first-person)
    narrative_voice_rules = style_rules.get("narrative_voice", [])
    if any("first-person" in str(rule).lower() for rule in narrative_voice_rules):
        # Simple heuristic: check for first-person pronouns
        first_person_words = ["i ", "i'm", "i've", "my ", "mine "]
        has_first_person = any(word in content_lower for word in first_person_words)

        if not has_first_person:
            violations.append(
                Violation(
                    severity=Severity.WARNING,
                    category="brand_voice",
                    message="Content lacks first-person perspective",
                    suggestion="Use 'I', 'my', or 'I'm' to add personal authenticity",
                )
            )

    return violations


def _validate_platform_rules(content: str, platform: str) -> list[Violation]:
    """Validate content against platform-specific rules.

    Args:
        content: Post content to validate
        platform: Platform name (e.g., "linkedin")

    Returns:
        List of violations related to platform rules
    """
    violations: list[Violation] = []

    # Load platform rules
    platform_rules = load_constraints("PlatformRules")
    platform_config = platform_rules.get(platform, {})

    if not platform_config:
        return violations  # Platform not configured

    # Character limits
    char_limits = platform_config.get("character_limits", {})
    content_length = len(content)

    optimal_min = char_limits.get("optimal_min", 0)
    optimal_max = char_limits.get("optimal_max", 0)
    absolute_max = char_limits.get("absolute_max", 3000)

    if optimal_min > 0 and content_length < optimal_min:
        violations.append(
            Violation(
                severity=Severity.SUGGESTION,
                category="platform_rules",
                message=f"Content below optimal length: {content_length} chars (optimal: {optimal_min}-{optimal_max})",
                suggestion=f"Consider expanding by {optimal_min - content_length} characters for better engagement",
            )
        )
    elif optimal_max > 0 and content_length > optimal_max:
        violations.append(
            Violation(
                severity=Severity.WARNING,
                category="platform_rules",
                message=f"Content exceeds optimal length: {content_length} chars (optimal: {optimal_min}-{optimal_max})",
                suggestion=f"Consider condensing by {content_length - optimal_max} characters for better readability",
            )
        )

    if content_length > absolute_max:
        violations.append(
            Violation(
                severity=Severity.ERROR,
                category="platform_rules",
                message=f"Content exceeds platform maximum: {content_length} chars (max: {absolute_max})",
                suggestion=f"Remove {content_length - absolute_max} characters to meet platform limits",
            )
        )

    # Formatting rules
    formatting = platform_config.get("formatting_rules", {})

    # Check line breaks
    line_break_rules = formatting.get("line_breaks", {})
    if line_break_rules.get("required", False):
        # Check for reasonable paragraph breaks
        has_breaks = "\n\n" in content or "\n" in content
        if not has_breaks:
            violations.append(
                Violation(
                    severity=Severity.WARNING,
                    category="platform_rules",
                    message="Content lacks line breaks for readability",
                    suggestion="Add line breaks to separate ideas and improve scannability",
                )
            )

    # Check emoji usage
    emoji_rules = formatting.get("emojis", {})
    max_emojis = emoji_rules.get("max_recommended", 3)

    # Simple emoji detection (counts Unicode emoji ranges)
    emoji_count = sum(1 for char in content if ord(char) > 0x1F300)

    if emoji_count > max_emojis:
        violations.append(
            Violation(
                severity=Severity.WARNING,
                category="platform_rules",
                message=f"Too many emojis: {emoji_count} (recommended max: {max_emojis})",
                suggestion=f"Remove {emoji_count - max_emojis} emojis for professional tone",
            )
        )

    # Check hashtags
    hashtag_rules = formatting.get("hashtags", {})
    max_hashtags = hashtag_rules.get("max_recommended", 5)

    hashtag_count = content.count("#")

    if hashtag_count > max_hashtags:
        violations.append(
            Violation(
                severity=Severity.WARNING,
                category="platform_rules",
                message=f"Too many hashtags: {hashtag_count} (recommended max: {max_hashtags})",
                suggestion=f"Remove {hashtag_count - max_hashtags} hashtags to avoid looking spammy",
            )
        )

    # Check red flags
    red_flags = platform_config.get("red_flags", [])

    for flag in red_flags:
        flag_lower = flag.lower()

        # Special checks for specific red flags
        if "wall" in flag_lower and "text" in flag_lower:
            # Check for lack of paragraphs (> 300 chars without break)
            paragraphs = content.split("\n\n")
            has_wall = any(len(p) > 300 for p in paragraphs)
            if has_wall:
                violations.append(
                    Violation(
                        severity=Severity.WARNING,
                        category="platform_rules",
                        message="Contains wall of text (paragraph > 300 chars)",
                        suggestion="Break long paragraphs into smaller chunks",
                    )
                )

        elif "all caps" in flag_lower:
            # Check for excessive caps (> 20% of words)
            words = content.split()
            caps_words = [w for w in words if w.isupper() and len(w) > 1]
            if len(words) > 0 and len(caps_words) / len(words) > 0.2:
                violations.append(
                    Violation(
                        severity=Severity.WARNING,
                        category="platform_rules",
                        message=f"Excessive capitalization: {len(caps_words)} all-caps words",
                        suggestion="Use normal capitalization for professional tone",
                    )
                )

    return violations


def _calculate_score(violations: list[Violation]) -> float:
    """Calculate validation score from violations.

    Score calculation:
    - Start at 1.0 (perfect)
    - ERROR: -0.20 per violation
    - WARNING: -0.05 per violation
    - SUGGESTION: -0.02 per violation

    Args:
        violations: List of all violations

    Returns:
        Score between 0.0 and 1.0
    """
    error_count = sum(1 for v in violations if v.severity == Severity.ERROR)
    warning_count = sum(1 for v in violations if v.severity == Severity.WARNING)
    suggestion_count = sum(1 for v in violations if v.severity == Severity.SUGGESTION)

    score = 1.0 - (error_count * 0.20) - (warning_count * 0.05) - (suggestion_count * 0.02)

    return max(0.0, score)  # Clamp to 0.0 minimum
