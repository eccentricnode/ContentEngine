"""Tests for blueprint loader."""

from pathlib import Path
import pytest
import yaml
from lib.blueprint_loader import (
    load_framework,
    load_workflow,
    load_constraints,
    clear_cache,
    list_blueprints,
    get_blueprints_dir,
)


@pytest.fixture
def mock_blueprints_dir(tmp_path: Path) -> Path:
    """Create a mock blueprints directory for testing."""
    blueprints_dir = tmp_path / "blueprints"

    # Create directory structure
    (blueprints_dir / "frameworks" / "linkedin").mkdir(parents=True)
    (blueprints_dir / "workflows").mkdir(parents=True)
    (blueprints_dir / "constraints").mkdir(parents=True)

    # Create sample framework
    framework_data = {
        "name": "STF",
        "platform": "linkedin",
        "description": "Storytelling Framework",
        "structure": {
            "sections": ["Problem", "Tried", "Worked", "Lesson"]
        },
        "validation": {
            "min_sections": 4,
            "min_chars": 600,
            "max_chars": 1500
        }
    }
    framework_path = blueprints_dir / "frameworks" / "linkedin" / "STF.yaml"
    with open(framework_path, 'w') as f:
        yaml.dump(framework_data, f)

    # Create sample workflow
    workflow_data = {
        "name": "SundayPowerHour",
        "type": "workflow",
        "description": "Weekly batch content creation",
        "steps": [
            {"name": "Context Mining", "duration": "20min"},
            {"name": "Pillar Categorization", "duration": "10min"}
        ]
    }
    workflow_path = blueprints_dir / "workflows" / "SundayPowerHour.yaml"
    with open(workflow_path, 'w') as f:
        yaml.dump(workflow_data, f)

    # Create sample constraint
    constraint_data = {
        "name": "BrandVoice",
        "type": "constraint",
        "characteristics": ["technical", "authentic", "confident"],
        "forbidden_phrases": ["leverage synergy", "disrupt the market"]
    }
    constraint_path = blueprints_dir / "constraints" / "BrandVoice.yaml"
    with open(constraint_path, 'w') as f:
        yaml.dump(constraint_data, f)

    return blueprints_dir


@pytest.fixture(autouse=True)
def clear_blueprint_cache() -> None:
    """Clear cache before each test."""
    clear_cache()


def test_get_blueprints_dir() -> None:
    """Test getting blueprints directory path."""
    blueprints_dir = get_blueprints_dir()
    assert blueprints_dir.exists()
    assert blueprints_dir.name == "blueprints"


def test_load_framework_success(monkeypatch: pytest.MonkeyPatch, mock_blueprints_dir: Path) -> None:
    """Test successfully loading a framework blueprint."""
    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: mock_blueprints_dir)

    framework = load_framework("STF")

    assert framework["name"] == "STF"
    assert framework["platform"] == "linkedin"
    assert "structure" in framework
    assert len(framework["structure"]["sections"]) == 4
    assert framework["validation"]["min_chars"] == 600


def test_load_framework_not_found(monkeypatch: pytest.MonkeyPatch, mock_blueprints_dir: Path) -> None:
    """Test loading a framework that doesn't exist."""
    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: mock_blueprints_dir)

    with pytest.raises(FileNotFoundError, match="Framework blueprint not found"):
        load_framework("NonExistent")


def test_load_framework_caching(monkeypatch: pytest.MonkeyPatch, mock_blueprints_dir: Path) -> None:
    """Test that frameworks are cached after first load."""
    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: mock_blueprints_dir)

    # Load framework first time
    load_framework("STF")

    # Modify the file
    framework_path = mock_blueprints_dir / "frameworks" / "linkedin" / "STF.yaml"
    with open(framework_path, 'w') as f:
        yaml.dump({"name": "MODIFIED"}, f)

    # Load framework second time - should get cached version
    framework2 = load_framework("STF", use_cache=True)
    assert framework2["name"] == "STF"  # Not "MODIFIED"

    # Load with cache disabled - should get new version
    framework3 = load_framework("STF", use_cache=False)
    assert framework3["name"] == "MODIFIED"


def test_load_workflow_success(monkeypatch: pytest.MonkeyPatch, mock_blueprints_dir: Path) -> None:
    """Test successfully loading a workflow blueprint."""
    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: mock_blueprints_dir)

    workflow = load_workflow("SundayPowerHour")

    assert workflow["name"] == "SundayPowerHour"
    assert workflow["type"] == "workflow"
    assert len(workflow["steps"]) == 2
    assert workflow["steps"][0]["name"] == "Context Mining"


