#!/usr/bin/env python3
"""
Trinity - Main Entry Point
Rule #96: No clever one-liners, explicit logic
Rule #28: Structured logging
Rule #5: Type safety and error handling
"""
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.builder import SiteBuilder, SiteBuilderError
from src.validator import ContentValidator, ValidationError
from src.llm_client import LLMClient, LLMClientError
from src.content_engine import ContentEngine, ContentEngineError
from src.guardian import TrinityGuardian, GuardianError

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


def apply_emergency_truncate(data: Any, max_len: int = 60, _depth: int = 0) -> Any:
    """
    Recursively truncate all strings in a nested data structure.
    
    This is the Self-Healing mechanism: when Guardian detects content overflow,
    we apply aggressive truncation to all text content and retry the build.
    
    Args:
        data: Dictionary, list, string, or other data type
        max_len: Maximum string length before truncation
        _depth: Internal recursion depth tracker (protects against circular refs)
        
    Returns:
        Deep copy of data with all strings truncated to max_len
        
    Raises:
        RecursionError: If depth exceeds 50 (protection against circular references)
    """
    # FIXED: Recursion bomb protection (Rule #12)
    if _depth > 50:
        logger.error(f"Recursion depth exceeded (possible circular reference)")
        raise RecursionError("Maximum recursion depth exceeded in truncate")
    
    if isinstance(data, dict):
        return {k: apply_emergency_truncate(v, max_len, _depth + 1) for k, v in data.items()}
    elif isinstance(data, list):
        return [apply_emergency_truncate(i, max_len, _depth + 1) for i in data]
    elif isinstance(data, str):
        if len(data) > max_len:
            return data[:max_len] + "..."
        return data
    return data


