"""
Test LLM client caching functionality.
"""

import pytest

from trinity.components.llm_client import AsyncLLMClient, LLMClientError


@pytest.mark.asyncio
async def test_cache_basic():
    """Test basic caching functionality."""
    # Enable caching
    async with AsyncLLMClient(enable_cache=True, cache_ttl=60) as client:
        prompt = "Say 'Hello Cache' in JSON format"

        # First call (cache miss, would call LLM)
        try:
            response1 = await client.generate_content(prompt, use_cache=True)

            # Second call (cache hit, instant)
            response2 = await client.generate_content(prompt, use_cache=True)

            # Responses should be identical (from cache)
            assert response1 == response2

        except LLMClientError as e:
            # LLM not available, skip test
            pytest.skip(f"LLM not available: {e}")


@pytest.mark.asyncio
async def test_cache_disabled():
    """Test that caching can be disabled."""
    async with AsyncLLMClient(enable_cache=False) as client:
        # Cache should not be initialized
        assert client.cache is None


@pytest.mark.asyncio
async def test_cache_bypass():
    """Test cache bypass with use_cache=False."""
    async with AsyncLLMClient(enable_cache=True) as client:
        prompt = "Generate random number in JSON"

        try:
            # Both calls should go to LLM (not cached)
            response1 = await client.generate_content(prompt, use_cache=False)
            response2 = await client.generate_content(prompt, use_cache=False)

            # Responses might be different (random)
            assert response1 is not None
            assert response2 is not None

        except LLMClientError as e:
            pytest.skip(f"LLM not available: {e}")


@pytest.mark.asyncio
async def test_cache_different_prompts():
    """Test that different prompts get different cache keys."""
    async with AsyncLLMClient(enable_cache=True) as client:
        try:
            response1 = await client.generate_content("Say 'A' in JSON")
            response2 = await client.generate_content("Say 'B' in JSON")

            # Different prompts should have different responses
            assert response1 != response2

        except LLMClientError as e:
            pytest.skip(f"LLM not available: {e}")


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics retrieval."""
    async with AsyncLLMClient(enable_cache=True) as client:
        if client.cache is None:
            pytest.skip("Cache not initialized")

        stats = await client.cache.get_stats_async()

        # Should have memory and filesystem tiers
        assert "memory" in stats
        assert "filesystem" in stats

        # Memory stats
        assert stats["memory"]["tier"] == "memory"
        assert "entries" in stats["memory"]

        # Filesystem stats
        assert stats["filesystem"]["tier"] == "filesystem"
        assert "entries" in stats["filesystem"]


@pytest.mark.asyncio
async def test_cache_cleanup():
    """Test cache cleanup."""
    async with AsyncLLMClient(enable_cache=True) as client:
        if client.cache is None:
            pytest.skip("Cache not initialized")

        # Clear cache
        result = await client.cache.clear_async()

        # Should return counts
        assert isinstance(result, dict)
        assert "memory" in result
        assert "filesystem" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
