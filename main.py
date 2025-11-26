#!/usr/bin/env python3
"""
Trinity Core - Main Entry Point
Rule #96: No clever one-liners, explicit logic
Rule #28: Structured logging
Rule #5: Type safety and error handling
"""
import sys
import logging
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.builder import SiteBuilder, SiteBuilderError
from src.validator import ContentValidator, ValidationError
from src.llm_client import LLMClient, LLMClientError
from src.content_engine import ContentEngine, ContentEngineError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/trinity.log')
    ]
)
logger = logging.getLogger(__name__)


def build_site_from_mock_data(theme: str = "enterprise") -> Path:
    """
    Build site using mock data (no LLM required).
    Useful for testing templates and themes.
    
    Args:
        theme: Theme name to apply
        
    Returns:
        Path to generated HTML
    """
    logger.info("Building site from mock data...")
    
    # Mock content matching ContentSchema
    mock_content = {
        "brand_name": "Trinity Core",
        "tagline": "Deterministic Layouts. AI-Powered Content.",
        "menu_items": [
            {"label": "Features", "url": "#features"},
            {"label": "Examples", "url": "#examples"},
            {"label": "Docs", "url": "#docs"}
        ],
        "cta": {"label": "Get Started", "url": "#start"},
        "hero": {
            "title": "Build Static Sites at Light Speed",
            "subtitle": "Combine human-crafted HTML skeletons with LLM-generated content. No hallucinations, just results.",
            "cta_primary": {"label": "View Demo", "url": "#demo"},
            "cta_secondary": {"label": "Read Docs", "url": "#docs"}
        },
        "repos": [
            {
                "name": "trinity-core",
                "description": "Python-based static site generator with Jinja2 templates and LLM integration.",
                "url": "https://github.com/example/trinity-core",
                "tags": ["Python", "Jinja2", "LLM"],
                "stars": 127
            },
            {
                "name": "skeleton-library",
                "description": "Collection of accessible, semantic HTML/Tailwind components.",
                "url": "https://github.com/example/skeleton-library",
                "tags": ["HTML", "Tailwind", "A11y"],
                "stars": 89
            },
            {
                "name": "content-painter",
                "description": "LLM wrapper for content generation with strict schema validation.",
                "url": "https://github.com/example/content-painter",
                "tags": ["Python", "Ollama", "Validation"],
                "stars": 54
            }
        ]
    }
    
    # Validate content
    validator = ContentValidator()
    try:
        validator.validate_content_schema(mock_content)
    except ValidationError as e:
        logger.error(f"Content validation failed: {e}")
        raise
    
    # Build page
    builder = SiteBuilder()
    output_path = builder.build_page(
        content=mock_content,
        theme=theme,
        output_filename=f"index_{theme}.html"
    )
    
    # Validate output HTML
    try:
        validator.validate_html5(output_path)
        warnings = validator.check_accessibility(output_path)
        if warnings:
            logger.warning(f"Accessibility warnings: {len(warnings)}")
    except ValidationError as e:
        logger.warning(f"Post-build validation warning: {e}")
    
    return output_path


def build_all_themes():
    """Build demo pages for all available themes."""
    logger.info("=== Building demo pages for all themes ===")
    
    builder = SiteBuilder()
    themes = builder.list_available_themes()
    
    results = []
    for theme in themes:
        try:
            output = build_site_from_mock_data(theme=theme)
            results.append((theme, output, "✓"))
            logger.info(f"✓ {theme}: {output}")
        except Exception as e:
            results.append((theme, None, f"✗ {e}"))
            logger.error(f"✗ {theme} failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)
    for theme, path, status in results:
        print(f"{status} {theme:15s} {path or 'FAILED'}")
    print("=" * 60)


def build_with_llm(input_data_path: str, theme: str = "enterprise"):
    """
    Build site using LLM to generate content.
    
    Args:
        input_data_path: Path to raw portfolio data
        theme: Theme to apply
    """
    logger.info("🧠 Building site with LLM content generation...")
    
    try:
        # Initialize ContentEngine
        engine = ContentEngine()
        
        # Generate content with LLM
        logger.info(f"Generating {theme}-themed content from {input_data_path}")
        content = engine.generate_content_with_fallback(
            raw_text_path=input_data_path,
            theme=theme,
            fallback_path="data/input_content.json"
        )
        
        # Validate generated content
        validator = ContentValidator()
        validator.validate_content_schema(content)
        
        # Build page
        builder = SiteBuilder()
        output_path = builder.build_page(
            content=content,
            theme=theme,
            output_filename=f"index_{theme}_llm.html"
        )
        
        logger.info(f"✓ LLM-generated page created: {output_path}")
        return output_path
        
    except ContentEngineError as e:
        logger.error(f"ContentEngine failed: {e}")
        raise
    except ValidationError as e:
        logger.error(f"Generated content validation failed: {e}")
        raise
    except Exception as e:
        logger.critical(f"Unexpected error in LLM build: {e}")
        raise


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Trinity Core - Static Site Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build demo pages for all themes
  python main.py --demo-all
  
  # Build single theme demo
  python main.py --demo --theme brutalist
  
  # Build with LLM (not yet implemented)
  python main.py --input data/repos.json --theme editorial
        """
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Build demo page with mock data'
    )
    
    parser.add_argument(
        '--demo-all',
        action='store_true',
        help='Build demo pages for all themes'
    )
    
    parser.add_argument(
        '--theme',
        type=str,
        default='enterprise',
        choices=['enterprise', 'brutalist', 'editorial'],
        help='Theme to apply (default: enterprise)'
    )
    
    parser.add_argument(
        '--input',
        type=str,
        default='data/raw_portfolio.txt',
        help='Input file with raw portfolio data (for LLM generation)'
    )
    
    parser.add_argument(
        '--use-llm',
        action='store_true',
        help='Use LLM to generate content from raw data'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Validate theme config without building'
    )
    
    args = parser.parse_args()
    
    try:
        # Validate theme config
        if args.validate_only:
            validator = ContentValidator()
            required_keys = [
                "nav_bg", "text_primary", "text_secondary", "nav_link", 
                "btn_primary", "hero_bg", "card_bg", "heading_primary", "body_text"
            ]
            validator.validate_theme_config(Path("config/themes.json"), required_keys)
            print("✓ Theme configuration is valid")
            return 0
        
        # Build demo for all themes
        if args.demo_all:
            build_all_themes()
            return 0
        
        # Build single demo
        if args.demo:
            output = build_site_from_mock_data(theme=args.theme)
            print(f"\n✓ Demo page generated: {output}")
            print(f"  Open in browser: file://{output.absolute()}")
            return 0
        
        # Build with LLM
        if args.use_llm:
            output = build_with_llm(args.input, theme=args.theme)
            print(f"\n🧠 LLM-generated page created: {output}")
            print(f"  Open in browser: file://{output.absolute()}")
            return 0
        
        # Build with static input (legacy)
        if args.input and not args.use_llm:
            logger.warning("--input without --use-llm will be ignored. Use --use-llm to activate LLM.")
        
        # No action specified
        parser.print_help()
        return 1
        
    except KeyboardInterrupt:
        logger.info("Build interrupted by user")
        return 130
    except Exception as e:
        logger.critical(f"Build failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
