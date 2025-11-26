"""
Unit tests for Circuit Breaker implementation.
"""
import time

import pytest

from trinity.exceptions import CircuitOpenError
from trinity.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitState,
)


class TestCircuitBreakerBasics:
    """Test basic circuit breaker functionality."""

    def test_circuit_starts_closed(self):
        """Circuit should start in CLOSED state."""
        breaker = CircuitBreaker()
        assert breaker.state == CircuitState.CLOSED

    def test_successful_call_keeps_circuit_closed(self):
        """Successful calls should keep circuit closed."""
        breaker = CircuitBreaker()

        result = breaker.call(lambda: "success")

        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.stats.successful_requests == 1
        assert breaker.stats.failed_requests == 0

    def test_circuit_opens_after_threshold_failures(self):
        """Circuit should open after failure threshold is exceeded."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            expected_exception=ValueError
        )

        # Fail 3 times
        for _ in range(3):
            with pytest.raises(ValueError):
                breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))

        assert breaker.state == CircuitState.OPEN
        assert breaker.stats.failed_requests == 3

    def test_open_circuit_blocks_calls(self):
        """Open circuit should block calls immediately."""
        breaker = CircuitBreaker(
            failure_threshold=2,
            expected_exception=ValueError
        )

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))

        # Next call should fail fast with CircuitOpenError
        with pytest.raises(CircuitOpenError) as exc_info:
            breaker.call(lambda: "should not execute")

        assert "OPEN" in str(exc_info.value)

    def test_circuit_transitions_to_half_open(self):
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=1,  # 1 second
            expected_exception=ValueError
        )

        # Open circuit
        with pytest.raises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(1.1)

        # Next call should transition to HALF_OPEN
        result = breaker.call(lambda: "success")

        assert result == "success"
        assert breaker.state == CircuitState.CLOSED  # Success closes circuit

    def test_half_open_failure_reopens_circuit(self):
        """Failure in HALF_OPEN state should reopen circuit."""
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=1,
            expected_exception=ValueError
        )

        # Open circuit
        with pytest.raises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))

        time.sleep(1.1)

        # Fail during recovery
        with pytest.raises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))

        assert breaker.state == CircuitState.OPEN

    def test_decorator_interface(self):
        """Circuit breaker should work as decorator."""
        breaker = CircuitBreaker(failure_threshold=2)

        @breaker
        def my_function():
            return "success"

        result = my_function()
        assert result == "success"

    def test_reset_circuit(self):
        """Manual reset should close circuit."""
        breaker = CircuitBreaker(
            failure_threshold=1,
            expected_exception=ValueError
        )

        # Open circuit
        with pytest.raises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))

        assert breaker.state == CircuitState.OPEN

        # Reset
        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.stats.state_changes >= 2  # CLOSED -> OPEN -> CLOSED


class TestCircuitBreakerStatistics:
    """Test circuit breaker statistics."""

    def test_stats_track_requests(self):
        """Stats should track all requests."""
        breaker = CircuitBreaker(expected_exception=ValueError)

        # 3 successes
        for _ in range(3):
            breaker.call(lambda: "success")

        # 2 failures
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))

        assert breaker.stats.total_requests == 5
        assert breaker.stats.successful_requests == 3
        assert breaker.stats.failed_requests == 2

    def test_failure_rate_calculation(self):
        """Stats should calculate failure rate correctly."""
        breaker = CircuitBreaker(expected_exception=ValueError)

        # 1 success, 1 failure
        breaker.call(lambda: "success")
        with pytest.raises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))

        assert breaker.stats.failure_rate == 0.5
        assert breaker.stats.success_rate == 0.5

    def test_get_status(self):
        """get_status should return comprehensive state."""
        breaker = CircuitBreaker(
            name="test-breaker",
            failure_threshold=5
        )

        status = breaker.get_status()

        assert status["name"] == "test-breaker"
        assert status["state"] == "closed"
        assert status["failure_threshold"] == 5
        assert "stats" in status


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry."""

    def test_register_and_get_breaker(self):
        """Registry should store and retrieve breakers."""
        registry = CircuitBreakerRegistry()
        breaker = CircuitBreaker(name="my-breaker")

        registry.register("my-breaker", breaker)
        retrieved = registry.get("my-breaker")

        assert retrieved is breaker

    def test_get_all_status(self):
        """Registry should return status of all breakers."""
        registry = CircuitBreakerRegistry()
        breaker1 = CircuitBreaker(name="breaker-1")
        breaker2 = CircuitBreaker(name="breaker-2")

        registry.register("breaker-1", breaker1)
        registry.register("breaker-2", breaker2)

        all_status = registry.get_all_status()

        assert "breaker-1" in all_status
        assert "breaker-2" in all_status

    def test_reset_all_breakers(self):
        """Registry should reset all breakers."""
        registry = CircuitBreakerRegistry()
        breaker = CircuitBreaker(
            name="breaker",
            failure_threshold=1,
            expected_exception=ValueError
        )

        registry.register("breaker", breaker)

        # Open circuit
        with pytest.raises(ValueError):
            breaker.call(lambda: (_ for _ in ()).throw(ValueError("test")))

        assert breaker.state == CircuitState.OPEN

        # Reset all
        registry.reset_all()

        assert breaker.state == CircuitState.CLOSED
