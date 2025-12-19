# Middleware - Enterprise Rate Limiting & Security

## 🎯 Overview

Production-grade middleware components for:
- **Rate Limiting** (per-user, per-IP, per-API)
- Request throttling and burst protection
- Security headers (coming in Tier 2)
- CORS configuration (coming in Tier 2)

Follows **Azure API Management**, **GitHub Enterprise API**, and **Stack Overflow** patterns.

## ✅ Features

### 1. **Token Bucket Rate Limiting** (`rate_limiter.py`)
- Sliding window algorithm (accurate, not leaky)
- Redis-backed (multi-replica support)
- Graceful fallback to in-memory
- Per-user and per-IP limits
- Burst protection
- Standard HTTP 429 responses with `Retry-After` headers

### 2. **Automatic Identifier Detection**
- Authenticated users: `user:{user_id}` (from JWT/session)
- Anonymous users: `ip:{ip_address}` (X-Forwarded-For aware)
- Custom identifiers supported

### 3. **Standard Rate Limit Headers**
- `X-RateLimit-Limit`: Max requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets
- `Retry-After`: Seconds until limit resets (HTTP 429 only)

## 🚀 Quick Start

### Decorator Usage (Recommended)

```python
from middleware import rate_limit

@bp.route("/api/create", methods=["POST"])
@rate_limit(max_requests=100, window_seconds=60)  # 100 req/min
async def create_resource():
    # Your code here
    return jsonify({"success": True})
```

### Class Usage (Advanced)

```python
from middleware import RateLimiter

limiter = RateLimiter(max_requests=1000, window_seconds=3600)  # 1000 req/hour

async def my_handler(request):
    # Extract identifier
    user_id = request.user_id or request.remote_addr
    
    # Check rate limit
    allowed, retry_after = await limiter.is_allowed(user_id, request.path)
    
    if not allowed:
        return {"error": "Rate limit exceeded"}, 429
    
    # Process request
    return {"success": True}
```

## 📊 Rate Limit Tiers

Based on **GitHub Enterprise API** and **Azure API Management** patterns:

| Tier | Limit | Window | Use Case | Example |
|------|-------|--------|----------|---------|
| **Anonymous** | 60 | 60s | Public API, unauthenticated | IP-based |
| **Authenticated** | 5,000 | 3600s | Standard users | User ID-based |
| **Premium** | 15,000 | 3600s | Paid plans | User ID-based |
| **Admin** | 100,000 | 3600s | Internal services | API key-based |

### Our Current Limits

```python
# Browser agent creation (expensive)
@rate_limit(max_requests=10, window_seconds=60)  # 10 agents/min

# Agent deletion
@rate_limit(max_requests=20, window_seconds=60)  # 20 deletes/min

# Task creation (moderate)
@rate_limit(max_requests=100, window_seconds=60)  # 100 tasks/min

# Read operations (generous)
@rate_limit(max_requests=1000, window_seconds=60)  # 1000 reads/min
```

## 🔐 Security Best Practices

### 1. Redis Key Isolation

```python
# Keys are automatically prefixed
"rate:user:123:/api/create:1234567890"
"rate:ip:192.168.1.1:/api/list:1234567890"

# Window start timestamp prevents key collisions
```

### 2. Distributed Protection

- **With Redis**: Shared counters across all replicas
- **Without Redis**: Each replica has separate counters (not ideal, but works)

### 3. Proxy-Aware IP Detection

```python
# Automatically handles:
# 1. X-Forwarded-For (AWS ALB, Azure Application Gateway)
# 2. X-Real-IP (nginx)
# 3. request.remote_addr (direct connection)

ip = (
    request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    or request.headers.get("X-Real-IP", "")
    or request.remote_addr
)
```

### 4. Attack Mitigation

**DDoS Protection:**
```python
# Low limits for expensive operations
@rate_limit(max_requests=5, window_seconds=60)  # Only 5 per minute
async def expensive_operation():
    ...
```

**Brute Force Protection:**
```python
# Login endpoint
@rate_limit(max_requests=5, window_seconds=300)  # 5 attempts per 5 minutes
async def login():
    ...
```

**Scraping Protection:**
```python
# Data export
@rate_limit(max_requests=10, window_seconds=3600)  # 10 per hour
async def export_data():
    ...
```

## 📈 Monitoring & Observability

### Health Check Integration

Rate limiter status is included in `/api/agents/health/ready`:

```bash
curl http://localhost:50505/api/agents/health/ready
```

Response:
```json
{
  "status": "ready",
  "components": {
    "database": {"status": "healthy"},
    "redis": {
      "status": "healthy",
      "mode": "redis",
      "rate_limiting": "enabled"
    },
    "memory_state": {"status": "healthy"}
  }
}
```

### Rate Limit Logs