def test_load_workflow_not_found(monkeypatch: pytest.MonkeyPatch, mock_blueprints_dir: Path) -> None:
    """Test loading a workflow that doesn't exist."""
    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: mock_blueprints_dir)

    with pytest.raises(FileNotFoundError, match="Workflow blueprint not found"):
        load_workflow("NonExistent")


def test_load_constraints_success(monkeypatch: pytest.MonkeyPatch, mock_blueprints_dir: Path) -> None:
    """Test successfully loading a constraint blueprint."""
    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: mock_blueprints_dir)

    constraint = load_constraints("BrandVoice")

    assert constraint["name"] == "BrandVoice"
    assert constraint["type"] == "constraint"
    assert "technical" in constraint["characteristics"]
    assert "leverage synergy" in constraint["forbidden_phrases"]


def test_load_constraints_not_found(monkeypatch: pytest.MonkeyPatch, mock_blueprints_dir: Path) -> None:
    """Test loading a constraint that doesn't exist."""
    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: mock_blueprints_dir)

    with pytest.raises(FileNotFoundError, match="Constraint blueprint not found"):
        load_constraints("NonExistent")


def test_clear_cache_all(monkeypatch: pytest.MonkeyPatch, mock_blueprints_dir: Path) -> None:
    """Test clearing entire cache."""
    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: mock_blueprints_dir)

    # Load some blueprints to populate cache
    load_framework("STF")
    load_workflow("SundayPowerHour")

    # Clear entire cache
    clear_cache()

    # Modify files
    framework_path = mock_blueprints_dir / "frameworks" / "linkedin" / "STF.yaml"
    with open(framework_path, 'w') as f:
        yaml.dump({"name": "CLEARED"}, f)

    # Load again - should get new version since cache was cleared
    framework = load_framework("STF")
    assert framework["name"] == "CLEARED"


def test_clear_cache_specific_key(monkeypatch: pytest.MonkeyPatch, mock_blueprints_dir: Path) -> None:
    """Test clearing specific cache key."""
    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: mock_blueprints_dir)

    # Load both blueprints
    load_framework("STF")
    load_workflow("SundayPowerHour")

    # Clear only framework cache
    clear_cache("framework:linkedin:STF")

    # Modify framework file
    framework_path = mock_blueprints_dir / "frameworks" / "linkedin" / "STF.yaml"
    with open(framework_path, 'w') as f:
        yaml.dump({"name": "CLEARED"}, f)

    # Modify workflow file
    workflow_path = mock_blueprints_dir / "workflows" / "SundayPowerHour.yaml"
    with open(workflow_path, 'w') as f:
        yaml.dump({"name": "MODIFIED"}, f)

    # Framework should get new version (cache cleared)
    framework = load_framework("STF")
    assert framework["name"] == "CLEARED"

    # Workflow should get cached version (cache not cleared)
    workflow = load_workflow("SundayPowerHour")
    assert workflow["name"] == "SundayPowerHour"  # Not "MODIFIED"


def test_list_blueprints_all(monkeypatch: pytest.MonkeyPatch, mock_blueprints_dir: Path) -> None:
    """Test listing all blueprints."""
    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: mock_blueprints_dir)

    blueprints = list_blueprints()

    assert "frameworks" in blueprints
    assert "workflows" in blueprints
    assert "constraints" in blueprints

    assert "linkedin/STF" in blueprints["frameworks"]
    assert "SundayPowerHour" in blueprints["workflows"]
    assert "BrandVoice" in blueprints["constraints"]


def test_list_blueprints_by_category(monkeypatch: pytest.MonkeyPatch, mock_blueprints_dir: Path) -> None:
    """Test listing blueprints by specific category."""
    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: mock_blueprints_dir)

    # List only workflows
    workflows = list_blueprints(category="workflows")

    assert "workflows" in workflows
    assert "frameworks" not in workflows
    assert "constraints" not in workflows
    assert "SundayPowerHour" in workflows["workflows"]


def test_load_invalid_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test loading a blueprint with invalid YAML."""
    blueprints_dir = tmp_path / "blueprints"
    (blueprints_dir / "frameworks" / "linkedin").mkdir(parents=True)

    # Create invalid YAML file
    invalid_yaml = blueprints_dir / "frameworks" / "linkedin" / "Invalid.yaml"
    with open(invalid_yaml, 'w') as f:
        f.write("invalid: yaml: content: [unclosed")

    monkeypatch.setattr("lib.blueprint_loader.get_blueprints_dir", lambda: blueprints_dir)

    with pytest.raises(yaml.YAMLError, match="Failed to parse"):
        load_framework("Invalid")
