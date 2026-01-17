"""Tests for Blueprint database model."""

from datetime import datetime
from lib.database import Blueprint, SessionLocal


def test_create_blueprint() -> None:
    """Test creating a blueprint record."""
    db = SessionLocal()

    blueprint = Blueprint(
        name="STF",
        category="framework",
        platform="linkedin",
        data={
            "name": "STF",
            "description": "Storytelling Framework",
            "structure": {"sections": ["Problem", "Tried", "Worked", "Lesson"]}
        },
        version="1.0"
    )

    db.add(blueprint)
    db.commit()
    db.refresh(blueprint)

    # Verify creation
    assert blueprint.id is not None
    assert blueprint.name == "STF"
    assert blueprint.category == "framework"
    assert blueprint.platform == "linkedin"
    assert blueprint.data["name"] == "STF"
    assert blueprint.version == "1.0"
    assert isinstance(blueprint.created_at, datetime)
    assert isinstance(blueprint.updated_at, datetime)

    # Cleanup
    db.delete(blueprint)
    db.commit()
    db.close()


def test_read_blueprint() -> None:
    """Test reading a blueprint record."""
    db = SessionLocal()

    # Create
    blueprint = Blueprint(
        name="MRS",
        category="framework",
        platform="linkedin",
        data={"name": "MRS", "description": "Mistake-Realization-Shift"}
    )
    db.add(blueprint)
    db.commit()
    blueprint_id = blueprint.id

    # Read
    retrieved = db.query(Blueprint).filter(Blueprint.id == blueprint_id).first()

    assert retrieved is not None
    assert retrieved.name == "MRS"
    assert retrieved.category == "framework"
    assert retrieved.data["description"] == "Mistake-Realization-Shift"

    # Cleanup
    db.delete(retrieved)
    db.commit()
    db.close()


def test_update_blueprint() -> None:
    """Test updating a blueprint record."""
    db = SessionLocal()

    # Create
    blueprint = Blueprint(
        name="BrandVoice",
        category="constraint",
        platform=None,
        data={"characteristics": ["technical", "authentic"]},
        version="1.0"
    )
    db.add(blueprint)
    db.commit()

    # Update
    setattr(blueprint, "data", {"characteristics": ["technical", "authentic", "confident"]})
    setattr(blueprint, "version", "1.1")
    db.commit()
    db.refresh(blueprint)

    # Verify update
    assert len(blueprint.data["characteristics"]) == 3
    assert "confident" in blueprint.data["characteristics"]
    assert blueprint.version == "1.1"
    assert blueprint.updated_at >= blueprint.created_at

    # Cleanup
    db.delete(blueprint)
    db.commit()
    db.close()


def test_delete_blueprint() -> None:
    """Test deleting a blueprint record."""
    db = SessionLocal()

    # Create
    blueprint = Blueprint(
        name="TempBlueprint",
        category="workflow",
        platform=None,
        data={"name": "Temp"}
    )
    db.add(blueprint)
    db.commit()
    blueprint_id = blueprint.id

    # Delete
    db.delete(blueprint)
    db.commit()

    # Verify deletion
    retrieved = db.query(Blueprint).filter(Blueprint.id == blueprint_id).first()
    assert retrieved is None

    db.close()


def test_query_blueprints_by_category() -> None:
    """Test querying blueprints by category."""
    db = SessionLocal()

    # Create multiple blueprints
    framework1 = Blueprint(
        name="STF",
        category="framework",
        platform="linkedin",
        data={"name": "STF"}
    )
    framework2 = Blueprint(
        name="MRS",
        category="framework",
        platform="linkedin",
        data={"name": "MRS"}
    )
    constraint = Blueprint(
        name="BrandVoice",
        category="constraint",
        platform=None,
        data={"name": "BrandVoice"}
    )

    db.add_all([framework1, framework2, constraint])
    db.commit()

    # Query frameworks
    frameworks = db.query(Blueprint).filter(Blueprint.category == "framework").all()
    assert len(frameworks) >= 2
    assert all(bp.category == "framework" for bp in frameworks)

    # Query constraints
    constraints = db.query(Blueprint).filter(Blueprint.category == "constraint").all()
    assert len(constraints) >= 1
    assert all(bp.category == "constraint" for bp in constraints)

    # Cleanup
    db.delete(framework1)
    db.delete(framework2)
    db.delete(constraint)
    db.commit()
    db.close()


def test_blueprint_repr() -> None:
    """Test Blueprint __repr__ method."""
    blueprint = Blueprint(
        name="TestBlueprint",
        category="framework",
        platform="linkedin",
        data={"test": "data"}
    )

    repr_str = repr(blueprint)
    assert "Blueprint" in repr_str
    assert "TestBlueprint" in repr_str
    assert "framework" in repr_str


def test_blueprint_with_null_platform() -> None:
    """Test creating blueprint without platform (for workflows/constraints)."""
    db = SessionLocal()

    blueprint = Blueprint(
        name="SundayPowerHour",
        category="workflow",
        platform=None,  # Workflows don't have platform
        data={"name": "SundayPowerHour", "steps": []}
    )

    db.add(blueprint)
    db.commit()
    db.refresh(blueprint)

    assert blueprint.platform is None
    assert blueprint.category == "workflow"

    # Cleanup
    db.delete(blueprint)
    db.commit()
    db.close()


def test_blueprint_json_data_persistence() -> None:
    """Test that complex JSON data persists correctly."""
    db = SessionLocal()

    complex_data = {
        "name": "ComplexBlueprint",
        "structure": {
            "sections": ["Intro", "Body", "Conclusion"],
            "min_chars": 600,
            "max_chars": 1500
        },
        "validation": {
            "rules": ["no_buzzwords", "specific_examples"],
            "forbidden_phrases": ["leverage", "synergy"]
        },
        "examples": [
            {"title": "Example 1", "content": "..."},
            {"title": "Example 2", "content": "..."}
        ]
    }

    blueprint = Blueprint(
        name="ComplexBlueprint",
        category="framework",
        platform="linkedin",
        data=complex_data
    )

    db.add(blueprint)
    db.commit()
    blueprint_id = blueprint.id

    # Close and reopen session to ensure persistence
    db.close()
    db = SessionLocal()

    # Retrieve and verify
    retrieved = db.query(Blueprint).filter(Blueprint.id == blueprint_id).first()
    assert retrieved is not None
    assert retrieved.data["name"] == "ComplexBlueprint"
    assert len(retrieved.data["structure"]["sections"]) == 3
    assert retrieved.data["structure"]["min_chars"] == 600
    assert "leverage" in retrieved.data["validation"]["forbidden_phrases"]
    assert len(retrieved.data["examples"]) == 2

    # Cleanup
    db.delete(retrieved)
    db.commit()
    db.close()
