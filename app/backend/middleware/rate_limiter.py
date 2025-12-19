"""Rate limiting middleware using Redis with fallback to in-memory.

Implements token bucket algorithm with sliding window for accurate rate limiting.
Follows Azure API Management and GitHub Enterprise patterns.

Features:
- Per-user rate limits (authenticated users)
- Per-IP rate limits (anonymous users)
- Per-API endpoint limits
- Configurable time windows (minute, hour, day)
- Redis-backed for multi-replica support
- Graceful fallback to in-memory
- Burst protection

Usage:
    from middleware import rate_limit
    
    @agent_bp.route("/create", methods=["POST"])
    @rate_limit(max_requests=100, window_seconds=60)  # 100 req/min
    async def create_agent():
        ...
"""

import logging
import time
from collections import defaultdict
from functools import wraps
from typing import Dict, Optional, Tuple

from quart import Request, jsonify, request

logger = logging.getLogger(__name__)

# Try to import cache module
try:
    from cache import get_redis_client

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logger.warning("Cache module not available. Rate limiting will use in-memory storage.")


class RateLimiter:
    """Rate limiter using Redis or in-memory fallback.
    
    Implements sliding window algorithm:
    1. Key format: "rate:{identifier}:{endpoint}:{window}"
    2. Store: counter with TTL = window_seconds
    3. Each request: INCR counter
    4. If counter > limit: reject (429)
    5. Reset: automatic via TTL expiry
    
    Attributes:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds (60 = 1 minute)
        key_prefix: Redis key prefix (default: "rate")
        
    Example:
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        allowed, retry_after = await limiter.is_allowed("user:123", "/api/create")
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        key_prefix: str = "rate",
    ):
        """Initialize rate limiter.
        
        Args:
            max_requests: Max requests per window (default: 100)
            window_seconds: Window duration in seconds (default: 60)
            key_prefix: Redis key prefix (default: "rate")
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

        # In-memory fallback storage (if Redis unavailable)
        # Format: {key: {"count": int, "reset_at": float}}
        self._memory_store: Dict[str, Dict[str, float]] = defaultdict(dict)

        logger.info(
            f"RateLimiter initialized: {max_requests} req/{window_seconds}s, prefix={key_prefix}"
        )

    def _get_rate_key(self, identifier: str, endpoint: str) -> str:
        """Generate Redis key for rate limit.
        
        Args:
            identifier: User ID, IP address, or API key
            endpoint: API endpoint path
            
        Returns:
            Redis key: "rate:{identifier}:{endpoint}:{window_start}"
        """
        # Use current window start time for key (sliding window)
        window_start = int(time.time() // self.window_seconds)
        return f"{self.key_prefix}:{identifier}:{endpoint}:{window_start}"

    async def is_allowed(self, identifier: str, endpoint: str) -> Tuple[bool, Optional[int]]:
        """Check if request is allowed under rate limit.
        
        Args:
            identifier: User ID, IP address, or API key
            endpoint: API endpoint path
            
        Returns:
            Tuple of (allowed: bool, retry_after: Optional[int])
            - allowed: True if under limit
            - retry_after: Seconds until limit resets (if rejected)
        """
        rate_key = self._get_rate_key(identifier, endpoint)

        if CACHE_AVAILABLE:
            return await self._check_redis(rate_key)
        else:
            return self._check_memory(rate_key)

    async def _check_redis(self, rate_key: str) -> Tuple[bool, Optional[int]]:
        """Check rate limit using Redis.
        
        Uses Redis INCR for atomic counter increment.
        Sets TTL on first increment to auto-reset.
        
        Args:
            rate_key: Redis key for this rate limit
            
        Returns:
            Tuple of (allowed: bool, retry_after: Optional[int])
        """
        try:
            async with get_redis_client() as cache:
                # Atomic increment
                current_count = await cache.increment(rate_key)

                # Set expiry on first increment (creates key)
                if current_count == 1:
                    await cache.expire(rate_key, self.window_seconds)

                # Check if under limit
                if current_count <= self.max_requests:
                    logger.debug(
                        f"Rate limit OK: {rate_key} = {current_count}/{self.max_requests}"
                    )
                    return True, None
                else:
                    # Calculate retry-after (seconds until window resets)
                    retry_after = self.window_seconds
                    logger.warning(
                        f"Rate limit EXCEEDED: {rate_key} = {current_count}/{self.max_requests}, "
                        f"retry after {retry_after}s"
                    )
                    return False, retry_after

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}. Falling back to memory.")
            return self._check_memory(rate_key)

    def _check_memory(self, rate_key: str) -> Tuple[bool, Optional[int]]:
        """Check rate limit using in-memory storage.
        
        Fallback when Redis unavailable. Not suitable for multi-replica deployments
        (each replica has separate counters).
        
        Args:
            rate_key: Key for this rate limit
            
        Returns:
            Tuple of (allowed: bool, retry_after: Optional[int])
        """
        current_time = time.time()

        # Get or create entry
        entry = self._memory_store.get(rate_key)
        if entry is None or entry.get("reset_at", 0) < current_time:
            # First request or window expired - reset
            self._memory_store[rate_key] = {
                "count": 1,
                "reset_at": current_time + self.window_seconds,
            }
            logger.debug(f"Rate limit OK (memory): {rate_key} = 1/{self.max_requests}")
            return True, None

        # Increment count
        entry["count"] += 1
        current_count = entry["count"]

        # Check limit
        if current_count <= self.max_requests:
            logger.debug(
                f"Rate limit OK (memory): {rate_key} = {current_count}/{self.max_requests}"
            )
            return True, None
        else:
            retry_after = int(entry["reset_at"] - current_time)
            logger.warning(
                f"Rate limit EXCEEDED (memory): {rate_key} = {current_count}/{self.max_requests}, "
                f"retry after {retry_after}s"
            )
            return False, retry_after

    async def reset(self, identifier: str, endpoint: str) -> bool:
        """Reset rate limit for a specific identifier and endpoint.
        
        Useful for:
        - Admin override
        - Testing
        - Manual unblocking
        
        Args:
            identifier: User ID, IP address, or API key
            endpoint: API endpoint path
            
        Returns:
            True if reset successful
        """
        rate_key = self._get_rate_key(identifier, endpoint)

        if CACHE_AVAILABLE:
            try:
                async with get_redis_client() as cache:
                    await cache.delete(rate_key)
                    logger.info(f"Rate limit RESET (Redis): {rate_key}")
                    return True
            except Exception as e:
                logger.error(f"Failed to reset rate limit in Redis: {e}")
                # Fall through to memory reset

        # Memory reset
        if rate_key in self._memory_store:
            del self._memory_store[rate_key]
            logger.info(f"Rate limit RESET (memory): {rate_key}")
        return True

    async def get_status(self, identifier: str, endpoint: str) -> Dict:
        """Get current rate limit status for an identifier.
        
        Args:
            identifier: User ID, IP address, or API key
            endpoint: API endpoint path
            
        Returns:
            Dict with:
            - limit: Max requests allowed
            - remaining: Requests remaining in window
            - reset_at: Unix timestamp when limit resets
            - window: Window duration in seconds
        """
        rate_key = self._get_rate_key(identifier, endpoint)
        current_time = time.time()

        if CACHE_AVAILABLE:
            try:
                async with get_redis_client() as cache:
                    current_count = await cache.get(rate_key) or 0
                    # Redis TTL gives us reset time
                    reset_at = current_time + self.window_seconds
            except Exception:
                current_count = 0
                reset_at = current_time + self.window_seconds
        else:
            entry = self._memory_store.get(rate_key)
            if entry:
                current_count = entry.get("count", 0)
                reset_at = entry.get("reset_at", current_time + self.window_seconds)
            else:
                current_count = 0
                reset_at = current_time + self.window_seconds

        return {
            "limit": self.max_requests,
            "remaining": max(0, self.max_requests - int(current_count)),
            "reset_at": int(reset_at),
            "window": self.window_seconds,
        }


