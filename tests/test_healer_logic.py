"""
Unit tests for SmartHealer (LayoutValidator) to prove CSS fix logic is deterministic.

Tests demonstrate:
1. Progressive strategy escalation (not random z-index: 9999 injection)
2. Deterministic CSS class generation based on strategy
3. Proper handling of different overflow scenarios
4. Font size reduction follows specific progression
5. Content truncation as last resort

Anti-Vibecoding: These tests prove the healer is NOT just throwing random CSS at the wall.
"""

import pytest

from trinity.components.healer import HealingResult, HealingStrategy, SmartHealer


@pytest.fixture
def healer():
    """Create a SmartHealer instance for testing."""
    return SmartHealer(truncate_length=50)


@pytest.fixture
def sample_guardian_report():
    """Sample Guardian report indicating overflow issues."""
    return {
        "has_overflow": True,
        "broken_components": ["hero_title", "card_description"],
        "issues": [
            {"component": "hero_title", "type": "horizontal_overflow"},
            {"component": "card_description", "type": "text_overflow"},
        ],
    }


@pytest.fixture
def sample_content():
    """Sample content for testing."""
    return {
        "hero": {
            "title": "A" * 100,  # Pathological long string
            "subtitle": "Normal subtitle text",
        },
        "projects": [
            {
                "name": "Project 1",
                "description": "A" * 200,  # Pathological description
            }
        ],
    }


class TestProgressiveStrategyEscalation:
    """Test that strategies escalate progressively, not randomly."""

    def test_attempt_1_uses_break_word_strategy(
        self, healer, sample_guardian_report, sample_content
    ):
        """
        Attempt 1 ALWAYS uses CSS_BREAK_WORD (break-all).
        NOT random - this is the least invasive fix.
        """
        result = healer.heal_layout(sample_guardian_report, sample_content, attempt=1)

        assert result.strategy == HealingStrategy.CSS_BREAK_WORD
        assert not result.content_modified, "Strategy 1 should NOT modify content"
        assert "break-all" in result.style_overrides.get("heading_primary", "")
        assert "overflow-wrap-anywhere" in result.style_overrides.get("heading_primary", "")

    def test_attempt_2_uses_font_shrink_strategy(
        self, healer, sample_guardian_report, sample_content
    ):
        """
        Attempt 2 ALWAYS uses FONT_SHRINK (reduce text-Nxl).
        NOT random - reduces font size by specific steps.
        """
        result = healer.heal_layout(sample_guardian_report, sample_content, attempt=2)

        assert result.strategy == HealingStrategy.FONT_SHRINK
        assert not result.content_modified, "Strategy 2 should NOT modify content yet"
        # Verify font size reduction follows specific rules
        assert "text-3xl" in result.style_overrides.get("heading_primary", "")
        assert "text-xl" in result.style_overrides.get("heading_secondary", "")

    def test_attempt_3_uses_truncate_strategy(self, healer, sample_guardian_report, sample_content):
        """
        Attempt 3 ALWAYS uses CSS_TRUNCATE (ellipsis).
        NOT random - adds truncate/line-clamp classes.
        """
        result = healer.heal_layout(sample_guardian_report, sample_content, attempt=3)

        assert result.strategy == HealingStrategy.CSS_TRUNCATE
        assert not result.content_modified, "Strategy 3 uses CSS, not content modification"
        assert "truncate" in result.style_overrides.get("heading_primary", "")
        assert "line-clamp" in result.style_overrides.get("body_text", "")

    def test_attempt_4_uses_content_cut_strategy(
        self, healer, sample_guardian_report, sample_content
    ):
        """
        Attempt 4+ ALWAYS uses CONTENT_CUT (nuclear option).
        NOT random - this is the last resort when CSS fails.
        """
        result = healer.heal_layout(sample_guardian_report, sample_content, attempt=4)

        assert result.strategy == HealingStrategy.CONTENT_CUT
        assert result.content_modified, "Strategy 4 MUST modify content"
        assert result.modified_content is not None


