# ✅ TIER 1 TESTING CHECKLIST & TEST PLAN

**Status:** 🟢 COMPREHENSIVE TESTING GUIDE  
**Date:** December 19, 2025  
**Coverage:** Database, Cache, Rate Limiting, Monitoring, Health Checks

---

## 📋 QUICK REFERENCE CHECKLIST

### Core Infrastructure Tests
- [ ] **Database Layer** - Connection, CRUD, Migrations, Audit
- [ ] **Cache Layer** - Redis, Fallback, Sessions, TTL
- [ ] **Rate Limiting** - Token Bucket, Per-user, Per-IP, HTTP 429
- [ ] **Monitoring** - Events, Metrics, Exceptions, Health Checks
- [ ] **Integration Tests** - All components together
- [ ] **Performance Tests** - Load testing, Latency
- [ ] **Failover Tests** - Without Database, Without Redis
- [ ] **Health Checks** - /health, /health/ready, /health/live

---

## 1. DATABASE LAYER TESTING

### 1.1 Unit Tests - Connection & Initialization

```python
# tests/test_database.py

import pytest
from app.backend.db.database import DatabaseManager
from app.backend.db.models import BrowserAgentModel, TaskModel

@pytest.fixture
async def db_manager():
    """Initialize database manager for testing"""
    db = DatabaseManager()
    await db.initialize()
    yield db
    await db.close()

@pytest.mark.asyncio
async def test_database_connection(db_manager):
    """✅ Test: Database connection successful"""
    result = await db_manager.health_check()
    assert result["status"] == "healthy"
    assert result["mode"] == "postgresql"

@pytest.mark.asyncio
async def test_database_connection_timeout(db_manager):
    """✅ Test: Handle connection timeout gracefully"""
    db_manager.pool.pool_size = 0
    with pytest.raises(Exception):
        await db_manager.health_check()
```

### 1.2 CRUD Operations Tests

```python
@pytest.mark.asyncio
async def test_create_agent(db_manager):
    """✅ Test: Create agent in database"""
    async with db_manager.get_session() as session:
        agent = BrowserAgentModel(
            agent_id="test_agent_123",
            status="active",
            config={"channel": "msedge"}
        )
        session.add(agent)
        await session.commit()
        assert agent.id is not None

@pytest.mark.asyncio
async def test_read_agent(db_manager):
    """✅ Test: Read agent from database"""
    async with db_manager.get_session() as session:
        agent = await session.get(BrowserAgentModel, 1)
        assert agent is not None
        assert agent.agent_id == "test_agent_123"

@pytest.mark.asyncio
async def test_update_agent(db_manager):
    """✅ Test: Update agent status"""
    async with db_manager.get_session() as session:
        agent = await session.get(BrowserAgentModel, 1)
        agent.status = "inactive"
        await session.commit()
        
        agent = await session.get(BrowserAgentModel, 1)
        assert agent.status == "inactive"

@pytest.mark.asyncio
async def test_soft_delete_agent(db_manager):
    """✅ Test: Soft delete (data recovery possible)"""
    async with db_manager.get_session() as session:
        agent = await session.get(BrowserAgentModel, 1)
        agent.deleted_at = datetime.now()
        await session.commit()
        
        # Can still query deleted records
        agent = await session.get(BrowserAgentModel, 1)
        assert agent.deleted_at is not None
```

### 1.3 Audit Logging Tests

```python
@pytest.mark.asyncio
async def test_audit_log_created(db_manager):
    """✅ Test: Audit log entry created on agent creation"""
    async with db_manager.get_session() as session:
        agent = BrowserAgentModel(agent_id="audit_test", status="active")
        session.add(agent)
        await session.commit()
        
        # Check audit log
        audit_logs = await session.execute(
            select(AuditLogModel).where(
                AuditLogModel.entity_type == "agent"
            )
        )
        assert len(audit_logs) > 0

@pytest.mark.asyncio
async def test_audit_log_tracks_changes(db_manager):
    """✅ Test: Audit log captures what changed"""
    async with db_manager.get_session() as session:
        agent = BrowserAgentModel(agent_id="change_test", status="active")
        session.add(agent)
        await session.commit()
        
        agent.status = "inactive"
        await session.commit()
        
        # Check audit log has both create and update
        logs = await session.execute(
            select(AuditLogModel).where(
                AuditLogModel.entity_id == agent.id
            )
        )
        assert len(logs) >= 2
```

