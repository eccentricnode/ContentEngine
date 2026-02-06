"""Brand Planner agent for strategic content planning.

The Brand Planner is the strategic brain that transforms captured context into content plans.
It decides WHAT to post by:
- Assigning pillars (35/30/20/15 distribution)
- Selecting frameworks (STF/MRS/SLA/PIF)
- Choosing game strategy (traffic vs building-in-public)
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from lib.blueprint_loader import load_constraints, load_framework
from lib.context_synthesizer import DailyContext
from lib.errors import AIError
from lib.ollama import OllamaClient


class Game(str, Enum):
    """Content game strategy - traffic vs building in public."""
    TRAFFIC = "traffic"
    BUILDING_IN_PUBLIC = "building_in_public"


class HookType(str, Enum):
    """Hook types organized by game strategy."""
    # Traffic hooks
    PROBLEM_FIRST = "problem_first"
    RESULT_FIRST = "result_first"
    INSIGHT_FIRST = "insight_first"

    # Building in public hooks
    SHIPPED = "shipped"
    LEARNING = "learning"
    PROGRESS = "progress"


# Map hook types to their games
TRAFFIC_HOOKS = {HookType.PROBLEM_FIRST, HookType.RESULT_FIRST, HookType.INSIGHT_FIRST}
BUILDING_HOOKS = {HookType.SHIPPED, HookType.LEARNING, HookType.PROGRESS}


@dataclass
class ContentIdea:
    """A content idea extracted from context."""
    title: str
    core_insight: str
    source_theme: str
    audience_value: str  # low/medium/high
    suggested_pillar: Optional[str] = None


@dataclass
class ContentBrief:
    """A fully planned content brief ready for generation."""
    idea: ContentIdea
    pillar: str
    framework: str
    game: Game
    hook_type: HookType
    context_summary: str
    structure_preview: str
    rationale: str


@dataclass
class PlanningResult:
    """Result of content planning operation."""
    briefs: list[ContentBrief]
    distribution: dict[str, int]
    game_breakdown: dict[str, int]
    total_ideas_extracted: int
    success: bool = True
    errors: list[str] = field(default_factory=list)


class DistributionTracker:
    """Tracks and manages pillar distribution (35/30/20/15).

    Maintains running totals per pillar and provides methods
    to determine priority order and override suggestions when
    distribution is unbalanced.
    """

    # Target percentages
    TARGETS = {
        "what_building": 35,
        "what_learning": 30,
        "sales_tech": 20,
        "problem_solution": 15,
    }

    def __init__(self) -> None:
        self._counts: dict[str, int] = {
            "what_building": 0,
            "what_learning": 0,
            "sales_tech": 0,
            "problem_solution": 0,
        }

    @property
    def total(self) -> int:
        """Total posts tracked."""
        return sum(self._counts.values())

    def get_current_percentage(self, pillar: str) -> float:
        """Get current percentage for a pillar."""
        if self.total == 0:
            return 0.0
        return (self._counts[pillar] / self.total) * 100

    def get_deviation(self, pillar: str) -> float:
        """Get deviation from target (positive = over, negative = under)."""
        return self.get_current_percentage(pillar) - self.TARGETS[pillar]

    def get_priority_order(self) -> list[str]:
        """Get pillars sorted by priority (most underrepresented first).

        Returns:
            List of pillar names, sorted from most underrepresented to least.
        """
        # Sort by deviation (most negative first = most underrepresented)
        return sorted(
            self._counts.keys(),
            key=lambda p: self.get_deviation(p)
        )

    def should_override(self, suggested: str) -> Optional[str]:
        """Check if suggested pillar should be overridden due to imbalance.

        Args:
            suggested: The pillar suggested by LLM or algorithm

        Returns:
            Alternative pillar if override needed, None if suggestion is fine.
        """
        # If no posts yet, accept any suggestion
        if self.total == 0:
            return None

        suggested_deviation = self.get_deviation(suggested)

        # If suggested pillar is >10% over target, override
        if suggested_deviation > 10:
            # Get the most underrepresented pillar
            priority = self.get_priority_order()
            # Return first pillar that's underrepresented
            for pillar in priority:
                if self.get_deviation(pillar) < 0:
                    return pillar

        return None

    def record(self, pillar: str) -> None:
        """Record a pillar usage."""
        if pillar not in self._counts:
            raise ValueError(f"Unknown pillar: {pillar}")
        self._counts[pillar] += 1

    def get_counts(self) -> dict[str, int]:
        """Get current counts."""
        return self._counts.copy()

    def get_percentages(self) -> dict[str, float]:
        """Get current percentages for all pillars."""
        return {
            pillar: self.get_current_percentage(pillar)
            for pillar in self._counts
        }


class BrandPlanner:
    """Strategic content planner that transforms context into content briefs.

    The Brand Planner:
    1. Extracts content ideas from daily context
    2. Assigns pillars based on 35/30/20/15 distribution
    3. Decides game strategy (traffic vs building-in-public)
    4. Selects appropriate frameworks
    5. Generates hook types and structure previews
    """

    def __init__(self, model: str = "llama3:8b") -> None:
        """Initialize Brand Planner.

        Args:
            model: Ollama model to use for LLM reasoning
        """
        self.model = model
        self._strategy: Optional[dict[str, Any]] = None
        self._pillars: Optional[dict[str, Any]] = None
        self._ollama: Optional[OllamaClient] = None

    @property
    def strategy(self) -> dict[str, Any]:
        """Lazy load ContentStrategy blueprint."""
        if self._strategy is None:
            self._strategy = load_constraints("ContentStrategy")
        return self._strategy

    @property
    def pillars(self) -> dict[str, Any]:
        """Lazy load ContentPillars blueprint."""
        if self._pillars is None:
            self._pillars = load_constraints("ContentPillars")
        return self._pillars

    @property
    def ollama(self) -> OllamaClient:
        """Lazy load Ollama client."""
        if self._ollama is None:
            self._ollama = OllamaClient(model=self.model)
        return self._ollama

    def plan_week(
        self,
        contexts: list[DailyContext],
        target_posts: int = 10,
    ) -> PlanningResult:
        """Plan a week's worth of content from aggregated context.

        Args:
            contexts: List of DailyContext objects to plan from
            target_posts: Target number of posts to plan (default: 10)

        Returns:
            PlanningResult with content briefs and distribution stats
        """
        errors: list[str] = []
        tracker = DistributionTracker()

        # Aggregate context into single summary
        aggregated = self._aggregate_contexts(contexts)

        # Extract ideas (ask for more than target to allow filtering)
        ideas_needed = int(target_posts * 1.5)
        try:
            ideas = self._extract_ideas(aggregated, ideas_needed)
        except AIError as e:
            return PlanningResult(
                briefs=[],
                distribution={},
                game_breakdown={},
                total_ideas_extracted=0,
                success=False,
                errors=[f"Failed to extract ideas: {e}"],
            )

        if not ideas:
            return PlanningResult(
                briefs=[],
                distribution={},
                game_breakdown={},
                total_ideas_extracted=0,
                success=False,
                errors=["No content ideas could be extracted from context"],
            )

        # Plan briefs for each idea
        briefs: list[ContentBrief] = []
        game_counts = {Game.TRAFFIC.value: 0, Game.BUILDING_IN_PUBLIC.value: 0}

        for idea in ideas[:target_posts]:
            try:
                # Assign pillar (respecting distribution)
                pillar = self._assign_pillar(idea, tracker)

                # Decide game and hook type
                game, hook_type = self._decide_game(pillar, idea)

                # Select framework
                framework = self._select_framework(pillar, game, idea)

                # Generate context summary and structure preview
                context_summary = self._generate_context_summary(idea, aggregated)
                structure_preview = self._generate_structure_preview(framework, idea)
                rationale = self._generate_rationale(idea, pillar, framework, game)

                brief = ContentBrief(
                    idea=idea,
                    pillar=pillar,
                    framework=framework,
                    game=game,
                    hook_type=hook_type,
                    context_summary=context_summary,
                    structure_preview=structure_preview,
                    rationale=rationale,
                )

                briefs.append(brief)
                tracker.record(pillar)
                game_counts[game.value] += 1

            except Exception as e:
                errors.append(f"Failed to plan brief for '{idea.title}': {e}")

        return PlanningResult(
            briefs=briefs,
            distribution=tracker.get_counts(),
            game_breakdown=game_counts,
            total_ideas_extracted=len(ideas),
            success=len(briefs) > 0,
            errors=errors,
        )

    def _aggregate_contexts(self, contexts: list[DailyContext]) -> dict[str, Any]:
        """Aggregate multiple DailyContext objects into a single summary.

        Args:
            contexts: List of DailyContext objects

        Returns:
            Aggregated context dictionary
        """
        all_themes: list[str] = []
        all_decisions: list[str] = []
        all_progress: list[str] = []

        for ctx in contexts:
            all_themes.extend(ctx.themes)
            all_decisions.extend(ctx.decisions)
            all_progress.extend(ctx.progress)

        return {
            "themes": all_themes,
            "decisions": all_decisions,
            "progress": all_progress,
            "days_covered": len(contexts),
        }

    def _extract_ideas(self, context: dict[str, Any], count: int) -> list[ContentIdea]:
        """Extract content ideas from aggregated context using LLM.

        Args:
            context: Aggregated context dictionary
            count: Number of ideas to extract

        Returns:
            List of ContentIdea objects
        """
        # Build prompt for idea extraction
        prompt = f"""You are a content strategist for a software engineer/AI engineer's LinkedIn presence.

