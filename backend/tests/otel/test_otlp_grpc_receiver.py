"""Tests for OTLP/gRPC TraceService receiver."""

import json
import uuid
from typing import Any

import grpc
import pytest
from sqlmodel import Session

from app.db.entities import WorkspaceRecord
from app.db.session import engine
from app.otel.collector_validation import (
    BackpressureExceededError,
    RateLimitExceededError,
    global_backpressure_monitor,
    global_rate_limiter,
)
from app.otel.otlp_grpc_receiver import OTLPTraceServiceServicer, create_otlp_grpc_server
from app.schemas.auth_api import APIKeyCreateRequest, ServiceAccountRole
from app.services.auth_service import AuthService


class MockServicerContext:
    """Mock gRPC ServicerContext for testing servicer execution."""

    def __init__(self, metadata: list[tuple[str, str]] | None = None) -> None:
        self._metadata = metadata or []
        self.aborted = False
        self.code: grpc.StatusCode | None = None
        self.details: str | None = None

    def invocation_metadata(self) -> list[tuple[str, str]]:
        return self._metadata

    def abort(self, code: grpc.StatusCode, details: str) -> None:
        self.aborted = True
        self.code = code
        self.details = details
        raise grpc.RpcError(details)


def _admin_metadata(session: Session) -> list[tuple[str, str]]:
    """gRPC metadata carrying a freshly issued ADMIN key for the default workspace."""
    key = AuthService(session).create_api_key(
        APIKeyCreateRequest(name="grpc-test-admin", role=ServiceAccountRole.ADMIN)
    )
    return [("authorization", f"Bearer {key.raw_key}")]


@pytest.fixture(autouse=True)
def reset_limiters() -> None:
    """Reset rate limiter and backpressure state before each test."""
    global_rate_limiter.reset()
    global_backpressure_monitor.reset()


def _make_grpc_payload() -> dict[str, Any]:
    t_id = uuid.uuid4().hex
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "grpc-agent"}}]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": t_id,
                                "spanId": "grpc_s1",
                                "name": "grpc_step",
                                "kind": "INTERNAL",
                                "startTimeUnixNano": 1700000000_000_000_000,
                                "endTimeUnixNano": 1700000001_000_000_000,
                                "attributes": [
                                    {"key": "agent.role", "value": {"stringValue": "worker"}}
                                ],
                                "status": {"code": "OK"},
                            }
                        ]
                    }
                ],
            }
        ]
    }


def test_grpc_servicer_export_success(session: Session) -> None:
    """Test successful gRPC Export with default workspace."""
    servicer = OTLPTraceServiceServicer(session_factory=lambda: Session(engine))
    context = MockServicerContext(metadata=_admin_metadata(session))
    payload = _make_grpc_payload()

    resp = servicer.Export(payload, context)
    assert resp["traces_ingested"] == 1
    assert resp["spans_ingested"] == 1
    assert len(resp["trace_ids"]) == 1
    assert context.aborted is False


def test_grpc_servicer_export_with_bearer_token(session: Session) -> None:
    """Test gRPC Export authenticating via authorization Bearer metadata."""
    ws = WorkspaceRecord(name="gRPC WS", slug="grpc-ws")
    session.add(ws)
    session.commit()
    session.refresh(ws)
    expected_ws_id = str(ws.workspace_id)
    key_resp = AuthService(session).create_api_key(
        APIKeyCreateRequest(
            workspace_id=ws.workspace_id,
            name="gRPC Key",
            role=ServiceAccountRole.ENGINEER,
        )
    )

    servicer = OTLPTraceServiceServicer(session_factory=lambda: Session(engine))
    context = MockServicerContext(metadata=[("authorization", f"Bearer {key_resp.raw_key}")])
    payload = _make_grpc_payload()

    resp = servicer.Export(payload, context)
    assert resp["traces_ingested"] == 1
    assert resp["workspace_id"] == expected_ws_id


def test_grpc_servicer_export_with_x_api_key_metadata(session: Session) -> None:
    """Test gRPC Export authenticating via x-api-key metadata."""
    ws = WorkspaceRecord(name="gRPC Header WS", slug="grpc-hdr-ws")
    session.add(ws)
    session.commit()
    session.refresh(ws)
    expected_ws_id = str(ws.workspace_id)
    key_resp = AuthService(session).create_api_key(
        APIKeyCreateRequest(
            workspace_id=ws.workspace_id,
            name="gRPC Header Key",
            role=ServiceAccountRole.ADMIN,
        )
    )

    servicer = OTLPTraceServiceServicer(session_factory=lambda: Session(engine))
    context = MockServicerContext(metadata=[("x-api-key", key_resp.raw_key)])
    payload = _make_grpc_payload()

    resp = servicer.Export(payload, context)
    assert resp["traces_ingested"] == 1
    assert resp["workspace_id"] == expected_ws_id


def test_grpc_servicer_invalid_key_aborts_unauthenticated(session: Session) -> None:
    """Test gRPC Export aborts with UNAUTHENTICATED on invalid API key."""
    servicer = OTLPTraceServiceServicer(session_factory=lambda: Session(engine))
    context = MockServicerContext(metadata=[("authorization", "Bearer invalid_key")])

    with pytest.raises(grpc.RpcError):
        servicer.Export(_make_grpc_payload(), context)

    assert context.aborted is True
    assert context.code == grpc.StatusCode.UNAUTHENTICATED


