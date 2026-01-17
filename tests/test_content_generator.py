"""Tests for content_generator."""

from unittest.mock import MagicMock, patch

import pytest

from agents.linkedin.content_generator import (
    GenerationResult,
    _prepare_template_context,
    generate_post,
)
from lib.blueprint_loader import load_constraints, load_framework
from lib.errors import AIError


@pytest.fixture
def sample_context() -> dict:
    """Sample context for testing."""
    return {
        "themes": ["Built blueprint system", "Added validation"],
        "decisions": ["Use YAML for blueprints"],
        "progress": ["Completed 13 user stories"],
    }


@pytest.fixture
def valid_post_content() -> str:
    """Valid post content that passes validation."""
    return "A" * 800  # Meets STF min_chars requirement


def test_generate_post_auto_selects_framework(sample_context: dict) -> None:
    """Test that generate_post auto-selects framework when not specified."""
    with patch("agents.linkedin.content_generator.OllamaClient") as mock_ollama:
        # Mock LLM response with valid content
        mock_client = MagicMock()
        mock_client.generate_content_ideas.return_value = "A" * 800
        mock_ollama.return_value = mock_client

        result = generate_post(
            context=sample_context, pillar="what_building", framework=None
        )

        # Should auto-select STF for what_building
        assert result.framework_used == "STF"


def test_generate_post_uses_specified_framework(sample_context: dict) -> None:
    """Test that generate_post uses specified framework."""
    with patch("agents.linkedin.content_generator.OllamaClient") as mock_ollama:
        mock_client = MagicMock()
        mock_client.generate_content_ideas.return_value = "A" * 700  # Valid for MRS
        mock_ollama.return_value = mock_client

        result = generate_post(
            context=sample_context, pillar="what_learning", framework="MRS"
        )

        assert result.framework_used == "MRS"


def test_generate_post_returns_valid_content(
    sample_context: dict, valid_post_content: str
) -> None:
    """Test that generate_post returns valid content on first try."""
    with patch("agents.linkedin.content_generator.OllamaClient") as mock_ollama:
        mock_client = MagicMock()
        mock_client.generate_content_ideas.return_value = valid_post_content
        mock_ollama.return_value = mock_client

        result = generate_post(
            context=sample_context, pillar="what_building", framework="STF"
        )

        assert result.is_valid is True
        assert result.content == valid_post_content
        assert result.validation_score == 1.0
        assert result.iterations == 1
        assert len(result.violations) == 0


def test_generate_post_retries_on_invalid_content(sample_context: dict) -> None:
    """Test that generate_post retries when content is invalid."""
    with patch("agents.linkedin.content_generator.OllamaClient") as mock_ollama:
        mock_client = MagicMock()

        # First attempt: too short, second attempt: valid
        mock_client.generate_content_ideas.side_effect = [
            "Too short",  # Invalid
            "A" * 800,  # Valid
        ]
        mock_ollama.return_value = mock_client

        result = generate_post(
            context=sample_context,
            pillar="what_building",
            framework="STF",
            max_iterations=3,
        )

        assert result.is_valid is True
        assert result.iterations == 2
        assert mock_client.generate_content_ideas.call_count == 2


def test_generate_post_returns_best_attempt_after_max_iterations(
    sample_context: dict,
) -> None:
    """Test that generate_post returns best attempt if never valid."""
    with patch("agents.linkedin.content_generator.OllamaClient") as mock_ollama:
        mock_client = MagicMock()

        # All attempts invalid, but second is better
        mock_client.generate_content_ideas.side_effect = [
            "Too short",  # Score ~0.8
            "A" * 500,  # Score ~0.8 but closer to valid range
            "Still short",  # Score ~0.8
        ]
        mock_ollama.return_value = mock_client

        result = generate_post(
            context=sample_context,
            pillar="what_building",
            framework="STF",
            max_iterations=3,
        )

        # Should return best attempt
        assert result.is_valid is False
        assert result.iterations == 3
        assert len(result.violations) > 0
        assert result.validation_score > 0.0


def test_generate_post_raises_ai_error_on_first_failure(sample_context: dict) -> None:
    """Test that generate_post raises AIError if first attempt fails."""
    with patch("agents.linkedin.content_generator.OllamaClient") as mock_ollama:
        mock_client = MagicMock()
        mock_client.generate_content_ideas.side_effect = AIError("Connection failed")
        mock_ollama.return_value = mock_client

        with pytest.raises(AIError, match="Connection failed"):
            generate_post(context=sample_context, pillar="what_building", framework="STF")


