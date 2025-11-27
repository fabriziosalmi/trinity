"""
Test LLM client caching functionality.
"""

import pytest

from trinity.components.llm_client import AsyncLLMClient, LLMClientError


@pytest.mark.asyncio
async def test_cache_basic(mocker):
    """Test basic caching functionality."""
    # Mock the HTTP response
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"response": '{"message": "Hello Cache"}'}
    mock_response.status_code = 200
    
    # Mock the post method
    mock_post = mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

    # Enable caching
    async with AsyncLLMClient(enable_cache=True, cache_ttl=60) as client:
        prompt = "Say 'Hello Cache' in JSON format"

        # First call (cache miss, would call LLM)
        response1 = await client.generate_content(prompt, use_cache=True)

        # Second call (cache hit, instant)
        response2 = await client.generate_content(prompt, use_cache=True)

        # Responses should be identical (from cache)
        assert response1 == response2
        
        # Verify LLM was called only once
        assert mock_post.call_count == 1

@pytest.mark.asyncio
async def test_cache_disabled():
    """Test that caching can be disabled."""
    async with AsyncLLMClient(enable_cache=False) as client:
        # Cache should not be initialized
        assert client.cache is None

@pytest.mark.asyncio
async def test_cache_bypass(mocker):
    """Test cache bypass with use_cache=False."""
    # Mock the HTTP response
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"response": '{"message": "Random"}'}
    mock_response.status_code = 200
    
    # Mock the post method
    mock_post = mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

    async with AsyncLLMClient(enable_cache=True) as client:
        prompt = "Generate random number in JSON"

        # Both calls should go to LLM (not cached)
        response1 = await client.generate_content(prompt, use_cache=False)
        response2 = await client.generate_content(prompt, use_cache=False)

        # Responses might be different (random)
        assert response1 is not None
        assert response2 is not None
        
        # Verify LLM was called twice
        assert mock_post.call_count == 2

@pytest.mark.asyncio
async def test_cache_different_prompts(mocker):
    """Test that different prompts get different cache keys."""
    # Mock the HTTP response
    mock_response = mocker.Mock()
    mock_response.json.side_effect = [
        {"response": '{"message": "A"}'},
        {"response": '{"message": "B"}'}
    ]
    mock_response.status_code = 200
    
    # Mock the post method
    mock_post = mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

    async with AsyncLLMClient(enable_cache=True) as client:
        response1 = await client.generate_content("Say 'A' in JSON")
        response2 = await client.generate_content("Say 'B' in JSON")

        # Different prompts should have different responses
        assert response1 != response2
        
        # Verify LLM was called twice
        assert mock_post.call_count == 2


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
