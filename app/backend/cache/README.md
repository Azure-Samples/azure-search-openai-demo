# Redis Cache Layer - Enterprise Session Management

## 🎯 Overview

Distributed caching and session management using **Redis** with **automatic fallback** to in-memory. Follows **Microsoft Azure Cache for Redis** and **GitHub Enterprise** best practices.

## ✅ Features

### 1. **Redis Manager** (`cache/cache.py`)
- Async Redis client with `redis-py`
- Connection pooling
- Health checks
- **Graceful fallback** to in-memory dict
- JSON serialization
- Atomic operations (INCR for rate limiting)

### 2. **Session Manager** (`cache/session.py`)
- Distributed session storage
- Automatic expiry (default 1 hour)
- Session updates extend TTL
- Perfect for multi-replica deployments

## 🚀 Quick Start

### Option 1: Azure Cache for Redis

```bash
# Get connection string from Azure Portal
export REDIS_URL="rediss://:password@myredis.redis.cache.windows.net:6380/0"

# Or individual components
export REDIS_HOST="myredis.redis.cache.windows.net"
export REDIS_PORT=6380
export REDIS_PASSWORD="mypassword"

python -m quart run --port 50505
```

### Option 2: Local Redis (Docker)

```bash
# Start Redis container
docker run --name redis-cache \
  -p 6379:6379 \
  -d redis:7-alpine

# Set connection
export REDIS_URL="redis://localhost:6379/0"

python -m quart run --port 50505
```

### Option 3: No Redis (Fallback Mode)

```bash
# Don't set REDIS_URL - app uses in-memory cache
python -m quart run --port 50505
```

**App will log:**
```
WARNING: No Redis configuration found. Will run in fallback mode (in-memory).
```

## 📊 Usage Examples

### Basic Caching

```python
from cache import get_redis_client

async with get_redis_client() as cache:
    # Set with expiry (60 seconds)
    await cache.set("user:123", {"name": "John"}, expiry=60)
    
    # Get value
    user = await cache.get("user:123")
    
    # Delete
    await cache.delete("user:123")
    
    # Check existence
    exists = await cache.exists("user:123")
```

### Session Management

```python
from cache import get_session_manager

session_mgr = get_session_manager(session_ttl=3600)  # 1 hour

# Create session
session_id = await session_mgr.create_session(
    user_id="user_123",
    data={"role": "admin"}
)

# Get session (auto-extends TTL)
session = await session_mgr.get_session(session_id)

# Update session
await session_mgr.update_session(session_id, {"last_page": "/dashboard"})

# Delete session
await session_mgr.delete_session(session_id)
```

### Rate Limiting (Coming in Step 3)

```python
from cache import get_redis_client

async with get_redis_client() as cache:
    # Atomic increment
    count = await cache.increment(f"rate:{user_id}:{minute}")
    
    # Set expiry (1 minute window)
    await cache.expire(f"rate:{user_id}:{minute}", 60)
    
    if count > 100:  # Rate limit exceeded
        return "Too many requests", 429
```

## 🏥 Health Check

Redis health is included in `/api/agents/health/ready`:

```bash
curl http://localhost:50505/api/agents/health/ready
```

Response:
```json
{
  "status": "ready",
  "components": {
    "database": {"status": "healthy"},
    "taskade_api": {"status": "healthy"},
    "redis": {
      "status": "healthy",
      "mode": "redis",
      "connections": 42,
      "commands": 1523
    },
    "memory_state": {"status": "healthy"}
  }
}
```

## 🔐 Security Best Practices

### 1. Azure Cache for Redis

- **SSL/TLS**: Always use `rediss://` (SSL) in production
- **Access Keys**: Rotate regularly (Azure Portal)
- **Network**: Use Private Endpoints or VNet integration
- **Firewall**: Restrict IP ranges

### 2. Connection String Security

```bash
# ❌ Bad - hardcoded in code
REDIS_URL = "redis://password@host:6379"

# ✅ Good - environment variable
REDIS_URL = os.getenv("REDIS_URL")

# ✅ Best - Azure Key Vault
# Retrieved at startup from Key Vault
```

### 3. Data Encryption

