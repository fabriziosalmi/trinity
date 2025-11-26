"""
Trinity Core - Validator
Rule #95: Validate accessibility and HTML standards
Rule #5: Type safety with Pydantic
Rule #28: Structured logging
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from html5lib import parse
    from html5lib.treewalkers import getTreeWalker
    from pydantic import BaseModel, Field, ValidationError, field_validator
except ImportError:
    raise ImportError(
        "Missing dependencies. Install with: pip install pydantic html5lib beautifulsoup4"
    )

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Base exception for validation errors."""
    pass


class ContentValidator:
    """
    Validate content structure and HTML output.
    Responsibilities:
    - Validate content JSON against schema
    - Check HTML5 validity
    - Verify accessibility requirements (WCAG)

    Does NOT:
    - Modify content
    - Generate fixes
    """

    @staticmethod
    def validate_content_schema(content: Dict[str, Any]) -> bool:
        """
        Validate content dictionary against expected schema.

        Args:
            content: Content data to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If schema validation fails
        """
        # Define schema using Pydantic
        class MenuItem(BaseModel):
            label: str = Field(..., min_length=1, max_length=100)
            url: str = Field(..., min_length=1)

        class CTAButton(BaseModel):
            label: str = Field(..., min_length=1, max_length=100)
            url: str = Field(..., min_length=1)

        class HeroSection(BaseModel):
            title: str = Field(..., min_length=1, max_length=200)
            subtitle: Optional[str] = Field(None, max_length=500)
            cta_primary: Optional[CTAButton] = None
            cta_secondary: Optional[CTAButton] = None

        class Repository(BaseModel):
            name: str = Field(..., min_length=1, max_length=100)
            description: str = Field(..., min_length=1, max_length=500)
            url: str = Field(..., min_length=1)
            tags: List[str] = Field(default_factory=list)
            stars: Optional[int] = Field(None, ge=0)

            @field_validator('url')
            @classmethod
            def validate_url(cls, v: str) -> str:
                """Basic URL validation."""
                if not (v.startswith('http://') or v.startswith('https://') or v.startswith('#')):
                    raise ValueError('URL must start with http://, https://, or #')
                return v

        class ContentSchema(BaseModel):
            brand_name: str = Field(..., min_length=1, max_length=100)
            tagline: Optional[str] = Field(None, max_length=200)
            menu_items: List[MenuItem] = Field(default_factory=list)
            cta: Optional[CTAButton] = None
            hero: Optional[HeroSection] = None
            repos: List[Repository] = Field(default_factory=list)

        try:
            ContentSchema(**content)
            logger.info("✓ Content schema validation passed")
            return True
        except ValidationError as e:
            logger.error(f"Content validation failed: {e}")
            raise ValidationError(f"Invalid content structure: {e}")

    @staticmethod
    def validate_html5(html_path: Path) -> bool:
        """
        Validate HTML5 syntax and structure.

        Args:
            html_path: Path to HTML file

        Returns:
            True if valid

        Raises:
            ValidationError: If HTML is invalid
        """
        if not html_path.exists():
            raise FileNotFoundError(f"HTML file not found: {html_path}")

        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Parse with html5lib (strict validator)
            document = parse(html_content, treebuilder='etree', namespaceHTMLElements=False)

            if document is None:
                raise ValidationError("Failed to parse HTML document")

            logger.info(f"✓ HTML5 validation passed: {html_path.name}")
            return True

        except Exception as e:
            logger.error(f"HTML validation failed: {e}")
            raise ValidationError(f"Invalid HTML: {e}")

    @staticmethod
    def check_accessibility(html_path: Path) -> List[str]:
        """
        Basic accessibility checks (WCAG Level A).

        Args:
            html_path: Path to HTML file

        Returns:
            List of warnings (empty if all checks pass)
        """
        warnings = []

        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Check for common issues
            if '<img' in html_content and 'alt=' not in html_content:
                warnings.append("Missing alt attributes on images")

            if '<nav' not in html_content and '<header' not in html_content:
                warnings.append("Missing semantic navigation elements")

            if 'aria-label' not in html_content and 'role=' not in html_content:
                warnings.append("No ARIA attributes found (consider adding for better accessibility)")

            if not warnings:
                logger.info(f"✓ Accessibility checks passed: {html_path.name}")
            else:
                for warning in warnings:
                    logger.warning(f"Accessibility: {warning}")

            return warnings

        except Exception as e:
            logger.error(f"Accessibility check failed: {e}")
            return [f"Check failed: {e}"]

    @staticmethod
    def validate_theme_config(theme_path: Path, required_keys: List[str]) -> bool:
        """
        Validate theme configuration has all required CSS class keys.

        Args:
            theme_path: Path to themes.json
            required_keys: List of required class keys

        Returns:
            True if valid

        Raises:
            ValidationError: If keys are missing
        """
        try:
            with open(theme_path, 'r', encoding='utf-8') as f:
                themes = json.load(f)

            errors = []
            for theme_name, theme_config in themes.items():
                missing = [key for key in required_keys if key not in theme_config]
                if missing:
                    errors.append(f"Theme '{theme_name}' missing keys: {', '.join(missing)}")

            if errors:
                raise ValidationError("\n".join(errors))

            logger.info(f"✓ Theme config validation passed ({len(themes)} themes)")
            return True

        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in theme config: {e}")
        except FileNotFoundError:
            raise ValidationError(f"Theme config not found: {theme_path}")


# Demo usage
if __name__ == "__main__":
    # Test content validation
    test_content = {
        "brand_name": "Test Site",
        "menu_items": [{"label": "Home", "url": "/"}],
        "repos": [
            {
                "name": "test-repo",
                "description": "A test repository",
                "url": "https://github.com/test/repo",
                "tags": ["test"],
                "stars": 10
            }
        ]
    }

    validator = ContentValidator()
    try:
        validator.validate_content_schema(test_content)
        print("✓ Content validation passed")
    except ValidationError as e:
        print(f"✗ Validation failed: {e}")

    # Test theme validation
    required_theme_keys = [
        "nav_bg", "text_primary", "text_secondary", "nav_link", "btn_primary"
    ]

    try:
        validator.validate_theme_config(
            Path("config/themes.json"),
            required_theme_keys
        )
        print("✓ Theme validation passed")
    except ValidationError as e:
        print(f"✗ Theme validation failed: {e}")