def test_grpc_servicer_viewer_role_aborts_permission_denied(session: Session) -> None:
    """Test gRPC Export aborts with PERMISSION_DENIED on VIEWER role."""
    ws = WorkspaceRecord(name="gRPC Viewer WS", slug="grpc-v-ws")
    session.add(ws)
    session.commit()
    session.refresh(ws)
    key_resp = AuthService(session).create_api_key(
        APIKeyCreateRequest(
            workspace_id=ws.workspace_id,
            name="Viewer Key",
            role=ServiceAccountRole.VIEWER,
        )
    )

    servicer = OTLPTraceServiceServicer(session_factory=lambda: Session(engine))
    context = MockServicerContext(metadata=[("authorization", f"Bearer {key_resp.raw_key}")])

    with pytest.raises(grpc.RpcError):
        servicer.Export(_make_grpc_payload(), context)

    assert context.aborted is True
    assert context.code == grpc.StatusCode.PERMISSION_DENIED


def test_grpc_servicer_invalid_payload_aborts_invalid_argument(session: Session) -> None:
    """Test gRPC Export aborts with INVALID_ARGUMENT on invalid payload."""
    servicer = OTLPTraceServiceServicer(session_factory=lambda: Session(engine))
    context = MockServicerContext(metadata=_admin_metadata(session))

    with pytest.raises(grpc.RpcError):
        servicer.Export({"invalid": "data"}, context)

    assert context.aborted is True
    assert context.code == grpc.StatusCode.INVALID_ARGUMENT


def test_grpc_servicer_rate_limit_aborts_resource_exhausted(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test gRPC Export aborts with RESOURCE_EXHAUSTED when rate limited."""

    def mock_check_rate_limit(key: str) -> None:
        raise RateLimitExceededError("Rate limit exceeded")

    monkeypatch.setattr(global_rate_limiter, "check_rate_limit", mock_check_rate_limit)

    servicer = OTLPTraceServiceServicer(session_factory=lambda: Session(engine))
    context = MockServicerContext(metadata=_admin_metadata(session))

    with pytest.raises(grpc.RpcError):
        servicer.Export(_make_grpc_payload(), context)

    assert context.aborted is True
    assert context.code == grpc.StatusCode.RESOURCE_EXHAUSTED


def test_grpc_servicer_backpressure_aborts_resource_exhausted(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test gRPC Export aborts with RESOURCE_EXHAUSTED under backpressure."""

    def mock_track_request() -> None:
        raise BackpressureExceededError("System overloaded")

    monkeypatch.setattr(global_backpressure_monitor, "track_request", mock_track_request)

    servicer = OTLPTraceServiceServicer(session_factory=lambda: Session(engine))
    context = MockServicerContext(metadata=_admin_metadata(session))

    with pytest.raises(grpc.RpcError):
        servicer.Export(_make_grpc_payload(), context)

    assert context.aborted is True
    assert context.code == grpc.StatusCode.RESOURCE_EXHAUSTED


def test_grpc_server_in_process_network_channel(session: Session) -> None:
    """Test live in-process gRPC server and client channel communication."""
    server = create_otlp_grpc_server(
        session_factory=lambda: Session(engine), host="127.0.0.1", port=0
    )
    assigned_port = server.add_insecure_port("127.0.0.1:0")
    server.start()

    try:
        with grpc.insecure_channel(f"127.0.0.1:{assigned_port}") as channel:
            export_stub = channel.unary_unary(
                "/opentelemetry.proto.collector.trace.v1.TraceService/Export",
                request_serializer=lambda x: json.dumps(x).encode("utf-8"),
                response_deserializer=lambda x: json.loads(x.decode("utf-8")),
            )
            payload = _make_grpc_payload()
            response = export_stub(payload, metadata=_admin_metadata(session))
            assert response["traces_ingested"] == 1
            assert response["spans_ingested"] == 1
    finally:
        server.stop(grace=None)


def test_grpc_servicer_request_normalization_formats(session: Session) -> None:
    """Test gRPC Export normalizes JSON string, bytes, and custom object payloads."""
    servicer = OTLPTraceServiceServicer(session_factory=lambda: Session(engine))
    context = MockServicerContext(metadata=_admin_metadata(session))
    payload = _make_grpc_payload()

    # JSON string
    str_payload = json.dumps(payload)
    res_str = servicer.Export(str_payload, context)
    assert res_str["traces_ingested"] == 1

    # Bytes
    bytes_payload = json.dumps(payload).encode("utf-8")
    res_bytes = servicer.Export(bytes_payload, context)
    assert res_bytes["traces_ingested"] == 1

    # Object with __dict__
    class CustomObj:
        def __init__(self, data: dict[str, Any]) -> None:
            self.resourceSpans = data["resourceSpans"]

    obj_payload = CustomObj(payload)
    res_obj = servicer.Export(obj_payload, context)
    assert res_obj["traces_ingested"] == 1


def test_grpc_servicer_anonymous_aborts_unauthenticated(session: Session) -> None:
    """Anonymous gRPC exports are rejected in every environment outside development opt-in."""
    servicer = OTLPTraceServiceServicer(session_factory=lambda: Session(engine))
    context = MockServicerContext()

    with pytest.raises(grpc.RpcError):
        servicer.Export(_make_grpc_payload(), context)

    assert context.aborted is True
    assert context.code == grpc.StatusCode.UNAUTHENTICATED