def build_site_from_mock_data(theme: str = "enterprise", enable_guardian: bool = False, guardian_dom_only: bool = False) -> Path:
    """
    Build site using mock data (no LLM required).
    Useful for testing templates and themes.
    
    Args:
        theme: Theme name to apply
        enable_guardian: Run Guardian QA after build
        guardian_dom_only: Use DOM-only checks (no Vision AI)
        
    Returns:
        Path to generated HTML
    """
    logger.info("Building site from mock data...")
    
    # Mock content matching ContentSchema
    mock_content = {
        "brand_name": "Trinity",
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
    
    # Guardian QA (if enabled)
    if enable_guardian:
        try:
            logger.info("👁️  Activating Guardian for layout inspection...")
            guardian = TrinityGuardian(enable_vision_ai=not guardian_dom_only)
            report = guardian.audit_layout(str(output_path.resolve()))
            
            if report["approved"]:
                logger.info(f"✅ Guardian Approved: {report['reason']}")
            else:
                logger.warning(f"❌ Guardian Rejected: {report['reason']}")
                if report['issues']:
                    for issue in report['issues']:
                        logger.warning(f"  Issue: {issue}")
                logger.info(f"🛠️  Suggested Fix: {report['fix_suggestion']}")
        except GuardianError as e:
            logger.error(f"Guardian QA failed: {e}")
    
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


def build_with_llm(input_data_path: str, theme: str = "enterprise", enable_guardian: bool = False, guardian_dom_only: bool = False):
    """
    Build site using LLM to generate content.
    
    Args:
        input_data_path: Path to raw portfolio data
        theme: Theme to apply
        enable_guardian: Run Guardian QA after build
        guardian_dom_only: Use DOM-only checks (no Vision AI)
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
        
        # Guardian QA (if enabled)
        if enable_guardian:
            try:
                logger.info("👁️  Activating Guardian for layout inspection...")
                guardian = TrinityGuardian(enable_vision_ai=not guardian_dom_only)
                report = guardian.audit_layout(str(output_path.resolve()))
                
                if report["approved"]:
                    logger.info(f"✅ Guardian Approved: {report['reason']}")
                else:
                    logger.warning(f"❌ Guardian Rejected: {report['reason']}")
                    if report['issues']:
                        for issue in report['issues']:
                            logger.warning(f"  Issue: {issue}")
                    logger.info(f"🛠️  Suggested Fix: {report['fix_suggestion']}")
                    
                    # Self-healing implemented in trinity.engine (TrinityEngine.heal_layout)
            except GuardianError as e:
                logger.error(f"Guardian QA failed: {e}")
        
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
        description="Trinity - Static Site Generator",
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
        help='Input file with raw portfolio data (for LLM) or JSON content (for static build)'
    )
    
    parser.add_argument(
        '--use-llm',
        action='store_true',
        help='Use LLM to generate content from raw data'
    )
    
    parser.add_argument(
        '--static-json',
        action='store_true',
        help='Use static JSON content directly (for testing/chaos mode)'
    )
    
    parser.add_argument(
        '--guardian',
        action='store_true',
        help='Enable Guardian vision-based layout QA (requires Qwen VL)'
    )
    
    parser.add_argument(
        '--guardian-only-dom',
        action='store_true',
        help='Use Guardian with DOM checks only (faster, no Vision AI)'
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
            output = build_site_from_mock_data(
                theme=args.theme,
                enable_guardian=args.guardian,
                guardian_dom_only=args.guardian_only_dom
            )
            print(f"\n✓ Demo page generated: {output}")
            print(f"  Open in browser: file://{output.absolute()}")
            return 0
        
        # Build with LLM
        if args.use_llm:
            output = build_with_llm(
                args.input,
                theme=args.theme,
                enable_guardian=args.guardian,
                guardian_dom_only=args.guardian_only_dom
            )
            print(f"\n🧠 LLM-generated page created: {output}")
            print(f"  Open in browser: file://{output.absolute()}")
            return 0
        
        # Build with static JSON (chaos mode)
        if args.static_json:
            import json
            print(f"📄 Loading static JSON content from: {args.input}")
            
            with open(args.input, "r", encoding="utf-8") as f:
                content = json.load(f)
            
            # Validate
            validator = ContentValidator()
            try:
                validator.validate_content_schema(content)
            except ValidationError as e:
                logger.error(f"Content validation failed: {e}")
                print(f"❌ Invalid content schema: {e}")
                return 1
            
            # Self-Healing Loop
            max_retries = 3
            attempt = 0
            current_content = content  # Working copy
            builder = SiteBuilder()
            filename = f"index_{args.theme}_chaos.html"
            output_path = None
            
            while attempt < max_retries:
                print(f"\n🔄 Build Attempt {attempt + 1}/{max_retries}...")
                
                # 1. Build page
                output_path = builder.build_page(
                    content=current_content,
                    theme=args.theme,
                    output_filename=filename
                )
                print(f"✓ Page built: {output_path}")
                
                # 2. If Guardian is disabled, exit early
                if not args.guardian:
                    print(f"\nOpen in browser: file://{output_path.absolute()}")
                    return 0
                
                # 3. Guardian Audit
                try:
                    print("👁️  Guardian is inspecting...")
                    abs_path = output_path.resolve()
                    
                    guardian = TrinityGuardian(enable_vision_ai=not args.guardian_only_dom)
                    report = guardian.audit_layout(str(abs_path))
                    
                    print("\n" + "=" * 60)
                    print("GUARDIAN AUDIT REPORT")
                    print("=" * 60)
                    
                    if report["approved"]:
                        print(f"✅ STATUS: APPROVED")
                        print(f"Reason: {report['reason']}")
                        print("=" * 60)
                        print(f"\n🏆 Success! Layout passed Guardian QA.")
                        print(f"\nOpen in browser: file://{output_path.absolute()}")
                        return 0
                    else:
                        print(f"❌ STATUS: REJECTED")
                        print(f"Reason: {report['reason']}")
                        if report['issues']:
                            print(f"\nIssues Found ({len(report['issues'])}):")
                            for i, issue in enumerate(report['issues'], 1):
                                print(f"  {i}. {issue}")
                        print(f"\n🛠️  Suggested Fix: {report['fix_suggestion'].upper()}")
                        print("=" * 60)
                        
                        # Self-Healing Logic
                        if attempt < max_retries - 1:
                            fix = report['fix_suggestion'].upper()
                            print(f"\n🚑 Self-Healing: Applying '{fix}' to content...")
                            
                            # Apply aggressive truncation
                            current_content = apply_emergency_truncate(current_content, max_len=50)
                            attempt += 1
                            print(f"   → All strings truncated to 50 characters")
                            print(f"   → Retrying build with fixed content...\n")
                        else:
                            print("\n💀 Max retries reached. Giving up.")
                            # Rename broken file
                            broken_path = output_path.parent / f"BROKEN_{filename}"
                            os.rename(str(output_path), str(broken_path))
                            print(f"   → Broken layout saved as: {broken_path}")
                            print(f"\nOpen broken file: file://{broken_path.absolute()}")
                            return 1
                    
                except GuardianError as e:
                    logger.error(f"Guardian QA failed: {e}")
                    print(f"❌ Guardian error: {e}")
                    return 1
            
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