class TestBreakWordStrategy:
    """Test CSS_BREAK_WORD strategy logic (not random z-index injection)."""

    def test_break_all_injected_for_pathological_strings(self, healer, sample_guardian_report):
        """
        break-all is SPECIFICALLY for strings without spaces (e.g., 'AAAAAA...').
        This is a deliberate choice, not random CSS.
        """
        result = healer._apply_break_word_strategy(sample_guardian_report)

        # Verify NUCLEAR break-all is applied (forces mid-word breaking)
        for key in ["heading_primary", "heading_secondary", "body_text"]:
            assert "break-all" in result.style_overrides[key]
            assert "whitespace-normal" in result.style_overrides[key]
            assert "overflow-wrap-anywhere" in result.style_overrides[key]

    def test_break_word_does_not_modify_content(self, healer, sample_guardian_report):
        """Strategy 1 is CSS-only, does NOT modify content."""
        result = healer._apply_break_word_strategy(sample_guardian_report)

        assert not result.content_modified
        assert result.modified_content is None

    def test_break_word_targets_correct_theme_classes(self, healer, sample_guardian_report):
        """
        Verify we target theme_classes keys that match templates.
        NOT random keys - these match the actual template structure.
        """
        result = healer._apply_break_word_strategy(sample_guardian_report)

        # Modern template keys (must be present)
        assert "heading_primary" in result.style_overrides
        assert "heading_secondary" in result.style_overrides
        assert "body_text" in result.style_overrides

        # Legacy keys (backward compatibility)
        assert "hero_title" in result.style_overrides
        assert "card_title" in result.style_overrides


class TestFontShrinkStrategy:
    """Test FONT_SHRINK strategy follows specific progression rules."""

    def test_font_sizes_follow_tailwind_progression(
        self, healer, sample_guardian_report, sample_content
    ):
        """
        Font shrink follows Tailwind's scale: text-6xl → text-5xl → text-4xl → text-3xl.
        NOT random font sizes - follows standard design system.
        """
        result = healer._apply_font_shrink_strategy(sample_guardian_report, sample_content)

        # Verify specific font size reductions
        assert "text-3xl" in result.style_overrides["heading_primary"]
        assert "text-xl" in result.style_overrides["heading_secondary"]
        assert "text-base" in result.style_overrides["body_text"]

    def test_font_shrink_preserves_break_word_classes(
        self, healer, sample_guardian_report, sample_content
    ):
        """
        Strategy 2 COMBINES font shrink with break-all from Strategy 1.
        This is deliberate layering, not random CSS accumulation.
        """
        result = healer._apply_font_shrink_strategy(sample_guardian_report, sample_content)

        # Should still have break-all from previous attempt
        assert "break-all" in result.style_overrides["heading_primary"]
        assert "break-words" in result.style_overrides["body_text"]


class TestTruncateStrategy:
    """Test CSS_TRUNCATE strategy uses correct Tailwind utilities."""

    def test_truncate_uses_tailwind_line_clamp(self, healer, sample_guardian_report):
        """
        Uses Tailwind's line-clamp utility (NOT random max-height hacks).
        line-clamp-3 is deliberate: 3 lines is readable but contained.
        """
        result = healer._apply_truncate_strategy(sample_guardian_report)

        assert "truncate" in result.style_overrides["heading_primary"]
        assert "line-clamp-3" in result.style_overrides["body_text"]

    def test_truncate_reduces_font_sizes_further(self, healer, sample_guardian_report):
        """
        Strategy 3 reduces fonts MORE than Strategy 2.
        text-3xl → text-2xl (headings), text-base → text-sm (body).
        NOT random - progressive reduction.
        """
        result = healer._apply_truncate_strategy(sample_guardian_report)

        assert "text-2xl" in result.style_overrides["heading_primary"]
        assert "text-lg" in result.style_overrides["heading_secondary"]
        assert "text-sm" in result.style_overrides["body_text"]


