"""Main FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import check_db_health, init_db
from app.otel.otlp_http_receiver import standard_otlp_router


class VersionResponse(BaseModel):
    """System version response model."""

    version: str
    build_date: str
    commit_sha: str
    environment: str


class SystemInfoResponse(BaseModel):
    """System information and operational module status."""

    version: str
    feature_modules: list[str]
    database_status: str
    api_status: str
    environment: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Execute startup and shutdown lifecycle tasks."""
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS: explicit allowlist from CORS_ALLOWED_ORIGINS (wildcards are rejected at startup).
# Development defaults to the local frontend origins; other environments must configure it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(standard_otlp_router)


@app.get(
    "/health",
    tags=["system"],
    summary="Root health probe",
    description="Root-level health check probe for container orchestrators.",
)
def root_health() -> dict[str, str]:
    """Root health endpoint for basic liveness probes."""
    return {"status": "ok", "service": settings.PROJECT_NAME}


@app.get(
    "/version",
    response_model=VersionResponse,
    tags=["system"],
    summary="System version",
    description="Current release version, build date, commit SHA, and runtime environment.",
)
def get_version() -> VersionResponse:
    """Return version metadata."""
    return VersionResponse(
        version=settings.VERSION,
        build_date=settings.BUILD_DATE,
        commit_sha=settings.COMMIT_SHA,
        environment=settings.ENVIRONMENT,
    )


@app.get(
    "/system/info",
    response_model=SystemInfoResponse,
    tags=["system"],
    summary="System operational information",
    description="Operational status across core evaluation platform subsystems and modules.",
)
def get_system_info() -> SystemInfoResponse:
    """Return operational system info and status of integrated subsystems."""
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
