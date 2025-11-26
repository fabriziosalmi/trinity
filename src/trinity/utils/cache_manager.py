"""
Trinity Core - Multi-Tier Cache Manager

Implements 3-tier caching for LLM responses:
1. Memory (LRU, 100 entries, instant)
2. Redis (optional, ~1ms, persistent)
3. Filesystem (fallback, ~10ms, persistent)

Target: 40% cost reduction, 80% cache hit rate.

Usage:
    cache = CacheManager(enable_redis=True)

    # Check cache
    cached = await cache.get_async("prompt_hash")
    if cached:
        return cached

    # Generate and cache
    result = await llm.generate(prompt)
    await cache.set_async("prompt_hash", result, ttl=3600)
"""
import asyncio
import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# Optional Redis support
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.info("redis not available, using memory + filesystem cache only")


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: str
    created_at: float
    ttl: int
    hits: int = 0
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl <= 0:
            return False  # No expiration
        return time.time() - self.created_at > self.ttl

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'CacheEntry':
        """Create from dictionary."""
        return cls(**data)


class MemoryCache:
    """
    In-memory LRU cache (tier 1).

    Fastest cache tier (~0.01ms), but volatile.
    Use for frequently accessed prompts.
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize memory cache.

        Args:
            max_size: Maximum number of entries (LRU eviction)
        """
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU

        logger.info(f"MemoryCache initialized: max_size={max_size}")

    def get(self, key: str) -> Optional[str]:
        """Get value from memory cache."""
        entry = self._cache.get(key)

        if entry is None:
            return None

        if entry.is_expired():
            # Remove expired entry
            self._cache.pop(key, None)
            if key in self._access_order:
                self._access_order.remove(key)
            return None

        # Update LRU order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        # Update hit count
        entry.hits += 1

        logger.debug(f"MemoryCache HIT: {key[:16]}... (hits={entry.hits})")
        return entry.value

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        """Set value in memory cache."""
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            if self._access_order:
                oldest_key = self._access_order.pop(0)
                self._cache.pop(oldest_key, None)
                logger.debug(f"MemoryCache EVICT: {oldest_key[:16]}...")

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl,
            size_bytes=len(value.encode('utf-8'))
        )

        self._cache[key] = entry

        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        logger.debug(f"MemoryCache SET: {key[:16]}... (size={entry.size_bytes}B, ttl={ttl}s)")

    def clear(self) -> int:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._access_order.clear()
        logger.info(f"MemoryCache CLEAR: {count} entries removed")
        return count

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_hits = sum(e.hits for e in self._cache.values())
        total_size = sum(e.size_bytes for e in self._cache.values())

        return {
            "tier": "memory",
            "entries": len(self._cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
            "total_size_bytes": total_size,
            "utilization": len(self._cache) / self.max_size if self.max_size > 0 else 0
        }


class FilesystemCache:
    """
    Filesystem cache (tier 3).

    Slowest tier (~10ms), but persistent across restarts.
    Use as fallback when Redis unavailable.
    """

    def __init__(self, cache_dir: str = ".cache/llm", max_size_mb: int = 100):
        """
        Initialize filesystem cache.

        Args:
            cache_dir: Directory for cache files
            max_size_mb: Maximum cache size in MB
        """
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"FilesystemCache initialized: {self.cache_dir} (max={max_size_mb}MB)")

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for key."""
        # Use first 2 chars for subdirectory (prevents too many files in one dir)
        subdir = self.cache_dir / key[:2]
        subdir.mkdir(exist_ok=True)
        return subdir / f"{key}.json"

    def get(self, key: str) -> Optional[str]:
        """Get value from filesystem cache."""
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            data = json.loads(cache_path.read_text(encoding='utf-8'))
            entry = CacheEntry.from_dict(data)

            if entry.is_expired():
                # Remove expired file
                cache_path.unlink()
                logger.debug(f"FilesystemCache EXPIRED: {key[:16]}...")
                return None

            logger.debug(f"FilesystemCache HIT: {key[:16]}...")
            return entry.value

        except Exception as e:
            logger.warning(f"FilesystemCache read error: {e}")
            return None

    async def get_async(self, key: str) -> Optional[str]:
        """Async get (runs in thread pool)."""
        return await asyncio.to_thread(self.get, key)

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        """Set value in filesystem cache."""
        cache_path = self._get_cache_path(key)

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl,
            size_bytes=len(value.encode('utf-8'))
        )

        try:
            cache_path.write_text(
                json.dumps(entry.to_dict(), indent=2),
                encoding='utf-8'
            )
            logger.debug(f"FilesystemCache SET: {key[:16]}... (size={entry.size_bytes}B)")

            # Check total cache size and cleanup if needed
            self._cleanup_if_needed()

        except Exception as e:
            logger.error(f"FilesystemCache write error: {e}")

    async def set_async(self, key: str, value: str, ttl: int = 3600) -> None:
        """Async set (runs in thread pool)."""
        await asyncio.to_thread(self.set, key, value, ttl)

    def _cleanup_if_needed(self) -> None:
        """Clean up old cache files if size limit exceeded."""
        total_size = sum(f.stat().st_size for f in self.cache_dir.rglob("*.json"))

        if total_size <= self.max_size_bytes:
            return

        # Sort files by modification time (oldest first)
        files = sorted(
            self.cache_dir.rglob("*.json"),
            key=lambda f: f.stat().st_mtime
        )

        # Remove oldest files until under limit
        removed = 0
        for f in files:
            if total_size <= self.max_size_bytes:
                break

            size = f.stat().st_size
            f.unlink()
            total_size -= size
            removed += 1

        if removed > 0:
            logger.info(f"FilesystemCache CLEANUP: {removed} files removed")

    def clear(self) -> int:
        """Clear all cache files."""
        files = list(self.cache_dir.rglob("*.json"))
        count = len(files)

        for f in files:
            f.unlink()

        logger.info(f"FilesystemCache CLEAR: {count} files removed")
        return count

    def get_stats(self) -> dict:
        """Get cache statistics."""
        files = list(self.cache_dir.rglob("*.json"))
        total_size = sum(f.stat().st_size for f in files)

        return {
            "tier": "filesystem",
            "entries": len(files),
            "total_size_bytes": total_size,
            "max_size_bytes": self.max_size_bytes,
            "utilization": total_size / self.max_size_bytes if self.max_size_bytes > 0 else 0,
            "cache_dir": str(self.cache_dir)
        }


class RedisCache:
    """
    Redis cache (tier 2).

    Fast persistent cache (~1ms), shared across processes.
    Requires Redis server running.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "trinity:llm:"
    ):
        """
        Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all cache keys
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis package required. Install with: pip install redis")

        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.client: Optional[aioredis.Redis] = None

        logger.info(f"RedisCache initialized: {redis_url}")

    async def connect(self) -> None:
        """Connect to Redis server."""
        if self.client is not None:
            return

        try:
            self.client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )
            await self.client.ping()
            logger.info("RedisCache connected")

        except Exception as e:
            logger.error(f"RedisCache connection failed: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("RedisCache disconnected")

    def _make_key(self, key: str) -> str:
        """Make Redis key with prefix."""
        return f"{self.key_prefix}{key}"

    async def get_async(self, key: str) -> Optional[str]:
        """Get value from Redis cache."""
        if self.client is None:
            await self.connect()

        try:
            redis_key = self._make_key(key)
            data = await self.client.get(redis_key)

            if data is None:
                return None

            # Parse cache entry
            entry_dict = json.loads(data)
            entry = CacheEntry.from_dict(entry_dict)

            if entry.is_expired():
                await self.client.delete(redis_key)
                logger.debug(f"RedisCache EXPIRED: {key[:16]}...")
                return None

            logger.debug(f"RedisCache HIT: {key[:16]}...")
            return entry.value

        except Exception as e:
            logger.warning(f"RedisCache get error: {e}")
            return None

    async def set_async(self, key: str, value: str, ttl: int = 3600) -> None:
        """Set value in Redis cache."""
        if self.client is None:
            await self.connect()

        try:
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl,
                size_bytes=len(value.encode('utf-8'))
            )

            redis_key = self._make_key(key)
            data = json.dumps(entry.to_dict())

            # Set with TTL
            if ttl > 0:
                await self.client.setex(redis_key, ttl, data)
            else:
                await self.client.set(redis_key, data)

            logger.debug(f"RedisCache SET: {key[:16]}... (size={entry.size_bytes}B, ttl={ttl}s)")

        except Exception as e:
            logger.error(f"RedisCache set error: {e}")

    async def clear_async(self) -> int:
        """Clear all cache entries with prefix."""
        if self.client is None:
            await self.connect()

        try:
            pattern = f"{self.key_prefix}*"
            keys = []

            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                count = await self.client.delete(*keys)
                logger.info(f"RedisCache CLEAR: {count} keys removed")
                return count

            return 0

        except Exception as e:
            logger.error(f"RedisCache clear error: {e}")
            return 0

    async def get_stats_async(self) -> dict:
        """Get cache statistics."""
        if self.client is None:
            await self.connect()

        try:
            pattern = f"{self.key_prefix}*"
            keys = []

            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)

            # Get memory info
            info = await self.client.info("memory")

            return {
                "tier": "redis",
                "entries": len(keys),
                "redis_memory_used": info.get("used_memory", 0),
                "redis_url": self.redis_url.split("@")[-1]  # Hide credentials
            }

        except Exception as e:
            logger.error(f"RedisCache stats error: {e}")
            return {"tier": "redis", "error": str(e)}


class CacheManager:
    """
    Multi-tier cache manager.

    Implements cache hierarchy:
    1. Memory (fastest, volatile)
    2. Redis (fast, persistent, optional)
    3. Filesystem (slow, persistent, fallback)

    Cache flow:
    - GET: memory → redis → filesystem → miss
    - SET: all tiers simultaneously
    """

    def __init__(
        self,
        enable_redis: bool = True,
        redis_url: str = "redis://localhost:6379/0",
        cache_dir: str = ".cache/llm",
        memory_size: int = 100,
        filesystem_size_mb: int = 100
    ):
        """
        Initialize cache manager.

        Args:
            enable_redis: Enable Redis tier (requires server)
            redis_url: Redis connection URL
            cache_dir: Filesystem cache directory
            memory_size: Memory cache max entries
            filesystem_size_mb: Filesystem cache max size in MB
        """
        self.memory = MemoryCache(max_size=memory_size)
        self.filesystem = FilesystemCache(cache_dir=cache_dir, max_size_mb=filesystem_size_mb)

        self.redis: Optional[RedisCache] = None
        if enable_redis and REDIS_AVAILABLE:
            try:
                self.redis = RedisCache(redis_url=redis_url)
            except Exception as e:
                logger.warning(f"Redis initialization failed, using memory + filesystem only: {e}")

        logger.info(
            f"CacheManager initialized: "
            f"memory={memory_size} entries, "
            f"redis={'enabled' if self.redis else 'disabled'}, "
            f"filesystem={filesystem_size_mb}MB"
        )

    @staticmethod
    def hash_prompt(prompt: str, system_prompt: str = "", model: str = "") -> str:
        """
        Generate cache key from prompt.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: Model identifier

        Returns:
            SHA256 hash as cache key
        """
        content = f"{model}:{system_prompt}:{prompt}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def get_async(self, key: str) -> Optional[str]:
        """
        Get value from cache (tries all tiers).

        Args:
            key: Cache key (hash)

        Returns:
            Cached value or None if miss
        """
        # Try memory (fastest)
        value = self.memory.get(key)
        if value is not None:
            return value

        # Try Redis
        if self.redis:
            try:
                value = await self.redis.get_async(key)
                if value is not None:
                    # Populate memory cache
                    self.memory.set(key, value)
                    return value
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        # Try filesystem (slowest)
        value = await self.filesystem.get_async(key)
        if value is not None:
            # Populate upper tiers
            self.memory.set(key, value)
            if self.redis:
                try:
                    await self.redis.set_async(key, value)
                except Exception:
                    pass
            return value

        return None

    async def set_async(self, key: str, value: str, ttl: int = 3600) -> None:
        """
        Set value in all cache tiers.

        Args:
            key: Cache key (hash)
            value: Value to cache
            ttl: Time to live in seconds (0 = no expiration)
        """
        # Set in all tiers simultaneously
        self.memory.set(key, value, ttl)

        tasks = [self.filesystem.set_async(key, value, ttl)]

        if self.redis:
            tasks.append(self.redis.set_async(key, value, ttl))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def clear_async(self) -> dict:
        """Clear all cache tiers."""
        memory_count = self.memory.clear()
        filesystem_count = self.filesystem.clear()

        redis_count = 0
        if self.redis:
            try:
                redis_count = await self.redis.clear_async()
            except Exception as e:
                logger.error(f"Redis clear failed: {e}")

        result = {
            "memory": memory_count,
            "filesystem": filesystem_count,
            "redis": redis_count
        }

        logger.info(f"CacheManager CLEAR: {result}")
        return result

    async def get_stats_async(self) -> dict:
        """Get statistics from all cache tiers."""
        stats = {
            "memory": self.memory.get_stats(),
            "filesystem": self.filesystem.get_stats()
        }

        if self.redis:
            try:
                stats["redis"] = await self.redis.get_stats_async()
            except Exception as e:
                stats["redis"] = {"error": str(e)}

        return stats

    async def __aenter__(self):
        """Async context manager entry."""
        if self.redis:
            await self.redis.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.redis:
            await self.redis.disconnect()


# Demo
if __name__ == "__main__":
    async def demo():
        print("=== CacheManager Demo ===\n")

        # Initialize cache (memory + filesystem, no Redis)
        async with CacheManager(enable_redis=False) as cache:
            # Generate cache key
            prompt = "Generate a brutalist portfolio"
            key = CacheManager.hash_prompt(prompt, model="llama3.2:3b")

            print(f"Cache key: {key[:16]}...\n")

            # First access (miss)
            print("1. First access (cache miss):")
            value = await cache.get_async(key)
            print(f"   Result: {value}\n")

            # Set cache
            print("2. Setting cache:")
            response = '{"brand_name": "John Doe", "repos": []}'
            await cache.set_async(key, response, ttl=60)
            print(f"   Cached: {len(response)} bytes\n")

            # Second access (hit)
            print("3. Second access (cache hit):")
            value = await cache.get_async(key)
            print(f"   Result: {value[:50]}...\n")

            # Stats
            print("4. Cache statistics:")
            stats = await cache.get_stats_async()
            for tier, tier_stats in stats.items():
                print(f"   {tier}: {tier_stats}")

    asyncio.run(demo())
