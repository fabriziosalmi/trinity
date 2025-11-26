#!/usr/bin/env python3
"""
Trinity Centuria Factory - Mass Theme Generator

Generates 100 diverse themes across 5 categories to enable robust ML training.
This is Data Augmentation for Frontend: forcing the model to learn DOM physics, not patterns.

Categories:
- Historical (20): Victorian, Art Deco, 1980s, etc.
- Tech (20): Terminal, iOS, Material Design, etc.
- Artistic (20): Bauhaus, Cubist, Pop Art, etc.
- Chaotic (20): Glitch, Trash, Maximalist, etc.
- Professional (20): Legal, Medical, Fintech, etc.

Usage:
    poetry run python scripts/mass_theme_generator.py --dry-run  # Preview themes
    poetry run python scripts/mass_theme_generator.py            # Generate all 100
    poetry run python scripts/mass_theme_generator.py --category tech --count 10
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict
import time

# FIXED: No more sys.path hacking - use poetry run or proper package install
from trinity.components.brain import ContentEngine, ContentEngineError
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

console = Console()

# Theme Definitions - The Centuria
THEME_CATEGORIES = {
    "historical": [
        "Victorian steampunk with brass and dark wood",
        "Art Deco 1920s with gold geometric patterns",
        "1950s retro diner with pastel colors",
        "1960s psychedelic with vibrant swirls",
        "1970s disco with metallic and neon",
        "1980s neon arcade with pink and cyan",
        "1990s grunge with dark distressed textures",
        "Ancient Egyptian with hieroglyphs and gold",
        "Medieval manuscript with illuminated letters",
        "Renaissance art with rich tapestry colors",
        "Baroque opulence with ornate gold details",
        "Industrial revolution with iron and coal",
        "Wild West saloon with wood and leather",
        "Roaring twenties jazz club aesthetic",
        "World War II propaganda poster style",
        "Cold War brutalist concrete aesthetic",
        "Swinging sixties mod style",
        "Y2K futuristic chrome and silver",
        "Early internet geocities aesthetic",
        "Fax machine office 1990s beige",
    ],
    "tech": [
        "DOS terminal green on black monospace",
        "Apple II retro computing amber text",
        "Windows 95 classic gray and teal",
        "Mac OS 9 aqua interface style",
        "iOS 6 skeuomorphic rich textures",
        "Material Design bold colors and shadows",
        "Flat design minimalist bright colors",
        "Neumorphism soft shadows and depth",
        "Glassmorphism frosted translucent layers",
        "Cyberpunk neon city dystopian future",
        "Matrix green code on black",
        "Tron grid electric blue circuits",
        "Hacker terminal dark with green accents",
        "Sci-fi hologram interface blue glow",
        "Retro computer CRT scanline effect",
        "Teletext blocky pixelated graphics",
        "Command line ultra minimal black white",
        "Synthwave retrowave purple pink gradient",
        "Vaporwave aesthetic pink teal glitch",
        "Y2K cyber glossy metallic chrome",
    ],
    "artistic": [
        "Bauhaus geometric primary colors",
        "Cubist fragmented angular shapes",
        "Pop Art bold comic book style",
        "Abstract expressionism paint splatter",
        "Minimalist Japanese zen white space",
        "Maximalist ornate detailed patterns",
        "Art Nouveau organic flowing lines",
        "Constructivist angular red black white",
        "Dadaist chaotic collage random",
        "Surrealist dreamlike unexpected elements",
        "Impressionist soft pastel brush strokes",
        "Pointillism dotted stippled texture",
        "Watercolor soft bleeding transparent",
        "Graffiti street art spray paint",
        "Stencil art high contrast silhouettes",
        "Pixel art retro 8-bit blocky",
        "Low poly geometric faceted 3D",
        "Isometric architectural technical drawing",
        "Memphis design colorful geometric 80s",
        "Swiss design grid-based typography",
    ],
    "chaotic": [
        "Glitch art digital corruption artifacts",
        "Trashcore intentionally ugly clashing",
        "Brutalist raw concrete harsh",
        "Anti-design deliberately broken layout",
        "Noise static TV interference",
        "Zalgo text corrupted Unicode chaos",
        "Geocities maximalist all animations",
        "MySpace profile garish autoplaying music",
        "Windows XP error messages everywhere",
        "BSOD blue screen of death theme",
        "Comic Sans ransom note aesthetic",
        "Papyrus ancient tacky font",
        "Rainbow gradient WordArt 90s",
        "Clippy assistant annoying paperclip",
        "Pop-up ads everywhere blinking text",
        "Under construction animated GIFs",
        "Marquee scrolling text nonstop",
        "Blink tag flashing headache",
        "Frames within frames nested chaos",
        "Tables for layout broken grids",
    ],
    "professional": [
        "Legal firm conservative navy blue",
        "Medical clean white sterile minimal",
        "Financial corporate dark green",
        "Accounting professional gray spreadsheet",
        "Consulting McKinsey blue white",
        "Real estate luxury gold elegant",
        "Insurance trustworthy blue stable",
        "Banking secure vault dark teal",
        "Government official boring beige",
        "Academic institutional serif traditional",
        "Pharmaceutical clinical white blue",
        "Architecture modern concrete minimal",
        "Engineering technical blueprint blue",
        "Aviation pilot cockpit precise",
        "Automotive industrial metallic gray",
        "Energy sector industrial yellow black",
        "Telecommunications connected network blue",
        "Retail e-commerce bright inviting",
        "Hospitality warm welcoming earth tones",
        "Nonprofit compassionate soft pastels",
    ],
}


def generate_themes(
    categories: List[str],
    count_per_category: int,
    dry_run: bool = False,
    output_path: Path = Path("config/themes.json")
) -> Dict[str, Dict[str, str]]:
    """
    Generate themes across specified categories.
    
    Args:
        categories: List of category names to generate from
        count_per_category: Number of themes to generate per category
        dry_run: If True, only print what would be generated
        output_path: Where to save themes.json
    
    Returns:
        Dictionary of {theme_name: theme_config}
    """
    # Load existing themes
    existing_themes = {}
    if output_path.exists():
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_themes = json.load(f)
            console.print(f"[dim]Loaded {len(existing_themes)} existing themes[/dim]\n")
        except json.JSONDecodeError:
            console.print("[yellow]Warning: Could not parse existing themes.json[/yellow]\n")
    
    # Prepare theme descriptions
    theme_queue = []
    for category in categories:
        if category not in THEME_CATEGORIES:
            console.print(f"[red]Error:[/red] Unknown category '{category}'")
            console.print(f"[yellow]Valid:[/yellow] {', '.join(THEME_CATEGORIES.keys())}")
            continue
        
        descriptions = THEME_CATEGORIES[category][:count_per_category]
        for i, description in enumerate(descriptions, 1):
            theme_name = f"{category}_{i:02d}"
            theme_queue.append((theme_name, description))
    
    if dry_run:
        console.print("[bold cyan]DRY RUN - Preview of themes to generate:[/bold cyan]\n")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Theme Name", style="cyan")
        table.add_column("Description", style="yellow")
        
        for name, desc in theme_queue:
            table.add_row(name, desc[:60] + "..." if len(desc) > 60 else desc)
        
        console.print(table)
        console.print(f"\n[bold]Total:[/bold] {len(theme_queue)} themes")
        console.print(f"[dim]Run without --dry-run to generate[/dim]\n")
        return existing_themes
    
    # Initialize ContentEngine
    try:
        brain = ContentEngine()
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to initialize ContentEngine: {e}")
        console.print("[yellow]Check:[/yellow] Is LM Studio running?")
        sys.exit(1)
    
    # Generate themes with progress bar
    console.print(f"[bold cyan]🏭 Trinity Centuria Factory[/bold cyan]\n")
    console.print(f"Generating {len(theme_queue)} themes...\n")
    
    generated = {}
    failed = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Generating themes...", total=len(theme_queue))
        
        for theme_name, description in theme_queue:
            progress.update(task, description=f"[cyan]Generating {theme_name}...")
            
            try:
                theme_config = brain.generate_theme_from_vibe(description)
                generated[theme_name] = theme_config
                progress.console.print(f"[green]✓[/green] {theme_name}: {description[:40]}...")
                
                # Small delay to avoid overwhelming LLM
                time.sleep(0.5)
                
            except ContentEngineError as e:
                failed.append((theme_name, str(e)))
                progress.console.print(f"[red]✗[/red] {theme_name}: Failed - {e}")
            
            progress.advance(task)
    
    # Summary
    console.print(f"\n[bold green]✅ Generation complete![/bold green]\n")
    console.print(f"[green]Success:[/green] {len(generated)} themes")
    if failed:
        console.print(f"[red]Failed:[/red] {len(failed)} themes")
        for name, error in failed[:5]:
            console.print(f"  [dim]{name}: {error[:60]}...[/dim]")
    
    # FIXED: Check for duplicates before merging (Security & Data Integrity)
    duplicates = set(existing_themes.keys()) & set(generated.keys())
    if duplicates:
        console.print(f"\n[yellow]⚠️  Warning:[/yellow] {len(duplicates)} duplicate theme(s) detected:")
        for dup in list(duplicates)[:5]:
            console.print(f"  [dim]- {dup} (will be overwritten)[/dim]")
        if len(duplicates) > 5:
            console.print(f"  [dim]... and {len(duplicates) - 5} more[/dim]")
        console.print()
    
    # Merge with existing themes
    all_themes = {**existing_themes, **generated}
    
    # Save to file
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_themes, f, indent=2)
        
        console.print(f"\n[bold]Saved to:[/bold] [cyan]{output_path}[/cyan]")
        console.print(f"[bold]Total themes:[/bold] [magenta]{len(all_themes)}[/magenta]\n")
        
    except Exception as e:
        console.print(f"\n[red]❌ Failed to save themes[/red]: {e}\n")
        sys.exit(1)
    
    return all_themes


def main():
    parser = argparse.ArgumentParser(
        description="Trinity Centuria Factory - Mass Theme Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--category",
        "-c",
        choices=list(THEME_CATEGORIES.keys()) + ["all"],
        default="all",
        help="Theme category to generate (default: all)"
    )
    
    parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=20,
        help="Number of themes per category (default: 20)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview themes without generating"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("config/themes.json"),
        help="Output path for themes.json (default: config/themes.json)"
    )
    
    args = parser.parse_args()
    
    # Determine categories
    if args.category == "all":
        categories = list(THEME_CATEGORIES.keys())
    else:
        categories = [args.category]
    
    # Generate
    generate_themes(
        categories=categories,
        count_per_category=args.count,
        dry_run=args.dry_run,
        output_path=args.output
    )


if __name__ == "__main__":
    main()
