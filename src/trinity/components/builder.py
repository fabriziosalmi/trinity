"""
Trinity Core - Site Builder
Rule #14: Single Responsibility (Assembly only, not content generation)
Rule #5: Type safety and error handling
Rule #27: Separation of concerns
Rule #28: Structured logging
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

from trinity.utils.logger import get_logger

logger = get_logger(__name__)

# Rule #8: No Magic Numbers/Strings
DEFAULT_TEMPLATE_DIR = "library"
OUTPUT_DIR = "output"
THEMES_CONFIG_PATH = "config/themes.json"


class SiteBuilderError(Exception):
    """Base exception for SiteBuilder errors."""
    pass


class ThemeNotFoundError(SiteBuilderError):
    """Raised when requested theme doesn't exist."""
    pass


class TemplateNotFoundError(SiteBuilderError):
    """Raised when template file is missing."""
    pass


class SiteBuilder:
    """
    Deterministic HTML assembler.
    Responsibilities:
    - Load Jinja2 templates from library/
    - Inject content data and theme classes
    - Render static HTML
    - Write output to disk
    
    Does NOT:
    - Generate content (handled by LLM)
    - Modify layout structure (templates are immutable)
    """
    
    def __init__(self, template_dir: str = DEFAULT_TEMPLATE_DIR):
        """
        Initialize builder with template directory.
        
        Args:
            template_dir: Path to Jinja2 templates
            
        Raises:
            FileNotFoundError: If template directory doesn't exist
        """
        # Rule #5: Validate paths at initialization
        self.template_path = Path(template_dir)
        if not self.template_path.exists():
            raise FileNotFoundError(
                f"Template directory not found: {self.template_path}"
            )
            
        # Rule #64: Autoescape prevents XSS
        self.env = Environment(
            loader=FileSystemLoader(self.template_path),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        logger.info(f"SiteBuilder initialized with templates from: {self.template_path}")

    def load_theme_config(self, theme_name: str) -> Dict[str, str]:
        """
        Load CSS class mappings for specified theme.
        
        Args:
            theme_name: Theme identifier (e.g., "enterprise", "brutalist")
            
        Returns:
            Dictionary of CSS class mappings
            
        Raises:
            ThemeNotFoundError: If theme doesn't exist in config
            FileNotFoundError: If themes.json is missing
        """
        # Rule #7: Catch specific errors
        config_path = Path(THEMES_CONFIG_PATH)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Theme configuration not found: {config_path}")
            
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                themes = json.load(f)
            
            if theme_name not in themes:
                available = ", ".join(themes.keys())
                raise ThemeNotFoundError(
                    f"Theme '{theme_name}' not found. Available: {available}"
                )
                 
            logger.info(f"Loaded theme: {theme_name}")
            return themes[theme_name]
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in themes.json: {e}")
            raise SiteBuilderError(f"Failed to parse theme config: {e}")

    def build_page(
        self,
        content: Dict[str, Any],
        theme: str,
        output_filename: str = "index.html",
        template_name: str = "templates/base_layout.html",
        style_overrides: Optional[Dict[str, str]] = None
    ) -> Path:
        """
        Assemble and render complete HTML page.
        
        Args:
            content: Structured content data (validated elsewhere)
            theme: Theme name to apply
            output_filename: Output file name
            template_name: Base template to use
            style_overrides: Optional CSS class overrides from SmartHealer
                           Format: {"hero_title": "text-2xl break-all", ...}
            
        Returns:
            Path to generated HTML file
            
        Raises:
            TemplateNotFoundError: If template doesn't exist
            SiteBuilderError: If rendering fails
        """
        logger.info(f"Building page: {output_filename} (theme: {theme})")
        
        # Load theme classes
        theme_classes = self.load_theme_config(theme)
        
        # Merge style overrides from SmartHealer
        if style_overrides:
            logger.info(f"🎨 Applying {len(style_overrides)} CSS overrides from SmartHealer")
            for key, override_classes in style_overrides.items():
                if key in theme_classes:
                    original = theme_classes[key]
                    # Append override classes to existing ones
                    theme_classes[key] = f"{original} {override_classes}"
                    logger.debug(f"  {key}: '{original}' → '{theme_classes[key]}'")
                else:
                    # New key not in theme - add it
                    theme_classes[key] = override_classes
                    logger.debug(f"  {key}: NEW → '{override_classes}'")
        
        # Rule #27: Separation of Concerns (Logic vs Presentation)
        try:
            template = self.env.get_template(template_name)
        except TemplateNotFound as e:
            raise TemplateNotFoundError(f"Template not found: {template_name}") from e
        
        # Render with context
        try:
            rendered_html = template.render(
                content=content,
                theme_classes=theme_classes,
                meta={
                    "generator": "Trinity Core v0.2.0",
                    "theme": theme,
                    "build_date": "2025-11-26"  # TODO: Use datetime
                }
            )
            
            # Write to disk
            output_path = Path(OUTPUT_DIR) / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(rendered_html)
                
            logger.info(f"✓ Successfully generated: {output_path} ({len(rendered_html)} bytes)")
            return output_path
            
        except Exception as e:
            # Rule #7: Don't swallow errors
            logger.critical(f"Rendering failed for {output_filename}: {e}")
            raise SiteBuilderError(f"Failed to build page: {e}") from e

    def list_available_themes(self) -> list[str]:
        """Get list of available theme names."""
        try:
            with open(THEMES_CONFIG_PATH, "r", encoding="utf-8") as f:
                themes = json.load(f)
            return list(themes.keys())
        except (FileNotFoundError, json.JSONDecodeError):
            return []


# Rule #96: No clever one-liners - explicit demo code
if __name__ == "__main__":
    # Demo: Build page without LLM (using mock data)
    mock_content = {
        "brand_name": "Trinity Showcase",
        "menu_items": [
            {"label": "About", "url": "#about"},
            {"label": "Projects", "url": "#projects"},
            {"label": "Contact", "url": "#contact"}
        ],
        "cta": {"label": "Get Started", "url": "/start"},
        "hero": {
            "title": "Build Fast. Ship Faster.",
            "subtitle": "Deterministic layouts meet AI-powered content.",
            "cta_primary": {"label": "View Demo", "url": "#demo"},
            "cta_secondary": {"label": "Read Docs", "url": "/docs"}
        },
        "repos": [
            {
                "name": "trinity-core",
                "description": "Python-based static site generator with Jinja2 templates.",
                "url": "https://github.com/example/trinity",
                "tags": ["Python", "Jinja2", "Static Site"],
                "stars": 42
            }
        ]
    }
    
    try:
        builder = SiteBuilder()
        print(f"Available themes: {builder.list_available_themes()}")
        
        # Build with each theme
        for theme in ["enterprise", "brutalist", "editorial"]:
            output = builder.build_page(
                content=mock_content,
                theme=theme,
                output_filename=f"demo_{theme}.html"
            )
            print(f"✓ Built: {output}")
            
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
