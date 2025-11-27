"""
Trinity - Text Processor (The Enforcer)
Rule #8: No magic strings - all rules from config
Rule #14: Single responsibility - only text transformation
Rule #7: Explicit error handling with graceful degradation
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError

from trinity.utils.logger import get_logger

# Rule #28: Structured logging
logger = get_logger(__name__)

# Rule #8: No magic paths
DEFAULT_RULES_PATH = "config/content_rules.json"


class TextTransformationRules(BaseModel):
    """Pydantic schema for text transformation rules."""

    force_uppercase: Optional[bool] = False
    title_case: Optional[bool] = False
    capitalize_first: Optional[bool] = False
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    strip_extra_punctuation: Optional[bool] = False
    force_punctuation: Optional[str] = None
    suffix: Optional[str] = ""
    padding_suffix: Optional[str] = ""
    profanity_filter: Optional[bool] = False
    remove_fluff_words: Optional[List[str]] = Field(default_factory=list)
    replace_casual_terms: Optional[Dict[str, str]] = Field(default_factory=dict)


class ThemeRules(BaseModel):
    """Complete theme transformation configuration."""

    description: str
    transformations: Dict[str, TextTransformationRules]
    field_mapping: Dict[str, str]


class ContentRulesConfig(BaseModel):
    """Root configuration for all themes."""

    brutalist: ThemeRules
    editorial: ThemeRules
    enterprise: ThemeRules


class TextProcessorError(Exception):
    """Base exception for TextProcessor errors."""

    pass


class TextProcessor:
    """
    Configuration-driven text transformation engine.

    Responsibilities:
    - Load transformation rules from config
    - Apply deterministic transformations to content
    - Handle nested dictionaries and lists recursively

    Does NOT:
    - Generate content (handled by ContentEngine)
    - Validate content schema (handled by Validator)
    - Build HTML (handled by SiteBuilder)
    """

    def __init__(self, rules_path: str = DEFAULT_RULES_PATH):
        """
        Initialize TextProcessor with rules configuration.

        Args:
            rules_path: Path to content_rules.json

        Raises:
            FileNotFoundError: If rules config doesn't exist
            TextProcessorError: If config is invalid
        """
        path = Path(rules_path)
        if not path.exists():
            raise FileNotFoundError(f"Content rules not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_config = json.load(f)

            # Remove metadata before validation
            raw_config.pop("_meta", None)

            # Validate with Pydantic
            self.config = ContentRulesConfig(**raw_config)

            logger.info(f"TextProcessor initialized with rules from: {path}")

        except json.JSONDecodeError as e:
            raise TextProcessorError(f"Invalid JSON in rules config: {e}")
        except ValidationError as e:
            raise TextProcessorError(f"Invalid rules schema: {e}")

    def _apply_transformation(self, text: str, rules: TextTransformationRules) -> str:
        """
        Apply transformation rules to a single text string.

        Args:
            text: Input text
            rules: Transformation rules to apply

        Returns:
            Transformed text
        """
        if not isinstance(text, str) or not text.strip():
            return text

        result = text.strip()

        # Remove fluff words (brutalist style)
        if rules.remove_fluff_words:
            for word in rules.remove_fluff_words:
                # Case-insensitive word boundary replacement
                pattern = r"\b" + re.escape(word) + r"\b"
                result = re.sub(pattern, "", result, flags=re.IGNORECASE)
            # Clean up multiple spaces
            result = re.sub(r"\s+", " ", result).strip()

        # Replace casual terms (enterprise style)
        if rules.replace_casual_terms:
            for casual, professional in rules.replace_casual_terms.items():
                pattern = r"\b" + re.escape(casual) + r"\b"
                result = re.sub(pattern, professional, result, flags=re.IGNORECASE)

        # Profanity filter (enterprise style)
        if rules.profanity_filter:
            # Basic profanity list (expand as needed)
            profanity_list = ["damn", "hell", "crap", "shit", "fuck"]
            for word in profanity_list:
                pattern = r"\b" + re.escape(word) + r"\b"
                result = re.sub(pattern, "****", result, flags=re.IGNORECASE)

        # Case transformations
        if rules.force_uppercase:
            result = result.upper()
        elif rules.title_case:
            result = result.title()
        elif rules.capitalize_first:
            if result:
                result = result[0].upper() + result[1:]

        # Length constraints
        if rules.max_length and len(result) > rules.max_length:
            # Truncate at word boundary
            result = result[: rules.max_length].rsplit(" ", 1)[0]
            if rules.suffix:
                result += rules.suffix

        if rules.min_length and len(result) < rules.min_length:
            if rules.padding_suffix:
                result += rules.padding_suffix

        # Punctuation handling
        if rules.strip_extra_punctuation:
            # Remove multiple punctuation marks
            result = re.sub(r"[.!?]{2,}", ".", result)
            result = re.sub(r"\.{2,}", "", result)

        if rules.force_punctuation:
            # Ensure text ends with specified punctuation
            if result and result[-1] not in ".!?":
                result += rules.force_punctuation

        # Apply suffix
        if rules.suffix and not result.endswith(rules.suffix):
            result += rules.suffix

        return result.strip()

    def _get_field_rules(
        self, field_path: str, theme_rules: ThemeRules
    ) -> Optional[TextTransformationRules]:
        """
        Get transformation rules for a specific field path.

        Args:
            field_path: Dot-notation field path (e.g., "hero.title")
            theme_rules: Theme-specific rules

        Returns:
            Transformation rules or None
        """
        # Check exact match first
        if field_path in theme_rules.field_mapping:
            rule_name = theme_rules.field_mapping[field_path]
            return theme_rules.transformations.get(rule_name)

        # Check pattern match (e.g., repos[].description)
        for pattern, rule_name in theme_rules.field_mapping.items():
            if "[]" in pattern:
                # Convert pattern to regex
                regex_pattern = pattern.replace("[]", r"\[\d+\]").replace(".", r"\.")
                if re.match(regex_pattern, field_path):
                    return theme_rules.transformations.get(rule_name)

        return None

    def _process_recursive(
        self, data: Union[Dict, List, str, Any], theme_rules: ThemeRules, current_path: str = ""
    ) -> Union[Dict, List, str, Any]:
        """
        Recursively process data structure applying transformations.

        Args:
            data: Content data (dict, list, or primitive)
            theme_rules: Theme-specific transformation rules
            current_path: Current field path (for rule matching)

        Returns:
            Transformed data
        """
        # Handle dictionaries
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                new_path = f"{current_path}.{key}" if current_path else key
                result[key] = self._process_recursive(value, theme_rules, new_path)
            return result

        # Handle lists
        elif isinstance(data, list):
            result = []
            for idx, item in enumerate(data):
                new_path = f"{current_path}[{idx}]"
                result.append(self._process_recursive(item, theme_rules, new_path))
            return result

        # Handle strings (apply transformations)
        elif isinstance(data, str):
            rules = self._get_field_rules(current_path, theme_rules)
            if rules:
                try:
                    return self._apply_transformation(data, rules)
                except Exception as e:
                    logger.warning(f"Transformation failed for '{current_path}': {e}")
                    return data  # Return original on error
            return data

        # Return primitives unchanged
        else:
            return data

    def process_content(self, content: Dict[str, Any], theme: str) -> Dict[str, Any]:
        """
        Process content dictionary with theme-specific transformations.

        Args:
            content: Content dictionary from ContentEngine
            theme: Theme name (must exist in config)

        Returns:
            Transformed content dictionary

        Raises:
            TextProcessorError: If theme not found or processing fails
        """
        # Get theme rules
        theme_rules = getattr(self.config, theme, None)
        if not theme_rules:
            available = [name for name in dir(self.config) if not name.startswith("_")]
            raise TextProcessorError(
                f"Theme '{theme}' not found in rules. Available: {', '.join(available)}"
            )

        logger.info(f"Processing content with theme: {theme}")

        try:
            # Apply transformations recursively
            processed = self._process_recursive(content, theme_rules)

            logger.info(f"✓ Content transformations applied ({theme})")
            return processed

        except Exception as e:
            logger.error(f"Content processing failed: {e}")
            # Rule #7: Graceful degradation - return original on catastrophic failure
            logger.warning("Returning original content due to processing error")
            return content


# Demo usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test data
    test_content = {
        "brand_name": "Test Portfolio",
        "tagline": "This is a really very quite amazing portfolio site",
        "hero": {
            "title": "welcome to my awesome website",
            "subtitle": "I build crazy insane software tools that hack your productivity",
        },
        "repos": [
            {
                "name": "test-repo",
                "description": "A very simple tool to kill processes and filter data",
            },
            {
                "name": "another-repo",
                "description": "Just another project that does cool stuff with AI and machine learning",
            },
        ],
    }

    processor = TextProcessor()

    # Test each theme
    for theme in ["brutalist", "editorial", "enterprise"]:
        print(f"\n{'=' * 60}")
        print(f"THEME: {theme.upper()}")
        print("=" * 60)

        result = processor.process_content(test_content.copy(), theme)

        print(f"Hero Title: {result['hero']['title']}")
        print(f"Hero Subtitle: {result['hero']['subtitle']}")
        print(f"Repo 1: {result['repos'][0]['description']}")
        print(f"Tagline: {result.get('tagline', 'N/A')}")
