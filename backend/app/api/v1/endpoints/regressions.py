"""API endpoints for regression detection and quality gate policy evaluation."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.auth.dependencies import RequireEngineer
from app.db.session import get_session
from app.schemas.regression_api import (
    RegressionCheckRequest,
    RegressionPolicy,
    RegressionReport,
)
from app.services.regression_service import RegressionService

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


@router.get(
    "/policy/default",
    response_model=RegressionPolicy,
    summary="Get standard regression quality gate policy",
    description="Return the standard regression threshold policy configured for automated release gating.",
)
def get_default_policy() -> RegressionPolicy:
    """Return the default standard regression policy used by the evaluation platform."""
    return RegressionPolicy()


@router.post(
    "/check",
    response_model=RegressionReport,
    summary="Audit candidate evaluation against baseline for regressions",
    description="Execute an automated regression check comparing a candidate evaluation run against a baseline run using defined threshold policies.",
)
def check_regression(
    principal: RequireEngineer,
    request: RegressionCheckRequest,
    session: SessionDep,
) -> RegressionReport:
    """Execute a deterministic regression check comparing candidate evaluation to baseline."""
    service = RegressionService(session=session)
    report = service.check_regression(
        base_id=request.baseline_evaluation_id,
        candidate_id=request.candidate_evaluation_id,
        policy=request.policy,
    )
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"One or both evaluation runs not found: "
                f"baseline={request.baseline_evaluation_id}, candidate={request.candidate_evaluation_id}"
            ),
        )
    return report
