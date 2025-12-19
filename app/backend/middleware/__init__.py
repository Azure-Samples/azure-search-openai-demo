"""Middleware for rate limiting, authentication, and security.

This module provides enterprise-grade middleware components for:
- Rate limiting (per-user, per-IP, per-API)
- Request throttling
- IP blocking
- Security headers

Following Microsoft Azure and GitHub Enterprise patterns.
"""

from .rate_limiter import RateLimiter, rate_limit

__all__ = ["RateLimiter", "rate_limit"]
