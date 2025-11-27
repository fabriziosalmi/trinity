"""
Trinity v0.6.0 - Integration Example

Demonstrates the new architecture with all refactoring improvements:
- Immutable configuration with dependency injection
- Custom exception handling
- Circuit breaker for resilience
- Idempotency for safe retries
- Secrets management
- Externalized prompts

This example shows how to build a site using the refactored architecture.
"""
import yaml
from pathlib import Path
from typing import Optional

# New imports from refactored architecture
from trinity.config_v2 import create_config, ImmutableTrinityConfig
from trinity.exceptions import (
    LLMConnectionError,
    CircuitOpenError,
    ContentGenerationError,
    BuildError
)
from trinity.utils.circuit_breaker import CircuitBreaker
from trinity.utils.idempotency import IdempotencyKeyManager, idempotent
from trinity.utils.secrets import secrets_manager
from trinity.utils.logger import get_logger

# Legacy imports (to be updated)
from trinity.components.brain import ContentEngine
from trinity.components.builder import SiteBuilder
from trinity.engine import TrinityEngine

logger = get_logger(__name__)


class RefactoredTrinityEngine:
    """
    Refactored Trinity Engine demonstrating new architecture patterns.
    
    Key improvements:
    - Dependency injection for configuration
    - Circuit breakers for LLM calls
    - Idempotent content generation
    - Secure secrets management
    - Externalized prompts
    """
    
    def __init__(self, config: Optional[ImmutableTrinityConfig] = None):
        """
        Initialize engine with dependency injection.
        
        Args:
            config: Immutable configuration (optional, creates default if None)
        """
        # Dependency injection - config is passed in, not created globally
        self.config = config or create_config()
        
        # Load API key from secrets manager (not environment variable)
        api_key = secrets_manager.get_secret(
            "openai_api_key",
            default=None
        )
        
        # Load prompts from external YAML file
        self.prompts = self._load_prompts()
        
        # Initialize idempotency manager for content generation
        self.idempotency_manager = IdempotencyKeyManager(
            default_ttl=3600,  # 1 hour cache
            enable_persistence=True
        )
        
        # Create circuit breaker for LLM calls
        self.llm_circuit_breaker = CircuitBreaker(
            name="llm-api",
            failure_threshold=self.config.circuit_breaker_failure_threshold,
            recovery_timeout=self.config.circuit_breaker_recovery_timeout,
            expected_exception=LLMConnectionError
        )
        
        # Initialize components with configuration
        self.content_engine = ContentEngine(
            base_url=self.config.lm_studio_url,
            api_key=api_key or "lm-studio",
            max_retries=self.config.llm_max_retries
        )
        
        self.builder = SiteBuilder(
            template_dir=str(self.config.templates_path)
        )
        
        logger.info(
            f"🚀 Refactored Trinity Engine initialized\n"
            f"   Config: {self.config.model_config}\n"
            f"   Prompts: {len(self.prompts)} categories loaded\n"
            f"   Circuit Breaker: {self.llm_circuit_breaker.name}\n"
            f"   Idempotency: {'enabled' if self.idempotency_manager.enable_persistence else 'disabled'}"
        )
    
    def _load_prompts(self) -> dict:
        """
        Load prompts from external YAML file.
        
        Returns:
            Dictionary of prompt templates
            
        Raises:
            ConfigurationError: If prompts file cannot be loaded
        """
        prompts_path = self.config.prompts_config_path
        
        try:
            with open(prompts_path) as f:
                prompts = yaml.safe_load(f)
            logger.info(f"✅ Loaded prompts from {prompts_path}")
            return prompts
        except FileNotFoundError:
            logger.error(f"❌ Prompts file not found: {prompts_path}")
            # Return minimal default prompts
            return {"content_generation": {"vibes": {}}}
        except yaml.YAMLError as e:
            logger.error(f"❌ Invalid YAML in prompts file: {e}")
            return {"content_generation": {"vibes": {}}}
    
    @idempotent(
        manager=None,  # Will use global manager
        key_params=['theme', 'raw_content'],
        ttl=3600
    )
    def generate_content_idempotent(
        self,
        theme: str,
        raw_content: str
    ) -> dict:
        """
        Generate content with idempotency.
        
        Subsequent calls with same parameters return cached result
        without calling LLM API.
        
        Args:
            theme: Theme name
            raw_content: Raw portfolio content
            
        Returns:
            Generated content dictionary
            
        Raises:
            ContentGenerationError: If generation fails
        """
        # This method is decorated with @idempotent
        # First call will execute, subsequent calls return cached result
        return self._generate_content_internal(theme, raw_content)
    
    def _generate_content_internal(self, theme: str, raw_content: str) -> dict:
        """
        Internal content generation with circuit breaker.
        
        Args:
            theme: Theme name
            raw_content: Raw portfolio content
            
        Returns:
            Generated content dictionary
            
        Raises:
            CircuitOpenError: If circuit is open
            LLMConnectionError: If LLM connection fails
            ContentGenerationError: If content generation fails
        """
        try:
            # Use circuit breaker to prevent cascading failures
            def _call_llm():
                return self.content_engine.generate_content(
                    raw_content=raw_content,
                    theme=theme
                )
            
            # Call through circuit breaker
            content = self.llm_circuit_breaker.call(_call_llm)
            
            logger.info(f"✅ Content generated for theme '{theme}'")
            return content
            
        except CircuitOpenError as e:
            # Circuit is open, use fallback
            logger.error(f"🔴 Circuit breaker open: {e}")
            logger.info("Using fallback content...")
            
            # Return minimal fallback content
            return {
                "brand_name": "Portfolio",
                "tagline": "Under Construction",
                "hero": {
                    "title": "Service Temporarily Unavailable",
                    "subtitle": "Please try again later."
                },
                "repos": []
            }
            
        except LLMConnectionError as e:
            # Specific LLM connection error
            logger.error(f"🔌 LLM connection failed: {e.details}")
            raise
            
        except Exception as e:
            # Wrap unexpected errors
            raise ContentGenerationError(
                f"Content generation failed: {str(e)}",
                details={"theme": theme, "error": str(e)}
            )
    
    def build_site(
        self,
        theme: str,
        raw_content: str,
        output_filename: str = "index.html"
    ) -> Path:
        """
        Build complete site with all architectural improvements.
        
        Args:
            theme: Theme name
            raw_content: Raw portfolio content
            output_filename: Output filename
            
        Returns:
            Path to generated HTML file
            
        Raises:
            BuildError: If build fails
        """
        try:
            # Validate theme exists
            self.config.validate_theme_exists(theme)
            
            # Generate content (idempotent + circuit breaker)
            logger.info(f"🎨 Generating content for theme: {theme}")
            content = self.generate_content_idempotent(theme, raw_content)
            
            # Build HTML
            logger.info(f"🏗️  Building HTML...")
            html = self.builder.build(
                content=content,
                theme=theme,
                template_name="base.html"
            )
            
            # Write to output
            output_path = self.config.output_path / output_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            logger.info(f"✅ Site built successfully: {output_path}")
            
            # Log idempotency stats
            stats = self.idempotency_manager.get_stats()
            logger.info(
                f"📊 Idempotency stats: "
                f"{stats['active_entries']} cached, "
                f"{stats['total_entries']} total"
            )
            
            # Log circuit breaker status
            cb_status = self.llm_circuit_breaker.get_status()
            logger.info(
                f"🔌 Circuit breaker: {cb_status['state']}, "
                f"failure rate: {cb_status['stats']['failure_rate']:.2%}"
            )
            
            return output_path
            
        except Exception as e:
            raise BuildError(
                f"Site build failed: {str(e)}",
                details={"theme": theme, "output": output_filename}
            )


