"""Pydantic API schemas for API keys, service accounts, and authentication."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ServiceAccountRole(StrEnum):
    """Role-Based Access Control classifications for service accounts."""

    ADMIN = "ADMIN"
    ENGINEER = "ENGINEER"
    VIEWER = "VIEWER"


class APIKeyCreateRequest(BaseModel):
    """Payload to generate a new scoped API key."""

    name: str = Field(
        ..., min_length=1, max_length=128, description="Key name or service identifier"
    )
    workspace_id: UUID | None = Field(
        default=None, description="Target workspace ID (defaults to active default workspace)"
    )
    role: ServiceAccountRole = Field(
        default=ServiceAccountRole.ENGINEER, description="Service account permission tier"
    )
    created_by: str = Field(
        default="system", max_length=256, description="Creator identity or email"
    )
    expires_in_days: int | None = Field(
        default=None, ge=1, le=3650, description="Expiration TTL in days, or null for non-expiring"
    )


class APIKeyCreateResponse(BaseModel):
    """Response containing newly generated secret key (returned ONLY ONCE upon creation)."""

    key_id: UUID
    workspace_id: UUID
    name: str
    raw_key: str = Field(..., description="Secret plaintext API key token (returned only once)")
    key_prefix: str
    role: ServiceAccountRole
    created_by: str
    created_at: datetime
    expires_at: datetime | None
    is_active: bool


class APIKeyResponse(BaseModel):
    """Safe metadata representation of an API key (omits plaintext and hash)."""

    key_id: UUID
    workspace_id: UUID
    name: str
    key_prefix: str
    role: ServiceAccountRole
    created_by: str
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    is_active: bool


class AuthPrincipal(BaseModel):
    """Context object representing the authenticated caller or fallback identity."""

    is_authenticated: bool = Field(default=False)
    key_id: UUID | None = Field(default=None)
    workspace_id: UUID | None = Field(default=None)
    role: ServiceAccountRole = Field(default=ServiceAccountRole.VIEWER)
    name: str = Field(default="anonymous")
    is_service_account: bool = Field(default=False)