Given the following context from the past week, extract {count} content ideas that would make engaging LinkedIn posts.

CONTEXT:
Themes: {', '.join(context.get('themes', [])[:10])}
Decisions Made: {', '.join(context.get('decisions', [])[:10])}
Progress Achieved: {', '.join(context.get('progress', [])[:10])}

For each idea, provide:
1. title: A compelling post title (5-10 words)
2. core_insight: The main insight or takeaway (1-2 sentences)
3. source_theme: Which theme/decision/progress it came from
4. audience_value: How valuable this is to audience (low/medium/high)
5. suggested_pillar: Best fit pillar (what_building, what_learning, sales_tech, problem_solution)

PILLARS:
- what_building: Projects, features shipped, technical decisions, building journey
- what_learning: Learning journey, aha moments, knowledge synthesis
- sales_tech: Sales + tech intersection, close rate improvements, sales engineering
- problem_solution: Common pain points, specific solutions, actionable fixes

Output ONLY valid JSON array of objects. No explanation, just the JSON.
Example format:
[{{"title": "...", "core_insight": "...", "source_theme": "...", "audience_value": "high", "suggested_pillar": "what_building"}}]
"""

        try:
            response = self.ollama.generate_content_ideas(prompt)

            # Parse JSON response
            # Try to find JSON array in response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if not json_match:
                raise AIError(f"No JSON array found in response: {response[:200]}")

            ideas_data = json.loads(json_match.group())

            ideas: list[ContentIdea] = []
            for item in ideas_data:
                idea = ContentIdea(
                    title=item.get("title", "Untitled"),
                    core_insight=item.get("core_insight", ""),
                    source_theme=item.get("source_theme", ""),
                    audience_value=item.get("audience_value", "medium"),
                    suggested_pillar=item.get("suggested_pillar"),
                )
                ideas.append(idea)

            return ideas

        except json.JSONDecodeError as e:
            raise AIError(f"Failed to parse LLM response as JSON: {e}")

    def _assign_pillar(self, idea: ContentIdea, tracker: DistributionTracker) -> str:
        """Assign pillar to idea, respecting distribution targets.

        Args:
            idea: The content idea
            tracker: Distribution tracker for balance

        Returns:
            Assigned pillar name
        """
        # Start with LLM suggestion or default
        suggested = idea.suggested_pillar or "what_building"

        # Validate pillar name
        valid_pillars = {"what_building", "what_learning", "sales_tech", "problem_solution"}
        if suggested not in valid_pillars:
            suggested = "what_building"

        # Check if we should override for distribution balance
        override = tracker.should_override(suggested)
        if override:
            return override

        return suggested

    def _decide_game(self, pillar: str, idea: ContentIdea) -> tuple[Game, HookType]:
        """Decide which game (traffic vs building) and hook type.

        Decision logic based on ContentStrategy.yaml:
        1. Current goal biases the base (get_hired = 70% traffic)
        2. Pillar adjusts: what_learning/sales_tech/problem_solution → +traffic
        3. Keywords can shift: "shipped/built" → building, "pattern/mistake" → traffic

        Args:
            pillar: Assigned content pillar
            idea: The content idea

        Returns:
            Tuple of (Game, HookType)
        """
        # Get current goal from strategy
        current_goal = self.strategy.get("current_goal", {}).get("primary", "get_hired")

        # Base traffic probability based on goal
        if current_goal == "get_hired":
            traffic_prob = 0.70
        elif current_goal == "build_community":
            traffic_prob = 0.30
        else:  # "both"
            traffic_prob = 0.50

        # Pillar adjustments
        traffic_leaning_pillars = {"what_learning", "sales_tech", "problem_solution"}
        if pillar in traffic_leaning_pillars:
            traffic_prob += 0.10

        # Keyword signals in idea content
        text = f"{idea.title} {idea.core_insight}".lower()

        building_keywords = {"shipped", "built", "deployed", "launched", "released", "milestone"}
        traffic_keywords = {"pattern", "framework", "mistake", "lesson", "insight", "tip"}

        building_signals = sum(1 for kw in building_keywords if kw in text)
        traffic_signals = sum(1 for kw in traffic_keywords if kw in text)

        # Adjust probability based on signals
        if building_signals > traffic_signals:
            traffic_prob -= 0.20
        elif traffic_signals > building_signals:
            traffic_prob += 0.10

        # Clamp probability
        traffic_prob = max(0.2, min(0.9, traffic_prob))

        # Decide game (deterministic for reproducibility based on content hash)
        content_hash = hash(f"{idea.title}{idea.core_insight}") % 100
        game = Game.TRAFFIC if content_hash < (traffic_prob * 100) else Game.BUILDING_IN_PUBLIC

        # Select hook type based on game and content
        hook_type = self._select_hook_type(game, idea)

        return game, hook_type

    def _select_hook_type(self, game: Game, idea: ContentIdea) -> HookType:
        """Select the best hook type for the game and idea.

        Args:
            game: The selected game strategy
            idea: The content idea

        Returns:
            Appropriate HookType
        """
        text = f"{idea.title} {idea.core_insight}".lower()

        if game == Game.TRAFFIC:
            # Traffic hooks
            if any(kw in text for kw in ["problem", "struggle", "pain", "issue", "wrong"]):
                return HookType.PROBLEM_FIRST
            elif any(kw in text for kw in ["result", "achieved", "improved", "built", "created"]):
                return HookType.RESULT_FIRST
            else:
                return HookType.INSIGHT_FIRST
        else:
            # Building in public hooks
            if any(kw in text for kw in ["shipped", "launched", "released", "deployed", "done"]):
                return HookType.SHIPPED
            elif any(kw in text for kw in ["learned", "discovered", "realized", "found"]):
                return HookType.LEARNING
            else:
                return HookType.PROGRESS

    def _select_framework(self, pillar: str, game: Game, idea: ContentIdea) -> str:
        """Select the best framework for the content.

        Selection logic:
        1. Default mapping based on pillar
        2. Keyword overrides for specific patterns
        3. Validate against framework's compatible_pillars

        Args:
            pillar: Assigned content pillar
            game: Selected game strategy
            idea: The content idea

        Returns:
            Framework name (STF, MRS, SLA, PIF)
        """
        # Default mappings
        pillar_defaults = {
            "what_building": "STF",
            "what_learning": "MRS",
            "sales_tech": "STF",
            "problem_solution": "SLA",
        }

        framework = pillar_defaults.get(pillar, "STF")

        # Keyword overrides
        text = f"{idea.title} {idea.core_insight}".lower()

        if any(kw in text for kw in ["mistake", "wrong", "failed", "error", "lesson"]):
            framework = "MRS"  # Mistake Recognition Service
        elif any(kw in text for kw in ["poll", "question", "ask", "curious"]):
            framework = "PIF"  # Problem-Insight-Forward
        elif any(kw in text for kw in ["journey", "arc", "evolution", "growth"]):
            framework = "SLA"  # Strategic Learning Arc

        # Validate framework is compatible with pillar
        try:
            framework_data = load_framework(framework, "linkedin")
            compatible = framework_data.get("compatible_pillars", [])
            if compatible and pillar not in compatible:
                # Fall back to a compatible framework
                framework = pillar_defaults.get(pillar, "STF")
        except FileNotFoundError:
            pass  # Use default if framework not found

        return framework

    def _generate_context_summary(
        self,
        idea: ContentIdea,
        context: dict[str, Any],
    ) -> str:
        """Generate a context summary relevant to the idea.

        Args:
            idea: The content idea
            context: Full aggregated context

        Returns:
            Relevant context summary string
        """
        # Find related themes/decisions/progress
        related: list[str] = []

        for theme in context.get("themes", []):
            if any(word in theme.lower() for word in idea.source_theme.lower().split()):
                related.append(f"Theme: {theme}")

        for decision in context.get("decisions", []):
            if any(word in decision.lower() for word in idea.source_theme.lower().split()):
                related.append(f"Decision: {decision}")

        for progress in context.get("progress", []):
            if any(word in progress.lower() for word in idea.source_theme.lower().split()):
                related.append(f"Progress: {progress}")

        if related:
            return " | ".join(related[:3])

        return f"Source: {idea.source_theme}"

    def _generate_structure_preview(self, framework: str, idea: ContentIdea) -> str:
        """Generate a structure preview based on framework.

        Args:
            framework: Selected framework name
            idea: The content idea

        Returns:
            Structure preview string
        """
        previews = {
            "STF": f"Problem: [specific challenge] → Tried: [what failed] → Worked: [{idea.core_insight[:50]}...] → Lesson: [actionable takeaway]",
            "MRS": f"Mistake: [what went wrong] → Recognition: [moment of clarity] → Solution: [{idea.core_insight[:50]}...]",
            "SLA": f"Starting Point: [where you were] → Learning Arc: [journey] → Arrival: [{idea.core_insight[:50]}...]",
            "PIF": f"Problem: [pain point] → Insight: [{idea.core_insight[:50]}...] → Forward: [what to do next]",
        }

        return previews.get(framework, f"Content about: {idea.title}")

    def _generate_rationale(
        self,
        idea: ContentIdea,
        pillar: str,
        framework: str,
        game: Game,
    ) -> str:
        """Generate rationale for planning decisions.

        Args:
            idea: The content idea
            pillar: Assigned pillar
            framework: Selected framework
            game: Selected game

        Returns:
            Rationale string explaining decisions
        """
        parts = [
            f"Pillar: {pillar} (audience value: {idea.audience_value})",
            f"Framework: {framework} (best fit for {pillar})",
            f"Game: {game.value} (based on current goal)",
        ]

        return " | ".join(parts)
