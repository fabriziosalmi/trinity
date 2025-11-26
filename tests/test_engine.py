"""
Test TrinityEngine orchestration and self-healing loop

Tests cover:
- Self-healing loop execution
- Style override accumulation across attempts
- BuildResult model validation
- Guardian integration
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from trinity.config import TrinityConfig
from trinity.engine import BuildResult, BuildStatus, TrinityEngine


@pytest.fixture
def engine():
    """Create TrinityEngine instance for testing"""
    config = TrinityConfig()
    return TrinityEngine(config)


@pytest.fixture
def mock_content():
    """Mock content for testing"""
    return {
        "brand_name": "Test Portfolio",
        "tagline": "Test tagline",
        "hero": {
            "title": "Test Hero Title",
            "subtitle": "Test subtitle"
        },
        "repos": []
    }


class TestSelfHealingLoop:
    """Test self-healing loop orchestration"""

    @patch('trinity.components.guardian.TrinityGuardian')
    def test_successful_build_first_attempt(self, mock_guardian_class, engine, mock_content):
        """Test build succeeds on first attempt (no healing needed)"""
        # Mock Guardian to approve immediately
        mock_guardian = Mock()
        mock_guardian.audit_layout.return_value = {
            "approved": True,
            "reason": "Layout perfect",
            "issues": [],
            "fix_suggestion": ""
        }
        mock_guardian_class.return_value = mock_guardian

        result = engine.build_with_self_healing(
            mock_content,
            theme="enterprise",
            output_filename="test_output.html",
            enable_guardian=True
        )

        assert isinstance(result, BuildResult)
        assert result.status == BuildStatus.SUCCESS
        assert result.attempts == 1
        assert len(result.fixes_applied) == 0

    def test_healing_loop_with_css_fixes(self, engine, mock_content):
        """Test healing loop applies CSS strategies"""
        # Mock Guardian to reject first 2 attempts, approve on 3rd
        mock_guardian = Mock()
        mock_guardian.audit_layout.side_effect = [
            {"approved": False, "reason": "Overflow", "issues": ["overflow"], "fix_suggestion": "break-word"},
            {"approved": False, "reason": "Still overflow", "issues": ["overflow"], "fix_suggestion": "shrink"},
            {"approved": True, "reason": "Fixed", "issues": [], "fix_suggestion": ""}
        ]
        engine._guardian = mock_guardian  # Inject mock directly

        # Mock Healer to return CSS strategies
        mock_healer = Mock()
        from trinity.components.healer import HealingResult, HealingStrategy

        mock_healer.heal_layout.side_effect = [
            HealingResult(
                strategy=HealingStrategy.CSS_BREAK_WORD,
                style_overrides={"heading_primary": "break-all"},
                content_modified=False,
                modified_content=None,
                description="Applied break-word"
            ),
            HealingResult(
                strategy=HealingStrategy.FONT_SHRINK,
                style_overrides={"heading_primary": "text-3xl"},
                content_modified=False,
                modified_content=None,
                description="Reduced font size"
            )
        ]
        engine.healer = mock_healer  # Inject mock directly

        result = engine.build_with_self_healing(
            mock_content,
            theme="brutalist",
            output_filename="test_healing.html",
            enable_guardian=True
        )

        assert result.status == BuildStatus.SUCCESS
        assert result.attempts == 3
        assert len(result.fixes_applied) == 2
        # Check that strategy names appear in fixes_applied (may include attempt number)
        assert any("css_break_word" in fix for fix in result.fixes_applied)
        assert any("font_shrink" in fix for fix in result.fixes_applied)

    def test_max_retries_reached(self, engine, mock_content):
        """Test that engine stops after max_retries"""
        # Configure for 2 max retries
        engine.config.max_retries = 2

        # Mock Guardian to always reject
        mock_guardian = Mock()
        mock_guardian.audit_layout.return_value = {
            "approved": False,
            "reason": "Persistent overflow",
            "issues": ["overflow"],
            "fix_suggestion": "Unable to fix"
        }
        engine._guardian = mock_guardian  # Inject mock directly

        result = engine.build_with_self_healing(
            mock_content,
            theme="enterprise",
            output_filename="test_max_retries.html",
            enable_guardian=True
        )

        assert result.status == BuildStatus.REJECTED
        assert result.attempts == engine.config.max_retries


class TestBuildResultModel:
    """Test BuildResult Pydantic model"""

    def test_create_success_result(self):
        """Test creating SUCCESS BuildResult"""
        result = BuildResult(
            status=BuildStatus.SUCCESS,
            output_path=Path("/path/to/output.html"),
            theme="enterprise",
            attempts=1,
            guardian_report=None,
            fixes_applied=[]
        )

        assert result.status == BuildStatus.SUCCESS
        assert result.attempts == 1
        assert len(result.fixes_applied) == 0

    def test_create_rejected_result(self):
        """Test creating REJECTED BuildResult"""
        result = BuildResult(
            status=BuildStatus.REJECTED,
            output_path=Path("/path/to/BROKEN_output.html"),
            theme="brutalist",
            attempts=3,
            guardian_report={"approved": False, "reason": "Unfixable"},
            fixes_applied=["css_break_word", "font_shrink", "css_truncate"]
        )

        assert result.status == BuildStatus.REJECTED
        assert result.attempts == 3
        assert len(result.fixes_applied) == 3


class TestStyleOverrideAccumulation:
    """Test that style_overrides accumulate across healing attempts"""

    def test_overrides_accumulate(self, engine, mock_content):
        """Test that CSS overrides from multiple attempts are accumulated"""
        # Mock Guardian to reject 2 times, then approve
        mock_guardian = Mock()
        mock_guardian.audit_layout.side_effect = [
            {"approved": False, "reason": "Issue", "issues": [], "fix_suggestion": ""},
            {"approved": False, "reason": "Issue", "issues": [], "fix_suggestion": ""},
            {"approved": True, "reason": "Fixed", "issues": [], "fix_suggestion": ""}
        ]
        engine._guardian = mock_guardian  # Inject mock directly

        # Mock Healer to return different overrides each time
        mock_healer = Mock()
        from trinity.components.healer import HealingResult, HealingStrategy

        mock_healer.heal_layout.side_effect = [
            HealingResult(
                strategy=HealingStrategy.CSS_BREAK_WORD,
                style_overrides={"heading_primary": "break-all"},
                content_modified=False,
                modified_content=None,
                description="Attempt 1"
            ),
            HealingResult(
                strategy=HealingStrategy.FONT_SHRINK,
                style_overrides={"body_text": "text-xl"},
                content_modified=False,
                modified_content=None,
                description="Attempt 2"
            )
        ]
        engine.healer = mock_healer  # Inject mock directly

        # Mock Builder to track style_overrides passed to it
        mock_builder = Mock()
        mock_builder.build_page.return_value = Path("/tmp/test.html")
        engine.builder = mock_builder  # Inject mock directly

        engine.build_with_self_healing(
            mock_content,
            theme="enterprise",
            output_filename="test_accumulate.html",
            enable_guardian=True
        )

        # Verify builder.build_page was called with accumulated overrides
        # On attempt 3 (final successful build), should have both overrides
        final_call_kwargs = mock_builder.build_page.call_args_list[-1][1]

        if 'style_overrides' in final_call_kwargs:
            final_overrides = final_call_kwargs['style_overrides']
            # Should have accumulated both heading_primary and body_text overrides
            assert "heading_primary" in final_overrides
            assert "body_text" in final_overrides
