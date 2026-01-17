"""Tests for blueprint_engine validation and framework selection."""

from lib.blueprint_engine import check_brand_voice, select_framework, validate_content


def test_validate_content_valid_stf() -> None:
    """Test validation passes for valid STF content."""
    content = "A" * 800  # Valid length for STF (600-1500)
    result = validate_content(content, "STF", "linkedin")

    assert result.is_valid is True
    assert len(result.violations) == 0
    assert result.score == 1.0


def test_validate_content_too_short() -> None:
    """Test validation fails for content that's too short."""
    content = "Too short"  # Less than 600 chars for STF
    result = validate_content(content, "STF", "linkedin")

    assert result.is_valid is False
    assert any("too short" in v.lower() for v in result.violations)
    assert result.score < 1.0


def test_validate_content_too_long() -> None:
    """Test validation fails for content that's too long."""
    content = "A" * 2000  # More than 1500 chars for STF
    result = validate_content(content, "STF", "linkedin")

    assert result.is_valid is False
    assert any("too long" in v.lower() for v in result.violations)
    assert result.score < 1.0


def test_validate_content_with_forbidden_phrase() -> None:
    """Test validation detects forbidden phrases from brand voice."""
    content = (
        "We need to disrupt the market with our solution. " + "A" * 600
    )  # Add padding to meet min chars
    result = validate_content(content, "STF", "linkedin")

    assert result.is_valid is False
    assert any("forbidden phrase" in v.lower() for v in result.violations)
    assert result.score < 1.0


def test_validate_content_mrs_framework() -> None:
    """Test validation works with MRS framework."""
    content = "A" * 700  # Valid length for MRS (500-1300)
    result = validate_content(content, "MRS", "linkedin")

    assert result.is_valid is True
    assert len(result.violations) == 0


def test_validate_content_sla_framework() -> None:
    """Test validation works with SLA framework."""
    content = "A" * 600  # Valid length for SLA (500-1400)
    result = validate_content(content, "SLA", "linkedin")

    assert result.is_valid is True
    assert len(result.violations) == 0


def test_validate_content_pif_framework() -> None:
    """Test validation works with PIF framework."""
    content = "A" * 400  # Valid length for PIF (300-1000)
    result = validate_content(content, "PIF", "linkedin")

    assert result.is_valid is True
    assert len(result.violations) == 0


def test_validate_content_score_calculation() -> None:
    """Test that score decreases with violations."""
    # Valid content
    valid_content = "A" * 800
    valid_result = validate_content(valid_content, "STF", "linkedin")
    assert valid_result.score == 1.0

    # Content with violation (too short)
    invalid_content = "Too short"
    invalid_result = validate_content(invalid_content, "STF", "linkedin")
    assert invalid_result.score < 1.0


def test_validate_content_suggestions() -> None:
    """Test that suggestions are provided for invalid content."""
    content = "Too short"  # Less than min chars
    result = validate_content(content, "STF", "linkedin")

    assert len(result.suggestions) > 0
    assert any("expand" in s.lower() for s in result.suggestions)


def test_check_brand_voice_no_violations() -> None:
    """Test brand voice check passes for clean content."""
    content = "Built a new feature for the Content Engine using Python and SQLAlchemy."
    violations = check_brand_voice(content)

    assert len(violations) == 0


def test_check_brand_voice_forbidden_phrase() -> None:
    """Test brand voice check detects forbidden phrases."""
    content = "We need to leverage synergies to maximize ROI."
    violations = check_brand_voice(content)

    assert len(violations) > 0
    assert any("leverage synergies" in v.lower() for v in violations)


def test_check_brand_voice_multiple_violations() -> None:
    """Test brand voice check detects multiple forbidden phrases."""
    content = "Let's leverage synergies and disrupt with our rise and grind mindset."
    violations = check_brand_voice(content)

    # Should catch: "leverage synergies", "disrupt", and "rise and grind"
    assert len(violations) >= 3


def test_check_brand_voice_case_insensitive() -> None:
    """Test brand voice check is case insensitive."""
    content = "LEVERAGE SYNERGIES to maximize value."
    violations = check_brand_voice(content)

    assert len(violations) > 0


def test_select_framework_what_building() -> None:
    """Test framework selection for what_building pillar."""
    framework = select_framework("what_building")
    assert framework == "STF"


def test_select_framework_what_learning() -> None:
    """Test framework selection for what_learning pillar."""
    framework = select_framework("what_learning")
    assert framework == "MRS"


def test_select_framework_sales_tech() -> None:
    """Test framework selection for sales_tech pillar."""
    framework = select_framework("sales_tech")
    assert framework == "STF"


def test_select_framework_problem_solution() -> None:
    """Test framework selection for problem_solution pillar."""
    framework = select_framework("problem_solution")
    assert framework == "STF"


def test_select_framework_with_poll_context() -> None:
    """Test framework selection overrides to PIF for poll-related context."""
    context = {"theme": "Should I use Python or Go for this project?", "type": "poll"}
    framework = select_framework("what_building", context)

    assert framework == "PIF"


def test_select_framework_with_mistake_context() -> None:
    """Test framework selection overrides to MRS for mistake-related context."""
    context = {"theme": "I made a mistake by not using type hints", "type": "learning"}
    framework = select_framework("what_building", context)

    assert framework == "MRS"


def test_select_framework_default_fallback() -> None:
    """Test framework selection falls back to STF for unknown pillar."""
    framework = select_framework("unknown_pillar")
    assert framework == "STF"


def test_select_framework_context_keywords() -> None:
    """Test framework selection detects various context keywords."""
    # PIF keywords
    poll_context = {"content": "What's your opinion on this?"}
    assert select_framework("what_building", poll_context) == "PIF"

    question_context = {"content": "Should we ask the community?"}
    assert select_framework("what_building", question_context) == "PIF"

    # MRS keywords
    failed_context = {"content": "I failed to implement this correctly"}
    assert select_framework("what_building", failed_context) == "MRS"

    learned_context = {"content": "I learned the hard way that..."}
    assert select_framework("what_building", learned_context) == "MRS"


def test_validation_result_dataclass() -> None:
    """Test ValidationResult dataclass structure."""
    result = validate_content("A" * 800, "STF", "linkedin")

    assert hasattr(result, "is_valid")
    assert hasattr(result, "violations")
    assert hasattr(result, "warnings")
    assert hasattr(result, "suggestions")
    assert hasattr(result, "score")

    assert isinstance(result.is_valid, bool)
    assert isinstance(result.violations, list)
    assert isinstance(result.warnings, list)
    assert isinstance(result.suggestions, list)
    assert isinstance(result.score, float)
    assert 0.0 <= result.score <= 1.0
