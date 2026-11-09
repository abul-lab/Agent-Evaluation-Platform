"""API endpoints for evaluation governance policy lifecycle and auditing."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.auth.dependencies import RequireAdmin, RequireEngineer
from app.db.session import get_session
from app.schemas.policy_api import (
    PolicyAuditResponse,
    PolicyCreateRequest,
    PolicyResponse,
    PolicyUpdateRequest,
)
from app.services.policy_service import PolicyService

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


@router.get(
    "",
    response_model=list[PolicyResponse],
    summary="List governance policy profiles",
    description="Retrieve all stored governance policy profiles with optional active filtering.",
)
def list_policies(
    session: SessionDep,
    active_only: bool = Query(default=False, description="Filter for active policies only"),
) -> list[PolicyResponse]:
    """Retrieve all stored governance policy profiles."""
    service = PolicyService(session=session)
    return service.list_policies(active_only=active_only)


@router.post(
    "",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new governance policy profile",
    description="Create and persist a new evaluation governance policy profile with custom score floors and gating criteria.",
)
def create_policy(
    principal: RequireAdmin,
    request: PolicyCreateRequest,
    session: SessionDep,
) -> PolicyResponse:
    """Create and persist a new evaluation governance policy profile."""
    service = PolicyService(session=session)
    return service.create_policy(request)


@router.get(
    "/active",
    response_model=PolicyResponse,
    summary="Get active platform default policy profile",
    description="Retrieve or auto-seed the default platform governance policy profile.",
)
def get_active_policy(session: SessionDep) -> PolicyResponse:
    """Retrieve or auto-seed the default platform governance policy."""
    service = PolicyService(session=session)
    return service.get_active_default_policy()


@router.get(
    "/{policy_id}",
    response_model=PolicyResponse,
    summary="Get governance policy profile by ID",
    description="Fetch an existing governance policy profile by its unique UUID.",
)
def get_policy(
    policy_id: UUID,
    session: SessionDep,
) -> PolicyResponse:
    """Fetch an existing policy profile by unique UUID."""
    service = PolicyService(session=session)
    policy = service.get_policy(policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy profile '{policy_id}' not found.",
        )
    return policy


@router.put(
    "/{policy_id}",
    response_model=PolicyResponse,
    summary="Update governance policy profile",
    description="Update settings or rule thresholds for an existing policy profile.",
)
def update_policy(
    policy_id: UUID,
    request: PolicyUpdateRequest,
    principal: RequireAdmin,
    session: SessionDep,
) -> PolicyResponse:
    """Update settings or rule thresholds for an existing policy profile."""
    service = PolicyService(session=session)
    policy = service.update_policy(policy_id, request)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy profile '{policy_id}' not found.",
        )
    return policy


@router.delete(
    "/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a governance policy profile",
    description="Delete a custom non-default policy profile. Built-in default policy profiles are protected from deletion.",
)
def delete_policy(
    policy_id: UUID,
    principal: RequireAdmin,
    session: SessionDep,
) -> None:
    """Delete a custom non-default policy profile."""
    service = PolicyService(session=session)
    try:
        deleted = service.delete_policy(policy_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy profile '{policy_id}' not found.",
        )


@router.post(
    "/{policy_id}/audit/{evaluation_id}",
    response_model=PolicyAuditResponse,
    summary="Audit an evaluation against a governance policy",
    description="Audit an evaluation record against a designated governance policy profile to produce an auditable release compliance verdict.",
)
def audit_evaluation(
    policy_id: UUID,
    evaluation_id: UUID,
    principal: RequireEngineer,
    session: SessionDep,
) -> PolicyAuditResponse:
    """Audit an evaluation record against a designated governance policy profile."""
    service = PolicyService(session=session)
    audit_result = service.audit_evaluation(policy_id=policy_id, evaluation_id=evaluation_id)
    if not audit_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Either policy '{policy_id}' or evaluation '{evaluation_id}' was not found.",
        )
    return audit_result
