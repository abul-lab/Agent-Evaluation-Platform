"""Service layer for API key generation, verification, service account RBAC, and audit tracking."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlmodel import Session, col, select

from app.db.entities import APIKeyRecord, WorkspaceRecord
from app.schemas.auth_api import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyResponse,
    ServiceAccountRole,
)
from app.schemas.notification_api import NotificationEventType
from app.services.notification_service import NotificationEvent, NotificationService
from app.services.workspace_service import WorkspaceService


def hash_api_key(raw_key: str) -> str:
    """Compute SHA-256 cryptographic digest of raw plaintext API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Generate a secure cryptographic API key token, public prefix, and storage hash.

    Format: 'aep_' followed by 40 random hex characters.
    Prefix: 'aep_' followed by the first 8 hex characters and '...'.
    """
    token_hex = secrets.token_hex(20)
    raw_key = f"aep_{token_hex}"
    prefix = f"{raw_key[:12]}..."
    hashed_key = hash_api_key(raw_key)
    return raw_key, prefix, hashed_key


class AuthService:
    """Manages workspace-scoped API keys, service accounts, and authentication auditing."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.workspace_service = WorkspaceService(session)

    def create_api_key(
        self,
        request: APIKeyCreateRequest,
        actor_email: str = "system",
    ) -> APIKeyCreateResponse:
        """Issue a new scoped API key with SHA-256 storage and record audit logs."""
        target_ws_id = request.workspace_id
        if not target_ws_id:
            default_ws = self.workspace_service.get_default_workspace()
            target_ws_id = default_ws.workspace_id

        raw_key, prefix, hashed = generate_api_key()

        expires_at: datetime | None = None
        if request.expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=request.expires_in_days)

        record = APIKeyRecord(
            workspace_id=target_ws_id,
            name=request.name.strip(),
            hashed_key=hashed,
            key_prefix=prefix,
            role=request.role.value,
            created_by=request.created_by,
            created_at=datetime.now(UTC),
            expires_at=expires_at,
            is_active=True,
        )

        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)

        # Audit events: api_key_created & service_account_created
        self.workspace_service.log_activity(
            workspace_id=target_ws_id,
            actor_email=actor_email,
            action="api_key_created",
            resource_type="api_key",
            resource_id=str(record.key_id),
            details={
                "name": record.name,
                "role": record.role,
                "prefix": record.key_prefix,
                "expires_at": record.expires_at.isoformat() if record.expires_at else None,
            },
        )
        self.workspace_service.log_activity(
            workspace_id=target_ws_id,
            actor_email=actor_email,
            action="service_account_created",
            resource_type="service_account",
            resource_id=record.name,
            details={
                "role": record.role,
                "key_id": str(record.key_id),
            },
        )
        self.session.commit()

        # Dispatch API Key Created alert
        try:
            ws = self.session.get(WorkspaceRecord, target_ws_id)
            ws_name = ws.name if ws else "Default Workspace"
            notif_service = NotificationService(self.session)
            notif_service.dispatch_event(
                target_ws_id,
                NotificationEvent(
                    event_type=NotificationEventType.API_KEY_CREATED,
                    workspace_id=target_ws_id,
                    workspace_name=ws_name,
                    severity="INFO",
                    title=f"API Key Created: {record.name}",
                    reason=f"Service account key created with role {record.role}",
                    details={"key_id": str(record.key_id), "role": record.role},
                    link="http://localhost:3000/workspaces",
                ),
            )
        except Exception:
            pass

        return APIKeyCreateResponse(
            key_id=record.key_id,
            workspace_id=record.workspace_id,
            name=record.name,
            raw_key=raw_key,
            key_prefix=record.key_prefix,
            role=ServiceAccountRole(record.role),
            created_by=record.created_by,
            created_at=record.created_at,
            expires_at=record.expires_at,
            is_active=record.is_active,
        )

    def list_api_keys(self, workspace_id: UUID | None = None) -> list[APIKeyResponse]:
        """List active or all API keys for a workspace or across platform."""
        stmt = select(APIKeyRecord).order_by(col(APIKeyRecord.created_at).desc())
        if workspace_id:
            stmt = stmt.where(APIKeyRecord.workspace_id == workspace_id)

        records = self.session.exec(stmt).all()
        return [
            APIKeyResponse(
                key_id=r.key_id,
                workspace_id=r.workspace_id,
                name=r.name,
                key_prefix=r.key_prefix,
                role=ServiceAccountRole(r.role),
                created_by=r.created_by,
                created_at=r.created_at,
                expires_at=r.expires_at,
                last_used_at=r.last_used_at,
                is_active=r.is_active,
            )
            for r in records
        ]

    def revoke_api_key(self, key_id: UUID, actor_email: str = "system") -> bool:
        """Revoke an API key immediately and append an immutable audit log."""
        record = self.session.get(APIKeyRecord, key_id)
        if not record or not record.is_active:
            return False

        record.is_active = False
        self.session.add(record)

        self.workspace_service.log_activity(
            workspace_id=record.workspace_id,
            actor_email=actor_email,
            action="api_key_revoked",
            resource_type="api_key",
            resource_id=str(record.key_id),
            details={
                "name": record.name,
                "revoked_by": actor_email,
            },
        )
        self.session.commit()

        # Dispatch API Key Revoked alert
        try:
            ws = self.session.get(WorkspaceRecord, record.workspace_id)
            ws_name = ws.name if ws else "Default Workspace"
            notif_service = NotificationService(self.session)
            notif_service.dispatch_event(
                record.workspace_id,
                NotificationEvent(
                    event_type=NotificationEventType.API_KEY_REVOKED,
                    workspace_id=record.workspace_id,
                    workspace_name=ws_name,
                    severity="WARNING",
                    title=f"API Key Revoked: {record.name}",
                    reason="Secret service account key permanently revoked",
                    details={"key_id": str(key_id)},
                    link="http://localhost:3000/workspaces",
                ),
            )
        except Exception:
            pass

        return True

    def authenticate_key(self, raw_key: str) -> APIKeyRecord | None:
        """Authenticate an incoming Bearer token, check expiration, and update usage stats."""
        if not raw_key or not raw_key.startswith("aep_"):
            return None

        hashed = hash_api_key(raw_key)
        stmt = select(APIKeyRecord).where(
            APIKeyRecord.hashed_key == hashed,
            APIKeyRecord.is_active == True,  # noqa: E712
        )
        record = self.session.exec(stmt).first()
        if not record:
            return None

        now = datetime.now(UTC)
        if record.expires_at and now > record.expires_at.replace(
            tzinfo=UTC if record.expires_at.tzinfo is None else record.expires_at.tzinfo
        ):
            return None

        # Update last_used_at and log api_key_used
        record.last_used_at = now
        self.session.add(record)

        self.workspace_service.log_activity(
            workspace_id=record.workspace_id,
            actor_email=f"service_account:{record.name}",
            action="api_key_used",
            resource_type="api_key",
            resource_id=str(record.key_id),
            details={
                "name": record.name,
                "used_at": now.isoformat(),
            },
        )
        self.session.commit()
        return record
