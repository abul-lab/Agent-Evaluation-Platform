"""Security hardening regression tests: authentication, RBAC matrix, webhook masking, CORS."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlmodel import Session

from app.core.config import Settings, settings
from app.core.webhook_security import mask_webhook_url, scrub_webhook_url, validate_webhook_url
from app.schemas.auth_api import APIKeyCreateRequest, ServiceAccountRole
from app.services.auth_service import AuthService

API = "/api/v1"


def _issue_key(session: Session, role: ServiceAccountRole) -> str:
    return (
        AuthService(session)
        .create_api_key(APIKeyCreateRequest(name=f"hardening-{role.value.lower()}", role=role))
        .raw_key
    )


def _bearer(raw_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {raw_key}"}


@pytest.fixture
def viewer_key(session: Session) -> str:
    return _issue_key(session, ServiceAccountRole.VIEWER)


@pytest.fixture
def engineer_key(session: Session) -> str:
    return _issue_key(session, ServiceAccountRole.ENGINEER)


# --------------------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------------------


def test_health_remains_public(anon_client: TestClient) -> None:
    assert anon_client.get("/health").status_code == 200
    assert anon_client.get(f"{API}/health").status_code == 200


def test_anonymous_read_rejected_when_not_in_development(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "ALLOW_ANONYMOUS_VIEWER", True)
    assert anon_client.get(f"{API}/traces").status_code == 401


def test_anonymous_read_rejected_in_development_without_opt_in(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "ALLOW_ANONYMOUS_VIEWER", False)
    assert anon_client.get(f"{API}/traces").status_code == 401


def test_anonymous_development_access_is_read_only(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "ALLOW_ANONYMOUS_VIEWER", True)

    read = anon_client.get(f"{API}/traces")
    assert read.status_code == 200

    identity = anon_client.get(f"{API}/auth/verify")
    assert identity.status_code == 200
    assert identity.json()["is_authenticated"] is False
    assert identity.json()["role"] == "VIEWER"

    write = anon_client.post(f"{API}/workspaces", json={"name": "x", "slug": "x-anon"})
    assert write.status_code == 401


def test_invalid_key_is_rejected_even_in_development(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "ALLOW_ANONYMOUS_VIEWER", True)
    res = anon_client.get(f"{API}/traces", headers={"Authorization": "Bearer aep_nope"})
    assert res.status_code == 401


# --------------------------------------------------------------------------------------
# Authorization: every mutating route requires an authenticated identity
# --------------------------------------------------------------------------------------

MUTATING_ROUTES = [
    ("POST", f"{API}/auth/api-keys", {"name": "x"}),
    ("DELETE", f"{API}/auth/api-keys/{uuid.uuid4()}", None),
    ("POST", f"{API}/traces/upload", {}),
    ("POST", f"{API}/traces/validate", {}),
    ("POST", f"{API}/otel/ingest", {}),
    ("POST", f"{API}/otel/translate", {}),
    ("POST", f"{API}/otel/collector", {}),
    ("POST", "/v1/traces", {}),
    ("POST", f"{API}/evaluations/run", {}),
    ("POST", f"{API}/benchmarks/compare", {}),
    ("POST", f"{API}/regressions/check", {}),
    ("POST", f"{API}/policies", {}),
    ("PUT", f"{API}/policies/{uuid.uuid4()}", {}),
    ("DELETE", f"{API}/policies/{uuid.uuid4()}", None),
    ("POST", f"{API}/policies/{uuid.uuid4()}/audit/{uuid.uuid4()}", None),
    ("POST", f"{API}/workspaces", {"name": "x", "slug": "x"}),
    ("PUT", f"{API}/workspaces/{uuid.uuid4()}", {}),
    ("DELETE", f"{API}/workspaces/{uuid.uuid4()}", None),
    ("POST", f"{API}/workspaces/demo/seed", None),
    ("POST", f"{API}/workspaces/{uuid.uuid4()}/members", {}),
    ("DELETE", f"{API}/workspaces/{uuid.uuid4()}/members/{uuid.uuid4()}", None),
    ("POST", f"{API}/workspaces/{uuid.uuid4()}/notifications/channels", {}),
    ("PUT", f"{API}/workspaces/{uuid.uuid4()}/notifications/channels/{uuid.uuid4()}", {}),
    ("DELETE", f"{API}/workspaces/{uuid.uuid4()}/notifications/channels/{uuid.uuid4()}", None),
    ("POST", f"{API}/workspaces/{uuid.uuid4()}/notifications/channels/{uuid.uuid4()}/test", None),
]


@pytest.mark.parametrize(("method", "path", "body"), MUTATING_ROUTES)
def test_mutating_routes_reject_anonymous_callers(
    anon_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    # Even with anonymous development access enabled, writes must be refused.
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "ALLOW_ANONYMOUS_VIEWER", True)
    res = anon_client.request(method, path, json=body)
    assert res.status_code == 401, f"{method} {path} returned {res.status_code}"


def test_viewer_key_cannot_perform_engineer_or_admin_actions(
    anon_client: TestClient, viewer_key: str
) -> None:
    headers = _bearer(viewer_key)
    assert anon_client.get(f"{API}/traces", headers=headers).status_code == 200
    assert (
        anon_client.post(f"{API}/otel/translate", json={}, headers=headers).status_code == 403
    )
    assert (
        anon_client.post(
            f"{API}/policies",
            json={"name": "p", "rules": {}},
            headers=headers,
        ).status_code
        == 403
    )
    assert (
        anon_client.post(
            f"{API}/workspaces", json={"name": "w", "slug": "w-viewer"}, headers=headers
        ).status_code
        == 403
    )


def test_engineer_key_cannot_perform_admin_actions(
    anon_client: TestClient, engineer_key: str
) -> None:
    headers = _bearer(engineer_key)
    # Engineers may run validation/preview endpoints...
    res = anon_client.post(f"{API}/otel/translate", json={}, headers=headers)
    assert res.status_code not in (401, 403)
    # ...but not administer governance policy or workspaces.
    assert (
        anon_client.post(
            f"{API}/workspaces", json={"name": "w", "slug": "w-eng"}, headers=headers
        ).status_code
        == 403
    )
    assert (
        anon_client.post(f"{API}/workspaces/demo/seed", headers=headers).status_code == 403
    )
    assert (
        anon_client.delete(f"{API}/policies/{uuid.uuid4()}", headers=headers).status_code == 403
    )


# --------------------------------------------------------------------------------------
# Webhook protection
# --------------------------------------------------------------------------------------

SECRET_PATH = "/services/T00000/B00000/SECRETTOKEN123"
WEBHOOK = f"https://hooks.slack.com{SECRET_PATH}"


def _create_channel(client: TestClient, workspace_id: str, url: str) -> dict[str, Any]:
    res = client.post(
        f"{API}/workspaces/{workspace_id}/notifications/channels",
        json={"name": "ops", "channel_type": "SLACK", "webhook_url": url, "events": []},
    )
    assert res.status_code == 201, res.text
    body: dict[str, Any] = res.json()
    return body


def test_channel_responses_never_return_raw_webhook(client: TestClient) -> None:
    workspace_id = client.get(f"{API}/workspaces/default").json()["workspace_id"]
    created = _create_channel(client, workspace_id, WEBHOOK)

    assert "webhook_url" not in created
    assert created["webhook_url_masked"] == "https://hooks.slack.com/****"
    assert "SECRETTOKEN123" not in str(created)

    listed = client.get(f"{API}/workspaces/{workspace_id}/notifications/channels")
    assert listed.status_code == 200
    assert "SECRETTOKEN123" not in listed.text
    assert "webhook_url\"" not in listed.text


def test_channel_update_response_is_masked(client: TestClient) -> None:
    workspace_id = client.get(f"{API}/workspaces/default").json()["workspace_id"]
    created = _create_channel(client, workspace_id, WEBHOOK)
    updated = client.put(
        f"{API}/workspaces/{workspace_id}/notifications/channels/{created['channel_id']}",
        json={"name": "ops-2"},
    )
    assert updated.status_code == 200
    assert "SECRETTOKEN123" not in updated.text


@pytest.mark.parametrize(
    "url",
    [
        "http://hooks.slack.com/services/x",
        "https://user:pass@hooks.slack.com/services/x",
        "https://localhost/hook",
        "https://127.0.0.1/hook",
        "https://10.0.0.5/hook",
        "https://169.254.169.254/latest/meta-data",
        "ftp://example.com/hook",
    ],
)
def test_unsafe_webhook_destinations_are_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        validate_webhook_url(url)


def test_webhook_masking_and_error_scrubbing() -> None:
    assert mask_webhook_url(WEBHOOK) == "https://hooks.slack.com/****"
    scrubbed = scrub_webhook_url(f"Delivery failed: connect to {WEBHOOK} refused", WEBHOOK)
    assert "SECRETTOKEN123" not in (scrubbed or "")


# --------------------------------------------------------------------------------------
# CORS and configuration
# --------------------------------------------------------------------------------------


def test_cors_wildcard_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="development", CORS_ALLOWED_ORIGINS="*")


def test_production_requires_explicit_cors_origins() -> None:
    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production")


def test_production_accepts_explicit_origin_allowlist() -> None:
    cfg = Settings(
        ENVIRONMENT="production",
        CORS_ALLOWED_ORIGINS="https://app.example.com/, https://ops.example.com",
    )
    assert cfg.cors_origins == ["https://app.example.com", "https://ops.example.com"]


def test_development_defaults_to_local_frontend_origins() -> None:
    cfg = Settings(ENVIRONMENT="development")
    assert "http://localhost:3000" in cfg.cors_origins
    assert "*" not in cfg.cors_origins


def test_anonymous_access_requires_development_and_flag() -> None:
    assert Settings(ENVIRONMENT="development", ALLOW_ANONYMOUS_VIEWER=True).anonymous_access_enabled
    assert not Settings(
        ENVIRONMENT="production",
        CORS_ALLOWED_ORIGINS="https://a.example.com",
        ALLOW_ANONYMOUS_VIEWER=True,
    ).anonymous_access_enabled
    assert not Settings(ENVIRONMENT="development", ALLOW_ANONYMOUS_VIEWER=False).anonymous_access_enabled
