"""
Trinity Core - Circuit Breaker Pattern

Implements circuit breaker for external dependencies (LLM API, Playwright)
to prevent cascading failures and provide graceful degradation.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Failure threshold exceeded, requests fail fast
- HALF_OPEN: Testing if service recovered

References:
- https://martinfowler.com/bliki/CircuitBreaker.html
- https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker
"""
import time
import logging
from enum import Enum
from typing import Callable, Any, Optional, Type
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from trinity.exceptions import (
    CircuitBreakerError,
    CircuitOpenError,
    CircuitHalfOpenError,
    TrinityError
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failure threshold exceeded
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0
    
    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests
    
    @property
    def success_rate(self) -> float:
        """Calculate current success rate."""
        return 1.0 - self.failure_rate


class CircuitBreaker:
    """
    Circuit breaker implementation for resilient external service calls.
    
    Usage:
        >>> breaker = CircuitBreaker(
        ...     failure_threshold=5,
        ...     recovery_timeout=60,
        ...     expected_exception=LLMConnectionError
        ... )
        >>> 
        >>> @breaker
        ... def call_llm_api():
        ...     return llm.generate_content()
        ...
        >>> try:
        ...     result = call_llm_api()
        ... except CircuitOpenError:
        ...     # Circuit is open, use fallback
        ...     result = use_cached_response()
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
        half_open_max_attempts: int = 1,
        name: Optional[str] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type that triggers circuit breaker
            half_open_max_attempts: Attempts allowed in half-open state
            name: Optional name for logging and monitoring
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.half_open_max_attempts = half_open_max_attempts
        self.name = name or f"CircuitBreaker-{id(self)}"
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_attempts = 0
        self._stats = CircuitBreakerStats()
        
        logger.info(
            f"🔌 {self.name} initialized: "
            f"threshold={failure_threshold}, "
            f"timeout={recovery_timeout}s, "
            f"exception={expected_exception.__name__}"
        )
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self._state
    
    @property
    def stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        return self._stats
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._last_failure_time is None:
            return False
        
        time_since_failure = time.time() - self._last_failure_time
        return time_since_failure >= self.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self._stats.successful_requests += 1
        self._stats.last_success_time = datetime.now()
        
        if self._state == CircuitState.HALF_OPEN:
            # Successful recovery, close circuit
            logger.info(f"✅ {self.name}: Recovery successful, closing circuit")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_attempts = 0
            self._stats.state_changes += 1
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0
    
    def _on_failure(self, exception: Exception) -> None:
        """Handle failed call."""
        self._stats.failed_requests += 1
        self._stats.last_failure_time = datetime.now()
        self._last_failure_time = time.time()
        self._failure_count += 1
        
        logger.warning(
            f"⚠️  {self.name}: Failure #{self._failure_count} - {type(exception).__name__}: {exception}"
        )
        
        if self._state == CircuitState.HALF_OPEN:
            # Failure during recovery, reopen circuit
            logger.error(f"❌ {self.name}: Recovery failed, reopening circuit")
            self._state = CircuitState.OPEN
            self._half_open_attempts = 0
            self._stats.state_changes += 1
        
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                # Threshold exceeded, open circuit
                logger.error(
                    f"🔴 {self.name}: Failure threshold exceeded "
                    f"({self._failure_count}/{self.failure_threshold}), opening circuit"
                )
                self._state = CircuitState.OPEN
                self._stats.state_changes += 1
    
    def _call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitOpenError: If circuit is open
            CircuitHalfOpenError: If circuit is half-open and max attempts exceeded
        """
        self._stats.total_requests += 1
        
        # Check if we should attempt recovery
        if self._state == CircuitState.OPEN and self._should_attempt_reset():
            logger.info(f"🟡 {self.name}: Attempting recovery (half-open state)")
            self._state = CircuitState.HALF_OPEN
            self._half_open_attempts = 0
            self._stats.state_changes += 1
        
        # Handle circuit states
        if self._state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service unavailable. Retry after {self.recovery_timeout}s.",
                details={
                    "circuit_name": self.name,
                    "state": self._state.value,
                    "failure_count": self._failure_count,
                    "last_failure": self._last_failure_time,
                    "stats": {
                        "total_requests": self._stats.total_requests,
                        "failure_rate": self._stats.failure_rate,
                    }
                }
            )
        
        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_attempts >= self.half_open_max_attempts:
                raise CircuitHalfOpenError(
                    f"Circuit breaker '{self.name}' is HALF_OPEN. "
                    f"Maximum recovery attempts exceeded.",
                    details={
                        "circuit_name": self.name,
                        "state": self._state.value,
                        "attempts": self._half_open_attempts,
                    }
                )
            self._half_open_attempts += 1
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(e)
            raise
        except Exception as e:
            # Unexpected exception, don't trigger circuit breaker
            logger.warning(
                f"⚠️  {self.name}: Unexpected exception (not triggering circuit): "
                f"{type(e).__name__}: {e}"
            )
            raise
    
    def __call__(self, func: Callable) -> Callable:
        """
        Decorator interface for circuit breaker.
        
        Usage:
            @circuit_breaker
            def call_external_service():
                ...
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self._call(func, *args, **kwargs)
        
        return wrapper
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Explicit call interface for circuit breaker.
        
        Usage:
            result = circuit_breaker.call(external_service, arg1, arg2)
        """
        return self._call(func, *args, **kwargs)
    
    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        logger.info(f"🔄 {self.name}: Manual reset to CLOSED state")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_attempts = 0
        self._last_failure_time = None
        self._stats.state_changes += 1
    
    def get_status(self) -> dict:
        """
        Get current circuit breaker status.
        
        Returns:
            Dictionary with state and statistics
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "stats": {
                "total_requests": self._stats.total_requests,
                "successful_requests": self._stats.successful_requests,
                "failed_requests": self._stats.failed_requests,
                "failure_rate": self._stats.failure_rate,
                "success_rate": self._stats.success_rate,
                "state_changes": self._stats.state_changes,
                "last_failure": self._stats.last_failure_time.isoformat() if self._stats.last_failure_time else None,
                "last_success": self._stats.last_success_time.isoformat() if self._stats.last_success_time else None,
            }
        }


class CircuitBreakerRegistry:
    """
    Global registry for circuit breakers.
    
    Enables monitoring and management of all circuit breakers in the application.
    """
    
    _instance = None
    _breakers: dict[str, CircuitBreaker] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, name: str, breaker: CircuitBreaker) -> None:
        """Register a circuit breaker."""
        self._breakers[name] = breaker
        logger.info(f"📝 Registered circuit breaker: {name}")
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)
    
    def get_all_status(self) -> dict[str, dict]:
        """Get status of all registered circuit breakers."""
        return {
            name: breaker.get_status()
            for name, breaker in self._breakers.items()
        }
    
    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("🔄 All circuit breakers reset")


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()
