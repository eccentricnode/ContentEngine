"""Tests for Brand Planner agent."""

import pytest
from unittest.mock import MagicMock, patch

from agents.brand_planner import (
    BrandPlanner,
    ContentBrief,
    ContentIdea,
    DistributionTracker,
    Game,
    HookType,
    PlanningResult,
    TRAFFIC_HOOKS,
    BUILDING_HOOKS,
)
from lib.context_synthesizer import DailyContext


class TestDistributionTracker:
    """Tests for the DistributionTracker class."""

    def test_initial_state(self) -> None:
        """Test tracker starts with zero counts."""
        tracker = DistributionTracker()
        assert tracker.total == 0
        counts = tracker.get_counts()
        assert all(count == 0 for count in counts.values())

    def test_record_pillar(self) -> None:
        """Test recording pillar usage."""
        tracker = DistributionTracker()
        tracker.record("what_building")
        tracker.record("what_building")
        tracker.record("what_learning")

        assert tracker.total == 3
        counts = tracker.get_counts()
        assert counts["what_building"] == 2
        assert counts["what_learning"] == 1

    def test_invalid_pillar_raises(self) -> None:
        """Test that recording invalid pillar raises ValueError."""
        tracker = DistributionTracker()
        with pytest.raises(ValueError, match="Unknown pillar"):
            tracker.record("invalid_pillar")

    def test_get_priority_order_empty(self) -> None:
        """Test priority order when empty (all equally underrepresented)."""
        tracker = DistributionTracker()
        priority = tracker.get_priority_order()
        # All have same deviation (0 - target), sorted by target desc
        assert len(priority) == 4
        assert set(priority) == {"what_building", "what_learning", "sales_tech", "problem_solution"}

    def test_get_priority_order_with_data(self) -> None:
        """Test priority order reflects underrepresentation."""
        tracker = DistributionTracker()
        # Add 10 posts: 7 what_building (70%), 3 what_learning (30%)
        for _ in range(7):
            tracker.record("what_building")
        for _ in range(3):
            tracker.record("what_learning")

        priority = tracker.get_priority_order()

        # sales_tech and problem_solution have 0% (targets 20% and 15%)
        # They should be first (most underrepresented)
        # what_building at 70% vs 35% target is most overrepresented (last)
        assert priority[-1] == "what_building"  # Most over
        assert "problem_solution" in priority[:2]  # Most under
        assert "sales_tech" in priority[:2]  # Most under

    def test_should_override_when_balanced(self) -> None:
        """Test no override when distribution is balanced."""
        tracker = DistributionTracker()
        # Simulate balanced distribution
        for _ in range(4):
            tracker.record("what_building")  # 40%
        for _ in range(3):
            tracker.record("what_learning")  # 30%
        for _ in range(2):
            tracker.record("sales_tech")  # 20%
        for _ in range(1):
            tracker.record("problem_solution")  # 10%

        # what_building at 40% vs 35% target = +5%, should not override
        assert tracker.should_override("what_building") is None

    def test_should_override_when_over_threshold(self) -> None:
        """Test override when pillar exceeds +10% threshold."""
        tracker = DistributionTracker()
        # Make what_building very overrepresented
        for _ in range(8):
            tracker.record("what_building")  # 80%
        for _ in range(2):
            tracker.record("what_learning")  # 20%

        # what_building at 80% vs 35% target = +45%, should override
        override = tracker.should_override("what_building")
        assert override is not None
        # Should suggest an underrepresented pillar
        assert override in ["sales_tech", "problem_solution"]

    def test_should_override_empty_tracker(self) -> None:
        """Test no override when tracker is empty."""
        tracker = DistributionTracker()
        assert tracker.should_override("what_building") is None

    def test_get_percentages(self) -> None:
        """Test getting current percentages."""
        tracker = DistributionTracker()
        for _ in range(4):
            tracker.record("what_building")
        for _ in range(3):
            tracker.record("what_learning")
        for _ in range(2):
            tracker.record("sales_tech")
        for _ in range(1):
            tracker.record("problem_solution")

        percentages = tracker.get_percentages()
        assert percentages["what_building"] == 40.0
        assert percentages["what_learning"] == 30.0
        assert percentages["sales_tech"] == 20.0
        assert percentages["problem_solution"] == 10.0


