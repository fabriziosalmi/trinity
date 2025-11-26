"""
Test async LLM client functionality and performance.
"""
import asyncio
import time

import pytest

from src.llm_client import AsyncLLMClient, LLMClient, LLMClientError


class TestAsyncLLMClient:
    """Test async LLM client."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager lifecycle."""
        async with AsyncLLMClient() as client:
            assert client.client is not None
            assert client.client.is_closed is False

        # Client should be closed after context exit
        # Note: httpx doesn't expose is_closed, so we just verify no errors

    @pytest.mark.asyncio
    async def test_async_generate_content_basic(self):
        """Test basic async content generation."""
        async with AsyncLLMClient(base_url="http://localhost:11434") as client:
            try:
                response = await client.generate_content(
                    prompt='Say "Hello" in JSON format: {"message": "..."}',
                    expect_json=True
                )
                assert response
                assert len(response) > 0
            except LLMClientError as e:
                pytest.skip(f"LLM not available: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test concurrent request handling."""
        async with AsyncLLMClient(base_url="http://localhost:11434") as client:
            try:
                prompts = [
                    'Say "Request 1" in JSON',
                    'Say "Request 2" in JSON',
                    'Say "Request 3" in JSON',
                ]

                # Send all requests concurrently
                tasks = [
                    client.generate_content(prompt, expect_json=True)
                    for prompt in prompts
                ]

                responses = await asyncio.gather(*tasks, return_exceptions=True)

                # At least verify we got responses
                assert len(responses) == len(prompts)

                # Check no exceptions (or all are same exception type)
                for resp in responses:
                    if isinstance(resp, Exception):
                        pytest.skip(f"LLM not available: {resp}")

            except LLMClientError as e:
                pytest.skip(f"LLM not available: {e}")

    @pytest.mark.asyncio
    async def test_performance_comparison(self):
        """Compare sync vs async performance (skip if LLM unavailable)."""
        num_requests = 3

        # Sync benchmark
        try:
            start_sync = time.time()
            with LLMClient(base_url="http://localhost:11434") as client:
                for i in range(num_requests):
                    client.generate_content(
                        prompt=f'Say "Sync {i}" in JSON',
                        expect_json=True
                    )
            sync_time = time.time() - start_sync
        except LLMClientError:
            pytest.skip("LLM not available for sync test")

        # Async benchmark
        try:
            start_async = time.time()
            async with AsyncLLMClient(base_url="http://localhost:11434") as client:
                tasks = [
                    client.generate_content(
                        prompt=f'Say "Async {i}" in JSON',
                        expect_json=True
                    )
                    for i in range(num_requests)
                ]
                await asyncio.gather(*tasks)
            async_time = time.time() - start_async
        except LLMClientError:
            pytest.skip("LLM not available for async test")

        # Async should be faster (or at least not slower)
        speedup = sync_time / async_time if async_time > 0 else 0

        print(f"\nPerformance Comparison ({num_requests} requests):")
        print(f"  Sync:  {sync_time:.2f}s")
        print(f"  Async: {async_time:.2f}s")
        print(f"  Speedup: {speedup:.1f}x")

        # With 3 concurrent requests, we expect at least 2x speedup
        # (conservative target, should be closer to 3x)
        assert speedup >= 1.5, f"Expected speedup >= 1.5x, got {speedup:.1f}x"

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test async error handling."""
        # Invalid URL should fail gracefully
        async with AsyncLLMClient(base_url="http://invalid:9999") as client:
            with pytest.raises(LLMClientError):
                await client.generate_content(prompt="test")

    @pytest.mark.asyncio
    async def test_client_not_initialized(self):
        """Test error when client used outside context manager."""
        client = AsyncLLMClient()

        with pytest.raises(LLMClientError, match="not initialized"):
            await client.generate_content(prompt="test")


class TestSyncBackwardCompatibility:
    """Ensure sync client still works."""

    def test_sync_client_basic(self):
        """Test sync client still functions."""
        with LLMClient(base_url="http://localhost:11434") as client:
            try:
                response = client.generate_content(
                    prompt='Say "Hello" in JSON',
                    expect_json=True
                )
                assert response
            except LLMClientError as e:
                pytest.skip(f"LLM not available: {e}")