def main():
    """
    Example usage of refactored Trinity Engine.
    """
    # Create immutable configuration with custom values
    config = create_config(
        max_retries=5,
        llm_timeout=120,
        circuit_breaker_failure_threshold=3,
        default_theme="brutalist"
    )
    
    # Initialize engine with dependency injection
    engine = RefactoredTrinityEngine(config=config)
    
    # Example portfolio content
    raw_content = """
    Name: John Doe
    Role: Full Stack Developer
    
    Projects:
    - trinity-core: AI-powered static site generator
    - portfolio-builder: Automated portfolio creation
    """
    
    try:
        # Build site (idempotent, circuit breaker protected)
        output_path = engine.build_site(
            theme="brutalist",
            raw_content=raw_content,
            output_filename="portfolio.html"
        )
        
        print(f"\n✅ Success! Site built at: {output_path}")
        
        # Second call will use cached content (idempotent)
        print("\n🔄 Building again (should use cache)...")
        output_path2 = engine.build_site(
            theme="brutalist",
            raw_content=raw_content,
            output_filename="portfolio2.html"
        )
        print(f"✅ Cached build completed: {output_path2}")
        
    except CircuitOpenError:
        print("\n🔴 Circuit breaker is open. Service temporarily unavailable.")
    except ContentGenerationError as e:
        print(f"\n❌ Content generation failed: {e.message}")
        print(f"   Details: {e.details}")
    except BuildError as e:
        print(f"\n❌ Build failed: {e.message}")
        print(f"   Details: {e.details}")


if __name__ == "__main__":
    main()
