#!/usr/bin/env python3
"""
Migration script: themes.json → themes.yaml

Converts JSON theme configuration to YAML format with:
- Readable structure with comments
- Theme descriptions and metadata
- Preserved class mappings
- Better developer experience

Run: python scripts/migrate_themes_to_yaml.py
"""
import json
import yaml
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


# Theme descriptions (curated metadata)
THEME_DESCRIPTIONS = {
    "enterprise": {
        "description": "Clean, professional design for corporate portfolios",
        "category": "business",
        "color_palette": "blue, slate, white",
        "typography": "sans-serif, modern",
        "use_case": "Corporate websites, professional portfolios, B2B landing pages"
    },
    "brutalist": {
        "description": "Raw, bold aesthetic with stark contrasts and mono fonts",
        "category": "experimental",
        "color_palette": "yellow, black, cyan",
        "typography": "monospace, uppercase",
        "use_case": "Artist portfolios, experimental projects, bold statements"
    },
    "editorial": {
        "description": "Magazine-style layout with serif fonts and elegant typography",
        "category": "content",
        "color_palette": "stone, red, white",
        "typography": "serif, italic",
        "use_case": "Blogs, editorial sites, content-heavy portfolios"
    },
    "tech_01": {
        "description": "Hacker terminal aesthetic with green-on-dark theme",
        "category": "technical",
        "color_palette": "green, blue, gray-900",
        "typography": "monospace, technical",
        "use_case": "Developer portfolios, tech blogs, terminal-style sites"
    },
    "tech_02": {
        "description": "Retro-futuristic tech design with amber gradients",
        "category": "technical",
        "color_palette": "amber, orange, blue",
        "typography": "typewriter, uppercase",
        "use_case": "Tech startups, developer portfolios, sci-fi themes"
    },
    "retro_arcade": {
        "description": "80s arcade game aesthetic with neon colors and pixel vibes",
        "category": "retro",
        "color_palette": "pink, cyan, purple, blue",
        "typography": "bold, uppercase",
        "use_case": "Gaming portfolios, retro projects, fun personal sites"
    },
    "artistic_01": {
        "description": "Creative gradient design with artistic flair",
        "category": "creative",
        "color_palette": "purple, pink, blue, white",
        "typography": "bold, modern",
        "use_case": "Creative portfolios, design agencies, artistic projects"
    },
    "minimalist": {
        "description": "Clean, minimal design focusing on content and whitespace",
        "category": "minimal",
        "color_palette": "white, gray, black",
        "typography": "sans-serif, clean",
        "use_case": "Portfolio sites, minimal blogs, text-focused content"
    },
    "hacker": {
        "description": "Terminal-inspired dark theme for developers",
        "category": "technical",
        "color_palette": "green, black",
        "typography": "monospace, terminal",
        "use_case": "Developer portfolios, cybersecurity sites, tech blogs"
    }
}


def load_json_themes(json_path: Path) -> Dict[str, Any]:
    """Load themes from JSON file."""
    if not json_path.exists():
        raise FileNotFoundError(f"themes.json not found: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        themes = json.load(f)
    
    # Remove comment keys (// prefix in JSON)
    themes = {k: v for k, v in themes.items() if not k.startswith("//")}
    
    return themes


def enrich_theme_with_metadata(theme_name: str, theme_classes: Dict[str, str]) -> Dict[str, Any]:
    """Add metadata to theme configuration."""
    metadata = THEME_DESCRIPTIONS.get(theme_name, {
        "description": f"{theme_name.replace('_', ' ').title()} theme",
        "category": "custom",
        "color_palette": "custom",
        "typography": "custom",
        "use_case": "Custom theme"
    })
    
    return {
        "metadata": metadata,
        "classes": theme_classes
    }


def save_yaml_themes(themes: Dict[str, Any], yaml_path: Path) -> None:
    """Save themes to YAML file with comments."""
    # Prepare YAML content with header
    yaml_content = f"""# Trinity Theme Configuration (YAML)
#
# Migrated from themes.json on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
#
# Structure:
#   theme_name:
#     metadata:
#       description: Human-readable description
#       category: Theme category (business, technical, creative, etc.)
#       color_palette: Main colors used
#       typography: Font characteristics
#       use_case: Recommended use cases
#     classes:
#       component_name: Tailwind CSS classes
#
# Usage:
#   trinity build --theme brutalist
#   trinity theme-gen --name my_theme --base brutalist
#
# Rules:
#   - Rule #45: Consistent YAML formatting (2-space indentation)
#   - Rule #39: Developer-friendly configuration
#   - Rule #21: Centralized theme logic
#
# See: docs/THEMES_GUIDE.md for more information

"""
    
    # Add themes
    for theme_name, theme_data in sorted(themes.items()):
        yaml_content += f"\n# {theme_name.upper()} Theme\n"
        yaml_content += f"# {theme_data['metadata']['description']}\n"
        yaml_content += yaml.dump(
            {theme_name: theme_data},
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            indent=2
        )
    
    # Write to file
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(yaml_content, encoding='utf-8')
    
    print(f"✓ Saved YAML themes to: {yaml_path}")


def migrate_themes():
    """Main migration function."""
    # Paths
    json_path = Path("config/themes.json")
    yaml_path = Path("config/themes.yaml")
    backup_path = Path("config/themes.json.backup")
    
    print("=== Theme Migration: JSON → YAML ===\n")
    
    # Step 1: Load JSON themes
    print(f"1. Loading themes from {json_path}...")
    themes_json = load_json_themes(json_path)
    print(f"   Found {len(themes_json)} themes")
    
    # Step 2: Enrich with metadata
    print("\n2. Enriching themes with metadata...")
    themes_enriched = {}
    for theme_name, theme_classes in themes_json.items():
        themes_enriched[theme_name] = enrich_theme_with_metadata(theme_name, theme_classes)
        print(f"   ✓ {theme_name}: {themes_enriched[theme_name]['metadata']['description'][:50]}...")
    
    # Step 3: Save to YAML
    print(f"\n3. Saving to {yaml_path}...")
    save_yaml_themes(themes_enriched, yaml_path)
    
    # Step 4: Backup original JSON
    print(f"\n4. Creating backup at {backup_path}...")
    json_path.rename(backup_path)
    print(f"   ✓ Original JSON backed up")
    
    # Summary
    print("\n=== Migration Complete ===")
    print(f"Themes migrated: {len(themes_enriched)}")
    print(f"New YAML file: {yaml_path}")
    print(f"Backup: {backup_path}")
    print("\nNext steps:")
    print("1. Review config/themes.yaml")
    print("2. Test: trinity themes")
    print("3. Test: trinity build --theme brutalist")
    print("4. If all works, delete backup: rm config/themes.json.backup")


if __name__ == "__main__":
    try:
        migrate_themes()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
