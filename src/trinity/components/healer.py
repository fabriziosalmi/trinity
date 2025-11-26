"""
Trinity Smart Healer - Intelligent Layout Fixing

Implements Strategy Pattern for different fix approaches:
1. CSS_BREAK_WORD: Inject Tailwind classes (break-all, overflow-wrap)
2. CSS_TRUNCATE: Inject truncate/ellipsis classes
3. CONTENT_TRUNCATE: Aggressive string shortening (last resort)
"""
from enum import Enum
from typing import Any, Dict, List
from pathlib import Path

from trinity.utils.logger import get_logger

logger = get_logger(__name__)


class FixStrategy(str, Enum):
    """Available fix strategies for layout issues."""
    CSS_BREAK_WORD = "css_break_word"
    CSS_TRUNCATE = "css_truncate"
    CONTENT_TRUNCATE = "content_truncate"
    FONT_SHRINK = "font_shrink"


class SmartHealer:
    """
    Intelligent layout fixing engine.
    
    Analyzes Guardian reports and applies appropriate fixes using
    a strategy pattern approach.
    """
    
    def __init__(self, truncate_length: int = 50):
        """
        Initialize SmartHealer.
        
        Args:
            truncate_length: Max string length for CONTENT_TRUNCATE strategy
        """
        self.truncate_length = truncate_length
        logger.info(f"🚑 SmartHealer initialized (truncate_length={truncate_length})")
    
    def analyze_guardian_report(self, report: Dict[str, Any]) -> FixStrategy:
        """
        Analyze Guardian report and determine best fix strategy.
        
        Args:
            report: Guardian audit report
            
        Returns:
            Recommended fix strategy
        """
        reason = report.get("reason", "").lower()
        suggestion = report.get("fix_suggestion", "").upper()
        
        # DOM overflow -> Try CSS fix first
        if "overflow" in reason or "DOM" in suggestion:
            logger.info("📊 Detected DOM overflow → Recommending CSS_BREAK_WORD")
            return FixStrategy.CSS_BREAK_WORD
        
        # Text clipping -> Truncate with ellipsis
        if "clipped" in reason or "truncate" in suggestion.lower():
            logger.info("📊 Detected text clipping → Recommending CSS_TRUNCATE")
            return FixStrategy.CSS_TRUNCATE
        
        # Default fallback
        logger.info("📊 No specific issue detected → Recommending CONTENT_TRUNCATE")
        return FixStrategy.CONTENT_TRUNCATE
    
    def apply_fix(
        self,
        content: Dict[str, Any],
        strategy: FixStrategy,
        attempt: int = 1
    ) -> Dict[str, Any]:
        """
        Apply fix strategy to content.
        
        Args:
            content: Content dictionary to fix
            strategy: Fix strategy to apply
            attempt: Current attempt number (affects aggressiveness)
            
        Returns:
            Fixed content dictionary
        """
        logger.info(f"🚑 Applying fix: {strategy.value} (attempt {attempt})")
        
        if strategy == FixStrategy.CSS_BREAK_WORD:
            # TODO Phase 2: Inject CSS classes into template
            # For now, fallback to content truncate
            logger.warning("⚠️  CSS_BREAK_WORD not yet implemented, falling back to CONTENT_TRUNCATE")
            return self._apply_content_truncate(content, max_len=self.truncate_length)
        
        elif strategy == FixStrategy.CSS_TRUNCATE:
            # TODO Phase 2: Inject truncate classes
            logger.warning("⚠️  CSS_TRUNCATE not yet implemented, falling back to CONTENT_TRUNCATE")
            return self._apply_content_truncate(content, max_len=self.truncate_length)
        
        elif strategy == FixStrategy.FONT_SHRINK:
            # TODO Phase 2: Modify theme config to use smaller fonts
            logger.warning("⚠️  FONT_SHRINK not yet implemented, falling back to CONTENT_TRUNCATE")
            return self._apply_content_truncate(content, max_len=self.truncate_length)
        
        elif strategy == FixStrategy.CONTENT_TRUNCATE:
            # Progressively more aggressive based on attempt
            max_len = max(30, self.truncate_length - (attempt - 1) * 10)
            return self._apply_content_truncate(content, max_len=max_len)
        
        return content
    
    def _apply_content_truncate(self, data: Any, max_len: int) -> Any:
        """
        Recursively truncate all strings in nested data structure.
        
        Args:
            data: Data to truncate
            max_len: Maximum string length
            
        Returns:
            Truncated data
        """
        if isinstance(data, dict):
            return {k: self._apply_content_truncate(v, max_len) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._apply_content_truncate(i, max_len) for i in data]
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
    return healer._apply_content_truncate(data, max_len)