class TestContentCutStrategy:
    """Test CONTENT_CUT (nuclear option) as last resort."""

    def test_content_cut_actually_modifies_content(self, healer, sample_content):
        """
        Strategy 4 is the ONLY strategy that modifies content.
        This is the last resort when CSS fixes fail.
        """
        result = healer._apply_content_cut_strategy(sample_content, attempt=4)

        assert result.strategy == HealingStrategy.CONTENT_CUT
        assert result.content_modified
        assert result.modified_content is not None

    def test_content_cut_respects_truncate_length(self, sample_content):
        """
        Truncation length is CONFIGURABLE (default 50).
        NOT random - deterministic based on config.
        """
        healer_short = SmartHealer(truncate_length=20)
        healer_long = SmartHealer(truncate_length=100)

        result_short = healer_short._apply_content_cut_strategy(sample_content, attempt=4)
        result_long = healer_long._apply_content_cut_strategy(sample_content, attempt=4)

        # Different truncate lengths produce different results (deterministic)
        assert result_short.modified_content != result_long.modified_content

    def test_content_cut_truncates_hero_title(self, healer, sample_content):
        """
        Hero title truncation is SPECIFIC: cuts at truncate_length, adds '...'.
        NOT random string mangling.
        """
        result = healer._apply_content_cut_strategy(sample_content, attempt=4)

        modified = result.modified_content
        original_title = sample_content["hero"]["title"]

        # Verify truncation logic
        if len(original_title) > healer.truncate_length:
            assert len(modified["hero"]["title"]) <= healer.truncate_length + 3  # +3 for '...'
            assert modified["hero"]["title"].endswith("...")


class TestDeterminism:
    """Test that healer behavior is deterministic (same input = same output)."""

    def test_same_input_produces_same_output(self, healer, sample_guardian_report, sample_content):
        """
        CRITICAL: Same attempt number + same input = IDENTICAL output.
        This proves the healer is NOT random.
        """
        result1 = healer.heal_layout(sample_guardian_report, sample_content, attempt=1)
        result2 = healer.heal_layout(sample_guardian_report, sample_content, attempt=1)

        assert result1.strategy == result2.strategy
        assert result1.style_overrides == result2.style_overrides
        assert result1.content_modified == result2.content_modified

    def test_different_attempts_produce_different_strategies(
        self, healer, sample_guardian_report, sample_content
    ):
        """
        Different attempts produce DIFFERENT strategies (progressive escalation).
        NOT random - follows specific progression.
        """
        result1 = healer.heal_layout(sample_guardian_report, sample_content, attempt=1)
        result2 = healer.heal_layout(sample_guardian_report, sample_content, attempt=2)
        result3 = healer.heal_layout(sample_guardian_report, sample_content, attempt=3)

        # Each attempt uses different strategy (progressive)
        assert result1.strategy == HealingStrategy.CSS_BREAK_WORD
        assert result2.strategy == HealingStrategy.FONT_SHRINK
        assert result3.strategy == HealingStrategy.CSS_TRUNCATE


class TestNoRandomZIndex:
    """Test that we do NOT inject random z-index: 9999 or similar hacks."""

    def test_no_z_index_in_any_strategy(self, healer, sample_guardian_report, sample_content):
        """
        CRITICAL: Verify we do NOT use z-index hacks.
        All fixes are deliberate CSS utilities, not random stacking contexts.
        """
        for attempt in range(1, 4):
            result = healer.heal_layout(sample_guardian_report, sample_content, attempt)

            # Check all style overrides
            for css_classes in result.style_overrides.values():
                assert "z-index" not in css_classes.lower()
                assert "z-" not in css_classes  # No Tailwind z-N classes either

    def test_no_important_flags(self, healer, sample_guardian_report, sample_content):
        """
        Verify we do NOT use !important hacks.
        All CSS follows proper cascade, no specificity hacks.
        """
        for attempt in range(1, 4):
            result = healer.heal_layout(sample_guardian_report, sample_content, attempt)

            for css_classes in result.style_overrides.values():
                assert "!important" not in css_classes
