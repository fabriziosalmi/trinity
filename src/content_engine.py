"""
Trinity - Content Engine (The Brain)
Rule #7: Explicit error handling with retries
Rule #28: Structured logging
Rule #5: Type safety with Pydantic validation
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from openai import APIConnectionError, APIError, OpenAI
except ImportError:
    raise ImportError("openai package required. Install with: pip install openai")

from pydantic import BaseModel, Field, ValidationError

from src.text_processor import TextProcessor, TextProcessorError

# Rule #28: Structured logging
logger = logging.getLogger(__name__)

# Rule #8: No magic strings (these should come from config/settings.py in production)
# Docker-compatible: Uses LM_STUDIO_URL env var with fallback to localhost
DEFAULT_LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
DEFAULT_LM_STUDIO_KEY = "lm-studio"  # Dummy key, LM Studio ignores it
DEFAULT_MODEL_ID = "qwen2.5-coder-3b-instruct-mlx"


class RepositorySchema(BaseModel):
    """Pydantic schema for repository validation."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    url: str = Field(..., min_length=1)
    stars: Optional[int] = Field(None, ge=0)
    language: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class HeroSchema(BaseModel):
    """Pydantic schema for hero section."""

    title: str = Field(..., min_length=1, max_length=200)
    subtitle: str = Field(..., min_length=1, max_length=500)
    cta_primary: Optional[Dict[str, str]] = None
    cta_secondary: Optional[Dict[str, str]] = None


class GeneratedContentSchema(BaseModel):
    """Complete content structure returned by LLM."""

    brand_name: str = Field(..., min_length=1, max_length=100)
    tagline: Optional[str] = None
    hero: HeroSchema
    repos: List[RepositorySchema] = Field(..., min_items=1, max_items=20)
    menu_items: List[Dict[str, str]] = Field(default_factory=list)
    cta: Optional[Dict[str, str]] = None


class ContentEngineError(Exception):
    """Base exception for ContentEngine errors."""

    pass


