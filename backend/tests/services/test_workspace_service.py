"""Unit tests for WorkspaceService multi-tenant management and RBAC."""

from uuid import uuid4

import pytest
from sqlmodel import Session

from app.schemas.workspace_api import (
    WorkspaceCreateRequest,
    WorkspaceMemberAddRequest,
    WorkspaceRole,
    WorkspaceUpdateRequest,
)
from app.services.workspace_service import WorkspaceService


def test_get_default_workspace_seeds_when_empty(db_session: Session) -> None:
    """Verify that get_default_workspace auto-bootstraps the default workspace and admin member."""
    service = WorkspaceService(session=db_session)
    default_ws = service.get_default_workspace()

    assert default_ws is not None
    assert default_ws.name == "Default Workspace"
    assert default_ws.slug == "default"
    assert default_ws.is_default is True
    assert default_ws.member_count == 1

    # Verify admin member registered
    members = service.list_members(default_ws.workspace_id)
    assert len(members) == 1
    assert members[0].user_email == "admin@example.com"
    assert members[0].role == WorkspaceRole.ADMIN


def test_create_and_list_workspaces(db_session: Session) -> None:
    """Verify creating a custom workspace and listing all workspaces."""
    service = WorkspaceService(session=db_session)

    # Bootstrap default
    service.get_default_workspace()

    req = WorkspaceCreateRequest(
        name="Support Swarm Agents",
        description="Customer support automated agents",
        is_default=False,
    )
    created = service.create_workspace(req, creator_email="lead@example.com")

    assert created.name == "Support Swarm Agents"
    assert created.slug == "support-swarm-agents"
    assert created.member_count == 1

    all_workspaces = service.list_workspaces()
    assert len(all_workspaces) >= 2


def test_update_and_delete_workspace(db_session: Session) -> None:
    """Verify updating metadata and deleting a non-default workspace."""
    service = WorkspaceService(session=db_session)
    default_ws = service.get_default_workspace()

    # Attempt to delete default workspace raises ValueError
    with pytest.raises(ValueError, match="Cannot delete the default"):
        service.delete_workspace(default_ws.workspace_id)

    # Create temporary workspace
    temp = service.create_workspace(WorkspaceCreateRequest(name="Temporary Testing WS"))
    assert temp is not None

    # Update workspace
    updated = service.update_workspace(
        temp.workspace_id,
        WorkspaceUpdateRequest(description="Updated description"),
    )
    assert updated is not None
    assert updated.description == "Updated description"

    # Delete workspace
    assert service.delete_workspace(temp.workspace_id) is True
    assert service.get_workspace(temp.workspace_id) is None


def test_workspace_membership_and_rbac(db_session: Session) -> None:
    """Verify adding members, updating roles, and removing membership."""
    service = WorkspaceService(session=db_session)
    ws = service.get_default_workspace()

    # Add engineer
    member = service.add_member(
        ws.workspace_id,
        WorkspaceMemberAddRequest(
            user_email="engineer@example.com",
            role=WorkspaceRole.ENGINEER,
        ),
    )
    assert member.user_email == "engineer@example.com"
    assert member.role == WorkspaceRole.ENGINEER

    # Update role to VIEWER
    updated_member = service.add_member(
        ws.workspace_id,
        WorkspaceMemberAddRequest(
            user_email="engineer@example.com",
            role=WorkspaceRole.VIEWER,
        ),
    )
    assert updated_member.role == WorkspaceRole.VIEWER

    # List members
    members = service.list_members(ws.workspace_id)
    assert len(members) == 2

    # Remove member
    assert service.remove_member(ws.workspace_id, member.member_id) is True
    members_after = service.list_members(ws.workspace_id)
    assert len(members_after) == 1


def test_workspace_audit_logs(db_session: Session) -> None:
    """Verify audit log tracking for workspace governance actions."""
    service = WorkspaceService(session=db_session)
    ws = service.create_workspace(WorkspaceCreateRequest(name="Audited Workspace"))

    logs = service.list_audit_logs(ws.workspace_id)
    assert len(logs) >= 1
    assert logs[0].action == "WORKSPACE_CREATED"
    assert logs[0].resource_type == "WORKSPACE"


def test_workspace_not_found_handling(db_session: Session) -> None:
    """Verify KeyError on adding member to nonexistent workspace."""
    service = WorkspaceService(session=db_session)
    with pytest.raises(KeyError, match="not found"):
        service.add_member(
            uuid4(),
            WorkspaceMemberAddRequest(user_email="ghost@example.com"),
        )
