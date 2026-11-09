"""Pydantic API schemas for team and organization workspace management."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorkspaceRole(StrEnum):
    """Role-Based Access Control classifications within an organizational workspace."""

    ADMIN = "ADMIN"
    ENGINEER = "ENGINEER"
    VIEWER = "VIEWER"


class WorkspaceCreateRequest(BaseModel):
    """Payload to create a new organizational workspace boundary."""

    name: str = Field(..., min_length=1, max_length=128, description="Workspace display name")
    slug: str | None = Field(default=None, max_length=64, description="URL-safe unique identifier")
    description: str = Field(default="", description="Workspace purpose and scope")
    is_default: bool = Field(default=False, description="Set as platform default workspace")


class WorkspaceUpdateRequest(BaseModel):
    """Payload to update an existing workspace."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None)
    is_default: bool | None = Field(default=None)


class WorkspaceResponse(BaseModel):
    """Detailed response representation of an organizational workspace."""

    workspace_id: UUID
    name: str
    slug: str
    description: str
    is_default: bool
    member_count: int = Field(default=0, description="Total members in workspace")
    created_at: datetime
    updated_at: datetime


class WorkspaceMemberAddRequest(BaseModel):
    """Payload to invite or register a member into a workspace."""

    user_email: str = Field(..., min_length=3, max_length=256, description="Member email address")
    role: WorkspaceRole = Field(default=WorkspaceRole.ENGINEER, description="RBAC permission role")


class WorkspaceMemberResponse(BaseModel):
    """Response representation of a workspace member."""

    member_id: UUID
    workspace_id: UUID
    user_email: str
    role: WorkspaceRole
    joined_at: datetime


class WorkspaceAuditLogResponse(BaseModel):
    """Audit log entry capturing workspace governance actions."""

    log_id: UUID
    workspace_id: UUID
    actor_email: str
    action: str
    resource_type: str
    resource_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DemoSeedResponse(BaseModel):
    """Result of loading pre-configured showcase demo workspace."""

    workspace_id: UUID
    name: str
    slug: str
    traces_seeded: int
    evaluations_seeded: int
    policies_seeded: int
    channels_seeded: int
    api_key_prefix: str
    status: str = "ready"
