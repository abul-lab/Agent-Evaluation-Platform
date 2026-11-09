"""API v1 master router."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.benchmarks import router as benchmarks_router
from app.api.v1.endpoints.evaluations import router as evaluations_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.otel import router as otel_router
from app.api.v1.endpoints.policies import router as policies_router
from app.api.v1.endpoints.regressions import router as regressions_router
from app.api.v1.endpoints.traces import router as traces_router
from app.api.v1.endpoints.workspaces import router as workspaces_router
from app.auth.dependencies import require_viewer
from app.core.config import settings
from app.db.session import check_db_health
from app.otel.otlp_http_receiver import collector_router

api_router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    version: str
    environment: str


class VersionResponse(BaseModel):
    """System version response schema."""

    version: str
    build_date: str
    commit_sha: str
    environment: str


class SystemInfoResponse(BaseModel):
    """System operational information response schema."""

    version: str
    feature_modules: list[str]
    database_status: str
    api_status: str
    environment: str


@api_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the operational health and version of the API service.",
    tags=["system"],
)
def health_check() -> HealthResponse:
    """Return operational health status."""
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )


@api_router.get(
    "/version",
    response_model=VersionResponse,
    summary="Version info",
    description="Check release version, build date, and git commit SHA.",
    tags=["system"],
)
def version_info() -> VersionResponse:
    """Return platform version and build metadata."""
    return VersionResponse(
        version=settings.VERSION,
        build_date=settings.BUILD_DATE,
        commit_sha=settings.COMMIT_SHA,
        environment=settings.ENVIRONMENT,
    )


@api_router.get(
    "/system/info",
    response_model=SystemInfoResponse,
    summary="System info",
    description="Operational status across all active engine modules and database connection.",
    tags=["system"],
)
def system_info() -> SystemInfoResponse:
    """Return integrated subsystem and database health status."""
    return SystemInfoResponse(
        version=settings.VERSION,
        feature_modules=[
            "canonical_trace_schema",
            "golden_fixture_suite",
            "deterministic_evaluators",
            "findings_engine",
            "scorecard_engine",
            "risk_classification",
            "semantic_evaluator",
            "reporting_and_export",
            "workflow_graph",
            "benchmarks",
            "historical_analytics",
            "regression_detection",
            "evaluation_policies",
            "workspaces_and_rbac",
            "opentelemetry_connector",
            "api_key_authentication",
            "enterprise_notifications",
            "otel_collector_receiver",
        ],
        database_status=check_db_health(),
        api_status="operational",
        environment=settings.ENVIRONMENT,
    )


# Read floor: every router below requires an authenticated key in production, and
# anonymous VIEWER access in development only when ALLOW_ANONYMOUS_VIEWER=true.
# Mutating routes add a stricter role check on top of this floor.
_READ_FLOOR = [Depends(require_viewer)]

api_router.include_router(auth_router, dependencies=_READ_FLOOR)
api_router.include_router(traces_router, dependencies=_READ_FLOOR)
api_router.include_router(otel_router, dependencies=_READ_FLOOR)
# collector_router authenticates inside the OTLP handler (API key via Authorization or x-api-key).
api_router.include_router(collector_router)
api_router.include_router(evaluations_router, dependencies=_READ_FLOOR)
api_router.include_router(benchmarks_router, dependencies=_READ_FLOOR)
api_router.include_router(analytics_router, dependencies=_READ_FLOOR)
api_router.include_router(
    regressions_router, prefix="/regressions", tags=["regressions"], dependencies=_READ_FLOOR
)
api_router.include_router(
    policies_router, prefix="/policies", tags=["policies"], dependencies=_READ_FLOOR
)
api_router.include_router(
    workspaces_router, prefix="/workspaces", tags=["workspaces"], dependencies=_READ_FLOOR
)
api_router.include_router(notifications_router, dependencies=_READ_FLOOR)
