"""
Redis cache manager with graceful fallback.

Provides:
- Distributed caching
- Session storage
- Rate limiting support
- Automatic fallback to in-memory

Follows best practices:
- Microsoft Azure Cache for Redis patterns
- GitHub Enterprise caching strategies
- Stack Overflow async patterns
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional, Union

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis cache manager with graceful degradation.
    
    Features:
    - Async redis client
    - Connection pooling
    - Health checks
    - Automatic fallback to in-memory dict
    - JSON serialization
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis manager.
        
        Args:
            redis_url: Redis connection string (redis://host:port/db)
        """
        self.redis_url = redis_url or self._get_redis_url()
        self.client: Optional[Redis] = None
        self._is_initialized = False
        self._fallback_mode = False
        self._memory_cache: dict[str, tuple[Any, Optional[float]]] = {}  # (value, expiry)
        
    @staticmethod
    def _get_redis_url() -> Optional[str]:
        """
        Get Redis URL from environment variables.
        
        Priority:
        1. REDIS_URL (full connection string)
        2. Individual components (REDIS_HOST, REDIS_PORT, etc.)
        3. Azure Cache for Redis connection string
        """
        # Direct URL
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            return redis_url
        
        # Build from components
        host = os.getenv("REDIS_HOST")
        port = os.getenv("REDIS_PORT", "6379")
        password = os.getenv("REDIS_PASSWORD")
        db = os.getenv("REDIS_DB", "0")
        
        if host:
            if password:
                return f"redis://:{password}@{host}:{port}/{db}"
            return f"redis://{host}:{port}/{db}"
        
        logger.warning("No Redis configuration found. Will run in fallback mode (in-memory).")
        return None
    
    async def initialize(self) -> bool:
        """
        Initialize Redis connection.
        
        Returns:
            True if connected, False if fallback mode
        """
        if self._is_initialized:
            return not self._fallback_mode
        
        if not self.redis_url:
            logger.warning("Redis not configured. Running in fallback mode.")
            self._fallback_mode = True
            self._is_initialized = True
            return False
        
        try:
            # Create connection pool
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            
            # Test connection
            await self.client.ping()
            
            logger.info("Redis initialized successfully.")
            self._is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            logger.warning("Falling back to in-memory cache.")
            self._fallback_mode = True
            self._is_initialized = True
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.aclose()
            logger.info("Redis connection closed.")
    
    async def health_check(self) -> dict:
        """
        Check Redis health.
        
        Returns:
            Health status dict
        """
        if self._fallback_mode:
            return {
                "status": "degraded",
                "mode": "fallback",
                "message": "Running with in-memory cache",
                "cache_size": len(self._memory_cache)
            }
        
        if not self.client:
            return {
                "status": "down",
                "message": "Redis not initialized"
            }
        
        try:
            await self.client.ping()
            info = await self.client.info("stats")
            
            return {
                "status": "healthy",
                "mode": "redis",
                "message": "Redis connection OK",
                "connections": info.get("total_connections_received", 0),
                "commands": info.get("total_commands_processed", 0)
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "mode": "redis",
                "message": str(e)
            }
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if self._fallback_mode:
            return self._memory_get(key)
        
        try:
            value = await self.client.get(key)
            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expiry: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (JSON serializable)
            expiry: TTL in seconds (None = no expiry)
            
        Returns:
            True if successful
        """
        if self._fallback_mode:
            return self._memory_set(key, value, expiry)
        
        try:
            serialized = json.dumps(value)
            if expiry:
                await self.client.setex(key, expiry, serialized)
            else:
                await self.client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if self._fallback_mode:
            return self._memory_delete(key)
        
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if self._fallback_mode:
            return self._memory_exists(key)
        
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment counter (atomic).
        
        Useful for rate limiting.
        """
        if self._fallback_mode:
            return self._memory_increment(key, amount)
        
        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR error: {e}")
            return 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiry on key."""
        if self._fallback_mode:
            return self._memory_expire(key, seconds)
        
        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False
    
    # In-memory fallback methods
    
    def _memory_get(self, key: str) -> Optional[Any]:
        """Get from in-memory cache."""
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if expiry is None or asyncio.get_event_loop().time() < expiry:
                return value
            else:
                # Expired
                del self._memory_cache[key]
        return None
    
    def _memory_set(self, key: str, value: Any, expiry: Optional[int] = None) -> bool:
        """Set in in-memory cache."""
        expiry_time = None
        if expiry:
            expiry_time = asyncio.get_event_loop().time() + expiry
        self._memory_cache[key] = (value, expiry_time)
        return True
    
    def _memory_delete(self, key: str) -> bool:
        """Delete from in-memory cache."""
        if key in self._memory_cache:
            del self._memory_cache[key]
            return True
        return False
    
    def _memory_exists(self, key: str) -> bool:
        """Check existence in in-memory cache."""
        if key in self._memory_cache:
            _, expiry = self._memory_cache[key]
            if expiry is None or asyncio.get_event_loop().time() < expiry:
                return True
            else:
                del self._memory_cache[key]
        return False
    
    def _memory_increment(self, key: str, amount: int = 1) -> int:
        """Increment in in-memory cache."""
        current = self._memory_get(key) or 0
        new_value = current + amount
        self._memory_set(key, new_value)
        return new_value
    
    def _memory_expire(self, key: str, seconds: int) -> bool:
        """Set expiry in in-memory cache."""
        if key in self._memory_cache:
            value, _ = self._memory_cache[key]
            expiry_time = asyncio.get_event_loop().time() + seconds
            self._memory_cache[key] = (value, expiry_time)
            return True
        return False


# Global instance (singleton)
_redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> RedisManager:
    """Get global Redis manager instance."""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager


@asynccontextmanager
async def get_redis_client() -> AsyncGenerator[RedisManager, None]:
    """
    Get Redis client for use in endpoints.
    
    Usage:
        async with get_redis_client() as cache:
            await cache.set("key", "value", expiry=60)
            value = await cache.get("key")
    """
    manager = get_redis_manager()
    if not manager._is_initialized:
        await manager.initialize()
    yield manager
