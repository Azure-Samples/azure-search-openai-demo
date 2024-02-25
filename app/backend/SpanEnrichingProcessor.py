# Import the SpanProcessor class from the opentelemetry.sdk.trace module.
from opentelemetry.sdk.trace import SpanProcessor

class SpanEnrichingProcessorCB(SpanProcessor):

    def on_end(self, span):
        # Prefix the span name with the string "Updated-".
        span._name = "Updated-" + span.name
        span._attributes["enduser.id"] = "<User ID>"