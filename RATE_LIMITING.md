# Azure Rate Limit Configuration Guide

## Overview

This deployment includes comprehensive rate limiting to prevent hitting Azure service quotas and throttling limits.

## Service Rate Limits

### Azure Search
- **Queries Per Second (QPS)**: 5 (configurable in code)
- **Indexing Operations**: 2 per second
- **Throttling Response**: HTTP 429

**Configuration in code:**
```python
SEARCH_QPS_LIMIT = 5
SEARCH_INDEX_OPS_LIMIT = 2
```

### Azure OpenAI
- **Requests Per Minute (RPM)**: 90 (Standard tier)
- **Tokens Per Minute (TPM)**: 90,000
- **Throttling Response**: HTTP 429

**Configuration in code:**
```python
OPENAI_RPM_LIMIT = 90
OPENAI_TPM_LIMIT = 90000
```

### Azure Storage
- **Target Throughput**: 5 GB/s per storage account
- **Scalability Targets**: 20,000 IOPS per storage account
- **Throttling Response**: HTTP 503 (Service Unavailable)

## Rate Limiting Implementation

### 1. Token Bucket Algorithm

The system uses a token bucket rate limiter for smooth request distribution:

```python
# Example: Azure Search with 5 QPS limit
rate_limiter = RateLimiter(rate=5, burst=1)
await rate_limiter.acquire()  # Wait if needed
# Make request
```

**Benefits:**
- Smooth distribution of requests
- Prevents burst spikes
- Predictable throttling

### 2. Circuit Breaker Pattern

Prevents cascading failures when services become unavailable:

```python
circuit_breaker = CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60       # Try to recover after 60s
)

if circuit_breaker.is_open():
    raise Exception("Service circuit is open - waiting for recovery")
```

**States:**
- **Closed**: Normal operation, requests pass through
- **Open**: Service failing, requests rejected immediately
- **Half-Open**: Testing if service recovered

### 3. Exponential Backoff with Jitter

Retry failed requests with exponential delays:

```python
# Retry timing:
# Attempt 1: Fail immediately
# Attempt 2: Wait 1 second
# Attempt 3: Wait 2 seconds
# Attempt 4: Wait 4 seconds
# Attempt 5: Wait 8 seconds
# Attempt 6: Wait 16 seconds
```

**Features:**
- Respects Azure `Retry-After` headers
- Exponential growth up to 32 seconds max
- Prevents thundering herd

### 4. Concurrent Request Limiting

Limits maximum concurrent requests per service:

```python
MAX_CONCURRENT_SEARCH_REQUESTS = 5
MAX_CONCURRENT_OPENAI_REQUESTS = 2
```

## GitHub Actions Rate Limiting

### Deployment Concurrency

```yaml
concurrency:
  group: deployment-${{ github.ref }}
  cancel-in-progress: false
```

**Effect:**
- Only one deployment runs at a time per branch
- Prevents Azure resource conflicts
- Serializes infrastructure changes

### Job Timeouts

- Build and Test: 30 minutes
- Docker Build: 30 minutes (20 minute actual build)
- Azure Deploy: 45 minutes
- Health Check: 15 minutes

**Benefits:**
- Prevents runaway deployments
- Reasonable completion times
- Early failure detection

### Sequential Job Execution

Jobs run in order: Build → Test → Docker → Deploy → Monitor

```yaml
needs: build-and-test  # Wait for previous job
timeout-minutes: 30    # Individual timeout
```

## Monitoring and Alerting

### Application Insights Metrics

Monitor in Azure Portal:
1. Go to Application Insights resource
2. Check "Performance" tab for response times
3. View "Failures" for rate limit errors (HTTP 429)
4. Set up custom alerts

### Programmatic Monitoring

```python
from azure.monitor.query import MetricsQueryClient

# Query Azure Search request count
metrics = metrics_client.query_resource(
    resource_id=search_resource_id,
    metric_names=["QueryCount"],
    granularity=timedelta(minutes=1)
)

if metrics.query_count > SEARCH_QPS_LIMIT * 60:
    logger.warning("Search requests approaching limit")
```

### Alert Rules

Created during deployment:

```
Alert: "HighOpenAIRequestRate"
Condition: Average requests/sec > 90
Window: 5 minutes
Evaluation: Every 1 minute
Action: Send notification to team
```

