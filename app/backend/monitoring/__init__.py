"""Azure Application Insights monitoring integration.

Provides enterprise-grade telemetry, performance tracking, and exception monitoring.
Uses Azure Monitor OpenTelemetry for automatic instrumentation.

Features:
- Request/response tracking
- Exception logging
- Performance metrics
- Custom events and metrics
- Dependency tracking (Redis, Database, HTTP)
- Distributed tracing

Following Microsoft Azure Application Insights best practices.
"""

from .insights import ApplicationInsightsManager, track_event, track_metric

__all__ = ["ApplicationInsightsManager", "track_event", "track_metric"]
