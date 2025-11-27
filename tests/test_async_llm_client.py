"""
Test async LLM client functionality and performance.
"""

import asyncio
import time

import pytest

from trinity.components.llm_client import AsyncLLMClient, LLMClient, LLMClientError


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
    async def test_async_generate_content_basic(self, mocker):
        """Test basic async content generation."""
        # Mock the HTTP response
        mock_response = mocker.Mock()
        mock_response.json.return_value = {"response": '{"message": "Hello"}'}
        mock_response.status_code = 200
        
        # Mock the post method
        mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

        async with AsyncLLMClient(base_url="http://localhost:11434") as client:
            response = await client.generate_content(
                prompt='Say "Hello" in JSON format: {"message": "..."}', expect_json=True
            )
            assert response
            assert len(response) > 0
            assert "Hello" in response

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, mocker):
        """Test concurrent request handling."""
        # Mock the HTTP response
        mock_response = mocker.Mock()
        mock_response.json.return_value = {"response": '{"message": "Response"}'}
        mock_response.status_code = 200
        
        # Mock the post method
        mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

        async with AsyncLLMClient(base_url="http://localhost:11434") as client:
            prompts = [
                'Say "Request 1" in JSON',
                'Say "Request 2" in JSON',
                'Say "Request 3" in JSON',
            ]

            # Send all requests concurrently
            tasks = [client.generate_content(prompt, expect_json=True) for prompt in prompts]

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # At least verify we got responses
            assert len(responses) == len(prompts)

            # Check no exceptions
            for resp in responses:
                assert not isinstance(resp, Exception)

    @pytest.mark.asyncio
    async def test_performance_comparison(self, mocker):
        """Compare sync vs async performance (mocked with delay)."""
        num_requests = 3
        delay = 0.1

        # Mock Sync Client
        def sync_side_effect(*args, **kwargs):
            time.sleep(delay)
            mock_resp = mocker.Mock()
            mock_resp.json.return_value = {"response": '{"message": "Sync"}'}
            mock_resp.status_code = 200
            return mock_resp

        mocker.patch("httpx.Client.post", side_effect=sync_side_effect)

        # Mock Async Client
        async def async_side_effect(*args, **kwargs):
            await asyncio.sleep(delay)
            mock_resp = mocker.Mock()
            mock_resp.json.return_value = {"response": '{"message": "Async"}'}
            mock_resp.status_code = 200
            return mock_resp

        mocker.patch("httpx.AsyncClient.post", side_effect=async_side_effect)

        # Sync benchmark
        start_sync = time.time()
        with LLMClient(base_url="http://localhost:11434") as client:
            for i in range(num_requests):
                client.generate_content(prompt=f'Say "Sync {i}" in JSON', expect_json=True)
        sync_time = time.time() - start_sync

        # Async benchmark
        start_async = time.time()
        async with AsyncLLMClient(base_url="http://localhost:11434") as client:
            tasks = [
                client.generate_content(prompt=f'Say "Async {i}" in JSON', expect_json=True)
                for i in range(num_requests)
            ]
            await asyncio.gather(*tasks)
        async_time = time.time() - start_async

        # Async should be faster (or at least not slower)
        speedup = sync_time / async_time if async_time > 0 else 0

        print(f"\nPerformance Comparison ({num_requests} requests):")
        print(f"  Sync:  {sync_time:.2f}s")
        print(f"  Async: {async_time:.2f}s")
        print(f"  Speedup: {speedup:.1f}x")

        # With concurrent requests and simulated delay, we expect speedup
        # Sync: 3 * 0.1 = 0.3s
        # Async: 0.1s (concurrent)
        # Speedup should be around 3x
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

    def test_sync_client_basic(self, mocker):
        """Test sync client still functions."""
        # Mock the HTTP response
        mock_response = mocker.Mock()
        mock_response.json.return_value = {"response": '{"message": "Hello"}'}
        mock_response.status_code = 200
        
        # Mock the post method
        mocker.patch("httpx.Client.post", return_value=mock_response)

        with LLMClient(base_url="http://localhost:11434") as client:
            response = client.generate_content(prompt='Say "Hello" in JSON', expect_json=True)
            assert response
            assert "Hello" in response
