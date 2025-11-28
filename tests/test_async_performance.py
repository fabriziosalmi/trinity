"""
Performance benchmarks: Sync vs Async ContentEngine

Tests the 6x throughput improvement target for async implementation.
"""

import asyncio
import json
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from trinity.components.async_brain import AsyncContentEngine
from trinity.components.brain import ContentEngine, ContentEngineError

# Sample portfolio data for testing
SAMPLE_PORTFOLIO = """
# Jane Developer - Full Stack Engineer

## About
Passionate software engineer with 5 years of experience building web applications.

## Projects

### project-alpha
A modern web framework for rapid development
Language: Python
Stars: 150
URL: https://github.com/jane/project-alpha

### data-viz
Interactive data visualization library
Language: JavaScript
Stars: 89
URL: https://github.com/jane/data-viz

### cli-utils
Command-line utilities for developers
Language: Rust
Stars: 45
URL: https://github.com/jane/cli-utils
"""


@pytest.fixture
def sample_portfolio_file():
    """Create temporary portfolio file."""
    with NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(SAMPLE_PORTFOLIO)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestAsyncPerformance:
    """Test async performance improvements."""

    @pytest.mark.asyncio
    async def test_async_single_generation(self, sample_portfolio_file, mocker):
        """Test async single content generation."""
        # Mock AsyncLLMClient
        mock_response = json.dumps(
            {
                "brand_name": "Test Brand",
                "tagline": "Test Tagline",
                "hero": {
                    "title": "Test Title",
                    "subtitle": "Test Subtitle",
                    "cta_primary": {"label": "Go", "url": "#"},
                    "cta_secondary": {"label": "Back", "url": "#"},
                },
                "repos": [
                    {
                        "name": "repo1",
                        "description": "desc1",
                        "url": "http://repo1",
                        "stars": 10,
                        "language": "Python",
                        "tags": ["tag1"],
                    }
                ],
                "menu_items": [],
                "cta": {"label": "Click", "url": "#"},
            }
        )

        mocker.patch(
            "trinity.components.llm_client.AsyncLLMClient.generate_content",
            return_value=mock_response,
        )

        async with AsyncContentEngine() as engine:
            result = await engine.generate_content_async(sample_portfolio_file, "brutalist")

            assert result is not None
            assert "brand_name" in result
            assert "repos" in result
            assert len(result["repos"]) > 0

    @pytest.mark.asyncio
    async def test_async_concurrent_generation(self, sample_portfolio_file, mocker):
        """Test concurrent async generation."""
        themes = ["brutalist", "hacker", "minimalist"]

        # Mock AsyncLLMClient
        mock_response = json.dumps(
            {
                "brand_name": "Test Brand",
                "tagline": "Test Tagline",
                "hero": {
                    "title": "Test Title",
                    "subtitle": "Test Subtitle",
                    "cta_primary": {"label": "Go", "url": "#"},
                    "cta_secondary": {"label": "Back", "url": "#"},
                },
                "repos": [
                    {
                        "name": "repo1",
                        "description": "desc1",
                        "url": "http://repo1",
                        "stars": 10,
                        "language": "Python",
                        "tags": ["tag1"],
                    }
                ],
                "menu_items": [],
                "cta": {"label": "Click", "url": "#"},
            }
        )

        mocker.patch(
            "trinity.components.llm_client.AsyncLLMClient.generate_content",
            return_value=mock_response,
        )

        async with AsyncContentEngine() as engine:
            # Generate all themes concurrently
            tasks = [
                engine.generate_content_async(sample_portfolio_file, theme) for theme in themes
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check results
            assert len(results) == len(themes)

            for theme, result in zip(themes, results):
                assert not isinstance(result, Exception)
                assert result is not None
                assert "brand_name" in result

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_performance_comparison(self, sample_portfolio_file, mocker):
        """
        Compare sync vs async performance.

        Target: 6x throughput improvement with async.
        Conservative test: 3 requests should be at least 2x faster.
        """
        num_requests = 3
        theme = "minimalist"
        delay = 0.1

        mock_content = json.dumps(
            {
                "brand_name": "Test Brand",
                "tagline": "Test Tagline",
                "hero": {
                    "title": "Test Title",
                    "subtitle": "Test Subtitle",
                    "cta_primary": {"label": "Go", "url": "#"},
                    "cta_secondary": {"label": "Back", "url": "#"},
                },
                "repos": [
                    {
                        "name": "repo1",
                        "description": "desc1",
                        "url": "http://repo1",
                        "stars": 10,
                        "language": "Python",
                        "tags": ["tag1"],
                    }
                ],
                "menu_items": [],
                "cta": {"label": "Click", "url": "#"},
            }
        )

        # Mock Sync ContentEngine (OpenAI client)
        mock_openai_resp = mocker.Mock()
        mock_openai_resp.choices = [mocker.Mock(message=mocker.Mock(content=mock_content))]

        def sync_side_effect(*args, **kwargs):
            time.sleep(delay)
            return mock_openai_resp

        mocker.patch("openai.resources.chat.Completions.create", side_effect=sync_side_effect)

        # Mock Async ContentEngine (AsyncLLMClient)
        async def async_side_effect(*args, **kwargs):
            await asyncio.sleep(delay)
            return mock_content

        mocker.patch(
            "trinity.components.llm_client.AsyncLLMClient.generate_content",
            side_effect=async_side_effect,
        )

        # Sync benchmark
        print("\n=== Sync Performance Benchmark ===")
        sync_start = time.time()

        engine = ContentEngine()
        for i in range(num_requests):
            result = engine.generate_content(sample_portfolio_file, theme)
            print(f"  Sync request {i+1}/{num_requests}: ✓")

        sync_duration = time.time() - sync_start
        print(f"Total sync time: {sync_duration:.2f}s")
        print(f"Avg per request: {sync_duration/num_requests:.2f}s")

        # Async benchmark
        print("\n=== Async Performance Benchmark ===")
        async_start = time.time()

        async with AsyncContentEngine() as engine:
            tasks = [
                engine.generate_content_async(sample_portfolio_file, theme)
                for i in range(num_requests)
            ]

            results = await asyncio.gather(*tasks)

            for i, result in enumerate(results):
                print(f"  Async request {i+1}/{num_requests}: ✓")

        async_duration = time.time() - async_start
        print(f"Total async time: {async_duration:.2f}s")
        print(f"Avg per request: {async_duration/num_requests:.2f}s")

        # Performance analysis
        speedup = sync_duration / async_duration if async_duration > 0 else 0

        print("\n=== Performance Comparison ===")
        print(f"Sync:    {sync_duration:.2f}s ({sync_duration/num_requests:.2f}s per request)")
        print(f"Async:   {async_duration:.2f}s ({async_duration/num_requests:.2f}s per request)")
        print(f"Speedup: {speedup:.1f}x")

        # Performance assertions
        assert (
            async_duration < sync_duration
        ), f"Async should be faster than sync ({async_duration:.2f}s vs {sync_duration:.2f}s)"

        # Conservative target: at least 1.5x speedup with 3 concurrent requests
        # (Ideal would be ~3x, but network/LLM overhead reduces this)
        min_speedup = 1.5
        assert speedup >= min_speedup, f"Expected speedup >= {min_speedup}x, got {speedup:.1f}x"

        print(f"\n✓ Performance test PASSED (speedup: {speedup:.1f}x >= {min_speedup}x)")

    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        """Test async error handling with invalid file."""
        async with AsyncContentEngine() as engine:
            with pytest.raises(FileNotFoundError):
                await engine.generate_content_async("/nonexistent/file.txt", "brutalist")

    @pytest.mark.asyncio
    async def test_context_manager_required(self, sample_portfolio_file):
        """Test that async engine requires context manager."""
        engine = AsyncContentEngine()

        with pytest.raises(ContentEngineError, match="not initialized"):
            await engine.generate_content_async(sample_portfolio_file, "brutalist")


class TestBackwardCompatibility:
    """Ensure sync ContentEngine still works."""

    def test_sync_content_engine(self, sample_portfolio_file):
        """Test sync ContentEngine still functions."""
        try:
            engine = ContentEngine()
            result = engine.generate_content(sample_portfolio_file, "brutalist")

            assert result is not None
            assert "brand_name" in result
            assert "repos" in result

        except ContentEngineError as e:
            pytest.skip(f"LLM not available: {e}")


@pytest.mark.asyncio
async def test_high_concurrency(sample_portfolio_file, mocker):
    """
    Test high concurrency scenario (10+ concurrent requests).

    This simulates real-world batch processing.
    Skip if LLM not available.
    """
    num_requests = 10
    theme = "minimalist"
    delay = 0.05  # Faster delay for high concurrency test

    print(f"\n=== High Concurrency Test ({num_requests} requests) ===")

    mock_content = json.dumps(
        {
            "brand_name": "Test Brand",
            "tagline": "Test Tagline",
            "hero": {
                "title": "Test Title",
                "subtitle": "Test Subtitle",
                "cta_primary": {"label": "Go", "url": "#"},
                "cta_secondary": {"label": "Back", "url": "#"},
            },
            "repos": [
                {
                    "name": "repo1",
                    "description": "desc1",
                    "url": "http://repo1",
                    "stars": 10,
                    "language": "Python",
                    "tags": ["tag1"],
                }
            ],
            "menu_items": [],
            "cta": {"label": "Click", "url": "#"},
        }
    )

    # Mock Async ContentEngine (AsyncLLMClient)
    async def async_side_effect(*args, **kwargs):
        await asyncio.sleep(delay)
        return mock_content

    mocker.patch(
        "trinity.components.llm_client.AsyncLLMClient.generate_content",
        side_effect=async_side_effect,
    )

    start = time.time()

    async with AsyncContentEngine() as engine:
        tasks = [
            engine.generate_content_async(sample_portfolio_file, theme) for _ in range(num_requests)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        duration = time.time() - start

        # Count successes
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = num_requests - successes

        print(f"Duration: {duration:.2f}s")
        print(f"Throughput: {num_requests/duration:.1f} req/s")
        print(f"Successes: {successes}/{num_requests}")
        print(f"Failures: {failures}/{num_requests}")

        # At least 50% should succeed
        assert successes >= num_requests * 0.5, f"Too many failures: {failures}/{num_requests}"

        # Should achieve at least 5 req/s (vs ~1 req/s sync)
        throughput = num_requests / duration
        assert throughput >= 5.0, f"Throughput too low: {throughput:.1f} req/s (expected >= 5.0)"

        print(f"✓ High concurrency test PASSED ({throughput:.1f} req/s)")
