"""Blueprint loader for Content Engine.

Loads and caches YAML blueprint files for frameworks, workflows, and constraints.
"""

from pathlib import Path
from typing import Any, Optional, cast
import yaml


# In-memory cache for loaded blueprints
_blueprint_cache: dict[str, Any] = {}


def get_blueprints_dir() -> Path:
    """Get the blueprints directory path.

    Returns:
        Path to blueprints directory
    """
    # Get project root (parent of lib/)
    project_root = Path(__file__).parent.parent
    return project_root / "blueprints"


def load_framework(name: str, platform: str = "linkedin", use_cache: bool = True) -> dict[str, Any]:
    """Load a framework blueprint from YAML file.

    Args:
        name: Framework name (e.g., "STF", "MRS", "SLA", "PIF")
        platform: Platform name (default: "linkedin")
        use_cache: Whether to use cached version if available

    Returns:
        Dictionary containing framework blueprint data

    Raises:
        FileNotFoundError: If blueprint file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    cache_key = f"framework:{platform}:{name}"

    # Check cache
    if use_cache and cache_key in _blueprint_cache:
        return cast(dict[str, Any], _blueprint_cache[cache_key])

    # Load from file
    blueprints_dir = get_blueprints_dir()
    framework_path = blueprints_dir / "frameworks" / platform / f"{name}.yaml"

    if not framework_path.exists():
        raise FileNotFoundError(f"Framework blueprint not found: {framework_path}")

    try:
        with open(framework_path, 'r') as f:
            blueprint = cast(dict[str, Any], yaml.safe_load(f))

        # Cache the result
        _blueprint_cache[cache_key] = blueprint

        return blueprint
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse {framework_path}: {e}") from e


def load_workflow(name: str, use_cache: bool = True) -> dict[str, Any]:
    """Load a workflow blueprint from YAML file.

    Args:
        name: Workflow name (e.g., "SundayPowerHour", "Repurposing1to10")
        use_cache: Whether to use cached version if available

    Returns:
        Dictionary containing workflow blueprint data

    Raises:
        FileNotFoundError: If blueprint file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    cache_key = f"workflow:{name}"

    # Check cache
    if use_cache and cache_key in _blueprint_cache:
        return cast(dict[str, Any], _blueprint_cache[cache_key])

    # Load from file
    blueprints_dir = get_blueprints_dir()
    workflow_path = blueprints_dir / "workflows" / f"{name}.yaml"

    if not workflow_path.exists():
        raise FileNotFoundError(f"Workflow blueprint not found: {workflow_path}")

    try:
        with open(workflow_path, 'r') as f:
            blueprint = cast(dict[str, Any], yaml.safe_load(f))

        # Cache the result
        _blueprint_cache[cache_key] = blueprint

        return blueprint
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse {workflow_path}: {e}") from e


def load_constraints(name: str, use_cache: bool = True) -> dict[str, Any]:
    """Load a constraint blueprint from YAML file.

    Args:
        name: Constraint name (e.g., "BrandVoice", "ContentPillars", "PlatformRules")
        use_cache: Whether to use cached version if available

    Returns:
        Dictionary containing constraint blueprint data

    Raises:
        FileNotFoundError: If blueprint file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    cache_key = f"constraint:{name}"

    # Check cache
    if use_cache and cache_key in _blueprint_cache:
        return cast(dict[str, Any], _blueprint_cache[cache_key])

    # Load from file
    blueprints_dir = get_blueprints_dir()
    constraint_path = blueprints_dir / "constraints" / f"{name}.yaml"

    if not constraint_path.exists():
        raise FileNotFoundError(f"Constraint blueprint not found: {constraint_path}")

    try:
        with open(constraint_path, 'r') as f:
            blueprint = cast(dict[str, Any], yaml.safe_load(f))

        # Cache the result
        _blueprint_cache[cache_key] = blueprint

        return blueprint
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse {constraint_path}: {e}") from e


def clear_cache(cache_key: Optional[str] = None) -> None:
    """Clear the blueprint cache.

    Args:
        cache_key: Specific cache key to clear. If None, clears entire cache.
    """
    if cache_key:
        _blueprint_cache.pop(cache_key, None)
    else:
        _blueprint_cache.clear()


def list_blueprints(category: Optional[str] = None) -> dict[str, list[str]]:
    """List all available blueprints.

    Args:
        category: Optional category filter ("frameworks", "workflows", "constraints")

    Returns:
        Dictionary mapping categories to lists of blueprint names
    """
    blueprints_dir = get_blueprints_dir()
    result: dict[str, list[str]] = {}

    categories_to_check = [category] if category else ["frameworks", "workflows", "constraints"]

    for cat in categories_to_check:
        if cat == "frameworks":
            # Check all platform subdirectories
            frameworks_dir = blueprints_dir / "frameworks"
            if frameworks_dir.exists():
                framework_files = []
                for platform_dir in frameworks_dir.iterdir():
                    if platform_dir.is_dir():
                        for yaml_file in platform_dir.glob("*.yaml"):
                            framework_files.append(f"{platform_dir.name}/{yaml_file.stem}")
                result["frameworks"] = sorted(framework_files)
        else:
            cat_dir = blueprints_dir / cat
            if cat_dir.exists():
                yaml_files = [f.stem for f in cat_dir.glob("*.yaml")]
                result[cat] = sorted(yaml_files)

    return result