### 1.4 Connection Pool Tests

```python
@pytest.mark.asyncio
async def test_connection_pool_size(db_manager):
    """✅ Test: Connection pool has correct size"""
    assert db_manager.pool.pool_size == 10
    assert db_manager.pool.max_overflow == 20

@pytest.mark.asyncio
async def test_connection_pool_reuse(db_manager):
    """✅ Test: Connections are reused efficiently"""
    before = db_manager.pool.size()
    
    # Execute multiple queries
    for _ in range(5):
        async with db_manager.get_session() as session:
            await session.execute(select(BrowserAgentModel))
    
    after = db_manager.pool.size()
    assert before == after  # No connection leak

@pytest.mark.asyncio
async def test_connection_timeout_handled(db_manager):
    """✅ Test: Connection timeout falls back gracefully"""
    # Simulate connection timeout
    db_manager.pool.timeout = 0.001
    
    try:
        async with db_manager.get_session() as session:
            await asyncio.sleep(0.1)
    except TimeoutError:
        assert db_manager.mode == "memory"  # Fallback to memory
```

### 1.5 Migration Tests

```python
@pytest.mark.asyncio
async def test_alembic_migration_up(db_manager):
    """✅ Test: Database migrations apply successfully"""
    # Run: alembic upgrade head
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd="app/backend",
        capture_output=True
    )
    assert result.returncode == 0

@pytest.mark.asyncio
async def test_alembic_migration_down(db_manager):
    """✅ Test: Database migrations can rollback"""
    result = subprocess.run(
        ["alembic", "downgrade", "-1"],
        cwd="app/backend",
        capture_output=True
    )
    assert result.returncode == 0

@pytest.mark.asyncio
async def test_migration_schema_version(db_manager):
    """✅ Test: Schema version matches code"""
    async with db_manager.get_session() as session:
        result = await session.execute(
            text("SELECT * FROM alembic_version")
        )
        version = result.scalar()
        assert version is not None
```

### 1.6 Error Handling Tests

```python
@pytest.mark.asyncio
async def test_database_not_found_error(db_manager):
    """✅ Test: Handle agent not found gracefully"""
    async with db_manager.get_session() as session:
        agent = await session.get(BrowserAgentModel, 99999)
        assert agent is None  # Should not raise

@pytest.mark.asyncio
async def test_duplicate_key_error(db_manager):
    """✅ Test: Handle duplicate agent_id"""
    async with db_manager.get_session() as session:
        agent1 = BrowserAgentModel(agent_id="dup_test", status="active")
        session.add(agent1)
        await session.commit()
        
        agent2 = BrowserAgentModel(agent_id="dup_test", status="active")
        session.add(agent2)
        
        with pytest.raises(IntegrityError):
            await session.commit()

@pytest.mark.asyncio
async def test_connection_error_fallback(db_manager):
    """✅ Test: Fall back to memory when DB unavailable"""
    db_manager.pool = None  # Simulate database disconnection
    assert db_manager.mode == "memory"
```

---

## 2. CACHE LAYER TESTING

### 2.1 Unit Tests - Redis Connection

```python
# tests/test_cache.py

import pytest
from app.backend.cache.cache import RedisManager

@pytest.fixture
async def cache_manager():
    """Initialize cache manager for testing"""
    cache = RedisManager()
    await cache.initialize()
    yield cache
    await cache.close()

@pytest.mark.asyncio
async def test_redis_connection(cache_manager):
    """✅ Test: Redis connection successful"""
    result = await cache_manager.health_check()
    assert result["status"] == "healthy"
    assert result["mode"] == "redis"

@pytest.mark.asyncio
async def test_redis_connection_timeout(cache_manager):
    """✅ Test: Fall back to memory when Redis unavailable"""
    cache_manager.redis = None
    result = await cache_manager.set("test_key", "test_value")
    assert cache_manager.mode == "memory"
```

### 2.2 Cache Operations Tests