```python
# Sensitive data should be encrypted before caching
import base64
from cryptography.fernet import Fernet

# Encrypt before set
encrypted = fernet.encrypt(json.dumps(sensitive_data).encode())
await cache.set("secret:123", base64.b64encode(encrypted).decode())

# Decrypt after get
data = await cache.get("secret:123")
decrypted = fernet.decrypt(base64.b64decode(data))
```

## 📊 Azure Cache for Redis Tiers

| Tier | Use Case | Price | Features |
|------|----------|-------|----------|
| **Basic** | Dev/Test | $15/mo | Single node, no SLA |
| **Standard** | Production | $75/mo | Replication, 99.9% SLA |
| **Premium** | Enterprise | $500/mo | Persistence, clustering, VNet |
| **Enterprise** | Mission-critical | $2000/mo | Active geo-replication, modules |

**Recommendation:** Standard for production, Premium for high availability.

## 🎯 Performance Tips

### 1. Connection Pooling (Already Configured)

```python
# In cache.py - already optimized
self.client = redis.from_url(
    url,
    max_connections=20,  # Pool size
    socket_timeout=5,     # Read timeout
)
```

### 2. Key Naming Conventions

```python
# Use prefixes for organization
"session:{session_id}"
"user:{user_id}:profile"
"rate:{user_id}:{endpoint}:{minute}"
"cache:{resource_type}:{resource_id}"
```

### 3. TTL Strategy

```python
# Short TTL for frequently changing data
await cache.set("stock:AAPL", price, expiry=10)  # 10 seconds

# Medium TTL for user sessions
await cache.set("session:123", data, expiry=3600)  # 1 hour

# Long TTL for static data
await cache.set("config:app", settings, expiry=86400)  # 24 hours

# No expiry for permanent data
await cache.set("feature:flags", flags)  # No expiry
```

### 4. Batch Operations (Advanced)

```python
# Use pipeline for multiple operations
async with cache.client.pipeline() as pipe:
    pipe.set("key1", "value1")
    pipe.set("key2", "value2")
    pipe.incr("counter")
    await pipe.execute()
```

## 🐛 Troubleshooting

### Connection Timeout

```
ERROR: Failed to initialize Redis: timeout
```

**Solutions:**
1. Check firewall rules (Azure: Firewall settings)
2. Verify connection string
3. Check network latency
4. Increase timeout in `cache.py`

### SSL Certificate Error

```
ERROR: SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution:** Use `rediss://` (SSL) not `redis://`

### Memory Limit Exceeded

```
ERROR: OOM command not allowed when used memory > 'maxmemory'
```

**Solutions:**
1. Upgrade Redis tier
2. Set eviction policy (Azure Portal)
3. Reduce TTLs
4. Clear old keys

### Fallback Mode (Not an Error)

```
WARNING: No Redis configuration found. Will run in fallback mode.
```

**This is OK** - app works without Redis. Set `REDIS_URL` to enable.

## 📈 Monitoring

### Key Metrics

1. **Hit Rate**: Cache hits / total requests
2. **Memory Usage**: Current / max memory
3. **Connections**: Active connections
4. **Latency**: Command response time

### Azure Monitor Queries

```kusto
// Cache hit rate
AzureMetrics
| where ResourceProvider == "MICROSOFT.CACHE"
| where MetricName == "cachehits" or MetricName == "cachemisses"
| summarize hits=sum(Total), misses=sum(Total) by MetricName
| extend hit_rate = hits / (hits + misses) * 100

// Memory usage
AzureMetrics
| where MetricName == "usedmemory"
| summarize avg(Average), max(Maximum) by bin(TimeGenerated, 5m)
```

## 🔄 Migration from In-Memory to Redis

**Zero downtime:**

1. Deploy with Redis configured
2. Old sessions in memory continue working
3. New sessions use Redis
4. Gradually sessions migrate

**No code changes needed** - automatic fallback handles it!

## 🎓 Next Steps (Tier 1)

After completing Tier 1 Step 2 (Redis), continue with:

**Step 3: Rate Limiting** - Use Redis INCR for per-user limits
**Step 4: Application Insights** - Azure monitoring integration

See main Enterprise upgrade plan in project root.

## 📚 References

- [Azure Cache for Redis](https://learn.microsoft.com/azure/azure-cache-for-redis/)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [redis-py Documentation](https://redis-py.readthedocs.io/)

---

**Questions?** Check main project documentation or create an issue.