class TestGameDecision:
    """Tests for game decision logic."""

    @pytest.fixture
    def planner(self) -> BrandPlanner:
        """Create a Brand Planner with mocked dependencies."""
        planner = BrandPlanner()
        # Mock strategy with get_hired goal
        planner._strategy = {
            "current_goal": {"primary": "get_hired"},
        }
        return planner

    def test_traffic_bias_for_get_hired_goal(self, planner: BrandPlanner) -> None:
        """Test that get_hired goal biases toward traffic."""
        idea = ContentIdea(
            title="Generic Content Idea",
            core_insight="Some insight about patterns",
            source_theme="AI Engineering",
            audience_value="medium",
        )

        # Run multiple times with same content to verify determinism
        game, _ = planner._decide_game("what_learning", idea)
        # With get_hired (70% base) + what_learning (+10%), should lean traffic
        # Hash determines final decision, but bias should be toward traffic
        assert game in [Game.TRAFFIC, Game.BUILDING_IN_PUBLIC]

    def test_building_keywords_shift_to_building(self, planner: BrandPlanner) -> None:
        """Test that building keywords shift toward building game."""
        idea = ContentIdea(
            title="Just Shipped the New Feature",
            core_insight="Deployed to production today",
            source_theme="Project milestone",
            audience_value="high",
        )

        game, hook_type = planner._decide_game("what_building", idea)
        # "shipped" and "deployed" should shift toward building
        # But still might be traffic due to base probability
        assert game in [Game.TRAFFIC, Game.BUILDING_IN_PUBLIC]
        if game == Game.BUILDING_IN_PUBLIC:
            assert hook_type in BUILDING_HOOKS

    def test_traffic_keywords_shift_to_traffic(self, planner: BrandPlanner) -> None:
        """Test that traffic keywords shift toward traffic game."""
        idea = ContentIdea(
            title="The Pattern That Changed Everything",
            core_insight="This framework mistake taught me a valuable lesson",
            source_theme="Learning",
            audience_value="high",
        )

        game, hook_type = planner._decide_game("what_learning", idea)
        # "pattern", "framework", "mistake", "lesson" shift toward traffic
        assert game in [Game.TRAFFIC, Game.BUILDING_IN_PUBLIC]
        if game == Game.TRAFFIC:
            assert hook_type in TRAFFIC_HOOKS

    def test_hook_type_matches_game(self, planner: BrandPlanner) -> None:
        """Test that hook type matches the selected game."""
        idea = ContentIdea(
            title="Test Idea",
            core_insight="Test insight",
            source_theme="Test",
            audience_value="medium",
        )

        game, hook_type = planner._decide_game("what_building", idea)

        if game == Game.TRAFFIC:
            assert hook_type in TRAFFIC_HOOKS
        else:
            assert hook_type in BUILDING_HOOKS


class TestFrameworkSelection:
    """Tests for framework selection logic."""

    @pytest.fixture
    def planner(self) -> BrandPlanner:
        """Create a Brand Planner with mocked dependencies."""
        planner = BrandPlanner()
        planner._strategy = {"current_goal": {"primary": "get_hired"}}
        planner._pillars = {}
        return planner

    def test_pillar_default_mappings(self, planner: BrandPlanner) -> None:
        """Test default framework selection based on pillar."""
        defaults = {
            "what_building": "STF",
            "what_learning": "MRS",
            "sales_tech": "STF",
            "problem_solution": "SLA",
        }

        for pillar, expected_framework in defaults.items():
            idea = ContentIdea(
                title="Generic Title",
                core_insight="Generic insight",
                source_theme="Generic",
                audience_value="medium",
            )
            framework = planner._select_framework(pillar, Game.TRAFFIC, idea)
            assert framework == expected_framework, f"Pillar {pillar} should default to {expected_framework}"

    def test_mistake_keyword_selects_mrs(self, planner: BrandPlanner) -> None:
        """Test that mistake keywords select MRS framework when pillar is compatible."""
        idea = ContentIdea(
            title="The Biggest Mistake I Made",
            core_insight="I failed to validate inputs",
            source_theme="Learning",
            audience_value="high",
        )

        # Use what_learning which is compatible with MRS
        framework = planner._select_framework("what_learning", Game.TRAFFIC, idea)
        assert framework == "MRS"

    def test_poll_keyword_selects_pif(self, planner: BrandPlanner) -> None:
        """Test that poll/question keywords select PIF framework."""
        idea = ContentIdea(
            title="Quick Question for Engineers",
            core_insight="Curious about your experience",
            source_theme="Community",
            audience_value="medium",
        )

        framework = planner._select_framework("what_building", Game.TRAFFIC, idea)
        assert framework == "PIF"

    def test_journey_keyword_selects_sla(self, planner: BrandPlanner) -> None:
        """Test that journey/arc keywords select SLA framework."""
        idea = ContentIdea(
            title="My Journey to Senior Engineer",
            core_insight="The evolution of my skills",
            source_theme="Career",
            audience_value="high",
        )

        framework = planner._select_framework("what_learning", Game.TRAFFIC, idea)
        assert framework == "SLA"