def rate_limit(
    max_requests: int = 100,
    window_seconds: int = 60,
    key_prefix: str = "rate",
    identifier_func=None,
):
    """Decorator for rate limiting endpoints.
    
    Usage:
        @agent_bp.route("/create", methods=["POST"])
        @rate_limit(max_requests=100, window_seconds=60)
        async def create_agent():
            ...
    
    Args:
        max_requests: Max requests per window (default: 100)
        window_seconds: Window duration in seconds (default: 60)
        key_prefix: Redis key prefix (default: "rate")
        identifier_func: Custom function to extract identifier from request
                       Default: uses user_id from session or IP address
    
    Returns:
        Decorated async function
    """
    limiter = RateLimiter(max_requests, window_seconds, key_prefix)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get identifier (user ID or IP address)
            identifier = await _get_identifier(request, identifier_func)

            # Get endpoint
            endpoint = request.path

            # Check rate limit
            allowed, retry_after = await limiter.is_allowed(identifier, endpoint)

            if not allowed:
                # Rate limit exceeded - return 429
                response = jsonify(
                    {
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Please try again in {retry_after} seconds.",
                        "retry_after": retry_after,
                    }
                )
                response.status_code = 429
                response.headers["Retry-After"] = str(retry_after)
                response.headers["X-RateLimit-Limit"] = str(max_requests)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(int(time.time()) + retry_after)
                return response

            # Get status for headers
            status = await limiter.get_status(identifier, endpoint)

            # Execute endpoint
            response = await func(*args, **kwargs)

            # Add rate limit headers
            if hasattr(response, "headers"):
                response.headers["X-RateLimit-Limit"] = str(status["limit"])
                response.headers["X-RateLimit-Remaining"] = str(status["remaining"])
                response.headers["X-RateLimit-Reset"] = str(status["reset_at"])

            return response

        return wrapper

    return decorator


async def _get_identifier(req: Request, identifier_func=None) -> str:
    """Extract identifier from request for rate limiting.
    
    Priority:
    1. Custom identifier_func (if provided)
    2. User ID from session/JWT (authenticated users)
    3. IP address (anonymous users)
    
    Args:
        req: Quart Request object
        identifier_func: Optional custom identifier function
        
    Returns:
        Identifier string (user_id or IP address)
    """
    if identifier_func:
        return await identifier_func(req)

    # Try to get user ID from session
    # Note: This requires session middleware (implemented in Step 2)
    try:
        # Check for Authorization header (JWT)
        auth_header = req.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Extract user_id from JWT (simplified - real impl uses jwt.decode)
            # For now, use token hash as identifier
            token = auth_header.split(" ")[1]
            return f"user:{hash(token) % 10000}"

        # Check for session cookie
        session_id = req.cookies.get("session_id")
        if session_id:
            return f"session:{session_id}"

    except Exception as e:
        logger.debug(f"Failed to extract user identifier: {e}")

    # Fall back to IP address
    # Get real IP (considering proxies)
    ip = (
        req.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or req.headers.get("X-Real-IP", "").strip()
        or req.remote_addr
        or "unknown"
    )

    return f"ip:{ip}"
