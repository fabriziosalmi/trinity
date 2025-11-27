"""
Property-based tests for Trinity using Hypothesis.

These tests verify invariants and edge cases that are difficult to
catch with example-based tests.

Install: pip install hypothesis
"""

import pytest
from hypothesis import assume, given, settings, Verbosity
from hypothesis import strategies as st
from hypothesis.strategies import dictionaries, floats, integers, text

from trinity.config_v2 import create_config
from trinity.utils.circuit_breaker import CircuitBreaker, CircuitState
from trinity.utils.idempotency import IdempotencyKeyManager


class TestIdempotencyProperties:
    """Property-based tests for idempotency manager."""

    @given(
        param1=text(min_size=1, max_size=100),
        param2=integers(min_value=0, max_value=1000),
    )
    def test_same_inputs_produce_same_key(self, param1, param2):
        """Same inputs should always produce the same key."""
        manager = IdempotencyKeyManager(enable_persistence=False)

        key1 = manager.generate_key(param1=param1, param2=param2)
        key2 = manager.generate_key(param1=param1, param2=param2)

        assert key1 == key2, "Same inputs must produce identical keys"

    @given(
        param1=text(min_size=1, max_size=100),
        param2=text(min_size=1, max_size=100),
    )
    def test_different_inputs_produce_different_keys(self, param1, param2):
        """Different inputs should produce different keys."""
        assume(param1 != param2)  # Skip if inputs are accidentally equal

        manager = IdempotencyKeyManager(enable_persistence=False)

        key1 = manager.generate_key(value=param1)
        key2 = manager.generate_key(value=param2)

        assert key1 != key2, "Different inputs must produce different keys"

    @given(
        data=dictionaries(
            keys=text(min_size=1, max_size=10),
            values=integers() | text() | floats(allow_nan=False),
            min_size=1,
            max_size=10,
        )
    )
    def test_key_generation_is_deterministic(self, data):
        """Key generation should be deterministic for any input."""
        manager = IdempotencyKeyManager(enable_persistence=False)

        keys = [manager.generate_key(**data) for _ in range(5)]

        assert len(set(keys)) == 1, "Key generation must be deterministic"

    @given(result=text(min_size=1, max_size=1000), ttl=integers(min_value=1, max_value=3600))
    def test_stored_result_is_retrievable(self, result, ttl):
        """Stored results should be retrievable before expiration."""
        manager = IdempotencyKeyManager(enable_persistence=False, default_ttl=ttl)

        key = manager.generate_key(test="property_test")
        manager.store_result(key, result)

        retrieved = manager.get_result(key)

        assert retrieved == result, "Stored result must be retrievable"


class TestCircuitBreakerProperties:
    """Property-based tests for circuit breaker."""

    @given(
        threshold=integers(min_value=1, max_value=20), timeout=integers(min_value=1, max_value=300)
    )
    def test_circuit_opens_after_threshold_failures(self, threshold, timeout):
        """Circuit should open after exactly threshold failures."""
        breaker = CircuitBreaker(
            failure_threshold=threshold, recovery_timeout=timeout, expected_exception=ValueError
        )

        # Fail threshold-1 times
        for _ in range(threshold - 1):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))
            except ValueError:
                pass

        assert breaker.state == CircuitState.CLOSED, "Circuit should still be closed"

        # One more failure should open circuit
        try:
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))
        except ValueError:
            pass

        assert breaker.state == CircuitState.OPEN, "Circuit should be open after threshold"

    @given(successes=integers(min_value=1, max_value=100))
    def test_circuit_remains_closed_with_successes(self, successes):
        """Circuit should remain closed if all calls succeed."""
        breaker = CircuitBreaker(failure_threshold=5)

        for _ in range(successes):
            breaker.call(lambda: "success")

        assert breaker.state == CircuitState.CLOSED, "Circuit should remain closed"
        assert breaker.stats.successful_requests == successes
        assert breaker.stats.failed_requests == 0

    @given(
        failures=integers(min_value=1, max_value=10), threshold=integers(min_value=1, max_value=20)
    )
    def test_failure_count_accuracy(self, failures, threshold):
        """Failure count should accurately reflect number of failures."""
        assume(failures < threshold)  # Don't open circuit

        breaker = CircuitBreaker(failure_threshold=threshold, expected_exception=ValueError)

        for _ in range(failures):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))
            except ValueError:
                pass

        assert breaker.stats.failed_requests == failures
        assert breaker.state == CircuitState.CLOSED


class TestConfigurationProperties:
    """Property-based tests for configuration."""

    @given(
        max_retries=integers(min_value=1, max_value=10),
        llm_timeout=integers(min_value=1, max_value=600),
        truncate_length=integers(min_value=10, max_value=500),
    )
    def test_config_creation_with_valid_values(self, max_retries, llm_timeout, truncate_length):
        """Configuration should accept all valid values."""
        config = create_config(
            max_retries=max_retries, llm_timeout=llm_timeout, truncate_length=truncate_length
        )

        assert config.max_retries == max_retries
        assert config.llm_timeout == llm_timeout
        assert config.truncate_length == truncate_length

    @given(risk_threshold=floats(min_value=0.0, max_value=1.0))
    def test_risk_threshold_in_valid_range(self, risk_threshold):
        """Risk threshold should accept values between 0 and 1."""
        config = create_config(risk_threshold=risk_threshold)

        assert 0.0 <= config.risk_threshold <= 1.0

    def test_config_immutability(self):
        """Configuration should be immutable after creation."""
        config = create_config(max_retries=3)

        with pytest.raises(Exception):  # Pydantic ValidationError
            config.max_retries = 5


class TestLLMPromptProperties:
    """Property-based tests for LLM prompt generation."""

    @given(
        theme=st.sampled_from(["enterprise", "brutalist", "editorial"]),
        content=text(min_size=10, max_size=500),
    )
    def test_prompt_generation_is_deterministic(self, theme, content):
        """Same inputs should produce same prompt."""
        # This would test the prompt loading from YAML
        # Implementation depends on prompt loader
        pass


# Hypothesis settings for CI/CD
settings.register_profile("ci", max_examples=1000, deadline=None)
settings.register_profile("dev", max_examples=100, deadline=500)
settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)

# Use CI profile in GitHub Actions
import os

if os.getenv("CI"):
    settings.load_profile("ci")
else:
    settings.load_profile("dev")
