"""Integration tests for Authentication, Service Accounts, and Scoped RBAC permissions."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.schemas.auth_api import APIKeyCreateRequest, ServiceAccountRole
from app.services.auth_service import AuthService
from app.services.workspace_service import WorkspaceService

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "fixtures"


@pytest.fixture
def auth_tokens(db_session: Session) -> dict[str, str]:
    """Create test API keys for ADMIN, ENGINEER, and VIEWER service accounts."""
    service = AuthService(db_session)
    ws = WorkspaceService(db_session).get_default_workspace()

    admin_res = service.create_api_key(
        APIKeyCreateRequest(
            name="admin-ci", workspace_id=ws.workspace_id, role=ServiceAccountRole.ADMIN
        )
    )
    eng_res = service.create_api_key(
        APIKeyCreateRequest(
            name="engineer-ci", workspace_id=ws.workspace_id, role=ServiceAccountRole.ENGINEER
        )
    )
    viewer_res = service.create_api_key(
        APIKeyCreateRequest(
            name="viewer-dashboard", workspace_id=ws.workspace_id, role=ServiceAccountRole.VIEWER
        )
    )

    return {
        "admin": admin_res.raw_key,
        "engineer": eng_res.raw_key,
        "viewer": viewer_res.raw_key,
        "admin_key_id": str(admin_res.key_id),
        "eng_key_id": str(eng_res.key_id),
        "viewer_key_id": str(viewer_res.key_id),
        "workspace_id": str(ws.workspace_id),
    }


def test_auth_verify_endpoint(auth_tokens: dict[str, str]) -> None:
    client = TestClient(app)

    # 1. Verify with Bearer token
    res = client.get(
        "/api/v1/auth/verify",
        headers={"Authorization": f"Bearer {auth_tokens['admin']}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_authenticated"] is True
    assert data["role"] == "ADMIN"
    assert data["name"] == "admin-ci"
    assert data["is_service_account"] is True

    # 2. Anonymous callers are rejected when anonymous access is not enabled
    res_anon = client.get("/api/v1/auth/verify")
    assert res_anon.status_code == 401


def test_invalid_bearer_token_returns_401() -> None:
    client = TestClient(app)

    res = client.get(
        "/api/v1/auth/verify",
        headers={"Authorization": "Bearer aep_invalid_token_9999999999"},
    )
    assert res.status_code == 401
    assert "Invalid, expired, or revoked API key" in res.json()["detail"]


def test_create_list_and_revoke_api_keys(auth_tokens: dict[str, str]) -> None:
    client = TestClient(app)
    admin_headers = {"Authorization": f"Bearer {auth_tokens['admin']}"}

    # 1. Create API key as ADMIN
    create_payload = {
        "name": "jenkins-pipeline",
        "workspace_id": auth_tokens["workspace_id"],
        "role": "ENGINEER",
        "expires_in_days": 90,
    }
    create_res = client.post("/api/v1/auth/api-keys", json=create_payload, headers=admin_headers)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert "raw_key" in created_data
    assert created_data["raw_key"].startswith("aep_")
    new_key_id = created_data["key_id"]
    new_raw_key = created_data["raw_key"]

    # 2. List API keys
    list_res = client.get("/api/v1/auth/api-keys", headers=admin_headers)
    assert list_res.status_code == 200
    keys = list_res.json()
    assert any(k["key_id"] == new_key_id for k in keys)

    # 3. New key can authenticate
    verify_new = client.get(
        "/api/v1/auth/verify", headers={"Authorization": f"Bearer {new_raw_key}"}
    )
    assert verify_new.status_code == 200
    assert verify_new.json()["role"] == "ENGINEER"

    # 4. Revoke API key as ADMIN
    del_res = client.delete(f"/api/v1/auth/api-keys/{new_key_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["revoked"] is True

    # 5. Revoked key now fails authentication
    verify_revoked = client.get(
        "/api/v1/auth/verify", headers={"Authorization": f"Bearer {new_raw_key}"}
    )
    assert verify_revoked.status_code == 401


def test_role_permission_matrix_enforcement(auth_tokens: dict[str, str]) -> None:
    client = TestClient(app)
    eng_headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    viewer_headers = {"Authorization": f"Bearer {auth_tokens['viewer']}"}

    # A. ENGINEER role cannot create or revoke keys (requires ADMIN)
    create_res = client.post(
        "/api/v1/auth/api-keys",
        json={"name": "illegal-key", "role": "VIEWER"},
        headers=eng_headers,
    )
    assert create_res.status_code == 403
    assert "Insufficient permissions" in create_res.json()["detail"]

    del_res = client.delete(
        f"/api/v1/auth/api-keys/{auth_tokens['viewer_key_id']}",
        headers=eng_headers,
    )
    assert del_res.status_code == 403

    # B. VIEWER role cannot upload traces (requires ENGINEER or ADMIN)
    with open(FIXTURES_DIR / "clean_success_trace.json", encoding="utf-8") as f:
        trace_payload = json.load(f)

    upload_as_viewer = client.post(
        "/api/v1/traces/upload", json=trace_payload, headers=viewer_headers
    )
    assert upload_as_viewer.status_code == 403

    # C. ENGINEER role CAN upload traces
    upload_as_eng = client.post("/api/v1/traces/upload", json=trace_payload, headers=eng_headers)
    assert upload_as_eng.status_code == 201
    trace_id = upload_as_eng.json()["trace_id"]

    # D. VIEWER cannot run evaluations, but ENGINEER CAN run evaluations
    eval_as_viewer = client.post(
        "/api/v1/evaluations/run",
        json={"trace_id": trace_id},
        headers=viewer_headers,
    )
    assert eval_as_viewer.status_code == 403

    eval_as_eng = client.post(
        "/api/v1/evaluations/run",
        json={"trace_id": trace_id},
        headers=eng_headers,
    )
    assert eval_as_eng.status_code == 200
    assert eval_as_eng.json()["evaluation_id"] is not None

    # E. VIEWER CAN read traces, analytics, benchmarks (Read-Only)
    get_traces = client.get("/api/v1/traces", headers=viewer_headers)
    assert get_traces.status_code == 200

    get_analytics = client.get("/api/v1/analytics/trends", headers=viewer_headers)
    assert get_analytics.status_code == 200


def test_otel_ingest_with_bearer_authentication(auth_tokens: dict[str, str]) -> None:
    client = TestClient(app)
    eng_headers = {"Authorization": f"Bearer {auth_tokens['engineer']}"}
    viewer_headers = {"Authorization": f"Bearer {auth_tokens['viewer']}"}

    with open(FIXTURES_DIR / "otel" / "langgraph_trace.json", encoding="utf-8") as f:
        otel_payload = json.load(f)

    # 1. VIEWER token is rejected on OTEL ingest
    res_viewer = client.post("/api/v1/otel/ingest", json=otel_payload, headers=viewer_headers)
    assert res_viewer.status_code == 403

    # 2. ENGINEER token successfully ingests and translates OTEL trace
    res_eng = client.post("/api/v1/otel/ingest", json=otel_payload, headers=eng_headers)
    assert res_eng.status_code == 201
    data = res_eng.json()
    assert data["detected_framework"] == "LANGGRAPH"
    assert data["step_count"] > 0
    assert data["stored"] is True
