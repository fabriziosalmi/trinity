"""
Trinity Core CLI - Modern Command Line Interface

Built with Typer for excellent UX and type safety.
"""
import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from trinity import __version__
from trinity.config import TrinityConfig
from trinity.engine import TrinityEngine, BuildStatus
from trinity.utils.logger import setup_logger, get_logger

# Initialize Typer app
app = typer.Typer(
    name="trinity",
    help="Trinity Core - AI-Powered Static Site Generator with Self-Healing QA",
    add_completion=False,
)

console = Console()


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"Trinity Core v{__version__}", style="bold green")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
):
    """Trinity Core - Build AI-powered static sites with self-healing QA."""
    pass


@app.command()
def build(
    theme: str = typer.Option(
        "enterprise",
        "--theme",
        "-t",
        help="Theme to apply (enterprise, brutalist, editorial)"
    ),
    input_file: Optional[Path] = typer.Option(
        None,
        "--input",
        "-i",
        help="Input JSON content file"
    ),
    output: str = typer.Option(
        "index.html",
        "--output",
        "-o",
        help="Output filename"
    ),
    use_llm: bool = typer.Option(
        False,
        "--llm",
        help="Generate content with LLM from raw text"
    ),
    guardian: bool = typer.Option(
        False,
        "--guardian",
        "-g",
        help="Enable Guardian QA (with self-healing)"
    ),
    guardian_vision: bool = typer.Option(
        False,
        "--vision",
        help="Enable Vision AI analysis (requires Qwen VL)"
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)"
    ),
):
    """
    Build a static site page.
    
    Examples:
    
        # Build with static JSON content
        trinity build --input data/content.json --theme brutalist
        
        # Build with LLM generation
        trinity build --input data/raw_portfolio.txt --llm --theme editorial
        
        # Build with Guardian QA and self-healing
        trinity build --input data/content.json --guardian --theme enterprise
    """
    # Setup logging
    config = TrinityConfig()
    logger = setup_logger(log_level=log_level, log_file=config.log_file)
    
    console.print(f"\n[bold cyan]Trinity Core v{__version__}[/bold cyan]")
    console.print(f"Building: [yellow]{output}[/yellow] (theme: [green]{theme}[/green])\n")
    
    # Initialize engine
    config.guardian_enabled = guardian
    config.guardian_vision_ai = guardian_vision
    config.default_theme = theme
    engine = TrinityEngine(config)
    
    try:
        if use_llm:
            # LLM-powered build
            if not input_file:
                console.print("[red]Error:[/red] --input required for LLM mode", style="bold")
                raise typer.Exit(code=1)
            
            result = engine.build_with_llm(
                raw_text_path=str(input_file),
                theme=theme,
                output_filename=output,
                enable_guardian=guardian
            )
        else:
            # Static content build
            if input_file:
                with open(input_file, "r", encoding="utf-8") as f:
                    content = json.load(f)
            else:
                # Use mock data
                content = _get_mock_content()
            
            result = engine.build_with_self_healing(
                content=content,
                theme=theme,
                output_filename=output,
                enable_guardian=guardian
            )
        
        # Display result
        _display_build_result(result)
        
        # Exit with appropriate code
        if result.status == BuildStatus.SUCCESS:
            return  # Success exit
        else:
            raise typer.Exit(code=1)
            
    except typer.Exit:
        raise  # Re-raise typer exits
    except Exception as e:
        console.print(f"[red]Build failed:[/red] {e}", style="bold")
        logger.error(f"Build failed: {e}", exc_info=True)
        raise typer.Exit(code=1)


@app.command()
def chaos(
    theme: str = typer.Option(
        "brutalist",
        "--theme",
        "-t",
        help="Theme to test"
    ),
    guardian: bool = typer.Option(
        True,
        "--guardian/--no-guardian",
        help="Enable/disable Guardian (enabled by default)"
    ),
):
    """
    Run chaos test with intentionally broken content.
    
    Tests Guardian detection and self-healing capabilities.
    """
    console.print("\n[bold red]⚠️  CHAOS MODE ACTIVATED[/bold red]")
    console.print("Testing Guardian with intentionally broken layout...\n")
    
    config = TrinityConfig()
    logger = setup_logger(log_level="INFO", log_file=config.log_file)
    
    # Load chaos content
    chaos_file = config.data_dir / "chaos_content.json"
    if not chaos_file.exists():
        console.print(f"[red]Error:[/red] Chaos content not found: {chaos_file}")
        raise typer.Exit(code=1)
    
    with open(chaos_file, "r", encoding="utf-8") as f:
        content = json.load(f)
    
    # Build with Guardian
    config.guardian_enabled = guardian
    engine = TrinityEngine(config)
    
    result = engine.build_with_self_healing(
        content=content,
        theme=theme,
        output_filename=f"index_{theme}_chaos.html",
        enable_guardian=guardian
    )
    
    _display_build_result(result)
    
    if result.status == BuildStatus.REJECTED:
        console.print("\n✅ [green]Chaos test successful![/green]")
        console.print("Guardian correctly detected layout issues.")
        return  # Success exit for chaos test
    else:
        console.print("\n⚠️  [yellow]Unexpected result[/yellow]")
        raise typer.Exit(code=1)