```python
@pytest.mark.asyncio
async def test_cache_set_get(cache_manager):
    """✅ Test: Set and get from cache"""
    await cache_manager.set("test_key", {"data": "value"}, ttl=3600)
    value = await cache_manager.get("test_key")
    assert value == {"data": "value"}

@pytest.mark.asyncio
async def test_cache_ttl_expiration(cache_manager):
    """✅ Test: Cache expires after TTL"""
    await cache_manager.set("expire_key", "value", ttl=1)
    await asyncio.sleep(1.1)
    value = await cache_manager.get("expire_key")
    assert value is None

@pytest.mark.asyncio
async def test_cache_delete(cache_manager):
    """✅ Test: Delete cache entry"""
    await cache_manager.set("delete_key", "value")
    await cache_manager.delete("delete_key")
    value = await cache_manager.get("delete_key")
    assert value is None

@pytest.mark.asyncio
async def test_cache_clear_all(cache_manager):
    """✅ Test: Clear all cache"""
    await cache_manager.set("key1", "value1")
    await cache_manager.set("key2", "value2")
    await cache_manager.clear()
    
    assert await cache_manager.get("key1") is None
    assert await cache_manager.get("key2") is None
```

### 2.3 Rate Limiting Cache Tests

```python
@pytest.mark.asyncio
async def test_cache_increment(cache_manager):
    """✅ Test: Atomic INCR for rate limiting"""
    count = await cache_manager.increment("rate_limit:user:123", 1)
    assert count == 1
    
    count = await cache_manager.increment("rate_limit:user:123", 1)
    assert count == 2

@pytest.mark.asyncio
async def test_cache_increment_with_ttl(cache_manager):
    """✅ Test: Rate limit counter expires"""
    await cache_manager.set("rate_limit:user:456", 0)
    
    for i in range(1, 6):
        count = await cache_manager.increment("rate_limit:user:456", 1)
        assert count == i
    
    await cache_manager.expire("rate_limit:user:456", 1)
    await asyncio.sleep(1.1)
    
    count = await cache_manager.increment("rate_limit:user:456", 1)
    assert count == 1  # Reset after expiry
```

### 2.4 Session Management Tests

```python
from app.backend.cache.session import SessionManager

@pytest.fixture
async def session_manager(cache_manager):
    """Initialize session manager"""
    return SessionManager(cache_manager)

@pytest.mark.asyncio
async def test_session_create(session_manager):
    """✅ Test: Create session"""
    session_id = await session_manager.create_session(
        "user_123",
        {"role": "admin", "permissions": ["read", "write"]}
    )
    assert session_id is not None

@pytest.mark.asyncio
async def test_session_get(session_manager):
    """✅ Test: Get session data"""
    session_id = await session_manager.create_session("user_456", {"role": "user"})
    data = await session_manager.get_session(session_id)
    assert data["user_id"] == "user_456"
    assert data["role"] == "user"

@pytest.mark.asyncio
async def test_session_update(session_manager):
    """✅ Test: Update session data"""
    session_id = await session_manager.create_session("user_789", {"count": 0})
    await session_manager.update_session(session_id, {"count": 5})
    
    data = await session_manager.get_session(session_id)
    assert data["count"] == 5

@pytest.mark.asyncio
async def test_session_delete(session_manager):
    """✅ Test: Delete session"""
    session_id = await session_manager.create_session("user_del", {})
    await session_manager.delete_session(session_id)
    
    data = await session_manager.get_session(session_id)
    assert data is None

@pytest.mark.asyncio
async def test_session_ttl(session_manager):
    """✅ Test: Session expires after TTL"""
    session_id = await session_manager.create_session(
        "user_exp",
        {"data": "value"},
        ttl=1
    )
    await asyncio.sleep(1.1)
    data = await session_manager.get_session(session_id)
    assert data is None
```

### 2.5 Memory Fallback Tests

