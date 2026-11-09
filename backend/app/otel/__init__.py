"""OpenTelemetry to Canonical Agent Trace Schema (CATS) connector and native collector package."""

from app.otel.collector_receiver import CollectorBatchResult, CollectorReceiver
from app.otel.collector_validation import (
    BackpressureExceededError,
    BackpressureMonitor,
    CollectorRateLimiter,
    PayloadValidationError,
    RateLimitExceededError,
    global_backpressure_monitor,
    global_rate_limiter,
    validate_collector_payload,
)
from app.otel.otel_adapter import DetectedFramework, FrameworkDetector
from app.otel.otel_models import (
    OTELEvent,
    OTELIngestResponse,
    OTELLink,
    OTELResource,
    OTELSpan,
    OTELStatus,
    OTELTrace,
)
from app.otel.otel_parser import parse_otel_payload, validate_otel_trace
from app.otel.otel_to_cats import translate_otel_trace_to_cats
from app.otel.otlp_grpc_receiver import OTLPTraceServiceServicer, create_otlp_grpc_server
from app.otel.otlp_http_receiver import OTLPCollectorResponse

__all__ = [
    "BackpressureExceededError",
    "BackpressureMonitor",
    "CollectorBatchResult",
    "CollectorRateLimiter",
    "CollectorReceiver",
    "DetectedFramework",
    "FrameworkDetector",
    "OTELEvent",
    "OTELIngestResponse",
    "OTELLink",
    "OTELResource",
    "OTELSpan",
    "OTELStatus",
    "OTELTrace",
    "OTLPCollectorResponse",
    "OTLPTraceServiceServicer",
    "PayloadValidationError",
    "RateLimitExceededError",
    "create_otlp_grpc_server",
    "global_backpressure_monitor",
    "global_rate_limiter",
    "parse_otel_payload",
    "translate_otel_trace_to_cats",
    "validate_collector_payload",
    "validate_otel_trace",
]
