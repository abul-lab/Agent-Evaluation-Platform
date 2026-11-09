"""API router endpoints for historical evaluation analytics and quality trends."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.analytics_api import AnalyticsTrendsResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get(
    "/trends",
    response_model=AnalyticsTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve historical quality trends and volume metrics",
    description="Calculate longitudinal evaluation trends, daily throughput volume, score trajectories, and recurring finding distributions.",
)
def get_historical_trends(
    session: SessionDep,
    days: Annotated[int, Query(ge=0, le=365)] = 30,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
) -> AnalyticsTrendsResponse:
    """Retrieve historical evaluation analytics across a configurable time window."""
    service = AnalyticsService(session=session)
    return service.get_historical_trends(days=days, limit=limit)