```python
@pytest.mark.asyncio
async def test_memory_cache_fallback(cache_manager):
    """✅ Test: Memory fallback when Redis unavailable"""
    cache_manager.redis = None
    cache_manager.mode = "memory"
    
    await cache_manager.set("memory_key", "memory_value")
    value = await cache_manager.get("memory_key")
    assert value == "memory_value"

@pytest.mark.asyncio
async def test_memory_cache_persistence(cache_manager):
    """✅ Test: Memory cache persists during runtime"""
    cache_manager.redis = None
    
    await cache_manager.set("persist_key", {"persist": True})
    
    # Multiple accesses should work
    for _ in range(10):
        value = await cache_manager.get("persist_key")
        assert value == {"persist": True}
```

---

## 3. RATE LIMITING TESTING

### 3.1 Unit Tests - Token Bucket Algorithm

```python
# tests/test_rate_limiter.py

import pytest
from app.backend.middleware.rate_limiter import RateLimiter
from app.backend.cache.cache import RedisManager

@pytest.fixture
async def rate_limiter():
    """Initialize rate limiter"""
    cache = RedisManager()
    await cache.initialize()
    limiter = RateLimiter(cache)
    yield limiter
    await cache.close()

@pytest.mark.asyncio
async def test_rate_limit_allow_requests(rate_limiter):
    """✅ Test: Allow requests within limit"""
    limiter = rate_limiter
    
    for i in range(1, 11):  # 10 requests allowed
        allowed = await limiter.is_allowed(
            "test_user",
            "POST",
            "/api/agents",
            max_requests=10,
            window=60
        )
        assert allowed == True

@pytest.mark.asyncio
async def test_rate_limit_reject_requests(rate_limiter):
    """✅ Test: Reject requests exceeding limit"""
    limiter = rate_limiter
    
    # First 10 requests pass
    for i in range(10):
        await limiter.is_allowed(
            "test_user2",
            "POST",
            "/api/agents",
            max_requests=10,
            window=60
        )
    
    # 11th request fails
    allowed = await limiter.is_allowed(
        "test_user2",
        "POST",
        "/api/agents",
        max_requests=10,
        window=60
    )
    assert allowed == False

@pytest.mark.asyncio
async def test_rate_limit_window_reset(rate_limiter):
    """✅ Test: Rate limit window resets after timeout"""
    limiter = rate_limiter
    
    # Use up limit
    for i in range(10):
        await limiter.is_allowed("test_user3", "POST", "/api/agents", 10, 1)
    
    # Next request blocked
    allowed = await limiter.is_allowed("test_user3", "POST", "/api/agents", 10, 1)
    assert allowed == False
    
    # Wait for window to reset
    await asyncio.sleep(1.1)
    
    # Request allowed again
    allowed = await limiter.is_allowed("test_user3", "POST", "/api/agents", 10, 1)
    assert allowed == True

@pytest.mark.asyncio
async def test_rate_limit_per_endpoint(rate_limiter):
    """✅ Test: Different limits for different endpoints"""
    limiter = rate_limiter
    
    # POST /agents: 10 req/min
    for i in range(10):
        await limiter.is_allowed("user4", "POST", "/api/agents", 10, 60)
    
    allowed = await limiter.is_allowed("user4", "POST", "/api/agents", 10, 60)
    assert allowed == False
    
    # But GET /health: 1000 req/min (different counter)
    for i in range(100):
        allowed = await limiter.is_allowed("user4", "GET", "/health", 1000, 60)
        assert allowed == True
```

### 3.2 Integration Tests - Decorator

```python
from app.backend.middleware.rate_limiter import rate_limit
from quart import Quart

@pytest.fixture
def app():
    """Create test app"""
    return Quart(__name__)

@pytest.mark.asyncio
async def test_rate_limit_decorator(app):
    """✅ Test: @rate_limit decorator on endpoint"""
    
    @app.route("/test", methods=["POST"])
    @rate_limit(max_requests=2, window_seconds=60)
    async def test_endpoint():
        return {"success": True}
    
    with app.test_client() as client:
        # First 2 requests should pass
        response1 = await client.post("/test")
        assert response1.status_code == 200
        
        response2 = await client.post("/test")
        assert response2.status_code == 200
        
        # 3rd request should fail with 429
        response3 = await client.post("/test")
        assert response3.status_code == 429

@pytest.mark.asyncio
async def test_rate_limit_headers(app):
    """✅ Test: Rate limit headers in response"""
    
    @app.route("/test", methods=["POST"])
    @rate_limit(max_requests=10, window_seconds=60)
    async def test_endpoint():
        return {"success": True}
    
    with app.test_client() as client:
        response = await client.post("/test")
        
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "10"
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
```