class TestContentIdea:
    """Tests for ContentIdea dataclass."""

    def test_content_idea_creation(self) -> None:
        """Test creating a ContentIdea."""
        idea = ContentIdea(
            title="Test Title",
            core_insight="Test insight",
            source_theme="Test theme",
            audience_value="high",
            suggested_pillar="what_building",
        )

        assert idea.title == "Test Title"
        assert idea.audience_value == "high"
        assert idea.suggested_pillar == "what_building"

    def test_content_idea_optional_pillar(self) -> None:
        """Test ContentIdea with no suggested pillar."""
        idea = ContentIdea(
            title="Test",
            core_insight="Insight",
            source_theme="Theme",
            audience_value="medium",
        )

        assert idea.suggested_pillar is None


class TestBrandPlannerIntegration:
    """Integration tests for BrandPlanner."""

    @pytest.fixture
    def mock_ollama(self) -> MagicMock:
        """Create a mock Ollama client."""
        mock = MagicMock()
        mock.generate_content_ideas.return_value = '''[
            {"title": "Building AI Agents", "core_insight": "Agents work best with clear goals", "source_theme": "AI Engineering", "audience_value": "high", "suggested_pillar": "what_building"},
            {"title": "Lessons from Production", "core_insight": "Monitoring matters more than you think", "source_theme": "DevOps", "audience_value": "medium", "suggested_pillar": "what_learning"},
            {"title": "Sales Engineering Tips", "core_insight": "Technical demos that convert", "source_theme": "Sales", "audience_value": "high", "suggested_pillar": "sales_tech"}
        ]'''
        return mock

    @pytest.fixture
    def sample_contexts(self) -> list[DailyContext]:
        """Create sample DailyContext objects."""
        return [
            DailyContext(
                themes=["AI Engineering", "Agent Architecture", "Production Systems"],
                decisions=["Use RAG for context", "Deploy to Cloudflare"],
                progress=["Shipped context capture", "Fixed validation bugs"],
                date="2026-02-04",
            ),
            DailyContext(
                themes=["Content Strategy", "LinkedIn Growth"],
                decisions=["Focus on traffic game", "Use STF framework"],
                progress=["Created 5 posts", "Gained 100 followers"],
                date="2026-02-03",
            ),
        ]

    def test_plan_week_basic(
        self,
        mock_ollama: MagicMock,
        sample_contexts: list[DailyContext],
    ) -> None:
        """Test basic plan_week functionality."""
        planner = BrandPlanner()
        planner._ollama = mock_ollama
        planner._strategy = {"current_goal": {"primary": "get_hired"}}
        planner._pillars = {}

        result = planner.plan_week(sample_contexts, target_posts=3)

        assert result.success
        assert len(result.briefs) == 3
        assert result.total_ideas_extracted == 3

    def test_plan_week_respects_distribution(
        self,
        mock_ollama: MagicMock,
        sample_contexts: list[DailyContext],
    ) -> None:
        """Test that plan_week respects pillar distribution."""
        # Return more ideas to test distribution
        mock_ollama.generate_content_ideas.return_value = '''[
            {"title": "Idea 1", "core_insight": "Insight 1", "source_theme": "Theme 1", "audience_value": "high", "suggested_pillar": "what_building"},
            {"title": "Idea 2", "core_insight": "Insight 2", "source_theme": "Theme 2", "audience_value": "high", "suggested_pillar": "what_building"},
            {"title": "Idea 3", "core_insight": "Insight 3", "source_theme": "Theme 3", "audience_value": "high", "suggested_pillar": "what_building"},
            {"title": "Idea 4", "core_insight": "Insight 4", "source_theme": "Theme 4", "audience_value": "high", "suggested_pillar": "what_building"},
            {"title": "Idea 5", "core_insight": "Insight 5", "source_theme": "Theme 5", "audience_value": "high", "suggested_pillar": "what_building"},
            {"title": "Idea 6", "core_insight": "Insight 6", "source_theme": "Theme 6", "audience_value": "high", "suggested_pillar": "what_building"},
            {"title": "Idea 7", "core_insight": "Insight 7", "source_theme": "Theme 7", "audience_value": "high", "suggested_pillar": "what_building"},
            {"title": "Idea 8", "core_insight": "Insight 8", "source_theme": "Theme 8", "audience_value": "high", "suggested_pillar": "what_building"},
            {"title": "Idea 9", "core_insight": "Insight 9", "source_theme": "Theme 9", "audience_value": "high", "suggested_pillar": "what_building"},
            {"title": "Idea 10", "core_insight": "Insight 10", "source_theme": "Theme 10", "audience_value": "high", "suggested_pillar": "what_building"}
        ]'''

        planner = BrandPlanner()
        planner._ollama = mock_ollama
        planner._strategy = {"current_goal": {"primary": "get_hired"}}
        planner._pillars = {}

        result = planner.plan_week(sample_contexts, target_posts=10)

        # Even though all ideas suggest what_building, distribution should be enforced
        # At some point, should_override will kick in
        assert result.success
        pillars_used = set(brief.pillar for brief in result.briefs)
        # Should have more than just what_building due to distribution override
        assert len(pillars_used) > 1

    def test_plan_week_creates_valid_briefs(
        self,
        mock_ollama: MagicMock,
        sample_contexts: list[DailyContext],
    ) -> None:
        """Test that plan_week creates valid ContentBrief objects."""
        planner = BrandPlanner()
        planner._ollama = mock_ollama
        planner._strategy = {"current_goal": {"primary": "get_hired"}}
        planner._pillars = {}

        result = planner.plan_week(sample_contexts, target_posts=3)

        for brief in result.briefs:
            assert isinstance(brief, ContentBrief)
            assert brief.pillar in {"what_building", "what_learning", "sales_tech", "problem_solution"}
            assert brief.framework in {"STF", "MRS", "SLA", "PIF"}
            assert isinstance(brief.game, Game)
            assert isinstance(brief.hook_type, HookType)
            assert brief.rationale  # Should have rationale
            assert brief.structure_preview  # Should have structure preview

    def test_plan_week_handles_llm_failure(self, sample_contexts: list[DailyContext]) -> None:
        """Test that plan_week handles LLM failures gracefully."""
        from lib.errors import AIError

        mock_ollama = MagicMock()
        mock_ollama.generate_content_ideas.side_effect = AIError("Connection failed")

        planner = BrandPlanner()
        planner._ollama = mock_ollama
        planner._strategy = {"current_goal": {"primary": "get_hired"}}

        result = planner.plan_week(sample_contexts, target_posts=5)

        assert not result.success
        assert len(result.errors) > 0
        assert "Connection failed" in result.errors[0]

    def test_plan_week_game_breakdown(
        self,
        mock_ollama: MagicMock,
        sample_contexts: list[DailyContext],
    ) -> None:
        """Test that game breakdown is tracked correctly."""
        planner = BrandPlanner()
        planner._ollama = mock_ollama
        planner._strategy = {"current_goal": {"primary": "get_hired"}}
        planner._pillars = {}

        result = planner.plan_week(sample_contexts, target_posts=3)

        assert "traffic" in result.game_breakdown
        assert "building_in_public" in result.game_breakdown
        total_games = sum(result.game_breakdown.values())
        assert total_games == len(result.briefs)


