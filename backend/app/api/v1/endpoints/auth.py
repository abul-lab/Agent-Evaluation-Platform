"""API router endpoints for API keys, service accounts, and authentication."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.auth.dependencies import CurrentPrincipal, RequireAdmin, RequireEngineer
from app.db.session import get_session
from app.schemas.auth_api import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyResponse,
    AuthPrincipal,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/api-keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
    description="Generate a new workspace-scoped API key. Plaintext key is returned ONLY ONCE upon creation.",
)
def create_api_key(
    request: APIKeyCreateRequest,
    principal: RequireAdmin,
    session: SessionDep,
) -> APIKeyCreateResponse:
    """Issue a new scoped API key with SHA-256 hash storage."""
    auth_service = AuthService(session)
    actor = principal.name if principal.is_authenticated else request.created_by
    return auth_service.create_api_key(request=request, actor_email=actor)


@router.get(
    "/api-keys",
    response_model=list[APIKeyResponse],
    status_code=status.HTTP_200_OK,
    summary="List API keys",
    description="List active and revoked API keys for the workspace.",
)
def list_api_keys(
    principal: RequireEngineer,
    session: SessionDep,
    workspace_id: Annotated[UUID | None, Query(description="Filter by workspace ID")] = None,
) -> list[APIKeyResponse]:
    """Retrieve metadata of all registered API keys."""
    auth_service = AuthService(session)
    target_ws = workspace_id or (principal.workspace_id if principal.is_authenticated else None)
    return auth_service.list_api_keys(workspace_id=target_ws)


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoke API key",
    description="Revoke an existing API key immediately.",
)
def revoke_api_key(
    key_id: UUID,
    principal: RequireAdmin,
    session: SessionDep,
) -> dict[str, str | bool]:
    """Revoke an API key and log an audit trail entry."""
    auth_service = AuthService(session)
    actor = principal.name if principal.is_authenticated else "admin"
    success = auth_service.revoke_api_key(key_id=key_id, actor_email=actor)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API Key with ID '{key_id}' not found or already inactive.",
        )
    return {"key_id": str(key_id), "revoked": True}


@router.get(
    "/verify",
    response_model=AuthPrincipal,
    status_code=status.HTTP_200_OK,
    summary="Verify caller credentials",
    description="Verify current Authorization header and inspect active principal permissions.",
)
def verify_credentials(
    principal: CurrentPrincipal,
) -> AuthPrincipal:
    """Inspect the authenticated caller principal."""
    return principal
