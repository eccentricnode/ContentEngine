"""Tests for PlatformRules constraint blueprint."""

from lib.blueprint_loader import load_constraints


def test_platformrules_loads_successfully() -> None:
    """Test that PlatformRules constraint loads without errors."""
    rules = load_constraints("PlatformRules")
    assert rules is not None
    assert rules["name"] == "PlatformRules"


def test_platformrules_required_fields() -> None:
    """Test that PlatformRules has all required fields."""
    rules = load_constraints("PlatformRules")

    assert "name" in rules
    assert "type" in rules
    assert "description" in rules
    assert "linkedin" in rules
    assert "validation" in rules


def test_platformrules_linkedin_character_limits() -> None:
    """Test LinkedIn character limit rules."""
    rules = load_constraints("PlatformRules")
    linkedin = rules["linkedin"]

    assert "character_limits" in linkedin
    limits = linkedin["character_limits"]

    assert limits["optimal_min"] == 800
    assert limits["optimal_max"] == 1200
    assert limits["absolute_max"] == 3000
    assert "description" in limits


def test_platformrules_linkedin_formatting_rules() -> None:
    """Test LinkedIn formatting rules structure."""
    rules = load_constraints("PlatformRules")
    linkedin = rules["linkedin"]

    assert "formatting_rules" in linkedin
    formatting = linkedin["formatting_rules"]

    # Verify all formatting rule categories
    assert "line_breaks" in formatting
    assert "emojis" in formatting
    assert "lists" in formatting
    assert "hashtags" in formatting
    assert "mentions" in formatting


def test_platformrules_linkedin_line_breaks() -> None:
    """Test LinkedIn line break rules."""
    rules = load_constraints("PlatformRules")
    line_breaks = rules["linkedin"]["formatting_rules"]["line_breaks"]

    assert line_breaks["required"] is True
    assert "description" in line_breaks
    assert "best_practices" in line_breaks
    assert len(line_breaks["best_practices"]) >= 3


def test_platformrules_linkedin_emojis() -> None:
    """Test LinkedIn emoji rules."""
    rules = load_constraints("PlatformRules")
    emojis = rules["linkedin"]["formatting_rules"]["emojis"]

    assert emojis["max_recommended"] == 3
    assert "description" in emojis
    assert "best_practices" in emojis


def test_platformrules_linkedin_hashtags() -> None:
    """Test LinkedIn hashtag rules."""
    rules = load_constraints("PlatformRules")
    hashtags = rules["linkedin"]["formatting_rules"]["hashtags"]

    assert hashtags["max_recommended"] == 5
    assert "placement" in hashtags
    assert "description" in hashtags
    assert "best_practices" in hashtags


def test_platformrules_linkedin_engagement_optimization() -> None:
    """Test LinkedIn engagement optimization rules."""
    rules = load_constraints("PlatformRules")
    linkedin = rules["linkedin"]

    assert "engagement_optimization" in linkedin
    engagement = linkedin["engagement_optimization"]

    assert "hook_placement" in engagement
    assert "First 2 lines" in engagement["hook_placement"]
    assert "call_to_action" in engagement
    assert "question_prompts" in engagement
    assert "readability" in engagement


def test_platformrules_linkedin_red_flags() -> None:
    """Test LinkedIn red flags list."""
    rules = load_constraints("PlatformRules")
    linkedin = rules["linkedin"]

    assert "red_flags" in linkedin
    red_flags = linkedin["red_flags"]

    assert isinstance(red_flags, list)
    assert len(red_flags) >= 5
    assert "Walls of text without line breaks" in red_flags
    assert "Excessive emojis (4+)" in red_flags


def test_platformrules_twitter_character_limits() -> None:
    """Test Twitter character limit rules."""
    rules = load_constraints("PlatformRules")

    assert "twitter" in rules
    twitter = rules["twitter"]

    assert "character_limits" in twitter
    limits = twitter["character_limits"]

    assert limits["per_tweet"] == 280
    assert "thread_recommended_max" in limits
    assert "description" in limits


def test_platformrules_blog_word_count() -> None:
    """Test Blog word count guidelines."""
    rules = load_constraints("PlatformRules")

    assert "blog" in rules
    blog = rules["blog"]

    assert "word_count" in blog
    word_count = blog["word_count"]

    assert "short_form" in word_count
    assert "medium_form" in word_count
    assert "long_form" in word_count
    assert "tutorial" in word_count


def test_platformrules_validation_severity_levels() -> None:
    """Test validation severity levels (errors, warnings, suggestions)."""
    rules = load_constraints("PlatformRules")

    assert "validation" in rules
    validation = rules["validation"]

    assert "errors" in validation
    assert "warnings" in validation
    assert "suggestions" in validation

    # Each severity level has description and examples
    for level in ["errors", "warnings", "suggestions"]:
        assert "description" in validation[level]
        assert "examples" in validation[level]
        assert len(validation[level]["examples"]) >= 3


def test_platformrules_cross_platform_rules() -> None:
    """Test cross-platform validation rules."""
    rules = load_constraints("PlatformRules")

    assert "cross_platform" in rules
    cross_platform = rules["cross_platform"]

    assert "accessibility" in cross_platform
    assert "brand_consistency" in cross_platform

    # Accessibility rules
    assert isinstance(cross_platform["accessibility"], list)
    assert len(cross_platform["accessibility"]) >= 3

    # Brand consistency rules
    assert isinstance(cross_platform["brand_consistency"], list)
    assert len(cross_platform["brand_consistency"]) >= 3


def test_platformrules_metadata() -> None:
    """Test PlatformRules metadata fields."""
    rules = load_constraints("PlatformRules")

    assert "version" in rules
    assert "last_updated" in rules
    assert "platform_support" in rules

    platform_support = rules["platform_support"]
    assert platform_support["linkedin"] == "complete"
    assert platform_support["twitter"] == "planned"
    assert platform_support["blog"] == "planned"


def test_platformrules_caching() -> None:
    """Test that PlatformRules is cached after first load."""
    from lib.blueprint_loader import _blueprint_cache, clear_cache

    # Clear cache first
    clear_cache()
    assert "constraint:PlatformRules" not in _blueprint_cache

    # First load
    rules1 = load_constraints("PlatformRules")
    assert "constraint:PlatformRules" in _blueprint_cache

    # Second load (from cache)
    rules2 = load_constraints("PlatformRules")
    assert rules1 is rules2  # Same object reference


def test_platformrules_type() -> None:
    """Test that PlatformRules type is constraint."""
    rules = load_constraints("PlatformRules")
    assert rules["type"] == "constraint"


def test_platformrules_description() -> None:
    """Test that PlatformRules has descriptive text."""
    rules = load_constraints("PlatformRules")
    description = rules["description"]

    assert len(description) > 50
    assert "platform-specific" in description.lower()
    assert "linkedin" in description.lower()
