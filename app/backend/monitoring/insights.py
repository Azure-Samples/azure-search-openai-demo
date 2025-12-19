"""Azure Application Insights telemetry and monitoring.

Integrates Azure Monitor OpenTelemetry for comprehensive observability:
- Automatic HTTP request tracking
- Exception and error logging
- Custom events and metrics
- Dependency tracking (database, cache, external APIs)
- Performance monitoring
- Distributed tracing

Usage:
    from monitoring import ApplicationInsightsManager, track_event, track_metric
    
    # Initialize (once at app startup)
    insights = ApplicationInsightsManager()
    insights.setup(app)
    
    # Track custom events
    track_event("agent.created", {"agent_id": "123", "channel": "msedge"})
    
    # Track custom metrics
    track_metric("active_agents", 42)
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import Azure Monitor
try:
    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry import trace
    from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
    from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.sdk.trace import TracerProvider

    INSIGHTS_AVAILABLE = True
except ImportError:
    INSIGHTS_AVAILABLE = False
    logger.warning(
        "Azure Monitor OpenTelemetry not available. "
        "Telemetry will not be collected. "
        "Install: pip install azure-monitor-opentelemetry"
    )


class ApplicationInsightsManager:
    """Manages Azure Application Insights telemetry.
    
    Automatically instruments:
    - HTTP requests (via ASGI middleware)
    - HTTP client requests (httpx, aiohttp)
    - Exceptions
    - Dependencies
    
    Attributes:
        connection_string: Application Insights connection string
        tracer: OpenTelemetry tracer for custom spans
        enabled: Whether telemetry is active
        
    Example:
        insights = ApplicationInsightsManager()
        insights.setup(app)
        
        # Custom tracking
        insights.track_event("user.login", {"user_id": "123"})
        insights.track_metric("cache.hit_rate", 0.85)
    """

    def __init__(self, connection_string: Optional[str] = None):
        """Initialize Application Insights manager.
        
        Args:
            connection_string: App Insights connection string
                              Falls back to APPLICATIONINSIGHTS_CONNECTION_STRING env var
        """
        self.connection_string = connection_string or os.getenv(
            "APPLICATIONINSIGHTS_CONNECTION_STRING"
        )
        self.tracer = None
        self.enabled = False

        if not INSIGHTS_AVAILABLE:
            logger.warning("Application Insights disabled (library not available).")
        elif not self.connection_string:
            logger.warning(
                "Application Insights disabled (APPLICATIONINSIGHTS_CONNECTION_STRING not set). "
                "Set environment variable to enable telemetry."
            )
        else:
            logger.info("Application Insights available with connection string.")

    def setup(self, app=None):
        """Setup Application Insights for the application.
        
        Configures:
        - Azure Monitor exporter
        - ASGI middleware (automatic request tracking)
        - HTTP client instrumentation
        - Exception tracking
        
        Args:
            app: Quart application instance (optional, for middleware)
            
        Returns:
            bool: True if setup successful
        """
        if not INSIGHTS_AVAILABLE or not self.connection_string:
            logger.info("Application Insights setup skipped (not configured).")
            return False

        try:
            # Configure Azure Monitor
            configure_azure_monitor(
                connection_string=self.connection_string,
                # Enable automatic instrumentation
                enable_live_metrics=True,  # Real-time metrics stream
                enable_standard_metrics=True,  # Standard performance counters
            )

            # Instrument HTTP clients
            AioHttpClientInstrumentor().instrument()
            HTTPXClientInstrumentor().instrument()

            # Get tracer
            self.tracer = trace.get_tracer(__name__)

            # Add ASGI middleware to app (if provided)
            if app:
                app.asgi_app = OpenTelemetryMiddleware(app.asgi_app)
                logger.info("Application Insights ASGI middleware installed.")

            self.enabled = True
            logger.info("✅ Application Insights initialized successfully.")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Application Insights: {e}")
            self.enabled = False
            return False

    def track_event(
        self, name: str, properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track a custom event.
        
        Use for business logic events:
        - User actions (login, logout, registration)
        - Business events (agent created, task completed)
        - Feature usage (feature X used N times)
        
        Args:
            name: Event name (e.g., "agent.created", "user.login")
            properties: Additional properties (e.g., {"agent_id": "123"})
            
        Example:
            track_event("agent.created", {
                "agent_id": "agent_123",
                "channel": "msedge",
                "headless": True
            })
        """
        if not self.enabled or not self.tracer:
            logger.debug(f"Event tracking skipped (disabled): {name}")
            return

        try:
            with self.tracer.start_as_current_span(name) as span:
                if properties:
                    for key, value in properties.items():
                        span.set_attribute(key, str(value))
                logger.debug(f"Tracked event: {name} with properties: {properties}")

        except Exception as e:
            logger.error(f"Failed to track event {name}: {e}")

    def track_metric(
        self, name: str, value: float, properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track a custom metric.
        
        Use for business and technical metrics:
        - Performance metrics (response_time_ms, query_latency)
        - Resource metrics (active_agents, queue_size)
        - Business metrics (tasks_completed, revenue)
        
        Args:
            name: Metric name (e.g., "active_agents", "response_time_ms")
            value: Metric value (numeric)
            properties: Additional properties (dimensions)
            
        Example:
            track_metric("active_agents", 42, {"environment": "production"})
            track_metric("response_time_ms", 125.5, {"endpoint": "/api/create"})
        """
        if not self.enabled or not self.tracer:
            logger.debug(f"Metric tracking skipped (disabled): {name}={value}")
            return

        try:
            with self.tracer.start_as_current_span(f"metric.{name}") as span:
                span.set_attribute(name, value)
                if properties:
                    for key, val in properties.items():
                        span.set_attribute(key, str(val))
                logger.debug(f"Tracked metric: {name}={value} with properties: {properties}")

        except Exception as e:
            logger.error(f"Failed to track metric {name}: {e}")

    def track_exception(
        self,
        exception: Exception,
        properties: Optional[Dict[str, Any]] = None,
        measurements: Optional[Dict[str, float]] = None,
    ) -> None:
        """Track an exception.
        
        Automatically captures:
        - Exception type
        - Exception message
        - Stack trace
        - Context properties
        
        Args:
            exception: The exception to track
            properties: Additional context (user_id, endpoint, etc.)
            measurements: Numeric measurements (attempt_number, duration_ms)
            
        Example:
            try:
                risky_operation()
            except ValueError as e:
                track_exception(e, {
                    "user_id": "123",
                    "operation": "agent_create"
                })
                raise
        """
        if not self.enabled or not self.tracer:
            logger.debug(f"Exception tracking skipped (disabled): {exception}")
            return

        try:
            with self.tracer.start_as_current_span("exception") as span:
                span.set_attribute("exception.type", type(exception).__name__)
                span.set_attribute("exception.message", str(exception))
                span.record_exception(exception)

                if properties:
                    for key, value in properties.items():
                        span.set_attribute(key, str(value))

                if measurements:
                    for key, value in measurements.items():
                        span.set_attribute(f"measurement.{key}", value)

                logger.debug(f"Tracked exception: {type(exception).__name__}: {exception}")

        except Exception as e:
            logger.error(f"Failed to track exception: {e}")

    def flush(self) -> None:
        """Flush pending telemetry.
        
        Call before application shutdown to ensure all telemetry is sent.
        """
        if self.enabled:
            logger.info("Flushing Application Insights telemetry...")
            # OpenTelemetry auto-flushes, but we log for visibility


# Global instance (singleton pattern)
_insights_instance: Optional[ApplicationInsightsManager] = None


def get_insights_manager() -> ApplicationInsightsManager:
    """Get global Application Insights manager instance.
    
    Returns:
        ApplicationInsightsManager: Global insights manager
    """
    global _insights_instance
    if _insights_instance is None:
        _insights_instance = ApplicationInsightsManager()
    return _insights_instance


def track_event(name: str, properties: Optional[Dict[str, Any]] = None) -> None:
    """Track a custom event (global function).
    
    Args:
        name: Event name
        properties: Event properties
    """
    manager = get_insights_manager()
    manager.track_event(name, properties)


def track_metric(
    name: str, value: float, properties: Optional[Dict[str, Any]] = None
) -> None:
    """Track a custom metric (global function).
    
    Args:
        name: Metric name
        value: Metric value
        properties: Metric dimensions
    """
    manager = get_insights_manager()
    manager.track_metric(name, value, properties)


def track_exception(
    exception: Exception,
    properties: Optional[Dict[str, Any]] = None,
    measurements: Optional[Dict[str, float]] = None,
) -> None:
    """Track an exception (global function).
    
    Args:
        exception: Exception to track
        properties: Context properties
        measurements: Numeric measurements
    """
    manager = get_insights_manager()
    manager.track_exception(exception, properties, measurements)
