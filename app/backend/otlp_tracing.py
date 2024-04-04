from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHTTPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as OTLPGRPCSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as OTLPHTTPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as OTLPGRPCMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader


def configure_oltp_http_tracing(service_name: str = "azure-search-openai-demo", endpoint: str = "http://localhost:4318"):
    # Service name is required for most backends
    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })

    traceProvider = TracerProvider(resource=resource)
    # Trick OLTP into thinking the httpx client is a requests session so that HTTP2 works
    processor = BatchSpanProcessor(OTLPHTTPSpanExporter(endpoint=f"{endpoint}/v1/traces",))
    traceProvider.add_span_processor(processor)
    trace.set_tracer_provider(traceProvider)

    reader = PeriodicExportingMetricReader(
        OTLPHTTPMetricExporter(endpoint=f"{endpoint}/v1/metrics")
    )
    meterProvider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meterProvider)


def configure_oltp_grpc_tracing(service_name: str = "azure-search-openai-demo", endpoint: str = "http://localhost:4317"):
    # Service name is required for most backends
    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })

    traceProvider = TracerProvider(resource=resource)
    # Trick OLTP into thinking the httpx client is a requests session so that HTTP2 works
    processor = BatchSpanProcessor(OTLPGRPCSpanExporter(endpoint=endpoint, insecure=True))
    traceProvider.add_span_processor(processor)
    trace.set_tracer_provider(traceProvider)

    reader = PeriodicExportingMetricReader(
        OTLPGRPCMetricExporter(endpoint=endpoint, insecure=True)
    )
    meterProvider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meterProvider)