@app.command()
def themes():
    """List available themes."""
    config = TrinityConfig()
    
    table = Table(title="Available Themes", show_header=True, header_style="bold magenta")
    table.add_column("Theme Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    
    theme_descriptions = {
        "enterprise": "Professional corporate design with clean gradients",
        "brutalist": "Raw, bold, unapologetically direct aesthetic",
        "editorial": "Magazine-inspired layout with elegant typography"
    }
    
    for theme in config.available_themes:
        description = theme_descriptions.get(theme, "No description")
        table.add_row(theme, description)
    
    console.print()
    console.print(table)
    console.print()


@app.command()
def config_info():
    """Show current Trinity configuration."""
    config = TrinityConfig()
    
    console.print("\n[bold cyan]Trinity Configuration[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    
    table.add_row("LM Studio URL", config.lm_studio_url)
    table.add_row("Templates Path", str(config.templates_path))
    table.add_row("Output Path", str(config.output_path))
    table.add_row("Default Theme", config.default_theme)
    table.add_row("Max Retries", str(config.max_retries))
    table.add_row("Guardian Enabled", str(config.guardian_enabled))
    table.add_row("Vision AI", str(config.guardian_vision_ai))
    table.add_row("Log Level", config.log_level)
    
    console.print(table)
    console.print()


def _display_build_result(result):
    """Display formatted build result."""
    console.print("\n" + "=" * 60)
    console.print("[bold]BUILD RESULT[/bold]")
    console.print("=" * 60)
    
    # Status
    status_colors = {
        BuildStatus.SUCCESS: "green",
        BuildStatus.FAILED: "red",
        BuildStatus.REJECTED: "yellow",
        BuildStatus.PARTIAL: "yellow"
    }
    color = status_colors.get(result.status, "white")
    console.print(f"Status: [{color}]{result.status.value.upper()}[/{color}]")
    
    # Basic info
    console.print(f"Theme: {result.theme}")
    console.print(f"Attempts: {result.attempts}")
    
    if result.output_path:
        console.print(f"Output: {result.output_path}")
        console.print(f"\n📂 Open in browser: [cyan]file://{result.output_path.absolute()}[/cyan]")
    
    # Fixes applied
    if result.fixes_applied:
        console.print(f"\n🚑 Fixes Applied ({len(result.fixes_applied)}):")
        for fix in result.fixes_applied:
            console.print(f"  • {fix}")
    
    # Guardian report
    if result.guardian_report:
        report = result.guardian_report
        if report["approved"]:
            console.print(f"\n✅ Guardian: [green]APPROVED[/green]")
            console.print(f"Reason: {report['reason']}")
        else:
            console.print(f"\n❌ Guardian: [red]REJECTED[/red]")
            console.print(f"Reason: {report['reason']}")
            if report.get("issues"):
                console.print(f"\nIssues ({len(report['issues'])}):")
                for issue in report["issues"]:
                    console.print(f"  • {issue}")
    
    # Errors
    if result.errors:
        console.print(f"\n❌ Errors ({len(result.errors)}):")
        for error in result.errors:
            console.print(f"  • [red]{error}[/red]")
    
    console.print("=" * 60 + "\n")


def _get_mock_content():
    """Get mock content for demo builds."""
    return {
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
            "subtitle": "Combine human-crafted HTML with LLM-generated content.",
            "cta_primary": {"label": "View Demo", "url": "#demo"},
            "cta_secondary": {"label": "Read Docs", "url": "#docs"}
        },
        "repos": [
            {
                "name": "trinity-core",
                "description": "Python static site generator with LLM integration.",
                "url": "https://github.com/example/trinity-core",
                "tags": ["Python", "Jinja2", "LLM"],
                "stars": 127
            }
        ]
    }


@app.command()
def mine_stats(
    dataset: Optional[Path] = typer.Option(
        None,
        "--dataset",
        "-d",
        help="Path to training dataset CSV"
    ),
):
    """
    Show ML training dataset statistics.
    
    Displays metrics about collected build events:
    - Total samples (successful + failed builds)
    - Success rate
    - Themes and strategies distribution
    
    Example:
        trinity mine-stats
    """
    from trinity.components.dataminer import TrinityMiner
    
    miner = TrinityMiner(dataset_path=dataset) if dataset else TrinityMiner()
    stats = miner.get_dataset_stats()
    
    console.print("\n[bold cyan]📊 Trinity ML Dataset Statistics[/bold cyan]\n")
    
    # Create stats table
    table = Table(title="Dataset Overview")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    
    table.add_row("Total Samples", str(stats["total_samples"]))
    table.add_row("Positive (Success)", f"[green]{stats['positive_samples']}[/green]")
    table.add_row("Negative (Failure)", f"[red]{stats['negative_samples']}[/red]")
    table.add_row("Success Rate", f"{stats['success_rate']}%")
    
    console.print(table)
    
    # Themes distribution
    if stats["themes"]:
        console.print(f"\n[bold]Themes:[/bold] {', '.join(stats['themes'])}")
    
    # Strategies distribution
    if stats["strategies"]:
        console.print(f"[bold]Strategies:[/bold] {', '.join(stats['strategies'])}")
    
    # Dataset location
    console.print(f"\n[dim]Dataset: {miner.dataset_path}[/dim]\n")


@app.command()
def mine_generate(
    count: int = typer.Option(
        100,
        "--count",
        "-n",
        help="Number of random builds to generate"
    ),
    themes: Optional[str] = typer.Option(
        None,
        "--themes",
        help="Comma-separated theme list (default: all themes)"
    ),
    enable_guardian: bool = typer.Option(
        True,
        "--guardian/--no-guardian",
        help="Enable Guardian QA for each build"
    ),
):
    """
    Generate synthetic training data by building random layouts.
    
    Creates hundreds/thousands of random content + theme combinations,
    passes them through the Guardian, and logs results to the training dataset.
    
    This is the DATA MINING phase - run overnight to collect ML training samples.
    
    Examples:
        # Generate 100 random builds across all themes
        trinity mine-generate --count 100
        
        # Generate 1000 brutalist layouts only
        trinity mine-generate --count 1000 --themes brutalist
        
        # Fast mining without Guardian (for testing)
        trinity mine-generate --count 50 --no-guardian
    """
    import random
    import string
    from trinity.components.dataminer import TrinityMiner
    
    setup_logger("INFO")
    config = TrinityConfig()
    engine = TrinityEngine(config)
    
    # Parse themes
    if themes:
        theme_list = [t.strip() for t in themes.split(",")]
    else:
        theme_list = ["enterprise", "brutalist", "editorial"]
    
    console.print(f"\n[bold cyan]⛏️  Trinity Data Mining Mode[/bold cyan]\n")
    console.print(f"Target: {count} random builds")
    console.print(f"Themes: {', '.join(theme_list)}")
    console.print(f"Guardian: {'Enabled' if enable_guardian else 'Disabled'}\n")
    
    def random_text(min_len=10, max_len=200):
        """Generate random text of varying length."""
        length = random.randint(min_len, max_len)
        # Mix of normal words and pathological patterns
        if random.random() < 0.2:
            # 20% chance of pathological pattern (AAAA..., long URLs, etc.)
            patterns = [
                "A" * length,
                "https://example.com/" + "x" * length,
                "NoSpacesJustOneVeryLongWord" * (length // 28 + 1),
            ]
            return random.choice(patterns)[:length]
        else:
            # Normal text with random length
            words = []
            current_len = 0
            while current_len < length:
                word_len = random.randint(3, 12)
                word = ''.join(random.choices(string.ascii_lowercase, k=word_len))
                words.append(word)
                current_len += word_len + 1  # +1 for space
            return ' '.join(words)[:length]
    
    # Generate random builds
    successful = 0
    failed = 0
    
    with console.status("[bold green]Mining data...") as status:
        for i in range(count):
            theme = random.choice(theme_list)
            
            # Generate random content
            content = {
                "brand_name": random_text(5, 30),
                "tagline": random_text(20, 80),
                "hero": {
                    "title": random_text(10, 100),
                    "subtitle": random_text(30, 150)
                },
                "repos": [
                    {
                        "name": random_text(5, 25),
                        "description": random_text(50, 200),
                        "url": "https://example.com",
                        "tags": ["tag1", "tag2"],
                        "stars": random.randint(0, 1000)
                    }
                    for _ in range(random.randint(1, 3))
                ]
            }
            
            # Build with engine (will auto-log to dataset)
            result = engine.build_with_self_healing(
                content=content,
                theme=theme,
                output_filename=f"mine_{i}.html",
                enable_guardian=enable_guardian
            )
            
            if result.status == BuildStatus.SUCCESS:
                successful += 1
            else:
                failed += 1
            
            # Update status
            status.update(f"[bold green]Mining: {i+1}/{count} "
                         f"(✅ {successful} | ❌ {failed})")
    
    console.print(f"\n[bold green]✅ Mining complete![/bold green]")
    console.print(f"   Successful: {successful}")
    console.print(f"   Failed: {failed}")
    console.print(f"   Total samples: {successful + failed}\n")
    
    # Show updated stats
    miner = TrinityMiner()
    stats = miner.get_dataset_stats()
    console.print(f"[dim]Dataset now contains {stats['total_samples']} total samples[/dim]\n")


if __name__ == "__main__":
    app()
