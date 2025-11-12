"""
Cache service with Redis and in-memory support.

Supports both Redis (for multi-instance deployments) and in-memory caching
(for local development or single-instance deployments).
"""

import json
import logging
import time
from typing import Any, Dict, Optional, Protocol

logger = logging.getLogger(__name__)


class CacheProtocol(Protocol):
    """Protocol for cache implementations."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...
    
    async def set(self, key: str, val: Any, ttl_s: int) -> None:
        """Set value in cache with TTL."""
        ...
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        ...
    
    async def close(self) -> None:
        """Close cache connection."""
        ...


class InMemoryCache:
    """In-memory cache implementation."""
    
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        entry = self._store.get(key)
        if not entry:
            return None
        if entry["exp"] < time.time():
            # expired
            self._store.pop(key, None)
            return None
        return entry["val"]
    
    async def set(self, key: str, val: Any, ttl_s: int) -> None:
        """Set value in cache with TTL."""
        self._store[key] = {"val": val, "exp": time.time() + ttl_s}
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        self._store.clear()
    
    async def close(self) -> None:
        """Close cache (no-op for in-memory)."""
        pass


class RedisCache:
    """Redis cache implementation."""
    
    def __init__(self, redis_url: str):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
        """
        self.redis_url = redis_url
        self._redis: Optional[Any] = None
        self._connected = False
    
    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is established."""
        if self._connected and self._redis:
            return
        
        try:
            import redis.asyncio as redis
            
            # Parse Redis URL
            # redis://[:password@]host[:port][/database]
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We'll handle JSON encoding/decoding
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            
            # Test connection
            await self._redis.ping()
            self._connected = True
            logger.info(f"Redis cache connected: {self.redis_url}")
        except ImportError:
            logger.error("redis library not installed. Install with: pip install redis")
            raise
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Will fall back gracefully on operations.")
            self._connected = False
            self._redis = None
            # Don't raise - allow graceful fallback
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            await self._ensure_connected()
            if not self._redis:
                return None
            
            data = await self._redis.get(key)
            if data is None:
                return None
            
            # Deserialize JSON
            return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get failed for key '{key}': {e}")
            return None
    
    async def set(self, key: str, val: Any, ttl_s: int) -> None:
        """Set value in Redis cache with TTL."""
        try:
            await self._ensure_connected()
            if not self._redis:
                return
            
            # Serialize to JSON
            data = json.dumps(val)
            
            # Set with TTL
            await self._redis.setex(key, ttl_s, data)
        except Exception as e:
            logger.warning(f"Redis set failed for key '{key}': {e}")
            # Don't raise - allow fallback to in-memory or no cache
    
    async def clear(self) -> None:
        """Clear all cache entries (use with caution in production)."""
        try:
            await self._ensure_connected()
            if self._redis:
                await self._redis.flushdb()
        except Exception as e:
            logger.warning(f"Redis clear failed: {e}")
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            try:
                await self._redis.close()
                self._connected = False
                logger.info("Redis cache connection closed")
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")


async def create_cache(redis_url: Optional[str] = None) -> CacheProtocol:
    """
    Create cache instance based on configuration.
    
    Args:
        redis_url: Optional Redis URL. If provided and valid, returns RedisCache.
                   Otherwise returns InMemoryCache.
    
    Returns:
        Cache instance (RedisCache or InMemoryCache)
    """
    if redis_url:
        try:
            cache = RedisCache(redis_url)
            # Test connection (don't raise on failure, just log)
            try:
                await cache._ensure_connected()
            except Exception:
                # Connection failed, but we'll still return RedisCache
                # It will fall back gracefully on each operation
                pass
            
            if cache._connected:
                logger.info("Using Redis cache for multi-instance support")
                return cache
            else:
                logger.warning("Redis connection failed, falling back to in-memory cache")
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}, falling back to in-memory cache")
    
    logger.info("Using in-memory cache (single-instance only)")
    return InMemoryCache()
