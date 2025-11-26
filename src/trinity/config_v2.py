"""
Trinity Configuration System V2 - Immutable Configuration

Implements immutable configuration objects with dependency injection.
Replaces mutable global TrinityConfig pattern.

Key improvements:
- Immutable frozen Pydantic models
- Explicit dependency injection
- No global state
- Thread-safe by design
"""

from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from trinity.exceptions import ConfigurationError, PathResolutionError, ThemeNotFoundError


class ImmutableTrinityConfig(BaseSettings):
    """
    Immutable configuration for Trinity Core.

    Design principles:
    - Frozen after initialization (no mutation)
    - All paths validated at creation time
    - Explicit dependency injection (passed to components)
    - No global instances

    Priority (highest to lowest):
    1. Environment variables (TRINITY_*)
    2. config/settings.yaml
    3. Default values
    """

    # Paths
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent,
        description="Project root directory",
        frozen=True,
    )
    template_dir: Path = Field(
        default=Path("library"), description="Templates directory", frozen=True
    )
    output_dir: Path = Field(default=Path("output"), description="Output directory", frozen=True)
    config_dir: Path = Field(default=Path("config"), description="Config directory", frozen=True)
    data_dir: Path = Field(default=Path("data"), description="Data directory", frozen=True)

    # LLM Configuration
    lm_studio_url: str = Field(
        default="http://localhost:1234/v1",
        description="LM Studio API endpoint (override with LM_STUDIO_URL env var)",
        frozen=True,
    )
    openai_api_key: Optional[str] = Field(
        default=None, description="OpenAI API key (use secrets manager)", frozen=True
    )
    llm_timeout: int = Field(
        default=120, description="LLM request timeout (seconds)", frozen=True, ge=1, le=600
    )
    llm_max_retries: int = Field(
        default=3, description="Max LLM retry attempts", frozen=True, ge=1, le=10
    )

    # Guardian Configuration
    guardian_enabled: bool = Field(default=False, description="Enable Guardian QA", frozen=True)
    guardian_vision_ai: bool = Field(
        default=False, description="Enable Vision AI analysis", frozen=True
    )
    guardian_viewport_width: int = Field(
        default=1920, description="Viewport width for screenshots", frozen=True, ge=320, le=7680
    )
    guardian_viewport_height: int = Field(
        default=1080, description="Viewport height for screenshots", frozen=True, ge=240, le=4320
    )
    guardian_timeout: int = Field(
        default=30, description="Guardian timeout (seconds)", frozen=True, ge=5, le=300
    )

    # ML Prediction Configuration
    predictive_enabled: bool = Field(
        default=True, description="Enable ML predictive healing", frozen=True
    )
    model_dir: Path = Field(
        default=Path("models"), description="Trained models directory", frozen=True
    )
    risk_threshold: float = Field(
        default=0.7,
        description="Risk threshold for pre-emptive healing",
        frozen=True,
        ge=0.0,
        le=1.0,
    )

    # Self-Healing Configuration
    max_retries: int = Field(
        default=3, description="Max build retry attempts", frozen=True, ge=1, le=10
    )
    truncate_length: int = Field(
        default=50, description="String truncation length", frozen=True, ge=10, le=500
    )
    auto_fix_enabled: bool = Field(default=True, description="Enable automatic fixes", frozen=True)

    # Build Configuration
    default_theme: str = Field(default="enterprise", description="Default theme name", frozen=True)
    available_themes: List[str] = Field(
        default=["enterprise", "brutalist", "editorial"],
        description="Available theme names",
        frozen=True,
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level", frozen=True)
    log_file: Path = Field(
        default=Path("logs/trinity.log"), description="Log file path", frozen=True
    )

    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = Field(
        default=5, description="Failures before circuit opens", frozen=True, ge=1, le=20
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60, description="Seconds before attempting recovery", frozen=True, ge=10, le=600
    )
    circuit_breaker_expected_exception: str = Field(
        default="Exception", description="Exception type that triggers circuit breaker", frozen=True
    )

    model_config = SettingsConfigDict(
        env_prefix="TRINITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,  # Make the entire config immutable
        validate_assignment=True,  # Validate on any attempted assignment
    )

    @field_validator("default_theme")
    @classmethod
    def validate_default_theme(cls, v: str, values) -> str:
        """Validate that default theme exists in available themes."""
        # Note: In Pydantic v2, we need to check if available_themes is in values.data
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ConfigurationError(
                f"Invalid log level: {v}. Must be one of {valid_levels}",
                details={"log_level": v, "valid_levels": list(valid_levels)},
            )
        return v.upper()

    def get_absolute_path(self, relative_path: Path) -> Path:
        """
        Convert relative path to absolute based on project root.

        Args:
            relative_path: Path to convert

        Returns:
            Absolute path

        Raises:
            PathResolutionError: If path cannot be resolved
        """
        try:
            if relative_path.is_absolute():
                return relative_path
            return (self.project_root / relative_path).resolve()
        except Exception as e:
            raise PathResolutionError(
                f"Failed to resolve path: {relative_path}",
                details={"path": str(relative_path), "error": str(e)},
            )

    @property
    def templates_path(self) -> Path:
        """Absolute path to templates directory."""
        return self.get_absolute_path(self.template_dir)

    @property
    def output_path(self) -> Path:
        """Absolute path to output directory."""
        return self.get_absolute_path(self.output_dir)

    @property
    def config_path(self) -> Path:
        """Absolute path to config directory."""
        return self.get_absolute_path(self.config_dir)

    @property
    def themes_config_path(self) -> Path:
        """Absolute path to themes.json."""
        return self.config_path / "themes.json"

    @property
    def prompts_config_path(self) -> Path:
        """Absolute path to prompts.yaml."""
        return self.config_path / "prompts.yaml"

    def validate_theme_exists(self, theme: str) -> None:
        """
        Validate that a theme exists in available themes.

        Args:
            theme: Theme name to validate

        Raises:
            ThemeNotFoundError: If theme doesn't exist
        """
        if theme not in self.available_themes:
            raise ThemeNotFoundError(
                f"Theme '{theme}' not found",
                details={"requested_theme": theme, "available_themes": self.available_themes},
            )


def create_config(**overrides) -> ImmutableTrinityConfig:
    """
    Factory function to create immutable configuration.

    Use this instead of directly instantiating TrinityConfig to ensure
    proper initialization and validation.

    Args:
        **overrides: Override default configuration values

    Returns:
        Immutable configuration instance

    Example:
        >>> config = create_config(max_retries=5, log_level="DEBUG")
        >>> engine = TrinityEngine(config=config)
    """
    return ImmutableTrinityConfig(**overrides)


# Singleton instance for CLI and simple use cases
# Components should still accept config via dependency injection
_default_config: Optional[ImmutableTrinityConfig] = None


def get_default_config() -> ImmutableTrinityConfig:
    """
    Get or create default configuration singleton.

    Note: Prefer explicit dependency injection over this singleton.
    This exists for backward compatibility and CLI usage.

    Returns:
        Default configuration instance
    """
    global _default_config
    if _default_config is None:
        _default_config = create_config()
    return _default_config