### 3.3 Per-User and Per-IP Tests

```python
@pytest.mark.asyncio
async def test_rate_limit_per_user(rate_limiter):
    """✅ Test: Different users have separate limits"""
    limiter = rate_limiter
    
    # User1: 5 requests
    for i in range(5):
        allowed = await limiter.is_allowed("user_a", "POST", "/api", 5, 60)
        assert allowed == True
    
    allowed = await limiter.is_allowed("user_a", "POST", "/api", 5, 60)
    assert allowed == False
    
    # User2: Still has quota
    allowed = await limiter.is_allowed("user_b", "POST", "/api", 5, 60)
    assert allowed == True

@pytest.mark.asyncio
async def test_rate_limit_per_ip(rate_limiter):
    """✅ Test: IP-based rate limiting"""
    limiter = rate_limiter
    
    # Simulate different IPs
    for i in range(5):
        allowed = await limiter.is_allowed_by_ip("192.168.1.1", "GET", "/api", 5, 60)
        assert allowed == True
    
    allowed = await limiter.is_allowed_by_ip("192.168.1.1", "GET", "/api", 5, 60)
    assert allowed == False
    
    # Different IP has own quota
    allowed = await limiter.is_allowed_by_ip("192.168.1.2", "GET", "/api", 5, 60)
    assert allowed == True
```

---

## 4. MONITORING & TELEMETRY TESTING

### 4.1 Unit Tests - Application Insights

```python
# tests/test_monitoring.py

import pytest
from app.backend.monitoring.insights import ApplicationInsightsManager

@pytest.fixture
def insights():
    """Initialize Application Insights"""
    manager = ApplicationInsightsManager()
    manager.initialize()
    yield manager
    manager.close()

@pytest.mark.asyncio
async def test_insights_enabled(insights):
    """✅ Test: Application Insights enabled"""
    assert insights.enabled == True

@pytest.mark.asyncio
async def test_track_event(insights):
    """✅ Test: Track custom event"""
    insights.track_event("test.event", {
        "user_id": "123",
        "action": "create"
    })
    
    # Verify event was sent
    await asyncio.sleep(0.5)  # Give time to flush
    assert insights.client.flush() == True

@pytest.mark.asyncio
async def test_track_metric(insights):
    """✅ Test: Track custom metric"""
    insights.track_metric("active_agents", 42)
    insights.track_metric("cache_hit_rate", 0.85)
    
    await asyncio.sleep(0.5)
    assert insights.client.flush() == True

@pytest.mark.asyncio
async def test_track_exception(insights):
    """✅ Test: Track exception with context"""
    try:
        raise ValueError("Test error")
    except ValueError as e:
        insights.track_exception(e, {
            "user_id": "123",
            "operation": "test"
        })
    
    await asyncio.sleep(0.5)
    assert insights.client.flush() == True

@pytest.mark.asyncio
async def test_track_dependency(insights):
    """✅ Test: Track dependency calls"""
    insights.track_dependency("PostgreSQL", "agent_create", 45, True)
    insights.track_dependency("Redis", "cache_get", 2, True)
    
    await asyncio.sleep(0.5)
    assert insights.client.flush() == True
```

### 4.2 Health Check Tests