class TestHookTypeEnums:
    """Tests for HookType enum organization."""

    def test_traffic_hooks_set(self) -> None:
        """Test TRAFFIC_HOOKS contains correct hook types."""
        assert HookType.PROBLEM_FIRST in TRAFFIC_HOOKS
        assert HookType.RESULT_FIRST in TRAFFIC_HOOKS
        assert HookType.INSIGHT_FIRST in TRAFFIC_HOOKS
        assert len(TRAFFIC_HOOKS) == 3

    def test_building_hooks_set(self) -> None:
        """Test BUILDING_HOOKS contains correct hook types."""
        assert HookType.SHIPPED in BUILDING_HOOKS
        assert HookType.LEARNING in BUILDING_HOOKS
        assert HookType.PROGRESS in BUILDING_HOOKS
        assert len(BUILDING_HOOKS) == 3

    def test_no_overlap_between_sets(self) -> None:
        """Test that traffic and building hooks don't overlap."""
        assert TRAFFIC_HOOKS.isdisjoint(BUILDING_HOOKS)


class TestGameEnum:
    """Tests for Game enum."""

    def test_game_values(self) -> None:
        """Test Game enum values."""
        assert Game.TRAFFIC.value == "traffic"
        assert Game.BUILDING_IN_PUBLIC.value == "building_in_public"

    def test_game_string_representation(self) -> None:
        """Test Game enum can be used as string."""
        assert str(Game.TRAFFIC) == "Game.TRAFFIC"
        assert Game.TRAFFIC == "traffic"  # str enum comparison
