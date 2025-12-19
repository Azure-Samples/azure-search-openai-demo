# Azure Application Insights - Enterprise Monitoring

## 🎯 Overview

Production-grade telemetry and observability using **Azure Monitor OpenTelemetry**. Automatically tracks requests, dependencies, exceptions, and custom events.

Follows **Microsoft Azure Application Insights** best practices for distributed systems.

## ✅ Features

### 1. **Automatic Instrumentation**
- HTTP requests (ASGI middleware)
- HTTP client calls (aiohttp, httpx)
- Database queries (via OpenTelemetry auto-instrumentation)
- Redis operations (via OpenTelemetry auto-instrumentation)
- Exception tracking with stack traces

### 2. **Custom Telemetry**
- Events (business logic tracking)
- Metrics (performance, resource usage)
- Manual exception tracking
- Custom spans for specific operations

### 3. **Real-Time Monitoring**
- Live Metrics Stream (1-second latency)
- Performance counters (CPU, memory, requests/sec)
- Failure rates and exceptions
- Dependency health

## 🚀 Quick Start

### 1. Get Application Insights Connection String

**Azure Portal:**
1. Navigate to your Application Insights resource
2. Copy **Connection String** from Overview page

**Example:**
```
InstrumentationKey=abc123...;IngestionEndpoint=https://westus2-0.in.applicationinsights.azure.com/;LiveEndpoint=https://westus2.livediagnostics.monitor.azure.microsoft.com/
```

### 2. Set Environment Variable

```bash
export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=abc123...;IngestionEndpoint=..."
```

**Or in `.env` file:**
```ini
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=abc123...
```

### 3. Initialize in Your App

```python
from quart import Quart
from monitoring import ApplicationInsightsManager

app = Quart(__name__)

# Initialize Application Insights
insights = ApplicationInsightsManager()
insights.setup(app)  # Auto-instruments ASGI middleware

@app.route("/")
async def index():
    return {"status": "ok"}
```

**That's it!** All requests, exceptions, and dependencies are now tracked automatically.

## 📊 Usage Examples

### Custom Events

Track business logic events:

```python
from monitoring import track_event

# User registration
track_event("user.registered", {
    "user_id": "123",
    "plan": "premium",
    "referral_source": "organic"
})

# Agent created
track_event("agent.created", {
    "agent_id": "agent_456",
    "channel": "msedge",
    "headless": "True"
})

# Feature usage
track_event("feature.used", {
    "feature": "automation",
    "platform": "upwork"
})
```

### Custom Metrics

Track KPIs and performance:

```python
from monitoring import track_metric

# Active resources
track_metric("active_agents", 42)
track_metric("queue_depth", 157)

# Performance metrics
track_metric("response_time_ms", 125.5, {"endpoint": "/api/create"})
track_metric("cache_hit_rate", 0.85, {"cache_type": "redis"})

# Business metrics
track_metric("tasks_completed", 1523, {"date": "2024-01-15"})
```

### Exception Tracking

Track errors with context:

```python
from monitoring import track_exception

try:
    risky_operation()
except ValueError as e:
    track_exception(e, {
        "user_id": "123",
        "operation": "agent_create",
        "input_data": str(data)
    })
    raise  # Re-raise after tracking
```

### Custom Spans (Advanced)

Track specific operations:

```python
from monitoring import get_insights_manager

insights = get_insights_manager()

async def expensive_operation():
    with insights.tracer.start_as_current_span("database.bulk_insert") as span:
        span.set_attribute("row_count", 10000)
        span.set_attribute("table", "agents")
        
        # Perform operation
        await db.bulk_insert(rows)
        
        span.set_attribute("duration_ms", elapsed_ms)
```

## 🔍 Azure Portal Queries

### Request Analytics

```kusto
// Request count by endpoint
requests
| where timestamp > ago(24h)
| summarize count() by name
| order by count_ desc

// Slowest requests
requests
| where timestamp > ago(1h)
| order by duration desc
| take 10
| project timestamp, name, duration, resultCode

// Failed requests
requests
| where timestamp > ago(24h) and success == false
| summarize count() by name, resultCode
| order by count_ desc
```

### Exception Analysis

```kusto
// Exception count by type
exceptions
| where timestamp > ago(24h)
| summarize count() by type
| order by count_ desc

// Recent exceptions with context
exceptions
| where timestamp > ago(1h)
| extend properties = todynamic(customDimensions)
| project timestamp, type, outerMessage, properties
| order by timestamp desc

// Exception rate trend
exceptions
| where timestamp > ago(7d)
| summarize count() by bin(timestamp, 1h)
| render timechart
```

### Custom Event Analysis

```kusto
// Agent creation by channel
customEvents
| where name == "agent.created"
| extend properties = todynamic(customDimensions)
| extend channel = tostring(properties.channel)
| summarize count() by channel

// Feature usage
customEvents
| where name == "feature.used"
| extend feature = tostring(customDimensions.feature)
| summarize count() by feature
| order by count_ desc
```

### Performance Metrics

```kusto
// Average response time by endpoint
requests
| where timestamp > ago(24h)
| summarize avg(duration) by name
| order by avg_duration desc

// P95 response time
requests
| where timestamp > ago(24h)
| summarize percentile(duration, 95) by name

// Request rate (per minute)
requests
| where timestamp > ago(1h)
| summarize count() by bin(timestamp, 1m)
| render timechart
```

### Dependency Tracking

