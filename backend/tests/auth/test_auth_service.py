"""Unit tests for AuthService: key generation, hashing, expiration, and audit logging."""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.db.entities import APIKeyRecord
from app.schemas.auth_api import APIKeyCreateRequest, ServiceAccountRole
from app.services.auth_service import AuthService, generate_api_key, hash_api_key
from app.services.workspace_service import WorkspaceService


def test_key_generation_and_hashing_contract() -> None:
    raw_key, prefix, hashed = generate_api_key()
    assert raw_key.startswith("aep_")
    assert len(raw_key) == 44
    assert prefix.startswith("aep_")
    assert prefix.endswith("...")
    assert len(hashed) == 64  # SHA-256 is 64 hex characters
    assert hash_api_key(raw_key) == hashed


def test_create_api_key_creates_record_and_audit_logs(db_session: Session) -> None:
    service = AuthService(db_session)
    ws_service = WorkspaceService(db_session)
    default_ws = ws_service.get_default_workspace()

    req = APIKeyCreateRequest(
        name="github-ci-runner",
        workspace_id=default_ws.workspace_id,
        role=ServiceAccountRole.ENGINEER,
        created_by="lead_devops@example.com",
        expires_in_days=30,
    )
    res = service.create_api_key(req, actor_email="lead_devops@example.com")

    assert res.key_id is not None
    assert res.name == "github-ci-runner"
    assert res.raw_key.startswith("aep_")
    assert res.role == ServiceAccountRole.ENGINEER
    assert res.expires_at is not None
    assert res.expires_at > datetime.now(UTC)

    # Check persistence (plaintext not in DB!)
    db_record = db_session.get(APIKeyRecord, res.key_id)
    assert db_record is not None
    assert db_record.hashed_key != res.raw_key
    assert db_record.hashed_key == hash_api_key(res.raw_key)

    # Check audit events: api_key_created & service_account_created
    logs = ws_service.list_audit_logs(default_ws.workspace_id)
    actions = [log.action for log in logs]
    assert "api_key_created" in actions
    assert "service_account_created" in actions


def test_authenticate_valid_key_updates_usage_and_logs(db_session: Session) -> None:
    service = AuthService(db_session)
    req = APIKeyCreateRequest(
        name="k8s-agent-daemon",
        role=ServiceAccountRole.ADMIN,
        created_by="admin@example.com",
    )
    created = service.create_api_key(req)

    # 1. Authenticate with valid key
    auth_record = service.authenticate_key(created.raw_key)
    assert auth_record is not None
    assert auth_record.name == "k8s-agent-daemon"
    assert auth_record.last_used_at is not None

    # Check api_key_used audit event
    ws_service = WorkspaceService(db_session)
    logs = ws_service.list_audit_logs(created.workspace_id)
    assert any(log.action == "api_key_used" for log in logs)


def test_authenticate_expired_key_returns_none(db_session: Session) -> None:
    service = AuthService(db_session)
    ws_service = WorkspaceService(db_session)
    default_ws = ws_service.get_default_workspace()

    raw_key, prefix, hashed = generate_api_key()
    expired_record = APIKeyRecord(
        workspace_id=default_ws.workspace_id,
        name="expired-key",
        hashed_key=hashed,
        key_prefix=prefix,
        role="ENGINEER",
        created_by="system",
        created_at=datetime.now(UTC) - timedelta(days=10),
        expires_at=datetime.now(UTC) - timedelta(days=1),  # Expired yesterday
        is_active=True,
    )
    db_session.add(expired_record)
    db_session.commit()

    assert service.authenticate_key(raw_key) is None


def test_revoke_api_key_deactivates_and_logs(db_session: Session) -> None:
    service = AuthService(db_session)
    req = APIKeyCreateRequest(name="temporary-token", role=ServiceAccountRole.VIEWER)
    created = service.create_api_key(req)

    # Before revoke: can authenticate
    assert service.authenticate_key(created.raw_key) is not None

    # Revoke
    success = service.revoke_api_key(created.key_id, actor_email="security@example.com")
    assert success is True

    # After revoke: cannot authenticate
    assert service.authenticate_key(created.raw_key) is None

    # Revoking again returns False
    assert service.revoke_api_key(created.key_id) is False

    # Check api_key_revoked audit event
    ws_service = WorkspaceService(db_session)
    logs = ws_service.list_audit_logs(created.workspace_id)
    assert any(log.action == "api_key_revoked" for log in logs)


def test_authenticate_malformed_and_unknown_keys(db_session: Session) -> None:
    service = AuthService(db_session)
    assert service.authenticate_key("") is None
    assert service.authenticate_key("invalid_prefix_123") is None
    assert service.authenticate_key("aep_0000000000000000000000000000000000000000") is None
