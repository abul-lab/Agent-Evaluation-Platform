"""OpenTelemetry OTLP/gRPC TraceService receiver."""

import json
import logging
from collections.abc import Callable
from concurrent import futures
from typing import Any

import grpc
from fastapi import HTTPException
from sqlmodel import Session

from app.auth.dependencies import ensure_collector_principal, resolve_principal
from app.otel.collector_receiver import CollectorBatchResult, CollectorReceiver
from app.otel.collector_validation import (
    BackpressureExceededError,
    PayloadValidationError,
    RateLimitExceededError,
    global_backpressure_monitor,
    global_rate_limiter,
)
from app.schemas.auth_api import AuthPrincipal

logger = logging.getLogger(__name__)

SERVICE_NAME = "opentelemetry.proto.collector.trace.v1.TraceService"
EXPORT_METHOD_NAME = "Export"


class OTLPTraceServiceServicer:
    """gRPC Servicer implementing opentelemetry.proto.collector.trace.v1.TraceService."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self.session_factory = session_factory

    def _extract_auth_from_metadata(
        self, session: Session, context: grpc.ServicerContext
    ) -> AuthPrincipal:
        """Extract credentials from gRPC metadata and resolve the ingesting principal.

        Anonymous calls abort with UNAUTHENTICATED; VIEWER keys abort with PERMISSION_DENIED.
        """
        metadata = dict(context.invocation_metadata())

        token: str | None = None
        for key, val in metadata.items():
            k_lower = key.lower()
            if k_lower == "authorization" and str(val).lower().startswith("bearer "):
                token = str(val)[7:].strip()
                break
            if k_lower in ("x-api-key", "api-key"):
                token = str(val).strip()
                break

        try:
            principal = resolve_principal(session, token)
            return ensure_collector_principal(principal)
        except HTTPException as exc:
            code = (
                grpc.StatusCode.PERMISSION_DENIED
                if exc.status_code == 403
                else grpc.StatusCode.UNAUTHENTICATED
            )
            context.abort(code, str(exc.detail))
            raise

    def _normalize_request_payload(self, request: Any) -> dict[str, Any] | list[dict[str, Any]]:
        """Normalize gRPC request payload from protobuf, JSON bytes, or dict."""
        if isinstance(request, (dict, list)):
            return request

        if isinstance(request, (bytes, bytearray)):
            try:
                parsed: dict[str, Any] | list[dict[str, Any]] = json.loads(request.decode("utf-8"))
                return parsed
            except Exception:
                pass

        if isinstance(request, str):
            loaded: dict[str, Any] | list[dict[str, Any]] = json.loads(request)
            return loaded

        # Handle protobuf-like objects with Dict-like or MessageToDict conversion
        if hasattr(request, "resource_spans") or hasattr(request, "resourceSpans"):
            # Try MessageToDict if google protobuf is used
            try:
                from google.protobuf.json_format import MessageToDict

                converted: dict[str, Any] = MessageToDict(request, preserving_proto_field_name=False)
                return converted
            except Exception:
                pass

        # Fallback to __dict__ if available
        if hasattr(request, "__dict__"):
            attrs: dict[str, Any] = request.__dict__
            return attrs

        raise PayloadValidationError(
            f"Cannot normalize gRPC request of type {type(request).__name__}"
        )

    def Export(self, request: Any, context: grpc.ServicerContext) -> dict[str, Any]:  # noqa: N802
        """Process gRPC Export call from OpenTelemetry Collector."""
        with self.session_factory() as session:
            principal = self._extract_auth_from_metadata(session, context)
            rate_key = str(principal.workspace_id or "default")

            # Rate Limiting
            try:
                global_rate_limiter.check_rate_limit(rate_key)
            except RateLimitExceededError as e:
                context.abort(
                    grpc.StatusCode.RESOURCE_EXHAUSTED,
                    f"Rate limit exceeded: {e}",
                )

            # Backpressure & concurrency monitoring
            try:
                with global_backpressure_monitor.track_request():
                    payload = self._normalize_request_payload(request)
                    receiver = CollectorReceiver(session)
                    batch_result: CollectorBatchResult = receiver.process_batch(
                        payload=payload,
                        workspace_id=principal.workspace_id,
                        auto_evaluate=True,
                    )
            except PayloadValidationError as e:
                context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"OTLP validation failed: {e}",
                )
            except BackpressureExceededError as e:
                context.abort(
                    grpc.StatusCode.RESOURCE_EXHAUSTED,
                    f"System overloaded: {e}",
                )
            except Exception as e:
                logger.error("Unhandled error in gRPC Export: %s", e)
                context.abort(
                    grpc.StatusCode.INTERNAL,
                    f"Collector processing error: {e}",
                )

            return {
                "partial_success": {
                    "rejected_spans": batch_result.rejected_spans,
                    "error_message": batch_result.error_message or "",
                },
                "traces_ingested": batch_result.traces_ingested,
                "spans_ingested": batch_result.spans_ingested,
                "trace_ids": batch_result.trace_ids,
                "evaluation_ids": batch_result.evaluation_ids,
                "workspace_id": batch_result.workspace_id,
            }


def create_otlp_grpc_server(
    session_factory: Callable[[], Session],
    host: str = "127.0.0.1",
    port: int = 4317,
    max_workers: int = 10,
) -> grpc.Server:
    """Create and configure a standard gRPC server hosting the OTLP TraceService."""
    servicer = OTLPTraceServiceServicer(session_factory)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))

    # Generic RPC method handler for TraceService/Export
    handler = grpc.unary_unary_rpc_method_handler(
        servicer.Export,
        request_deserializer=lambda x: json.loads(x.decode("utf-8")) if x else {},
        response_serializer=lambda x: json.dumps(x).encode("utf-8"),
    )

    generic_handler = grpc.method_handlers_generic_handler(
        SERVICE_NAME,
        {EXPORT_METHOD_NAME: handler},
    )
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_insecure_port(f"{host}:{port}")
    return server
