"""Tests for blueprints CLI commands."""

from pathlib import Path
import pytest
from click.testing import CliRunner
from cli import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


def test_blueprints_list_empty(runner: CliRunner) -> None:
    """Test blueprints list command when no blueprints exist."""
    result = runner.invoke(cli, ["blueprints", "list"])

    assert result.exit_code == 0
    assert "Available Blueprints" in result.output
    assert "FRAMEWORKS" in result.output
    assert "WORKFLOWS" in result.output
    assert "CONSTRAINTS" in result.output


def test_blueprints_list_with_category(runner: CliRunner) -> None:
    """Test blueprints list command with category filter."""
    result = runner.invoke(cli, ["blueprints", "list", "--category", "frameworks"])

    assert result.exit_code == 0
    assert "Available Blueprints" in result.output


def test_blueprints_list_with_yaml_files(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test blueprints list command with actual YAML files."""
    # Create mock blueprints directory
    blueprints_dir = tmp_path / "blueprints"
    (blueprints_dir / "frameworks" / "linkedin").mkdir(parents=True)
    (blueprints_dir / "workflows").mkdir(parents=True)
    (blueprints_dir / "constraints").mkdir(parents=True)

    # Create sample YAML files
    (blueprints_dir / "frameworks" / "linkedin" / "STF.yaml").write_text("name: STF")
    (blueprints_dir / "workflows" / "SundayPowerHour.yaml").write_text("name: SPH")
    (blueprints_dir / "constraints" / "BrandVoice.yaml").write_text("name: BV")

    # Mock the blueprints directory
    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: blueprints_dir)

    result = runner.invoke(cli, ["blueprints", "list"])

    assert result.exit_code == 0
    assert "STF" in result.output
    assert "SundayPowerHour" in result.output
    assert "BrandVoice" in result.output


def test_blueprints_help(runner: CliRunner) -> None:
    """Test blueprints help command."""
    result = runner.invoke(cli, ["blueprints", "--help"])

    assert result.exit_code == 0
    assert "Manage content blueprints" in result.output
    assert "list" in result.output