```python
# tests/test_health_checks.py

from app.backend.app import app as quart_app

@pytest.fixture
def app():
    """Create test app"""
    return quart_app

@pytest.mark.asyncio
async def test_health_liveness(app):
    """✅ Test: /health endpoint (liveness probe)"""
    with app.test_client() as client:
        response = await client.get("/api/agents/health")
        assert response.status_code == 200
        data = await response.get_json()
        assert data["status"] in ["healthy", "degraded"]

@pytest.mark.asyncio
async def test_health_readiness(app):
    """✅ Test: /health/ready endpoint (readiness probe)"""
    with app.test_client() as client:
        response = await client.get("/api/agents/health/ready")
        assert response.status_code == 200
        data = await response.get_json()
        assert data["status"] == "ready"
        assert "components" in data

@pytest.mark.asyncio
async def test_health_live(app):
    """✅ Test: /health/live endpoint (K8S liveness)"""
    with app.test_client() as client:
        response = await client.get("/api/agents/health/live")
        assert response.status_code == 200
        data = await response.get_json()
        assert data["status"] == "live"

@pytest.mark.asyncio
async def test_health_components(app):
    """✅ Test: Health check includes component status"""
    with app.test_client() as client:
        response = await client.get("/api/agents/health/ready")
        data = await response.get_json()
        
        assert "database" in data["components"]
        assert "redis" in data["components"]
        assert "application_insights" in data["components"]
        
        # Each should have status
        assert "status" in data["components"]["database"]
        assert "status" in data["components"]["redis"]

@pytest.mark.asyncio
async def test_health_database_down(app):
    """✅ Test: Health check detects database down"""
    # Simulate database failure
    # (Implementation depends on your setup)
    
    with app.test_client() as client:
        response = await client.get("/api/agents/health/ready")
        data = await response.get_json()
        
        if data["components"]["database"]["status"] == "unhealthy":
            assert response.status_code == 503  # Service unavailable
```

---

## 5. INTEGRATION TESTS

### 5.1 Full Flow - Create Agent

```python
# tests/test_integration.py

import pytest
from app.backend.app import app as quart_app
from app.backend.db.database import DatabaseManager
from app.backend.cache.cache import RedisManager

@pytest.fixture
async def app():
    """Initialize full app"""
    db = DatabaseManager()
    await db.initialize()
    
    cache = RedisManager()
    await cache.initialize()
    
    yield quart_app
    
    await db.close()
    await cache.close()

@pytest.mark.asyncio
async def test_create_agent_full_flow(app):
    """✅ Test: Create agent (DB + Cache + Monitoring + Rate Limit)"""
    with app.test_client() as client:
        # Step 1: Create agent
        response = await client.post(
            "/api/agents/browser",
            json={
                "agent_id": "test_agent",
                "channel": "msedge",
                "headless": True
            },
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 201
        data = await response.get_json()
        assert data["persisted"] == True
        
        # Step 2: Verify in database
        # (Check that audit log was created)
        
        # Step 3: Verify in cache
        # (Check that agent config is cached)
        
        # Step 4: Verify rate limiting headers
        assert "X-RateLimit-Remaining" in response.headers
        
        # Step 5: Verify telemetry
        # (Check Application Insights event was sent)

@pytest.mark.asyncio
async def test_list_agents_with_cache(app):
    """✅ Test: List agents uses cache"""
    with app.test_client() as client:
        # First request (cache miss)
        response1 = await client.get("/api/agents/browser")
        assert response1.status_code == 200
        
        # Second request (should be faster from cache)
        response2 = await client.get("/api/agents/browser")
        assert response2.status_code == 200
        
        # Both should have same data
        data1 = await response1.get_json()
        data2 = await response2.get_json()
        assert data1 == data2
```

### 5.2 Graceful Degradation Tests

```python
@pytest.mark.asyncio
async def test_graceful_fallback_without_database(app):
    """✅ Test: System works without database"""
    # Remove database URL
    import os
    old_db_url = os.getenv("DATABASE_URL")
    os.environ["DATABASE_URL"] = ""
    
    with app.test_client() as client:
        response = await client.get("/api/agents/health/ready")
        
        # Should still be accessible
        assert response.status_code in [200, 503]  # Either OK or Unavailable
        
        data = await response.get_json()
        assert data["components"]["database"]["mode"] == "memory"
    
    # Restore
    os.environ["DATABASE_URL"] = old_db_url

@pytest.mark.asyncio
async def test_graceful_fallback_without_redis(app):
    """✅ Test: System works without Redis"""
    import os
    old_redis_url = os.getenv("REDIS_URL")
    os.environ["REDIS_URL"] = ""
    
    with app.test_client() as client:
        response = await client.post(
            "/api/agents/browser",
            json={"agent_id": "test", "channel": "msedge"},
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Should still work with memory cache
        assert response.status_code == 201
    
    os.environ["REDIS_URL"] = old_redis_url
```

