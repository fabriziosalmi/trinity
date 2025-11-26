"""
Trinity Core - Idempotency Key Manager

Ensures operations can be safely retried without duplicate side effects.
Critical for content generation and healing operations.

Features:
- Hash-based key generation
- In-memory and persistent storage
- Automatic expiration
- Thread-safe operations

Reference:
- https://stripe.com/docs/api/idempotent_requests
"""
import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from trinity.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IdempotentResult:
    """
    Stored result for idempotent operation.

    Attributes:
        key: Idempotency key
        result: Operation result
        timestamp: When result was stored
        expires_at: When result expires
        metadata: Optional metadata
    """
    key: str
    result: Any
    timestamp: datetime
    expires_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if result has expired."""
        return datetime.now() > self.expires_at

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "key": self.key,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IdempotentResult":
        """Deserialize from dictionary."""
        return cls(
            key=data["key"],
            result=data["result"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            metadata=data.get("metadata", {})
        )


class IdempotencyKeyManager:
    """
    Manages idempotency keys for operations.

    Usage:
        >>> manager = IdempotencyKeyManager()
        >>>
        >>> # Generate key from input
        >>> key = manager.generate_key(theme="brutalist", content="...")
        >>>
        >>> # Check if operation was already performed
        >>> if result := manager.get_result(key):
        ...     return result
        >>>
        >>> # Perform operation and store result
        >>> result = expensive_operation()
        >>> manager.store_result(key, result, ttl=3600)
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        default_ttl: int = 3600,
        enable_persistence: bool = True
    ):
        """
        Initialize idempotency key manager.

        Args:
            storage_path: Path for persistent storage (optional)
            default_ttl: Default TTL in seconds for stored results
            enable_persistence: Enable persistent storage to disk
        """
        self.default_ttl = default_ttl
        self.enable_persistence = enable_persistence
        self.storage_path = storage_path or Path("data/idempotency_cache.json")

        # In-memory cache
        self._cache: Dict[str, IdempotentResult] = {}
        self._lock = threading.Lock()

        # Load from disk if persistence enabled
        if self.enable_persistence:
            self._load_from_disk()

        logger.info(
            f"🔑 Idempotency manager initialized: "
            f"ttl={default_ttl}s, persistence={enable_persistence}"
        )

    def generate_key(self, **kwargs) -> str:
        """
        Generate idempotency key from operation parameters.

        Args:
            **kwargs: Operation parameters to hash

        Returns:
            Hexadecimal hash string

        Example:
            >>> key = manager.generate_key(
            ...     theme="brutalist",
            ...     content="My portfolio",
            ...     operation="content_generation"
            ... )
            >>> # key = "a1b2c3d4e5f6..."
        """
        # Sort keys for consistent hashing
        sorted_params = json.dumps(kwargs, sort_keys=True)
        hash_obj = hashlib.sha256(sorted_params.encode())
        key = hash_obj.hexdigest()

        logger.debug(f"Generated idempotency key: {key[:16]}... from {list(kwargs.keys())}")
        return key

    def store_result(
        self,
        key: str,
        result: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store operation result with idempotency key.

        Args:
            key: Idempotency key
            result: Operation result to store
            ttl: Time-to-live in seconds (uses default if None)
            metadata: Optional metadata to store with result
        """
        ttl = ttl or self.default_ttl
        now = datetime.now()
        expires_at = now + timedelta(seconds=ttl)

        idempotent_result = IdempotentResult(
            key=key,
            result=result,
            timestamp=now,
            expires_at=expires_at,
            metadata=metadata or {}
        )

        with self._lock:
            self._cache[key] = idempotent_result
            logger.info(
                f"💾 Stored result for key {key[:16]}... "
                f"(expires in {ttl}s)"
            )

        if self.enable_persistence:
            self._save_to_disk()

    def get_result(self, key: str) -> Optional[Any]:
        """
        Retrieve stored result for idempotency key.

        Args:
            key: Idempotency key

        Returns:
            Stored result if exists and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                logger.debug(f"No cached result for key {key[:16]}...")
                return None

            idempotent_result = self._cache[key]

            # Check expiration
            if idempotent_result.is_expired():
                logger.info(f"♻️  Expired result for key {key[:16]}..., removing")
                del self._cache[key]
                if self.enable_persistence:
                    self._save_to_disk()
                return None

            logger.info(f"✅ Cache hit for key {key[:16]}...")
            return idempotent_result.result

    def has_key(self, key: str) -> bool:
        """
        Check if key exists (without retrieving result).

        Args:
            key: Idempotency key

        Returns:
            True if key exists and not expired
        """
        return self.get_result(key) is not None

    def invalidate(self, key: str) -> bool:
        """
        Invalidate a specific idempotency key.

        Args:
            key: Idempotency key to invalidate

        Returns:
            True if key was found and removed
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.info(f"🗑️  Invalidated key {key[:16]}...")
                if self.enable_persistence:
                    self._save_to_disk()
                return True
            return False

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            initial_count = len(self._cache)
            self._cache = {
                k: v for k, v in self._cache.items()
                if not v.is_expired()
            }
            removed = initial_count - len(self._cache)

            if removed > 0:
                logger.info(f"♻️  Cleaned up {removed} expired entries")
                if self.enable_persistence:
                    self._save_to_disk()

            return removed

    def clear_all(self) -> None:
        """Clear all stored results."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"🗑️  Cleared all {count} cached results")

            if self.enable_persistence:
                self._save_to_disk()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total = len(self._cache)
            expired = sum(1 for v in self._cache.values() if v.is_expired())

            return {
                "total_entries": total,
                "active_entries": total - expired,
                "expired_entries": expired,
                "storage_path": str(self.storage_path) if self.enable_persistence else None,
                "persistence_enabled": self.enable_persistence,
            }

    def _save_to_disk(self) -> None:
        """Save cache to disk."""
        if not self.enable_persistence:
            return

        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert cache to JSON-serializable format
            data = {
                k: v.to_dict() for k, v in self._cache.items()
            }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(data)} entries to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save idempotency cache: {e}")

    def _load_from_disk(self) -> None:
        """Load cache from disk."""
        if not self.enable_persistence or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            self._cache = {
                k: IdempotentResult.from_dict(v)
                for k, v in data.items()
            }

            # Clean up expired entries
            expired = self.cleanup_expired()
            active = len(self._cache)

            logger.info(
                f"Loaded {active + expired} entries from disk "
                f"({active} active, {expired} expired)"
            )
        except Exception as e:
            logger.error(f"Failed to load idempotency cache: {e}")
            self._cache = {}


