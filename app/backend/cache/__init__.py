"""
Redis Cache module for Agent Management System.

Provides distributed caching and session management with graceful fallback.
Follows Microsoft Azure and GitHub Enterprise best practices.
"""

from .cache import (
    RedisManager,
    get_redis_manager,
    get_redis_client,
)
from .session import (
    SessionManager,
    get_session_manager,
)

__all__ = [
    "RedisManager",
    "get_redis_manager",
    "get_redis_client",
    "SessionManager",
    "get_session_manager",
]