```kusto
// External API calls
dependencies
| where timestamp > ago(24h) and type == "Http"
| summarize count(), avg(duration) by target
| order by count_ desc

// Database query performance
dependencies
| where timestamp > ago(24h) and type == "SQL"
| summarize avg(duration), max(duration) by name

// Failed dependencies
dependencies
| where timestamp > ago(24h) and success == false
| summarize count() by target, resultCode
```

### Custom Metrics

```kusto
// Active agents over time
customMetrics
| where name == "active_agents"
| summarize avg(value) by bin(timestamp, 5m)
| render timechart

// Cache hit rate
customMetrics
| where name == "cache_hit_rate"
| summarize avg(value) by bin(timestamp, 1h)
| render timechart
```

## 🔧 Azure Portal Configuration

### 1. Alerts

**Example: High Error Rate**

```kusto
requests
| where timestamp > ago(5m) and success == false
| summarize error_rate = count() * 100.0 / (todouble(count()))
| where error_rate > 5  // Alert if >5% errors
```

**Create Alert:**
- Navigate to Alerts → New alert rule
- Paste query above
- Set threshold: error_rate > 5
- Action Group: Email/SMS/Webhook

### 2. Live Metrics

Enable real-time monitoring:
1. Navigate to Live Metrics in Azure Portal
2. View requests, failures, dependencies in real-time
3. Filter by cloud role, server, or custom dimensions

### 3. Application Map

Visualize dependencies:
1. Navigate to Application Map
2. See all dependencies (APIs, databases, caches)
3. Identify slow or failing components

### 4. Smart Detection

Automatic anomaly detection:
- Failure anomalies
- Performance degradation
- Memory leak detection
- Security issues

## 📈 Best Practices

### 1. Event Naming Convention

```python
# ✅ Good - hierarchical, descriptive
track_event("user.login.success", {...})
track_event("user.login.failed", {...})
track_event("agent.browser.started", {...})
track_event("payment.subscription.upgraded", {...})

# ❌ Bad - unclear, hard to query
track_event("thing_happened", {...})
track_event("event1", {...})
```

### 2. Metric Aggregation

```python
# ✅ Good - meaningful aggregation
track_metric("response_time_p95_ms", 250, {"endpoint": "/api/create"})
track_metric("active_users_count", 1523)

# ❌ Bad - too granular (use events instead)
track_metric("user_123_action", 1)
```

### 3. Property Cardinality

```python
# ✅ Good - low cardinality dimensions
track_event("request.completed", {
    "endpoint": "/api/create",     # ~10 values
    "status_code": "200",          # ~5 values
    "environment": "production"    # 2-3 values
})

# ❌ Bad - high cardinality (makes queries slow)
track_event("request.completed", {
    "user_id": "user_1234567890",  # Millions of values
    "timestamp": "2024-01-15..."   # Infinite values
})
```

### 4. Error Tracking

```python
# ✅ Good - context + re-raise
try:
    await db.insert(data)
except Exception as e:
    track_exception(e, {"operation": "db.insert", "table": "agents"})
    raise  # Re-raise for normal error handling

# ❌ Bad - swallow exception
try:
    await db.insert(data)
except Exception as e:
    track_exception(e)
    pass  # Silent failure!
```

### 5. Sampling (High Traffic Apps)

```python
# Configure sampling for cost control
from azure.monitor.opentelemetry import configure_azure_monitor

configure_azure_monitor(
    connection_string=CONNECTION_STRING,
    # Sample 10% of telemetry (for apps with >100M events/month)
    sampling_ratio=0.1
)
```

**When to sample:**
- >100M events per month
- >$500/month Application Insights cost
- Mostly uniform traffic (not bursty)

**When NOT to sample:**
- Critical errors (always log 100%)
- Low traffic apps (<10M events/month)
- Debugging/troubleshooting periods

## 🐛 Troubleshooting

### No Telemetry in Portal

**Problem:** Data not appearing in Application Insights

**Solutions:**
1. Check connection string is correct
2. Wait 2-5 minutes (ingestion delay)
3. Check firewall/proxy settings
4. Verify HTTPS outbound allowed to `*.applicationinsights.azure.com`

### "Module not found" Error

**Problem:** `ModuleNotFoundError: No module named 'azure.monitor.opentelemetry'`

**Solution:**
```bash
pip install azure-monitor-opentelemetry
pip install opentelemetry-instrumentation-aiohttp-client
pip install opentelemetry-instrumentation-httpx
pip install opentelemetry-instrumentation-asgi
```

### High Costs

**Problem:** Application Insights bills are high

**Solutions:**
1. Enable sampling (see above)
2. Reduce custom event/metric frequency
3. Use daily cap (Azure Portal → Usage and estimated costs)
4. Archive old data to blob storage

### Duplicate Telemetry

**Problem:** Same request tracked multiple times

**Solution:** Ensure `setup(app)` is called only once at startup, not per request.

## 🎓 Next Steps

**Tier 1 Complete!** 🎉 You've reached **88% Enterprise Readiness**

Continue with **Tier 2** features:
- CORS & Security Headers
- WebSocket support
- Kubernetes manifests
- OAuth2/JWT authentication

See main Enterprise upgrade plan in project root.

## 📚 References

- [Azure Application Insights Overview](https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [Azure Monitor OpenTelemetry](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/monitor/azure-monitor-opentelemetry)
- [Kusto Query Language (KQL)](https://learn.microsoft.com/azure/data-explorer/kusto/query/)

---

**Questions?** Check main project documentation or create an issue.
