"""API router endpoints for evaluation comparison and benchmark dataset analytics."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.auth.dependencies import RequireEngineer
from app.db.session import get_session
from app.schemas.benchmark_api import (
    BenchmarkSummaryResponse,
    ComparisonRequest,
    EvaluationComparisonResponse,
)
from app.services.benchmark_service import BenchmarkService

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/compare",
    response_model=EvaluationComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare two evaluation runs",
    description="Calculate mathematical score deltas, risk tier transition, domain-by-domain variance, and categorized finding differences between a baseline and target evaluation.",
)
def compare_evaluations(
    principal: RequireEngineer,
    request: ComparisonRequest,
    session: SessionDep,
) -> EvaluationComparisonResponse:
    """Compare a candidate evaluation against a baseline evaluation run."""
    service = BenchmarkService(session=session)
    result = service.compare_evaluations(
        base_id=request.base_evaluation_id,
        target_id=request.target_evaluation_id,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both evaluation runs were not found in the persistence store.",
        )
    return result


@router.get(
    "/summary",
    response_model=BenchmarkSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve benchmark dataset summary and ranked leaderboard",
    description="Calculate statistical distribution metrics (mean, min, max, pass rate) and ranked leaderboard of all evaluations.",
)
def get_benchmark_summary(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BenchmarkSummaryResponse:
    """Retrieve statistical benchmark aggregates and ranked evaluation items."""
    service = BenchmarkService(session=session)
    return service.get_benchmark_summary(limit=limit, offset=offset)
