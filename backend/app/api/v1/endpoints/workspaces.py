"""API endpoints for workspace management, RBAC team membership, and audit trails."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.auth.dependencies import RequireAdmin
from app.db.session import get_session
from app.schemas.workspace_api import (
    DemoSeedResponse,
    WorkspaceAuditLogResponse,
    WorkspaceCreateRequest,
    WorkspaceMemberAddRequest,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)
from app.services.demo_service import DemoService
from app.services.workspace_service import WorkspaceService

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


@router.get(
    "",
    response_model=list[WorkspaceResponse],
    summary="List all workspaces",
    description="Retrieve all registered organizational workspaces with membership counts.",
)
def list_workspaces(session: SessionDep) -> list[WorkspaceResponse]:
    """Retrieve all registered organizational workspaces."""
    service = WorkspaceService(session=session)
    return service.list_workspaces()


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
    description="Create a new organizational workspace and assign the creator as ADMIN.",
)
def create_workspace(
    request: WorkspaceCreateRequest,
    session: SessionDep,
    principal: RequireAdmin,
) -> WorkspaceResponse:
    """Create a new organizational workspace and assign the creator as ADMIN."""
    service = WorkspaceService(session=session)
    return service.create_workspace(request)


@router.post(
    "/demo/seed",
    response_model=DemoSeedResponse,
    status_code=status.HTTP_200_OK,
    summary="Seed showcase demo workspace",
    description="Seed or refresh a demonstration workspace populated with traces, scorecards, benchmark comparisons, governance policies, and notification channels.",
)
def seed_demo_workspace(principal: RequireAdmin, session: SessionDep) -> DemoSeedResponse:
    """Seed or refresh the showcase demo workspace."""
    service = DemoService(session=session)
    return service.seed_demo_workspace()


@router.get(
    "/default",
    response_model=WorkspaceResponse,
    summary="Get platform default workspace",
    description="Retrieve or bootstrap the platform default workspace.",
)
def get_default_workspace(session: SessionDep) -> WorkspaceResponse:
    """Retrieve or bootstrap the platform default workspace."""
    service = WorkspaceService(session=session)
    return service.get_default_workspace()


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get workspace by ID",
    description="Fetch workspace details and configuration by unique UUID.",
)
def get_workspace(
    workspace_id: UUID,
    session: SessionDep,
) -> WorkspaceResponse:
    """Fetch workspace details by unique UUID."""
    service = WorkspaceService(session=session)
    ws = service.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )
    return ws


@router.put(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update workspace details",
    description="Update workspace name, description, or default status.",
)
def update_workspace(
    workspace_id: UUID,
    request: WorkspaceUpdateRequest,
    session: SessionDep,
    principal: RequireAdmin,
) -> WorkspaceResponse:
    """Update workspace name, description, or default status."""
    service = WorkspaceService(session=session)
    ws = service.update_workspace(workspace_id, request)
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )
    return ws


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workspace",
    description="Delete a custom workspace and cascade delete its members and audit logs. Default workspaces cannot be deleted.",
)
def delete_workspace(
    workspace_id: UUID,
    session: SessionDep,
    principal: RequireAdmin,
) -> None:
    """Delete a custom workspace and cascade delete its members and audit logs."""
    service = WorkspaceService(session=session)
    try:
        deleted = service.delete_workspace(workspace_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberResponse],
    summary="List workspace team members",
    description="Retrieve all team members and their RBAC roles within a workspace.",
)
def list_workspace_members(
    workspace_id: UUID,
    session: SessionDep,
) -> list[WorkspaceMemberResponse]:
    """Retrieve all team members and their RBAC roles in a workspace."""
    service = WorkspaceService(session=session)
    if not service.get_workspace(workspace_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )
    return service.list_members(workspace_id)


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update a workspace team member",
    description="Register or update a member's role (ADMIN, ENGINEER, VIEWER) within the specified workspace.",
)
def add_workspace_member(
    workspace_id: UUID,
    request: WorkspaceMemberAddRequest,
    session: SessionDep,
    principal: RequireAdmin,
) -> WorkspaceMemberResponse:
    """Register or update a member's role within the specified workspace."""
    service = WorkspaceService(session=session)
    try:
        return service.add_member(workspace_id, request)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.delete(
    "/{workspace_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a team member from workspace",
    description="Revoke a team member's role and access from the workspace.",
)
def remove_workspace_member(
    workspace_id: UUID,
    member_id: UUID,
    session: SessionDep,
    principal: RequireAdmin,
) -> None:
    """Remove a member's access from the workspace."""
    service = WorkspaceService(session=session)
    removed = service.remove_member(workspace_id, member_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member '{member_id}' not found in workspace '{workspace_id}'.",
        )


@router.get(
    "/{workspace_id}/audit-logs",
    response_model=list[WorkspaceAuditLogResponse],
    summary="List workspace activity audit logs",
    description="Retrieve chronological, immutable audit trail entries recording all lifecycle and membership events in a workspace.",
)
def list_workspace_audit_logs(
    workspace_id: UUID,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[WorkspaceAuditLogResponse]:
    """Retrieve chronological audit trail entries for a workspace."""
    service = WorkspaceService(session=session)
    if not service.get_workspace(workspace_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )
    return service.list_audit_logs(workspace_id, limit=limit)
