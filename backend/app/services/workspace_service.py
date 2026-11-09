"""Service layer for multi-tenant workspace management, RBAC, and governance audit trails."""

import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlmodel import Session, col, select

from app.db.entities import (
    WorkspaceAuditLogRecord,
    WorkspaceMemberRecord,
    WorkspaceRecord,
)
from app.schemas.workspace_api import (
    WorkspaceAuditLogResponse,
    WorkspaceCreateRequest,
    WorkspaceMemberAddRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceRole,
    WorkspaceUpdateRequest,
)


def slugify(text: str) -> str:
    """Generate a clean URL-safe slug from display text."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug or "workspace"


class WorkspaceService:
    """Coordinates workspace boundaries, team memberships, and audit trails."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_response(self, record: WorkspaceRecord) -> WorkspaceResponse:
        """Map WorkspaceRecord entity to WorkspaceResponse schema with member count."""
        member_count = len(
            self.session.exec(
                select(WorkspaceMemberRecord).where(
                    WorkspaceMemberRecord.workspace_id == record.workspace_id
                )
            ).all()
        )
        return WorkspaceResponse(
            workspace_id=record.workspace_id,
            name=record.name,
            slug=record.slug,
            description=record.description,
            is_default=record.is_default,
            member_count=member_count,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def list_workspaces(self) -> list[WorkspaceResponse]:
        """List all registered workspaces."""
        records = self.session.exec(
            select(WorkspaceRecord).order_by(
                col(WorkspaceRecord.is_default).desc(),
                col(WorkspaceRecord.created_at).desc(),
            )
        ).all()
        return [self._to_response(rec) for rec in records]

    def get_workspace(self, workspace_id: UUID) -> WorkspaceResponse | None:
        """Fetch a specific workspace by ID."""
        record = self.session.get(WorkspaceRecord, workspace_id)
        if not record:
            return None
        return self._to_response(record)

    def get_default_workspace(self) -> WorkspaceResponse:
        """Retrieve the platform default workspace, auto-bootstrapping if not yet created."""
        record = self.session.exec(
            select(WorkspaceRecord).where(col(WorkspaceRecord.is_default).is_(True))
        ).first()

        if record:
            return self._to_response(record)

        # Bootstrap default workspace
        now = datetime.now(UTC)
        default_ws = WorkspaceRecord(
            name="Default Workspace",
            slug="default",
            description="Default organization workspace for agent evaluation traces and policies.",
            is_default=True,
            created_at=now,
            updated_at=now,
        )
        self.session.add(default_ws)
        self.session.commit()
        self.session.refresh(default_ws)

        # Register default workspace admin
        default_admin = WorkspaceMemberRecord(
            workspace_id=default_ws.workspace_id,
            user_email="admin@example.com",
            role=WorkspaceRole.ADMIN.value,
            joined_at=now,
        )
        self.session.add(default_admin)

        # Log workspace creation audit event
        self.log_activity(
            workspace_id=default_ws.workspace_id,
            actor_email="system@platform",
            action="WORKSPACE_INITIALIZED",
            resource_type="WORKSPACE",
            resource_id=str(default_ws.workspace_id),
            details={"name": default_ws.name, "is_default": True},
        )
        self.session.commit()

        return self._to_response(default_ws)

    def create_workspace(
        self,
        request: WorkspaceCreateRequest,
        creator_email: str = "admin@example.com",
    ) -> WorkspaceResponse:
        """Create and persist a new workspace and add creator as ADMIN."""
        if request.is_default:
            existing_defaults = self.session.exec(
                select(WorkspaceRecord).where(col(WorkspaceRecord.is_default).is_(True))
            ).all()
            for existing in existing_defaults:
                existing.is_default = False
                self.session.add(existing)

        slug = request.slug.strip().lower() if request.slug else slugify(request.name)

        now = datetime.now(UTC)
        record = WorkspaceRecord(
            name=request.name,
            slug=slug,
            description=request.description,
            is_default=request.is_default,
            created_at=now,
            updated_at=now,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)

        # Add creator as ADMIN
        admin_member = WorkspaceMemberRecord(
            workspace_id=record.workspace_id,
            user_email=creator_email,
            role=WorkspaceRole.ADMIN.value,
            joined_at=now,
        )
        self.session.add(admin_member)

        # Log audit entry
        self.log_activity(
            workspace_id=record.workspace_id,
            actor_email=creator_email,
            action="WORKSPACE_CREATED",
            resource_type="WORKSPACE",
            resource_id=str(record.workspace_id),
            details={"name": record.name, "slug": record.slug},
        )
        self.session.commit()

        return self._to_response(record)

    def update_workspace(
        self,
        workspace_id: UUID,
        request: WorkspaceUpdateRequest,
        actor_email: str = "admin@example.com",
    ) -> WorkspaceResponse | None:
        """Update an existing workspace's metadata."""
        record = self.session.get(WorkspaceRecord, workspace_id)
        if not record:
            return None

        if request.is_default:
            existing_defaults = self.session.exec(
                select(WorkspaceRecord).where(
                    col(WorkspaceRecord.is_default).is_(True),
                    WorkspaceRecord.workspace_id != workspace_id,
                )
            ).all()
            for existing in existing_defaults:
                existing.is_default = False
                self.session.add(existing)

        if request.name is not None:
            record.name = request.name
        if request.description is not None:
            record.description = request.description
        if request.is_default is not None:
            record.is_default = request.is_default

        record.updated_at = datetime.now(UTC)
        self.session.add(record)

        self.log_activity(
            workspace_id=record.workspace_id,
            actor_email=actor_email,
            action="WORKSPACE_UPDATED",
            resource_type="WORKSPACE",
            resource_id=str(record.workspace_id),
            details={"name": record.name},
        )
        self.session.commit()
        self.session.refresh(record)
        return self._to_response(record)

    def delete_workspace(
        self,
        workspace_id: UUID,
        actor_email: str = "admin@example.com",
    ) -> bool:
        """Delete a workspace and cascade delete members and audit logs."""
        record = self.session.get(WorkspaceRecord, workspace_id)
        if not record:
            return False
        if record.is_default:
            raise ValueError("Cannot delete the default platform workspace.")

        # Cascade delete members and logs
        members = self.session.exec(
            select(WorkspaceMemberRecord).where(WorkspaceMemberRecord.workspace_id == workspace_id)
        ).all()
        for m in members:
            self.session.delete(m)

        logs = self.session.exec(
            select(WorkspaceAuditLogRecord).where(
                WorkspaceAuditLogRecord.workspace_id == workspace_id
            )
        ).all()
        for log in logs:
            self.session.delete(log)

        self.session.delete(record)
        self.session.commit()
        return True

    def list_members(self, workspace_id: UUID) -> list[WorkspaceMemberResponse]:
        """List all team members registered in a workspace."""
        members = self.session.exec(
            select(WorkspaceMemberRecord)
            .where(WorkspaceMemberRecord.workspace_id == workspace_id)
            .order_by(col(WorkspaceMemberRecord.joined_at).asc())
        ).all()

        return [
            WorkspaceMemberResponse(
                member_id=m.member_id,
                workspace_id=m.workspace_id,
                user_email=m.user_email,
                role=WorkspaceRole(m.role),
                joined_at=m.joined_at,
            )
            for m in members
        ]

    def add_member(
        self,
        workspace_id: UUID,
        request: WorkspaceMemberAddRequest,
        actor_email: str = "admin@example.com",
    ) -> WorkspaceMemberResponse:
        """Add or update a team member's role in a workspace."""
        ws = self.session.get(WorkspaceRecord, workspace_id)
        if not ws:
            raise KeyError(f"Workspace '{workspace_id}' not found.")

        existing = self.session.exec(
            select(WorkspaceMemberRecord).where(
                WorkspaceMemberRecord.workspace_id == workspace_id,
                WorkspaceMemberRecord.user_email == request.user_email,
            )
        ).first()

        if existing:
            existing.role = request.role.value
            self.session.add(existing)
            self.log_activity(
                workspace_id=workspace_id,
                actor_email=actor_email,
                action="MEMBER_ROLE_UPDATED",
                resource_type="USER",
                resource_id=request.user_email,
                details={"role": request.role.value},
            )
            self.session.commit()
            self.session.refresh(existing)
            return WorkspaceMemberResponse(
                member_id=existing.member_id,
                workspace_id=existing.workspace_id,
                user_email=existing.user_email,
                role=WorkspaceRole(existing.role),
                joined_at=existing.joined_at,
            )

        new_member = WorkspaceMemberRecord(
            workspace_id=workspace_id,
            user_email=request.user_email,
            role=request.role.value,
            joined_at=datetime.now(UTC),
        )
        self.session.add(new_member)
        self.log_activity(
            workspace_id=workspace_id,
            actor_email=actor_email,
            action="MEMBER_ADDED",
            resource_type="USER",
            resource_id=request.user_email,
            details={"role": request.role.value},
        )
        self.session.commit()
        self.session.refresh(new_member)
        return WorkspaceMemberResponse(
            member_id=new_member.member_id,
            workspace_id=new_member.workspace_id,
            user_email=new_member.user_email,
            role=WorkspaceRole(new_member.role),
            joined_at=new_member.joined_at,
        )

    def remove_member(
        self,
        workspace_id: UUID,
        member_id: UUID,
        actor_email: str = "admin@example.com",
    ) -> bool:
        """Remove a member from a workspace."""
        member = self.session.get(WorkspaceMemberRecord, member_id)
        if not member or member.workspace_id != workspace_id:
            return False

        user_email = member.user_email
        self.session.delete(member)
        self.log_activity(
            workspace_id=workspace_id,
            actor_email=actor_email,
            action="MEMBER_REMOVED",
            resource_type="USER",
            resource_id=user_email,
            details={"member_id": str(member_id)},
        )
        self.session.commit()
        return True

    def list_audit_logs(
        self,
        workspace_id: UUID,
        limit: int = 50,
    ) -> list[WorkspaceAuditLogResponse]:
        """Fetch chronological audit trail entries for a workspace."""
        logs = self.session.exec(
            select(WorkspaceAuditLogRecord)
            .where(WorkspaceAuditLogRecord.workspace_id == workspace_id)
            .order_by(col(WorkspaceAuditLogRecord.created_at).desc())
            .limit(limit)
        ).all()

        return [
            WorkspaceAuditLogResponse(
                log_id=log.log_id,
                workspace_id=log.workspace_id,
                actor_email=log.actor_email,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                details=json.loads(log.details_json) if log.details_json else {},
                created_at=log.created_at,
            )
            for log in logs
        ]

    def log_activity(
        self,
        workspace_id: UUID,
        actor_email: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any],
    ) -> None:
        """Record an immutable governance activity event."""
        log = WorkspaceAuditLogRecord(
            workspace_id=workspace_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details_json=json.dumps(details),
            created_at=datetime.now(UTC),
        )
        self.session.add(log)
