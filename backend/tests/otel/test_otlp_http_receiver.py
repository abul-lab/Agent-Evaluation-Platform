"""Tests for OTLP/HTTP collector endpoints."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.entities import WorkspaceRecord
from app.otel.collector_validation import (
    BackpressureExceededError,
    RateLimitExceededError,
    global_backpressure_monitor,
    global_rate_limiter,
)
from app.schemas.auth_api import APIKeyCreateRequest, ServiceAccountRole
from app.services.auth_service import AuthService


@pytest.fixture(autouse=True)
def reset_limiters() -> None:
    """Reset rate limiter and backpressure state before each test."""
    global_rate_limiter.reset()
    global_backpressure_monitor.reset()


def _make_payload() -> dict[str, Any]:
    t_id = uuid.uuid4().hex
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "my-agent"}}]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": t_id,
                                "spanId": "s1",
                                "name": "step_1",
                                "kind": "INTERNAL",
                                "startTimeUnixNano": 1700000000_000_000_000,
                                "endTimeUnixNano": 1700000001_000_000_000,
                                "attributes": [
                                    {"key": "tool.name", "value": {"stringValue": "calculator"}}
                                ],
                                "status": {"code": "OK"},
                            }
                        ]
                    }
                ],
            }
        ]
    }


def test_collector_endpoint_unauthenticated_default_workspace(client: TestClient) -> None:
    """Test collector endpoint works without auth header in backward-compatible mode."""
    payload = _make_payload()
    resp = client.post("/api/v1/otel/collector", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracesIngested"] == 1
    assert data["spansIngested"] == 1
    assert len(data["traceIds"]) == 1
    assert data["workspaceId"] is not None


def test_collector_endpoint_with_bearer_api_key(client: TestClient, session: Session) -> None:
    """Test collector endpoint with valid Authorization Bearer key."""
    ws = WorkspaceRecord(name="OTEL Collector WS", slug="otel-col-ws")
    session.add(ws)
    session.commit()
    session.refresh(ws)
    key_resp = AuthService(session).create_api_key(
        APIKeyCreateRequest(
            workspace_id=ws.workspace_id,
            name="Collector Token",
            role=ServiceAccountRole.ENGINEER,
        )
    )

    payload = _make_payload()
    resp = client.post(
        "/api/v1/otel/collector",
        json=payload,
        headers={"Authorization": f"Bearer {key_resp.raw_key}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracesIngested"] == 1
    assert data["workspaceId"] == str(ws.workspace_id)


def test_collector_endpoint_with_x_api_key_header(anon_client: TestClient, session: Session) -> None:
    """Test collector endpoint with x-api-key header."""
    ws = WorkspaceRecord(name="Header Key WS", slug="header-key-ws")
    session.add(ws)
    session.commit()
    session.refresh(ws)
    key_resp = AuthService(session).create_api_key(
        APIKeyCreateRequest(
            workspace_id=ws.workspace_id,
            name="X-API-Key Token",
            role=ServiceAccountRole.ADMIN,
        )
    )

    payload = _make_payload()
    resp = anon_client.post(
        "/api/v1/otel/collector",
        json=payload,
        headers={"x-api-key": key_resp.raw_key},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracesIngested"] == 1
    assert data["workspaceId"] == str(ws.workspace_id)


def test_collector_endpoint_invalid_token(client: TestClient) -> None:
    """Test collector endpoint rejects invalid Bearer token with 401."""
    resp = client.post(
        "/api/v1/otel/collector",
        json=_make_payload(),
        headers={"Authorization": "Bearer aep_live_invalidkey123456789"},
    )
    assert resp.status_code == 401
    assert "Invalid, expired, or revoked API key" in resp.json()["detail"]


def test_collector_endpoint_viewer_role_rejected(client: TestClient, session: Session) -> None:
    """Test collector endpoint rejects VIEWER service accounts with 403."""
    ws = WorkspaceRecord(name="Viewer WS", slug="viewer-ws")
    session.add(ws)
    session.commit()
    session.refresh(ws)
    key_resp = AuthService(session).create_api_key(
        APIKeyCreateRequest(
            workspace_id=ws.workspace_id,
            name="Viewer Token",
            role=ServiceAccountRole.VIEWER,
        )
    )

    resp = client.post(
        "/api/v1/otel/collector",
        json=_make_payload(),
        headers={"Authorization": f"Bearer {key_resp.raw_key}"},
    )
    assert resp.status_code == 403
    assert "cannot ingest" in resp.json()["detail"]


def test_collector_endpoint_rate_limit_exceeded(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test collector endpoint returns 429 and Retry-After header when rate limited."""

    def mock_check_rate_limit(key: str) -> None:
        raise RateLimitExceededError(
            "Rate limit exceeded for workspace. Try again in 2.0s", retry_after=2.0
        )

    monkeypatch.setattr(global_rate_limiter, "check_rate_limit", mock_check_rate_limit)

    resp = client.post("/api/v1/otel/collector", json=_make_payload())
    assert resp.status_code == 429
    assert resp.headers.get("retry-after") == "2"
    assert "Rate limit exceeded" in resp.json()["detail"]


def test_collector_endpoint_backpressure_exceeded(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test collector endpoint returns 503 and Retry-After when backpressure is triggered."""

    def mock_check_payload_size(size: int) -> None:
        raise BackpressureExceededError("Server overloaded", retry_after=3.0)

    monkeypatch.setattr(global_backpressure_monitor, "check_payload_size", mock_check_payload_size)

    resp = client.post("/api/v1/otel/collector", json=_make_payload())
    assert resp.status_code == 503
    assert resp.headers.get("retry-after") == "3"


def test_collector_endpoint_invalid_payload_returns_422(client: TestClient) -> None:
    """Test collector endpoint returns 422 on invalid payload."""
    resp = client.post("/api/v1/otel/collector", json={"unsupported": "data"})
    assert resp.status_code == 422


def test_standard_v1_traces_endpoint_alias(client: TestClient) -> None:
    """Test /v1/traces standard OTLP endpoint alias functions correctly."""
    payload = _make_payload()
    resp = client.post("/v1/traces", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracesIngested"] == 1
    assert data["spansIngested"] == 1