```python
# Logs on every request (DEBUG level)
logger.debug("Rate limit OK: rate:user:123:/api/create:123 = 45/100")

# Logs on rate limit exceeded (WARNING level)
logger.warning("Rate limit EXCEEDED: rate:ip:1.2.3.4:/api/create:123 = 101/100, retry after 42s")
```

### Azure Monitor Query (Coming in Tier 1 Step 4)

```kusto
// Rate limit violations
traces
| where message contains "Rate limit EXCEEDED"
| summarize count() by tostring(customDimensions.endpoint), bin(timestamp, 5m)
| order by timestamp desc

// Top rate-limited users
traces
| where message contains "Rate limit EXCEEDED"
| extend identifier = extract("rate:([^:]+:[^:]+)", 1, message)
| summarize violations=count() by identifier
| order by violations desc
| take 10
```

## 🧪 Testing

### Unit Tests

```python
from middleware import RateLimiter

async def test_rate_limiter():
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    
    # First 5 requests should succeed
    for i in range(5):
        allowed, _ = await limiter.is_allowed("test_user", "/api/test")
        assert allowed, f"Request {i+1} should be allowed"
    
    # 6th request should be blocked
    allowed, retry_after = await limiter.is_allowed("test_user", "/api/test")
    assert not allowed, "Request 6 should be blocked"
    assert retry_after is not None, "Should have retry_after value"
```

### Integration Tests

```bash
# Test rate limiting (manual)
for i in {1..15}; do
  curl -X POST http://localhost:50505/api/agents/browser \
    -H "Content-Type: application/json" \
    -d '{"agent_id": "test_'$i'"}' \
    -w "\nStatus: %{http_code}\n"
done

# First 10 requests: 201 Created
# Next 5 requests: 429 Too Many Requests
```

### Load Testing

```python
# locustfile.py
from locust import HttpUser, task, between

class RateLimitTest(HttpUser):
    wait_time = between(0.1, 0.5)
    
    @task
    def create_agent(self):
        with self.client.post(
            "/api/agents/browser",
            json={"agent_id": f"agent_{self.user_id}"},
            catch_response=True
        ) as response:
            if response.status_code == 429:
                response.success()  # Expected!
            elif response.status_code != 201:
                response.failure(f"Got {response.status_code}")
```

Run with:
```bash
locust -f locustfile.py --host=http://localhost:50505
```

## 🔧 Configuration

### Environment Variables

```bash
# Redis configuration (enables Redis-backed rate limiting)
export REDIS_URL="redis://localhost:6379/0"

# Or Azure Cache for Redis
export REDIS_URL="rediss://:password@myredis.redis.cache.windows.net:6380/0"
```

### Custom Limits Per Environment

```python
import os

# Production: strict limits
if os.getenv("ENV") == "production":
    AGENT_CREATE_LIMIT = 10
    TASK_CREATE_LIMIT = 100
# Development: relaxed limits
else:
    AGENT_CREATE_LIMIT = 100
    TASK_CREATE_LIMIT = 1000

@bp.route("/api/create")
@rate_limit(max_requests=AGENT_CREATE_LIMIT, window_seconds=60)
async def create():
    ...
```

### Custom Identifier Function

```python
async def get_api_key_identifier(request):
    """Extract API key from header."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key}"
    return f"ip:{request.remote_addr}"

@bp.route("/api/premium")
@rate_limit(
    max_requests=15000,
    window_seconds=3600,
    identifier_func=get_api_key_identifier
)
async def premium_endpoint():
    ...
```

## 🐛 Troubleshooting

### Rate Limit Not Working

**Problem:** Requests not being rate limited

**Solutions:**
1. Check Redis connection: `redis-cli ping`
2. Verify decorator order (rate_limit should be AFTER @bp.route)
3. Check logs for "Rate limiting disabled" warnings
4. Ensure Redis URL is set in environment

### False Positives (Legitimate Users Blocked)

**Problem:** Users hitting limits unexpectedly

**Solutions:**
1. Check if using Redis (in-memory mode counts per replica)
2. Increase limits for authenticated users
3. Implement tiered limits (see Custom Identifier section)
4. Add IP whitelist for internal services

### Memory Leak in Fallback Mode

**Problem:** Memory grows in in-memory mode

**Solution:** Redis fallback does not auto-expire keys. Use Redis in production.

## 🎓 Next Steps (Tier 1)

After completing Tier 1 Step 3 (Rate Limiting), continue with:

**Step 4: Application Insights** - Azure monitoring, telemetry, alerts

See main Enterprise upgrade plan in project root.

## 📚 References

- [GitHub API Rate Limiting](https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting)
- [Azure API Management Rate Limits](https://learn.microsoft.com/azure/api-management/api-management-access-restriction-policies)
- [Stack Overflow API Throttling](https://api.stackexchange.com/docs/throttle)
- [Redis INCR for Rate Limiting](https://redis.io/commands/incr/)

---

**Questions?** Check main project documentation or create an issue.
