"""
Trinity Core - LLM Client
Rule #7: Explicit error handling for network calls
Rule #28: Structured logging
Rule #5: Type safety and validation
"""

import json
import logging
import time
from enum import Enum
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    raise ImportError("httpx required. Install with: pip install httpx")

logger = logging.getLogger(__name__)

# Rule #8: Constants
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_TEMPERATURE = 0.2


class LLMProvider(Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    LLAMACPP = "llamacpp"


class LLMClientError(Exception):
    """Base exception for LLM client errors."""

    pass


class LLMClient:
    """
    Fault-tolerant LLM API client.
    Responsibilities:
    - Send prompts to local LLM (Ollama/LlamaCPP)
    - Handle retries and timeouts
    - Parse JSON responses

    Does NOT:
    - Validate content schema (handled by validator)
    - Render HTML (handled by builder)
    """

    def __init__(
        self,
        provider: str = "ollama",
        model_name: str = "llama3.2:3b",
        base_url: str = "http://localhost:11434",
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        """
        Initialize LLM client.

        Args:
            provider: Provider type (ollama, llamacpp)
            model_name: Model identifier
            base_url: API endpoint
            timeout: Request timeout in seconds
            max_retries: Max retry attempts on failure
            temperature: Sampling temperature (0.0-2.0)
        """
        self.provider = LLMProvider(provider)
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature

        # HTTP client with sensible defaults
        self.client = httpx.Client(timeout=httpx.Timeout(timeout), follow_redirects=True)

        logger.info(f"LLMClient initialized: {provider}/{model_name} @ {base_url}")

    def _build_request_payload(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build provider-specific request payload."""
        if self.provider == LLMProvider.OLLAMA:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": self.temperature},
            }
            if system_prompt:
                payload["system"] = system_prompt
            return payload
        else:
            # LlamaCPP format
            return {"prompt": prompt, "temperature": self.temperature, "max_tokens": 2000}

    def generate_content(
        self, prompt: str, system_prompt: Optional[str] = None, expect_json: bool = True
    ) -> str:
        """
        Send prompt to LLM and return response.

        Args:
            prompt: User prompt
            system_prompt: System/instruction prompt
            expect_json: Whether to validate JSON response

        Returns:
            LLM response text

        Raises:
            LLMClientError: On connection/timeout/parse errors
        """
        endpoint = (
            f"{self.base_url}/api/generate"
            if self.provider == LLMProvider.OLLAMA
            else f"{self.base_url}/completion"
        )
        payload = self._build_request_payload(prompt, system_prompt)

        # Rule #7: Retry logic with exponential backoff
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"LLM request (attempt {attempt}/{self.max_retries})")

                response = self.client.post(
                    endpoint, json=payload, headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()

                # Parse response
                result = response.json()

                # Extract text based on provider
                if self.provider == LLMProvider.OLLAMA:
                    text = result.get("response", "")
                else:
                    text = result.get("content", "")

                if not text:
                    raise LLMClientError("Empty response from LLM")

                # Validate JSON if expected
                if expect_json:
                    try:
                        json.loads(text)  # Validate JSON structure
                    except json.JSONDecodeError as e:
                        logger.warning(f"Response is not valid JSON: {e}")
                        # Don't fail - let validator handle it

                logger.info(f"✓ LLM response received ({len(text)} chars)")
                return text

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP {e.response.status_code}: {e}")
                if attempt == self.max_retries:
                    raise LLMClientError(
                        f"LLM request failed after {self.max_retries} attempts: {e}"
                    )

            except httpx.TimeoutException:
                logger.warning(f"Request timeout (attempt {attempt})")
                if attempt == self.max_retries:
                    raise LLMClientError(f"LLM timeout after {self.max_retries} attempts")

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise LLMClientError(f"LLM client error: {e}")

            # Exponential backoff
            if attempt < self.max_retries:
                sleep_time = 2**attempt
                logger.info(f"Retrying in {sleep_time}s...")
                time.sleep(sleep_time)

        raise LLMClientError("Max retries exceeded")

    def close(self):
        """Close HTTP client."""
        self.client.close()
        logger.info("LLMClient closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Demo usage
if __name__ == "__main__":
    with LLMClient() as client:
        try:
            response = client.generate_content(
                prompt='Say \'Hello from Trinity\' in JSON format: {"message": "..."}',
                expect_json=True,
            )
            print(f"Response: {response}")
        except LLMClientError as e:
            print(f"Error: {e}")
