"""Tests for ContentPlan database model."""

from lib.database import ContentPlan, ContentPlanStatus, Post, PostStatus, SessionLocal


def test_create_content_plan() -> None:
    """Test creating a ContentPlan record."""
    db = SessionLocal()

    plan = ContentPlan(
        week_start_date="2026-01-20",
        pillar="what_building",
        framework="STF",
        idea="Building AI agents that extend capabilities"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    assert plan.id is not None
    assert plan.week_start_date == "2026-01-20"
    assert plan.pillar == "what_building"
    assert plan.framework == "STF"
    assert plan.idea == "Building AI agents that extend capabilities"
    assert plan.status == ContentPlanStatus.PLANNED
    assert plan.post_id is None
    assert plan.created_at is not None
    assert plan.updated_at is not None

    db.delete(plan)
    db.commit()
    db.close()


def test_read_content_plan() -> None:
    """Test reading a ContentPlan record."""
    db = SessionLocal()

    # Create
    plan = ContentPlan(
        week_start_date="2026-01-20",
        pillar="what_learning",
        framework="MRS",
        idea="Lessons from failed deploys"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    plan_id = plan.id

    # Read
    loaded_plan = db.query(ContentPlan).filter(ContentPlan.id == plan_id).first()
    assert loaded_plan is not None
    assert loaded_plan.week_start_date == "2026-01-20"
    assert loaded_plan.pillar == "what_learning"
    assert loaded_plan.framework == "MRS"

    db.delete(plan)
    db.commit()
    db.close()


def test_update_content_plan_status() -> None:
    """Test updating ContentPlan status."""
    db = SessionLocal()

    plan = ContentPlan(
        week_start_date="2026-01-20",
        pillar="sales_tech",
        framework="PIF",
        idea="What's your favorite AI tool?"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    # Update status
    setattr(plan, "status", ContentPlanStatus.IN_PROGRESS)
    db.commit()
    db.refresh(plan)

    assert plan.status == ContentPlanStatus.IN_PROGRESS

    db.delete(plan)
    db.commit()
    db.close()


def test_delete_content_plan() -> None:
    """Test deleting a ContentPlan record."""
    db = SessionLocal()

    plan = ContentPlan(
        week_start_date="2026-01-20",
        pillar="problem_solution",
        framework="STF",
        idea="Fixing memory leaks in Python"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    plan_id = plan.id

    # Delete
    db.delete(plan)
    db.commit()

    # Verify deleted
    deleted_plan = db.query(ContentPlan).filter(ContentPlan.id == plan_id).first()
    assert deleted_plan is None

    db.close()


def test_query_by_week() -> None:
    """Test querying ContentPlans by week_start_date."""
    db = SessionLocal()

    # Create multiple plans for same week
    plan1 = ContentPlan(
        week_start_date="2026-01-20",
        pillar="what_building",
        framework="STF",
        idea="Idea 1"
    )
    plan2 = ContentPlan(
        week_start_date="2026-01-20",
        pillar="what_learning",
        framework="MRS",
        idea="Idea 2"
    )
    plan3 = ContentPlan(
        week_start_date="2026-01-27",
        pillar="sales_tech",
        framework="SLA",
        idea="Idea 3"
    )
    db.add_all([plan1, plan2, plan3])
    db.commit()

    # Query by week
    week_plans = db.query(ContentPlan).filter(
        ContentPlan.week_start_date == "2026-01-20"
    ).all()

    assert len(week_plans) == 2
    assert all(p.week_start_date == "2026-01-20" for p in week_plans)

    db.delete(plan1)
    db.delete(plan2)
    db.delete(plan3)
    db.commit()
    db.close()


def test_query_by_pillar() -> None:
    """Test querying ContentPlans by pillar."""
    db = SessionLocal()

    plan1 = ContentPlan(
        week_start_date="2026-01-20",
        pillar="what_building",
        framework="STF",
        idea="Build 1"
    )
    plan2 = ContentPlan(
        week_start_date="2026-01-20",
        pillar="what_building",
        framework="SLA",
        idea="Build 2"
    )
    plan3 = ContentPlan(
        week_start_date="2026-01-20",
        pillar="what_learning",
        framework="MRS",
        idea="Learn 1"
    )
    db.add_all([plan1, plan2, plan3])
    db.commit()

    # Query by pillar
    building_plans = db.query(ContentPlan).filter(
        ContentPlan.pillar == "what_building"
    ).all()

    assert len(building_plans) == 2
    assert all(p.pillar == "what_building" for p in building_plans)

    db.delete(plan1)
    db.delete(plan2)
    db.delete(plan3)
    db.commit()
    db.close()


def test_content_plan_with_post_relationship() -> None:
    """Test ContentPlan relationship with Post."""
    db = SessionLocal()

    # Create post
    post = Post(
        content="Test post content",
        status=PostStatus.DRAFT
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    # Create plan linked to post
    plan = ContentPlan(
        week_start_date="2026-01-20",
        pillar="what_building",
        framework="STF",
        idea="Test idea",
        post_id=post.id
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    # Verify relationship
    assert plan.post_id == post.id
    assert plan.post is not None
    assert plan.post.content == "Test post content"

    db.delete(plan)
    db.delete(post)
    db.commit()
    db.close()


def test_content_plan_repr() -> None:
    """Test ContentPlan __repr__ method."""
    plan = ContentPlan(
        week_start_date="2026-01-20",
        pillar="what_building",
        framework="STF",
        idea="Test",
        status=ContentPlanStatus.PLANNED
    )

    repr_str = repr(plan)
    assert "ContentPlan" in repr_str
    assert "what_building" in repr_str
    assert "STF" in repr_str
    assert "PLANNED" in repr_str


def test_content_plan_status_enum() -> None:
    """Test ContentPlanStatus enum values."""
    db = SessionLocal()

    # Test all status values
    for status in [
        ContentPlanStatus.PLANNED,
        ContentPlanStatus.IN_PROGRESS,
        ContentPlanStatus.GENERATED,
        ContentPlanStatus.CANCELLED
    ]:
        plan = ContentPlan(
            week_start_date="2026-01-20",
            pillar="what_building",
            framework="STF",
            idea=f"Test {status.value}",
            status=status
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        assert plan.status == status

        db.delete(plan)
        db.commit()

    db.close()
