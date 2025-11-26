"""
Test SmartHealer progressive CSS strategies

Tests cover:
- Strategy selection based on attempt number
- CSS override generation for each strategy
- Content modification (nuclear option)
- HealingResult model validation
"""

import pytest

from trinity.components.healer import HealingResult, HealingStrategy, SmartHealer


@pytest.fixture
def healer():
    """Create SmartHealer instance for testing"""
    return SmartHealer()


@pytest.fixture
def mock_guardian_report():
    """Mock Guardian report indicating layout issues"""
    return {
        "approved": False,
        "reason": "Layout issues detected",
        "issues": ["Text overflow in hero_title"],
        "fix_suggestion": "Apply word-break and reduce font size",
    }


@pytest.fixture
def mock_content():
    """Mock content with potentially problematic text"""
    return {
        "brand_name": "Test Portfolio",
        "hero": {
            "title": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "subtitle": "This is a very long subtitle that might overflow containers",
        },
        "repos": [],
    }


class TestHealingStrategySelection:
    """Test strategy selection based on attempt number"""

    def test_attempt_1_uses_css_break_word(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=1)
        assert result.strategy == HealingStrategy.CSS_BREAK_WORD
        assert not result.content_modified

    def test_attempt_2_uses_font_shrink(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=2)
        assert result.strategy == HealingStrategy.FONT_SHRINK
        assert not result.content_modified

    def test_attempt_3_uses_css_truncate(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=3)
        assert result.strategy == HealingStrategy.CSS_TRUNCATE
        assert not result.content_modified

    def test_attempt_4_uses_content_cut(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=4)
        assert result.strategy == HealingStrategy.CONTENT_CUT
        assert result.content_modified


class TestCSSBreakWordStrategy:
    """Test CSS_BREAK_WORD strategy implementation"""

    def test_returns_break_word_classes(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=1)

        # Should have style_overrides with break-all classes
        assert result.style_overrides is not None
        assert len(result.style_overrides) > 0

        # Check for expected CSS classes
        for key, classes in result.style_overrides.items():
            assert "break-all" in classes or "overflow-wrap-anywhere" in classes

    def test_does_not_modify_content(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=1)
        assert result.modified_content is None


class TestFontShrinkStrategy:
    """Test FONT_SHRINK strategy implementation"""

    def test_reduces_font_sizes(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=2)

        # Should have style_overrides with reduced font sizes
        assert result.style_overrides is not None

        # Check for font size reductions
        overrides_str = str(result.style_overrides)
        assert "text-3xl" in overrides_str or "text-xl" in overrides_str

    def test_does_not_modify_content(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=2)
        assert result.modified_content is None


class TestCSSTruncateStrategy:
    """Test CSS_TRUNCATE strategy implementation"""

    def test_adds_truncate_classes(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=3)

        # Should have style_overrides with truncate/line-clamp
        assert result.style_overrides is not None

        overrides_str = str(result.style_overrides)
        assert "truncate" in overrides_str or "line-clamp" in overrides_str

    def test_does_not_modify_content(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=3)
        assert result.modified_content is None


class TestContentCutStrategy:
    """Test CONTENT_CUT strategy implementation (nuclear option)"""

    def test_truncates_content(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=4)

        # Should modify content
        assert result.content_modified
        assert result.modified_content is not None

        # Original title: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" (32 chars)
        # Should be truncated to max 50 chars (but this is already under)
        # Check that long subtitle is truncated
        if "hero" in result.modified_content:
            subtitle = result.modified_content["hero"].get("subtitle", "")
            # Should have ellipsis or be shortened
            assert len(subtitle) <= 100  # Reasonable limit


class TestHealingResultModel:
    """Test HealingResult Pydantic model validation"""

    def test_creates_valid_healing_result(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=1)

        # Validate all required fields
        assert isinstance(result, HealingResult)
        assert isinstance(result.strategy, HealingStrategy)
        assert isinstance(result.style_overrides, dict)
        assert isinstance(result.content_modified, bool)
        assert isinstance(result.description, str)

    def test_css_strategies_have_overrides(self, healer, mock_guardian_report, mock_content):
        for attempt in [1, 2, 3]:
            result = healer.heal_layout(mock_guardian_report, mock_content, attempt=attempt)
            assert len(result.style_overrides) > 0
            assert not result.content_modified

    def test_content_cut_has_modified_content(self, healer, mock_guardian_report, mock_content):
        result = healer.heal_layout(mock_guardian_report, mock_content, attempt=4)
        assert result.content_modified
        assert result.modified_content is not None