def test_generate_post_handles_refinement_failure(sample_context: dict) -> None:
    """Test that generate_post handles refinement failure gracefully."""
    with patch("agents.linkedin.content_generator.OllamaClient") as mock_ollama:
        mock_client = MagicMock()

        # First attempt succeeds but invalid, second fails
        mock_client.generate_content_ideas.side_effect = [
            "A" * 500,  # Invalid but okay
            AIError("Connection lost"),  # Refinement fails
        ]
        mock_ollama.return_value = mock_client

        result = generate_post(
            context=sample_context,
            pillar="what_building",
            framework="STF",
            max_iterations=3,
        )

        # Should return first attempt's content
        assert result.content == "A" * 500
        assert result.is_valid is False


def test_generate_post_with_pif_framework(sample_context: dict) -> None:
    """Test generate_post with PIF framework."""
    with patch("agents.linkedin.content_generator.OllamaClient") as mock_ollama:
        mock_client = MagicMock()
        mock_client.generate_content_ideas.return_value = "A" * 400  # Valid for PIF
        mock_ollama.return_value = mock_client

        result = generate_post(
            context=sample_context, pillar="what_building", framework="PIF"
        )

        assert result.framework_used == "PIF"
        assert result.is_valid is True


def test_generate_post_with_custom_model(sample_context: dict) -> None:
    """Test generate_post with custom model."""
    with patch("agents.linkedin.content_generator.OllamaClient") as mock_ollama:
        mock_client = MagicMock()
        mock_client.generate_content_ideas.return_value = "A" * 800
        mock_ollama.return_value = mock_client

        generate_post(
            context=sample_context,
            pillar="what_building",
            framework="STF",
            model="custom-model",
        )

        # Verify custom model was passed to OllamaClient
        mock_ollama.assert_called_once_with(model="custom-model")


def test_prepare_template_context() -> None:
    """Test _prepare_template_context prepares data correctly."""
    context: dict = {
        "themes": ["Theme 1"],
        "decisions": ["Decision 1"],
        "progress": ["Progress 1"],
    }
    framework = load_framework("STF", "linkedin")
    brand_voice = load_constraints("BrandVoice")
    pillars = load_constraints("ContentPillars")

    result = _prepare_template_context(
        context, "what_building", framework, brand_voice, pillars
    )

    # Check context section
    assert result["context"]["themes"] == ["Theme 1"]
    assert result["context"]["decisions"] == ["Decision 1"]
    assert result["context"]["progress"] == ["Progress 1"]

    # Check pillar section
    assert result["pillar_name"] == "What I'm Building"
    assert "pillar_description" in result

    # Check framework section
    assert result["framework_name"] == "STF"
    assert len(result["framework_sections"]) == 4  # STF has 4 sections

    # Check brand voice section
    assert len(result["brand_voice_characteristics"]) > 0
    assert len(result["forbidden_phrases"]) > 0
    assert len(result["brand_voice_style"]) > 0

    # Check validation section
    assert result["validation_min_chars"] == 600
    assert result["validation_max_chars"] == 1500
    assert result["validation_min_sections"] == 4


def test_prepare_template_context_limits_forbidden_phrases() -> None:
    """Test that _prepare_template_context limits forbidden phrases."""
    context: dict = {"themes": [], "decisions": [], "progress": []}
    framework = load_framework("STF", "linkedin")
    brand_voice = load_constraints("BrandVoice")
    pillars = load_constraints("ContentPillars")

    result = _prepare_template_context(
        context, "what_building", framework, brand_voice, pillars
    )

    # Should limit to 15 forbidden phrases
    assert len(result["forbidden_phrases"]) <= 15


def test_prepare_template_context_with_empty_context() -> None:
    """Test _prepare_template_context handles empty context."""
    context: dict = {}  # Empty context
    framework = load_framework("STF", "linkedin")
    brand_voice = load_constraints("BrandVoice")
    pillars = load_constraints("ContentPillars")

    result = _prepare_template_context(
        context, "what_building", framework, brand_voice, pillars
    )

    # Should handle empty context gracefully
    assert result["context"]["themes"] == []
    assert result["context"]["decisions"] == []
    assert result["context"]["progress"] == []


def test_generation_result_dataclass() -> None:
    """Test GenerationResult dataclass structure."""
    result = GenerationResult(
        content="Test content",
        framework_used="STF",
        validation_score=0.95,
        is_valid=True,
        iterations=2,
        violations=[],
    )

    assert result.content == "Test content"
    assert result.framework_used == "STF"
    assert result.validation_score == 0.95
    assert result.is_valid is True
    assert result.iterations == 2
    assert result.violations == []