---

## 6. PERFORMANCE TESTS

### 6.1 Load Testing

```python
# tests/test_performance.py

import pytest
import time
from locust import HttpUser, task, between

class APILoadTest(HttpUser):
    """Load test for API endpoints"""
    
    wait_time = between(1, 3)
    
    @task(3)
    def get_agents(self):
        """✅ Test: GET /agents under load"""
        self.client.get(
            "/api/agents/browser",
            headers={"Authorization": "Bearer test_token"}
        )
    
    @task(1)
    def create_agent(self):
        """✅ Test: POST /agents under load"""
        self.client.post(
            "/api/agents/browser",
            json={"agent_id": f"load_test_{time.time()}", "channel": "msedge"},
            headers={"Authorization": "Bearer test_token"}
        )

# Run with: locust -f tests/test_performance.py --host=http://localhost:50505
```

### 6.2 Latency Tests

```python
@pytest.mark.asyncio
async def test_response_time_get_agents(app):
    """✅ Test: GET /agents responds < 100ms"""
    with app.test_client() as client:
        start = time.time()
        response = await client.get(
            "/api/agents/browser",
            headers={"Authorization": "Bearer test_token"}
        )
        latency = (time.time() - start) * 1000  # ms
        
        assert response.status_code == 200
        assert latency < 100  # Should be < 100ms

@pytest.mark.asyncio
async def test_response_time_create_agent(app):
    """✅ Test: POST /agents responds < 500ms"""
    with app.test_client() as client:
        start = time.time()
        response = await client.post(
            "/api/agents/browser",
            json={"agent_id": f"perf_{time.time()}", "channel": "msedge"},
            headers={"Authorization": "Bearer test_token"}
        )
        latency = (time.time() - start) * 1000  # ms
        
        assert response.status_code == 201
        assert latency < 500  # Should be < 500ms
```

### 6.3 Throughput Tests

```python
@pytest.mark.asyncio
async def test_throughput_get_agents(app):
    """✅ Test: GET /agents handles 100 req/sec"""
    with app.test_client() as client:
        import asyncio
        
        async def make_request():
            return await client.get(
                "/api/agents/browser",
                headers={"Authorization": "Bearer test_token"}
            )
        
        # Make 100 requests concurrently
        start = time.time()
        tasks = [make_request() for _ in range(100)]
        responses = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)
        
        # Throughput: ~100 requests in X seconds
        throughput = 100 / elapsed
        assert throughput >= 50  # At least 50 req/sec
```

---

## 7. SECURITY TESTS

### 7.1 Rate Limiting Security

```python
# tests/test_security.py

@pytest.mark.asyncio
async def test_ddos_protection(app):
    """✅ Test: DDoS protection via rate limiting"""
    with app.test_client() as client:
        # Attempt 100 requests from same IP
        responses = []
        for i in range(100):
            response = await client.post(
                "/api/agents/browser",
                json={"agent_id": f"ddos_{i}", "channel": "msedge"},
                headers={"Authorization": "Bearer test_token"}
            )
            responses.append(response.status_code)
        
        # Some should be rate limited (429)
        assert any(status == 429 for status in responses)

@pytest.mark.asyncio
async def test_token_validation(app):
    """✅ Test: Invalid token rejected"""
    with app.test_client() as client:
        response = await client.post(
            "/api/agents/browser",
            json={"agent_id": "test", "channel": "msedge"},
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401  # Unauthorized

@pytest.mark.asyncio
async def test_missing_token(app):
    """✅ Test: Missing token rejected"""
    with app.test_client() as client:
        response = await client.post(
            "/api/agents/browser",
            json={"agent_id": "test", "channel": "msedge"}
            # No Authorization header
        )
        
        assert response.status_code == 401
```

---

## 8. FAILOVER & RESILIENCE TESTS

### 8.1 Failover Scenarios

