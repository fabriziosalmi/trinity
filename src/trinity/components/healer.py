"""
Trinity Smart Healer - Intelligent Layout Fixing

Implements Strategy Pattern for different fix approaches:
1. CSS_BREAK_WORD: Inject Tailwind classes (break-all, overflow-wrap)
2. FONT_SHRINK: Reduce font size (text-4xl → text-2xl)
3. CSS_TRUNCATE: Inject truncate/ellipsis classes
4. CONTENT_CUT: Aggressive string shortening (nuclear option, last resort)
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from trinity.utils.logger import get_logger

logger = get_logger(__name__)


class HealingStrategy(str, Enum):
    """Available healing strategies (progressive escalation)."""

    CSS_BREAK_WORD = "css_break_word"
    FONT_SHRINK = "font_shrink"
    CSS_TRUNCATE = "css_truncate"
    CONTENT_CUT = "content_cut"


class HealingResult(BaseModel):
    """Result of a healing attempt."""

    strategy: HealingStrategy
    style_overrides: Dict[str, str] = Field(default_factory=dict)
    content_modified: bool = False
    modified_content: Optional[Dict[str, Any]] = None
    description: str = ""


class SmartHealer:
    """
    Intelligent layout fixing engine with progressive strategy escalation.

    Strategy Progression (per attempt):
    1. CSS_BREAK_WORD: Add break-all, overflow-wrap classes
    2. FONT_SHRINK: Reduce font size (text-4xl → text-3xl → text-2xl)
    3. CSS_TRUNCATE: Add truncate/ellipsis classes
    4. CONTENT_CUT: Nuclear option - truncate actual content
    """

    # Component-to-CSS-class mapping (based on themes.json)
    COMPONENT_MAP = {
        "hero_title": "hero_title",
        "hero_subtitle": "hero_subtitle",
        "card_title": "card_title",
        "card_description": "card_description",
        "brand_name": "brand_name",
        "tagline": "tagline",
    }

    # Font size progression (text-Nxl values)
    FONT_SIZES = ["text-6xl", "text-5xl", "text-4xl", "text-3xl", "text-2xl", "text-xl", "text-lg"]

    def __init__(self, truncate_length: int = 50):
        """
        Initialize SmartHealer.

        Args:
            truncate_length: Max string length for CONTENT_CUT strategy
        """
        self.truncate_length = truncate_length
        self.override_history: Dict[str, List[str]] = {}  # Track what we've tried
        logger.info(f"🚑 SmartHealer initialized (truncate_length={truncate_length})")

    def heal_layout(
        self, guardian_report: Dict[str, Any], content: Dict[str, Any], attempt: int
    ) -> HealingResult:
        """
        Apply progressive healing strategy based on attempt number.

        Args:
            guardian_report: Guardian audit report
            content: Current content dictionary
            attempt: Current attempt number (1, 2, 3, ...)

        Returns:
            HealingResult with style overrides or modified content
        """
        logger.info(f"🚑 Healing attempt {attempt}")

        # Determine strategy based on attempt
        if attempt == 1:
            return self._apply_break_word_strategy(guardian_report)
        elif attempt == 2:
            return self._apply_font_shrink_strategy(guardian_report, content)
        elif attempt == 3:
            return self._apply_truncate_strategy(guardian_report)
        else:
            # Nuclear option: cut content
            return self._apply_content_cut_strategy(content, attempt)

    def _apply_break_word_strategy(self, report: Dict[str, Any]) -> HealingResult:
        """
        Strategy 1: Add CSS classes to force word breaking.

        NUCLEAR FIX (v0.5.0): break-all is extremely aggressive - breaks mid-word if needed.
        This handles pathological strings like "AAAAAAAAAAAAA..." without spaces.

        Injects: break-all, whitespace-normal, overflow-wrap-anywhere

        CRITICAL FIX (2025-01-26): Use correct theme_classes keys that match templates:
        - heading_primary (hero h1, section h2)
        - heading_secondary (card h3)
        - body_text (all <p> tags)
        """
        logger.info("📊 Strategy 1: CSS_BREAK_WORD - Adding nuclear break-all classes")

        # Apply nuclear CSS to all text components
        # break-all: Forces breaking even mid-word (no mercy)
        # whitespace-normal: Ensures whitespace can wrap
        # overflow-wrap-anywhere: Backup for extreme cases
        nuclear_css = "break-all whitespace-normal overflow-wrap-anywhere"

        overrides = {
            # Template keys (match theme_classes.X in templates)
            "heading_primary": nuclear_css,  # Hero h1, section h2
            "heading_secondary": nuclear_css,  # Card h3
            "body_text": nuclear_css,  # All <p> tags
            # Legacy keys (for backward compatibility)
            "hero_title": nuclear_css,
            "hero_subtitle": nuclear_css,
            "card_title": nuclear_css,
            "card_description": nuclear_css,
            "tagline": nuclear_css,
        }

        return HealingResult(
            strategy=HealingStrategy.CSS_BREAK_WORD,
            style_overrides=overrides,
            content_modified=False,
            description="Injected NUCLEAR break-all (mid-word breaking) to all text components via theme_classes keys",
        )

    def _apply_font_shrink_strategy(
        self, report: Dict[str, Any], content: Dict[str, Any]
    ) -> HealingResult:
        """
        Strategy 2: Reduce font sizes progressively.

        Finds text-Nxl classes and reduces them by one level.
        Uses theme_classes keys to match templates.
        """
        logger.info("📊 Strategy 2: FONT_SHRINK - Reducing font sizes")

        overrides = {
            # Template keys (match theme_classes.X)
            "heading_primary": "text-3xl break-all",  # Shrink hero/section headings
            "heading_secondary": "text-xl break-all",  # Shrink card headings
            "body_text": "text-base break-words",  # Keep body readable
            # Legacy keys
            "hero_title": "text-3xl break-all",
            "hero_subtitle": "text-lg break-words",
            "card_title": "text-xl break-all",
        }

        return HealingResult(
            strategy=HealingStrategy.FONT_SHRINK,
            style_overrides=overrides,
            content_modified=False,
            description="Reduced font sizes: headings (text-3xl/xl), body (text-base)",
        )

    def _apply_truncate_strategy(self, report: Dict[str, Any]) -> HealingResult:
        """
        Strategy 3: Add CSS truncate/ellipsis classes.

        Uses Tailwind's truncate, line-clamp utilities.
        Uses theme_classes keys to match templates.
        """
        logger.info("📊 Strategy 3: CSS_TRUNCATE - Adding ellipsis classes")

        overrides = {
            # Template keys (match theme_classes.X)
            "heading_primary": "truncate text-2xl",  # Hero/section headings
            "heading_secondary": "truncate text-lg",  # Card headings
            "body_text": "line-clamp-3 text-sm",  # Body paragraphs
            # Legacy keys
            "hero_title": "truncate text-2xl",
            "hero_subtitle": "line-clamp-2 text-base",
            "card_title": "truncate text-lg",
            "card_description": "line-clamp-3 text-sm",
            "tagline": "truncate",
        }

        return HealingResult(
            strategy=HealingStrategy.CSS_TRUNCATE,
            style_overrides=overrides,
            content_modified=False,
            description="Added truncate and line-clamp classes with reduced font sizes",
        )

    def _apply_content_cut_strategy(self, content: Dict[str, Any], attempt: int) -> HealingResult:
        """
        Strategy 4 (Nuclear): Actually modify the content by truncating strings.

        Progressively more aggressive based on attempt number.
        """
        # More aggressive with each attempt beyond 3
        max_len = max(30, self.truncate_length - (attempt - 4) * 10)

        logger.info(f"📊 Strategy 4 (NUCLEAR): CONTENT_CUT - Truncating to {max_len} chars")
        logger.warning("⚠️  Resorting to content truncation - CSS strategies failed")

        modified = self._truncate_recursive(content, max_len)

        return HealingResult(
            strategy=HealingStrategy.CONTENT_CUT,
            style_overrides={},
            content_modified=True,
            modified_content=modified,
            description=f"Truncated all strings to {max_len} characters (nuclear option)",
        )

    def _truncate_recursive(self, data: Any, max_len: int) -> Any:
        """
        Recursively truncate all strings in nested data structure.

        Args:
            data: Data to truncate
            max_len: Maximum string length

        Returns:
            Truncated data
        """
        if isinstance(data, dict):
            return {k: self._truncate_recursive(v, max_len) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._truncate_recursive(i, max_len) for i in data]
        elif isinstance(data, str):
            if len(data) > max_len:
                truncated = data[:max_len] + "..."
                logger.debug(f"✂️  Truncated: '{data[:20]}...' → '{truncated}'")
                return truncated
            return data
        return data


# Standalone helper function for backwards compatibility
def apply_emergency_truncate(data: Any, max_len: int = 60) -> Any:
    """
    Legacy truncation function for backwards compatibility.

    Args:
        data: Data to truncate
        max_len: Maximum string length

    Returns:
        Truncated data
    """
    healer = SmartHealer(truncate_length=max_len)
    return healer._truncate_recursive(data, max_len)