## Environment Variable Configuration

Set in `.env` or GitHub Secrets:

```bash
# Rate limiting
AZURE_SEARCH_QUERY_DELAY_MS=100          # Minimum delay between queries
AZURE_OPENAI_REQUEST_TIMEOUT=30          # HTTP timeout for OpenAI
AZURE_OPENAI_MAX_RETRIES=3               # Max retry attempts
AZURE_OPENAI_RETRY_DELAY_MS=1000         # Initial retry delay

# Concurrency
MAX_CONCURRENT_SEARCH_REQUESTS=5         # Parallel search requests
MAX_CONCURRENT_OPENAI_REQUESTS=2         # Parallel OpenAI requests
```

## Auto-Scaling Configuration

App Service Plan automatically scales based on CPU:

```bicep
rules: [
  {
    # Scale UP when CPU > 70%
    threshold: 70
    operator: GreaterThan
    action: IncreaseCount by 1
    cooldown: 5 minutes
  },
  {
    # Scale DOWN when CPU < 30%
    threshold: 30
    operator: LessThan
    action: DecreaseCount by 1
    cooldown: 10 minutes
  }
]

# Capacity: 1-3 instances
```

**Impact:**
- More instances = lower per-instance load
- Lower load = less likely to hit rate limits
- Cost increases with additional instances

## Testing Rate Limit Behavior

### Load Testing

```bash
# Test with concurrent requests
ab -n 100 -c 10 https://app-azure-search-prod.azurewebsites.net/api/search

# Monitor throttling
watch -n 1 'curl -w "Status: %{http_code}\n" https://...'
```

### Rate Limit Simulation

```python
import asyncio
from rate_limiter import get_throttler

throttler = get_throttler()

async def test_rate_limiting():
    tasks = []
    for i in range(20):
        tasks.append(throttler.throttle_search_request())
    
    # This will be delayed and throttled to 5 QPS
    await asyncio.gather(*tasks)
```

## Troubleshooting Rate Limit Issues

### Symptoms

1. **HTTP 429 (Too Many Requests)**
   - Solution: Check throttler configuration
   - Increase `AZURE_SEARCH_QUERY_DELAY_MS`
   - Reduce `MAX_CONCURRENT_SEARCH_REQUESTS`

2. **HTTP 503 (Service Unavailable)**
   - Solution: Circuit breaker likely open
   - Check service health in Azure Portal
   - Wait for auto-recovery (60 seconds)

3. **Timeouts**
   - Solution: Increase `AZURE_OPENAI_REQUEST_TIMEOUT`
   - Check network latency
   - Verify endpoint accessibility

### Debug Logs

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("rate_limiter")
```

Check logs in Azure:
- Application Insights → Logs → traces
- Filter by `rate_limiter` logger

## Cost Implications

### Free Tier Limits

- **Azure Search**: 3 units maximum (query-only)
- **Azure OpenAI**: Pay-as-you-go with rate limits
- **Storage**: 5 GB/month free

### Scaling Costs

| Config | Monthly Cost | Capacity |
|--------|-------------|----------|
| 1x S1 App Service | $74.88 | Low |
| 2x S1 App Service | $149.76 | Medium |
| 3x S1 App Service | $224.64 | High |

## Best Practices

1. ✅ **Monitor continuously** - Set up Application Insights alerts
2. ✅ **Test rate limits** - Load test before production
3. ✅ **Use circuit breakers** - Prevent cascade failures
4. ✅ **Configure retries** - Respect Retry-After headers
5. ✅ **Scale proactively** - Add capacity before limits hit
6. ✅ **Cache results** - Reduce duplicate requests
7. ✅ **Batch operations** - Group API calls where possible
8. ✅ **Monitor costs** - Track usage against budget

## Further Reading

- [Azure Search Rate Limits](https://learn.microsoft.com/en-us/azure/search/search-limits-quotas-capacity)
- [Azure OpenAI Rate Limits](https://learn.microsoft.com/en-us/azure/ai-services/openai/quotas-and-limits)
- [Azure Storage Scalability](https://learn.microsoft.com/en-us/azure/storage/common/scalability-targets-standard-accounts)
- [Circuit Breaker Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker)
- [Retry Pattern with Exponential Backoff](https://learn.microsoft.com/en-us/azure/architecture/patterns/retry)
