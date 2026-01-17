"""Tests for template renderer."""

from pathlib import Path
import pytest
from lib.template_renderer import (
    render_template,
    render_template_string,
    get_templates_dir,
)


@pytest.fixture
def mock_templates_dir(tmp_path: Path) -> Path:
    """Create a mock templates directory for testing."""
    templates_dir = tmp_path / "blueprints" / "templates"
    templates_dir.mkdir(parents=True)

    # Create sample template
    simple_template = templates_dir / "Simple.hbs"
    simple_template.write_text("Hello, {{name}}!")

    # Create more complex template
    complex_template = templates_dir / "LinkedInPost.hbs"
    complex_template.write_text("""You are a content writer for LinkedIn.

Context:
{{context}}

Framework: {{framework}}
Pillar: {{pillar}}

Brand Voice Guidelines:
{{#brandVoice}}
- {{.}}
{{/brandVoice}}

Generate a LinkedIn post following the framework and brand voice.""")

    return templates_dir


def test_get_templates_dir() -> None:
    """Test getting templates directory path."""
    templates_dir = get_templates_dir()
    assert templates_dir.name == "templates"
    assert templates_dir.parent.name == "blueprints"


def test_render_template_simple(monkeypatch: pytest.MonkeyPatch, mock_templates_dir: Path) -> None:
    """Test rendering a simple template."""
    monkeypatch.setattr("lib.template_renderer.get_templates_dir", lambda: mock_templates_dir)

    context = {"name": "Austin"}
    result = render_template("Simple.hbs", context)

    assert result == "Hello, Austin!"


def test_render_template_complex(monkeypatch: pytest.MonkeyPatch, mock_templates_dir: Path) -> None:
    """Test rendering a complex template with loops."""
    monkeypatch.setattr("lib.template_renderer.get_templates_dir", lambda: mock_templates_dir)

    context = {
        "context": "Built a content engine today",
        "framework": "STF",
        "pillar": "what_building",
        "brandVoice": ["technical but accessible", "authentic", "confident"]
    }

    result = render_template("LinkedInPost.hbs", context)

    # Check that all values were substituted
    assert "Built a content engine today" in result
    assert "STF" in result
    assert "what_building" in result
    assert "technical but accessible" in result
    assert "authentic" in result
    assert "confident" in result


def test_render_template_not_found(monkeypatch: pytest.MonkeyPatch, mock_templates_dir: Path) -> None:
    """Test rendering a template that doesn't exist."""
    monkeypatch.setattr("lib.template_renderer.get_templates_dir", lambda: mock_templates_dir)

    with pytest.raises(FileNotFoundError, match="Template not found"):
        render_template("NonExistent.hbs", {})


def test_render_template_missing_variable(
    monkeypatch: pytest.MonkeyPatch, mock_templates_dir: Path
) -> None:
    """Test rendering template with missing variable (should render empty string)."""
    monkeypatch.setattr("lib.template_renderer.get_templates_dir", lambda: mock_templates_dir)

    # Chevron renders missing variables as empty strings
    context: dict[str, str] = {}  # Missing 'name'
    result = render_template("Simple.hbs", context)

    assert result == "Hello, !"


def test_render_template_string_simple() -> None:
    """Test rendering a template string directly."""
    template = "Hello, {{name}}!"
    context = {"name": "Austin"}

    result = render_template_string(template, context)

    assert result == "Hello, Austin!"


def test_render_template_string_with_conditionals() -> None:
    """Test rendering template string with conditionals."""
    template = """{{#premium}}Premium User{{/premium}}{{^premium}}Free User{{/premium}}"""

    # Test with premium = true
    result1 = render_template_string(template, {"premium": True})
    assert "Premium User" in result1

    # Test with premium = false
    result2 = render_template_string(template, {"premium": False})
    assert "Free User" in result2


def test_render_template_string_with_loop() -> None:
    """Test rendering template string with loops."""
    template = """Items:
{{#items}}
- {{.}}
{{/items}}"""

    context = {"items": ["apple", "banana", "orange"]}
    result = render_template_string(template, context)

    assert "apple" in result
    assert "banana" in result
    assert "orange" in result


def test_render_template_string_nested_objects() -> None:
    """Test rendering template string with nested objects."""
    template = """User: {{user.name}}
Email: {{user.email}}
Role: {{user.role}}"""

    context = {
        "user": {
            "name": "Austin",
            "email": "austin@example.com",
            "role": "Engineer"
        }
    }

    result = render_template_string(template, context)

    assert "Austin" in result
    assert "austin@example.com" in result
    assert "Engineer" in result


def test_render_template_with_special_characters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test rendering template with special characters."""
    templates_dir = tmp_path / "blueprints" / "templates"
    templates_dir.mkdir(parents=True)

    template_path = templates_dir / "Special.hbs"
    template_path.write_text("Message: {{message}}")

    monkeypatch.setattr("lib.template_renderer.get_templates_dir", lambda: templates_dir)

    context = {"message": "Hello & <World>! 'Quotes' \"Double\""}
    result = render_template("Special.hbs", context)

    # Chevron escapes HTML entities by default
    assert "&amp;" in result
    assert "&lt;World&gt;" in result
    assert "'Quotes'" in result  # Single quotes not escaped
    assert "&quot;Double&quot;" in result


def test_render_template_empty_context(
    monkeypatch: pytest.MonkeyPatch, mock_templates_dir: Path
) -> None:
    """Test rendering template with empty context."""
    monkeypatch.setattr("lib.template_renderer.get_templates_dir", lambda: mock_templates_dir)

    result = render_template("Simple.hbs", {})

    # Missing variable renders as empty string
    assert result == "Hello, !"


def test_render_template_unicode_support() -> None:
    """Test rendering template with unicode characters."""
    template = "Greeting: {{greeting}}"
    context = {"greeting": "こんにちは 世界"}

    result = render_template_string(template, context)

    assert "こんにちは 世界" in result
