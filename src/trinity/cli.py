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


if __name__ == "__main__":
    app()