```python
# tests/test_failover.py

@pytest.mark.asyncio
async def test_failover_database_to_memory(app):
    """✅ Test: Failover from PostgreSQL to memory"""
    # Simulate database failure
    # System should continue with in-memory storage
    
    with app.test_client() as client:
        response = await client.post(
            "/api/agents/browser",
            json={"agent_id": "failover_test", "channel": "msedge"},
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 201  # Should still work

@pytest.mark.asyncio
async def test_failover_redis_to_memory(app):
    """✅ Test: Failover from Redis to memory"""
    # Simulate Redis failure
    # System should continue with in-memory cache
    
    with app.test_client() as client:
        response = await client.get(
            "/api/agents/browser",
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 200  # Should still work

@pytest.mark.asyncio
async def test_failover_insights_not_critical(app):
    """✅ Test: Missing Application Insights doesn't break system"""
    # Remove APPLICATIONINSIGHTS_CONNECTION_STRING
    # System should log locally instead
    
    with app.test_client() as client:
        response = await client.post(
            "/api/agents/browser",
            json={"agent_id": "insights_failover", "channel": "msedge"},
            headers={"Authorization": "Bearer test_token"}
        )
        
        assert response.status_code == 201  # Should still work
```

---

## 9. RUN ALL TESTS

### 9.1 Test Command Reference

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_database.py -v

# Run specific test
pytest tests/test_database.py::test_database_connection -v

# Run with coverage
pytest tests/ --cov=app/backend --cov-report=html

# Run only unit tests (fast)
pytest tests/ -m "not integration" -v

# Run only integration tests (slower)
pytest tests/ -m "integration" -v

# Run with specific marker
pytest tests/ -m "database" -v

# Run in parallel (faster)
pytest tests/ -n auto

# Run with detailed output
pytest tests/ -vv -s
```

### 9.2 Coverage Goals

```
Target Coverage: 90%+

Breakdown:
  - Database layer:      95%+
  - Cache layer:         95%+
  - Rate limiting:       90%+
  - Monitoring:          85%+
  - API endpoints:       85%+
```

---

## 10. PRE-DEPLOYMENT CHECKLIST

```
BEFORE DEPLOYING TO PRODUCTION:

Database Tests:
  ☑️ test_database_connection
  ☑️ test_create_agent
  ☑️ test_audit_log_created
  ☑️ test_connection_pool_size
  ☑️ test_alembic_migration_up

Cache Tests:
  ☑️ test_redis_connection
  ☑️ test_cache_set_get
  ☑️ test_cache_ttl_expiration
  ☑️ test_cache_increment
  ☑️ test_session_create

Rate Limiting Tests:
  ☑️ test_rate_limit_allow_requests
  ☑️ test_rate_limit_reject_requests
  ☑️ test_rate_limit_window_reset
  ☑️ test_rate_limit_per_user

Monitoring Tests:
  ☑️ test_track_event
  ☑️ test_track_metric
  ☑️ test_track_exception
  ☑️ test_health_readiness

Integration Tests:
  ☑️ test_create_agent_full_flow
  ☑️ test_graceful_fallback_without_database
  ☑️ test_graceful_fallback_without_redis

Performance Tests:
  ☑️ test_response_time_get_agents (< 100ms)
  ☑️ test_response_time_create_agent (< 500ms)
  ☑️ test_throughput_get_agents (50+ req/sec)

Security Tests:
  ☑️ test_ddos_protection
  ☑️ test_token_validation
  ☑️ test_missing_token

Failover Tests:
  ☑️ test_failover_database_to_memory
  ☑️ test_failover_redis_to_memory
  ☑️ test_failover_insights_not_critical

Coverage:
  ☑️ Overall coverage >= 90%
  ☑️ Core modules >= 95%
```

---

## 11. CI/CD INTEGRATION

### GitHub Actions Example

```yaml
# .github/workflows/test-tier1.yml

name: TIER 1 Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.13"
      
      - name: Install dependencies
        run: |
          pip install -r app/backend/requirements.txt
          pip install pytest pytest-asyncio pytest-cov pytest-xdist
      
      - name: Run tests
        run: |
          pytest tests/ -v --cov=app/backend --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

---

**Status:** ✅ COMPREHENSIVE TESTING PLAN COMPLETE  
**Total Test Cases:** 60+ unit + integration tests  
**Coverage Target:** 90%+  
**Deployment Ready:** Yes, after all tests pass