class ContentEngine:
    """
    LLM-powered content generator.
    Responsibilities:
    - Parse raw portfolio data
    - Generate theme-appropriate copy via LLM
    - Validate and structure output

    Does NOT:
    - Build HTML (handled by SiteBuilder)
    - Validate themes (handled by Validator)
    """

    def __init__(
        self,
        base_url: str = DEFAULT_LM_STUDIO_URL,
        api_key: str = DEFAULT_LM_STUDIO_KEY,
        model_id: str = DEFAULT_MODEL_ID,
        max_retries: int = 3,
        enable_text_processing: bool = True,
    ):
        """
        Initialize ContentEngine with LM Studio endpoint.

        Args:
            base_url: LM Studio API endpoint
            api_key: API key (dummy for LM Studio)
            model_id: Model identifier
            max_retries: Max retry attempts on failure
            enable_text_processing: Apply post-LLM text transformations
        """
        self.base_url = base_url
        self.model_id = model_id
        self.max_retries = max_retries
        self.enable_text_processing = enable_text_processing

        # Initialize OpenAI-compatible client
        self.client = OpenAI(base_url=base_url, api_key=api_key)

        # Initialize TextProcessor
        if self.enable_text_processing:
            try:
                self.text_processor = TextProcessor()
                logger.info("TextProcessor loaded (The Enforcer is active)")
            except Exception as e:
                logger.warning(f"TextProcessor initialization failed: {e}")
                self.text_processor = None
        else:
            self.text_processor = None

        logger.info(f"ContentEngine initialized: {base_url} (model: {model_id})")

    def _get_system_prompt(self, theme: str) -> str:
        """
        Generate system prompt based on theme personality.

        Args:
            theme: Theme name (enterprise, brutalist, editorial)

        Returns:
            System prompt string
        """
        base_instruction = (
            "You are a Content API Engine. Your task is to extract project data from raw text "
            "and transform it into a STRICT JSON object.\n\n"
            "CRITICAL RULES:\n"
            "1. Output ONLY valid JSON - no markdown, no code blocks, no explanations\n"
            "2. Follow the exact schema structure provided\n"
            "3. Rewrite descriptions based on the specified tone/role\n"
            "4. Select the TOP 6 most interesting projects based on stars/activity\n"
            "5. Generate compelling hero section copy matching the theme\n"
        )

        # Theme-specific personalities (The Vibe Engine)
        vibes = {
            "enterprise": {
                "role": "Chief Technology Officer at a Fortune 500 company",
                "tone": "Professional, reliable, scalable, benefit-driven, trustworthy",
                "instructions": (
                    "Rewrite project descriptions as Enterprise SaaS products. "
                    "Focus on: reliability, security, scalability, ROI, compliance. "
                    "Use terms like: 'Enterprise-grade', 'Production-ready', 'Mission-critical', 'Platform'."
                ),
                "hero_style": "Professional headline emphasizing expertise and reliability",
            },
            "brutalist": {
                "role": "Elite DevOps Engineer / Security Researcher",
                "tone": "Raw, direct, technical, uppercase emphasis, cynical, no-bullshit",
                "instructions": (
                    "Rewrite descriptions to be PUNCHY and TECHNICAL. MAX 10 WORDS. "
                    "Use uppercase for emphasis. "
                    "Use terms like: DEPLOY, MONITOR, KILL, DETECT, FILTER, BLOCK, AUTOMATE. "
                    "No marketing fluff. Just what it does."
                ),
                "hero_style": "Bold, aggressive headline. Short and technical.",
            },
            "editorial": {
                "role": "Senior Technology Editor at Wired Magazine",
                "tone": "Sophisticated, narrative, thoughtful, intriguing, journalistic",
                "instructions": (
                    "Rewrite descriptions as catchy editorial headlines or thought-provoking summaries. "
                    "Focus on: innovation, impact, creativity, the 'why' behind the tool. "
                    "Use narrative techniques: ask questions, create intrigue, tell a micro-story."
                ),
                "hero_style": "Compelling editorial headline that sparks curiosity",
            },
        }

        vibe = vibes.get(theme, vibes["enterprise"])

        # JSON schema template (one-shot learning for Qwen)
        json_structure = {
            "brand_name": "Your Name",
            "tagline": "Optional tagline based on theme",
            "hero": {
                "title": "Generated hero title matching theme personality",
                "subtitle": "Generated subtitle (2-3 sentences, theme-appropriate)",
                "cta_primary": {"label": "Primary Action", "url": "https://github.com/username"},
                "cta_secondary": {"label": "Secondary Action", "url": "#projects"},
            },
            "menu_items": [
                {"label": "Projects", "url": "#projects"},
                {"label": "About", "url": "#about"},
                {"label": "Contact", "url": "#contact"},
            ],
            "cta": {"label": "View GitHub", "url": "https://github.com/username"},
            "repos": [
                {
                    "name": "project-name",
                    "description": "Rewritten description based on theme tone",
                    "url": "https://github.com/user/repo",
                    "stars": 123,
                    "language": "Python",
                    "tags": ["tag1", "tag2"],
                }
            ],
        }

        return (
            f"{base_instruction}\n"
            f"ROLE: {vibe['role']}\n"
            f"TONE: {vibe['tone']}\n"
            f"TASK: {vibe['instructions']}\n"
            f"HERO STYLE: {vibe['hero_style']}\n\n"
            f"REQUIRED JSON STRUCTURE:\n{json.dumps(json_structure, indent=2)}\n\n"
            f"Remember: Output ONLY the JSON object, nothing else."
        )

    def _clean_llm_response(self, raw_response: str) -> str:
        """
        Clean LLM response by removing markdown code blocks and extra whitespace.

        Args:
            raw_response: Raw LLM output

        Returns:
            Cleaned JSON string
        """
        # Remove markdown code blocks
        cleaned = re.sub(r"```(?:json)?\s*", "", raw_response)
        cleaned = re.sub(r"```\s*$", "", cleaned)

        # Remove any text before first { or after last }
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)

        return cleaned.strip()

    def generate_content(self, raw_text_path: str, theme: str) -> Dict[str, Any]:
        """
        Generate structured content from raw portfolio data using LLM.

        Args:
            raw_text_path: Path to raw text file with portfolio data
            theme: Theme name for personality selection

        Returns:
            Validated content dictionary

        Raises:
            ContentEngineError: On LLM failure or validation error
        """
        # Rule #5: Validate input path
        path = Path(raw_text_path)
        if not path.exists():
            raise FileNotFoundError(f"Raw data file not found: {path}")

        raw_text = path.read_text(encoding="utf-8")

        # Truncate if too long for 3B model context (8k tokens ≈ 32k chars)
        max_chars = 30000
        if len(raw_text) > max_chars:
            logger.warning(f"Raw text truncated from {len(raw_text)} to {max_chars} chars")
            raw_text = raw_text[:max_chars]

        system_prompt = self._get_system_prompt(theme)

        logger.info(f"🧠 Connecting to LM Studio at {self.base_url} (theme: {theme})")

        # Rule #7: Retry logic with exponential backoff
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"LLM generation attempt {attempt}/{self.max_retries}")

                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"EXTRACT AND REWRITE THIS PORTFOLIO DATA:\n\n{raw_text}",
                        },
                    ],
                    temperature=0.7,  # Some creativity for rewriting
                    max_tokens=2500,
                    timeout=60,  # 60s timeout
                )

                content_str = response.choices[0].message.content.strip()

                # Clean response
                content_str = self._clean_llm_response(content_str)

                logger.debug(f"Cleaned LLM response: {content_str[:200]}...")

                # Parse JSON
                try:
                    data = json.loads(content_str)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from LLM: {content_str[:300]}...")
                    last_error = e
                    continue  # Retry

                # Validate with Pydantic
                try:
                    validated = GeneratedContentSchema(**data)
                    logger.info(f"✓ Content validated: {len(validated.repos)} repos, theme={theme}")

                    # Convert to dict for processing
                    content_dict = validated.model_dump()

                    # Apply text transformations (The Enforcer)
                    if self.text_processor:
                        try:
                            content_dict = self.text_processor.process_content(content_dict, theme)
                            logger.info("✓ Text transformations applied")
                        except TextProcessorError as e:
                            logger.warning(
                                f"Text processing failed: {e} (using unprocessed content)"
                            )

                    return content_dict

                except ValidationError as e:
                    logger.error(f"Pydantic validation failed: {e}")
                    last_error = e
                    continue  # Retry

            except APIConnectionError as e:
                logger.error(f"Cannot connect to LM Studio at {self.base_url}")
                last_error = e
                # Don't retry connection errors immediately
                break

            except APIError as e:
                logger.error(f"LM Studio API error: {e}")
                last_error = e
                continue  # Retry

            except Exception as e:
                logger.exception("Unexpected error in ContentEngine")
                last_error = e
                continue

        # All retries failed
        raise ContentEngineError(
            f"Failed to generate content after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    def generate_content_with_fallback(
        self, raw_text_path: str, theme: str, fallback_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate content with automatic fallback to static data on failure.

        Args:
            raw_text_path: Path to raw portfolio data
            theme: Theme name
            fallback_path: Path to fallback JSON (optional)

        Returns:
            Generated or fallback content
        """
        try:
            return self.generate_content(raw_text_path, theme)
        except ContentEngineError as e:
            logger.warning(f"LLM generation failed: {e}")

            if fallback_path and Path(fallback_path).exists():
                logger.info(f"Loading fallback content from {fallback_path}")
                with open(fallback_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.critical("No fallback available!")
                raise


# Demo usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    engine = ContentEngine()

    try:
        content = engine.generate_content(raw_text_path="data/raw_portfolio.txt", theme="brutalist")

        print("\n" + "=" * 60)
        print("GENERATED CONTENT")
        print("=" * 60)
        print(json.dumps(content, indent=2))

    except Exception as e:
        print(f"Error: {e}")