def idempotent(
    manager: IdempotencyKeyManager,
    key_params: Optional[list[str]] = None,
    ttl: Optional[int] = None
):
    """
    Decorator to make a function idempotent.

    Args:
        manager: IdempotencyKeyManager instance
        key_params: List of parameter names to use for key generation
        ttl: Time-to-live for cached result

    Usage:
        >>> manager = IdempotencyKeyManager()
        >>>
        >>> @idempotent(manager, key_params=['theme', 'content'])
        >>> def generate_content(theme: str, content: str):
        ...     return expensive_llm_call(theme, content)
        >>>
        >>> # First call executes function
        >>> result1 = generate_content("brutalist", "My portfolio")
        >>>
        >>> # Second call returns cached result
        >>> result2 = generate_content("brutalist", "My portfolio")
        >>> assert result1 == result2
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build key parameters
            if key_params:
                # Extract specified parameters
                import inspect
                sig = inspect.signature(func)
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()

                key_data = {
                    param: bound.arguments[param]
                    for param in key_params
                    if param in bound.arguments
                }
            else:
                # Use all parameters
                key_data = {
                    f"arg_{i}": arg for i, arg in enumerate(args)
                }
                key_data.update(kwargs)

            # Add function name to key
            key_data["__func__"] = func.__name__

            # Generate key
            key = manager.generate_key(**key_data)

            # Check cache
            if result := manager.get_result(key):
                logger.info(f"🎯 Idempotent cache hit for {func.__name__}")
                return result

            # Execute function
            logger.info(f"🔨 Executing {func.__name__} (cache miss)")
            result = func(*args, **kwargs)

            # Store result
            manager.store_result(key, result, ttl=ttl, metadata={
                "function": func.__name__,
                "params": key_data
            })

            return result

        return wrapper
    return decorator


# Global idempotency manager
_global_manager: Optional[IdempotencyKeyManager] = None


def get_global_manager() -> IdempotencyKeyManager:
    """Get or create global idempotency manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = IdempotencyKeyManager()
    return _global_manager
