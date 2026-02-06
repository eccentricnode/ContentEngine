"""Tests for blueprint directory structure."""

from pathlib import Path


def test_blueprint_directories_exist() -> None:
    """Test that all required blueprint directories exist."""
    base_path = Path(__file__).parent.parent / "blueprints"

    # Check main directory
    assert base_path.exists(), "blueprints/ directory should exist"

    # Check subdirectories
    expected_dirs = [
        "frameworks",
        "frameworks/linkedin",
        "workflows",
        "constraints",
        "templates",
    ]

    for dir_path in expected_dirs:
        full_path = base_path / dir_path
        assert full_path.exists(), f"{dir_path}/ should exist"
        assert full_path.is_dir(), f"{dir_path}/ should be a directory"


def test_blueprint_readme_exists() -> None:
    """Test that blueprint README exists and is not empty."""
    readme_path = Path(__file__).parent.parent / "blueprints" / "README.md"

    assert readme_path.exists(), "blueprints/README.md should exist"
    assert readme_path.stat().st_size > 0, "README should not be empty"

    # Check that it contains key sections
    content = readme_path.read_text()
    assert "Directory Structure" in content
    assert "Blueprint Types" in content
    assert "Usage" in content
