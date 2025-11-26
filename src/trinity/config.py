"""
Trinity Configuration System

Uses Pydantic Settings for type-safe configuration management.
Loads from config/settings.yaml and environment variables.
"""
import os
from pathlib import Path
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TrinityConfig(BaseSettings):
    """
    Centralized configuration for Trinity Core.
    
    Priority (highest to lowest):
    1. Environment variables (TRINITY_*)
    2. config/settings.yaml
    3. Default values
    """
    
    # Paths
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent,
        description="Project root directory"
    )
    template_dir: Path = Field(default=Path("library"), description="Templates directory")
    output_dir: Path = Field(default=Path("output"), description="Output directory")
    config_dir: Path = Field(default=Path("config"), description="Config directory")
    data_dir: Path = Field(default=Path("data"), description="Data directory")
    
    # LLM Configuration
    lm_studio_url: str = Field(
        default="http://192.168.100.12:1234/v1",
        description="LM Studio API endpoint"
    )
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    llm_timeout: int = Field(default=120, description="LLM request timeout (seconds)")
    llm_max_retries: int = Field(default=3, description="Max LLM retry attempts")
    
    # Guardian Configuration
    guardian_enabled: bool = Field(default=False, description="Enable Guardian QA")
    guardian_vision_ai: bool = Field(default=False, description="Enable Vision AI analysis")
    guardian_viewport_width: int = Field(default=1920, description="Viewport width for screenshots")
    guardian_viewport_height: int = Field(default=1080, description="Viewport height for screenshots")
    guardian_timeout: int = Field(default=30, description="Guardian timeout (seconds)")
    
    # ML Prediction Configuration (Phase 3)
    predictive_enabled: bool = Field(default=True, description="Enable ML predictive healing")
    model_dir: Path = Field(default=Path("models"), description="Trained models directory")
    risk_threshold: float = Field(default=0.7, description="Risk threshold for pre-emptive healing")
    
    # Self-Healing Configuration
    max_retries: int = Field(default=3, description="Max build retry attempts")
    truncate_length: int = Field(default=50, description="String truncation length")
    auto_fix_enabled: bool = Field(default=True, description="Enable automatic fixes")
    
    # Build Configuration
    default_theme: str = Field(default="enterprise", description="Default theme name")
    available_themes: List[str] = Field(
        default=["enterprise", "brutalist", "editorial"],
        description="Available theme names"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Path = Field(default=Path("logs/trinity.log"), description="Log file path")
    
    model_config = SettingsConfigDict(
        env_prefix="TRINITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    def get_absolute_path(self, relative_path: Path) -> Path:
        """Convert relative path to absolute based on project root."""
        if relative_path.is_absolute():
            return relative_path
        return (self.project_root / relative_path).resolve()
    
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


def load_config() -> TrinityConfig:
    """Load Trinity configuration from environment and defaults."""
    return TrinityConfig()
