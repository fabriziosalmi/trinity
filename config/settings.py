"""
Configuration settings with Pydantic validation.
Rule #8: No magic numbers/strings.
Rule #5: Type safety for all config.
"""
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    """LLM client configuration."""
    provider: str = Field(default="ollama", description="LLM provider (ollama, llamacpp)")
    model_name: str = Field(default="llama3.2:3b", description="Model identifier")
    base_url: str = Field(default="http://localhost:11434", description="API endpoint")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Max retry attempts")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Sampling temperature")


class BuildConfig(BaseModel):
    """Build process configuration."""
    template_dir: Path = Field(default=Path("library"), description="Template directory")
    output_dir: Path = Field(default=Path("output"), description="Output directory")
    log_dir: Path = Field(default=Path("logs"), description="Log directory")
    default_theme: str = Field(default="enterprise", description="Default theme name")
    validate_html: bool = Field(default=True, description="Enable HTML validation")
    minify_output: bool = Field(default=False, description="Minify generated HTML")
    
    @field_validator('template_dir', 'log_dir')
    @classmethod
    def dir_must_exist(cls, v: Path) -> Path:
        """Rule #5: Check directory existence."""
        if not v.exists():
            raise ValueError(f"Directory does not exist: {v}")
        return v


class ContentSchema(BaseModel):
    """Expected content structure for page generation."""
    brand_name: str = Field(..., min_length=1, max_length=100)
    tagline: Optional[str] = Field(None, max_length=200)
    menu_items: List[dict] = Field(default_factory=list)
    cta: Optional[dict] = None
    hero: Optional[dict] = None
    repos: Optional[List[dict]] = Field(default_factory=list)
    
    @field_validator('menu_items')
    @classmethod
    def validate_menu_items(cls, v: List[dict]) -> List[dict]:
        """Ensure menu items have required fields."""
        for item in v:
            if 'label' not in item or 'url' not in item:
                raise ValueError("Menu items must have 'label' and 'url' fields")
        return v


class AppSettings(BaseModel):
    """Global application settings."""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    build: BuildConfig = Field(default_factory=BuildConfig)
    debug: bool = Field(default=False, description="Enable debug mode")
    
    class Config:
        # Rule #64: Prevent arbitrary code execution
        validate_assignment = True


# Singleton instance
settings = AppSettings()
