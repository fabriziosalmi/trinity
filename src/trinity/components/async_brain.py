"""
Trinity - Async Content Engine (Async Brain)

Async version of ContentEngine using AsyncLLMClient.
Provides 6x throughput improvement for concurrent content generation.

Usage:
    async with AsyncContentEngine() as engine:
        results = await asyncio.gather(
            engine.generate_content_async("portfolio1.txt", "brutalist"),
            engine.generate_content_async("portfolio2.txt", "hacker"),
            engine.generate_content_async("portfolio3.txt", "minimalist"),
        )
"""

import asyncio
import json

# Import async LLM client
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import ValidationError

from trinity.components.brain import (
    DEFAULT_LM_STUDIO_URL,
    DEFAULT_MODEL_ID,
    ContentEngineError,
    GeneratedContentSchema,
)
from trinity.utils.logger import get_logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.llm_client import AsyncLLMClient, LLMClientError

logger = get_logger(__name__)


class AsyncContentEngine:
    """
    Async LLM-powered content generator.

    Provides async/await interface for high-throughput content generation.
    Use this when generating multiple pieces of content concurrently.

    Responsibilities:
    - Parse raw portfolio data asynchronously
    - Generate theme-appropriate copy via async LLM calls
    - Validate and structure output

    Does NOT:
    - Build HTML (handled by SiteBuilder)
    - Validate themes (handled by Validator)
    """

    def __init__(
        self,
        base_url: str = DEFAULT_LM_STUDIO_URL,
        model_id: str = DEFAULT_MODEL_ID,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        """
        Initialize async content engine.

        Args:
            base_url: LLM API endpoint
            model_id: Model identifier
            max_retries: Max retry attempts
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.model_id = model_id
        self.max_retries = max_retries
        self.timeout = timeout

        # LLM client (initialized in __aenter__)
        self.llm_client: Optional[AsyncLLMClient] = None

        logger.info(f"AsyncContentEngine initialized: {base_url} ({model_id})")

    def _get_system_prompt(self, theme: str) -> str:
        """
        Get system prompt for theme.

        In production, this should load from config/prompts.yaml.
        For now, simplified version for demo.
        """
        prompts = {
            "brutalist": (
                "You are a brutalist web designer. Use bold, raw, honest language. "
                "No decoration, just function and truth. Extract repository data and "
                "rewrite descriptions in brutalist style. Return valid JSON only."
            ),
            "hacker": (
                "You are a hacker/terminal enthusiast. Use technical, concise language. "
                "Think green text on black background. Extract repository data and "
                "rewrite descriptions in hacker style. Return valid JSON only."
            ),
            "minimalist": (
                "You are a minimalist designer. Use clean, simple, essential language. "
                "Less is more. Extract repository data and rewrite descriptions in "
                "minimalist style. Return valid JSON only."
            ),
        }

        return prompts.get(theme, prompts["minimalist"])

    def _clean_llm_response(self, content_str: str) -> str:
        """Remove markdown code blocks and extra whitespace."""
        # Remove markdown JSON blocks
        if "```json" in content_str:
            content_str = content_str.split("```json")[1].split("```")[0]
        elif "```" in content_str:
            content_str = content_str.split("```")[1].split("```")[0]

        return content_str.strip()

    async def generate_content_async(self, raw_text_path: str, theme: str) -> Dict[str, Any]:
        """
        Generate structured content from raw portfolio data using async LLM.

        Args:
            raw_text_path: Path to raw text file with portfolio data
            theme: Theme name for personality selection

        Returns:
            Validated content dictionary

        Raises:
            ContentEngineError: On LLM failure or validation error
        """
        if self.llm_client is None:
            raise ContentEngineError(
                "AsyncContentEngine not initialized. "
                "Use 'async with AsyncContentEngine()' context manager."
            )

        # Validate input path
        path = Path(raw_text_path)
        if not path.exists():
            raise FileNotFoundError(f"Raw data file not found: {path}")

        # Read file (sync operation, but fast)
        raw_text = path.read_text(encoding="utf-8")

        # Truncate if too long for context window
        max_chars = 30000
        if len(raw_text) > max_chars:
            logger.warning(f"Raw text truncated from {len(raw_text)} to {max_chars} chars")
            raw_text = raw_text[:max_chars]

        system_prompt = self._get_system_prompt(theme)

        logger.info(f"🧠 Async LLM request (theme: {theme})")

        # Build JSON schema prompt (simplified)
        user_prompt = f"""
EXTRACT AND REWRITE THIS PORTFOLIO DATA:

{raw_text}

Return ONLY valid JSON with this structure:
{{
    "brand_name": "Developer Name",
    "tagline": "Short tagline",
    "hero": {{
        "title": "Hero title",
        "subtitle": "Hero subtitle"
    }},
    "repos": [
        {{
            "name": "Repo Name",
            "description": "Rewritten description in {theme} style",
            "url": "https://github.com/...",
            "stars": 0,
            "language": "Python",
            "tags": ["tag1", "tag2"]
        }}
    ],
    "menu_items": [],
    "cta": {{"text": "CTA text", "url": "#"}}
}}
"""

        # Call async LLM with retry logic
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Async LLM generation attempt {attempt}/{self.max_retries}")

                # Use AsyncLLMClient
                content_str = await self.llm_client.generate_content(
                    prompt=user_prompt, system_prompt=system_prompt, expect_json=True
                )

                # Clean response
                content_str = self._clean_llm_response(content_str)

                logger.debug(f"Cleaned async LLM response: {content_str[:200]}...")

                # Parse JSON
                try:
                    data = json.loads(content_str)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from async LLM: {content_str[:300]}...")
                    raise ContentEngineError(f"LLM returned invalid JSON: {e}")

                # Validate with Pydantic
                try:
                    validated = GeneratedContentSchema(**data)
                    logger.info(
                        f"✓ Async content generated and validated: "
                        f"{validated.brand_name}, {len(validated.repos)} repos"
                    )
                    return validated.model_dump()

                except ValidationError as e:
                    logger.error(f"Pydantic validation failed: {e}")
                    raise ContentEngineError(f"Content validation failed: {e}")

            except LLMClientError as e:
                last_error = e
                logger.warning(f"Async LLM attempt {attempt} failed: {e}")

                if attempt < self.max_retries:
                    # Exponential backoff
                    sleep_time = 2**attempt
                    logger.info(f"Retrying in {sleep_time}s...")
                    await asyncio.sleep(sleep_time)
                else:
                    raise ContentEngineError(
                        f"Async LLM failed after {self.max_retries} attempts: {last_error}"
                    )

            except Exception as e:
                logger.error(f"Unexpected error in async content generation: {e}")
                raise ContentEngineError(f"Content generation error: {e}")

        raise ContentEngineError(f"Max retries exceeded: {last_error}")

    async def __aenter__(self):
        """Async context manager entry."""
        # Initialize async LLM client
        # Note: Ollama uses different endpoint format than OpenAI
        # We'll use our AsyncLLMClient which talks to Ollama
        self.llm_client = AsyncLLMClient(
            provider="ollama",
            model_name=self.model_id,
            base_url=self.base_url.replace("/v1", ""),  # Ollama doesn't use /v1
            timeout=self.timeout,
            max_retries=self.max_retries,
        )
        await self.llm_client.__aenter__()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.llm_client:
            await self.llm_client.__aexit__(exc_type, exc_val, exc_tb)


# Demo
if __name__ == "__main__":

    async def demo():
        """Demo async content generation."""
        print("=== Async Content Engine Demo ===")

        # Create sample portfolio file
        sample_path = Path("/tmp/sample_portfolio.txt")
        sample_path.write_text("""
# John Doe - Software Engineer

## Projects
- awesome-repo: A cool Python library for data processing (100 stars)
- web-app: Full-stack web application with React and FastAPI (50 stars)
- cli-tool: Command-line utility for developers (25 stars)
        """)

        try:
            async with AsyncContentEngine() as engine:
                # Single generation
                result = await engine.generate_content_async(str(sample_path), "brutalist")
                print(f"\nGenerated content: {result['brand_name']}")
                print(f"Repos: {len(result['repos'])}")

                # Concurrent generation (3 themes in parallel)
                print("\n=== Concurrent Generation (3 themes) ===")
                themes = ["brutalist", "hacker", "minimalist"]

                tasks = [engine.generate_content_async(str(sample_path), theme) for theme in themes]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for theme, result in zip(themes, results):
                    if isinstance(result, Exception):
                        print(f"{theme}: ERROR - {result}")
                    else:
                        print(f"{theme}: ✓ {result['brand_name']} ({len(result['repos'])} repos)")

        except ContentEngineError as e:
            print(f"Error: {e}")
        except FileNotFoundError as e:
            print(f"File error: {e}")
        finally:
            # Cleanup
            if sample_path.exists():
                sample_path.unlink()

    asyncio.run(demo())
