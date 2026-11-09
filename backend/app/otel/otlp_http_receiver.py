"""OpenTelemetry OTLP/HTTP collector receiver endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.auth.dependencies import ensure_collector_principal, resolve_principal
from app.db.session import get_session
from app.otel.collector_receiver import CollectorReceiver
from app.otel.collector_validation import (
    BackpressureExceededError,
    PayloadValidationError,
    RateLimitExceededError,
    global_backpressure_monitor,
    global_rate_limiter,
)
from app.schemas.auth_api import AuthPrincipal

collector_router = APIRouter(prefix="/otel", tags=["otel-collector"])
standard_otlp_router = APIRouter(tags=["otel-collector"])
router = collector_router
SessionDep = Annotated[Session, Depends(get_session)]


class OTLPPartialSuccess(BaseModel):
    """Standard OTLP partial success details."""

    rejectedSpans: int = Field(0, description="Number of spans rejected during translation")  # noqa: N815
    errorMessage: str = Field("", description="Error details for rejected spans")  # noqa: N815


class OTLPCollectorResponse(BaseModel):
    """Standard OTLP/HTTP ExportTraceServiceResponse with AEP evaluation metadata."""

    partialSuccess: OTLPPartialSuccess = Field(  # noqa: N815
        default_factory=lambda: OTLPPartialSuccess(rejectedSpans=0, errorMessage="")
    )
    tracesIngested: int = Field(..., description="Total individual agent trace graphs ingested")  # noqa: N815
    spansIngested: int = Field(..., description="Total spans processed across all traces")  # noqa: N815
    traceIds: list[str] = Field(default_factory=list, description="IDs of ingested CATS traces")  # noqa: N815
    evaluationIds: list[str] = Field(  # noqa: N815
        default_factory=list, description="IDs of auto-evaluated trace scorecards"
    )
    workspaceId: str | None = Field(None, description="Workspace UUID trace is bound to")  # noqa: N815


def resolve_collector_auth(
    session: Session,
    authorization_header: str | None = None,
    x_api_key_header: str | None = None,
) -> AuthPrincipal:
    """Resolve the ingesting principal from an Authorization Bearer or x-api-key header.

    Anonymous callers are rejected (HTTP 401); VIEWER keys are rejected (HTTP 403).
    """
    raw_token: str | None = None

    if authorization_header and authorization_header.lower().startswith("bearer "):
        raw_token = authorization_header[7:].strip()
    elif x_api_key_header:
        raw_token = x_api_key_header.strip()

    principal = resolve_principal(session, raw_token)
    return ensure_collector_principal(principal)


async def process_otlp_http_request(
    request: Request,
    payload: dict[str, Any] | list[dict[str, Any]],
    session: Session,
    authorization: str | None = None,
    x_api_key: str | None = None,
) -> OTLPCollectorResponse:
    """Core logic for OTLP HTTP receiver handling validation, rate limiting, and execution."""
    principal = resolve_collector_auth(session, authorization, x_api_key)
    rate_key = str(principal.workspace_id or "default")

    # Rate limiting
    try:
        global_rate_limiter.check_rate_limit(rate_key)
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(int(e.retry_after))},
        ) from e

    # Backpressure concurrency and size check
    body_bytes = await request.body()
    try:
        global_backpressure_monitor.check_payload_size(len(body_bytes))
    except BackpressureExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
            headers={"Retry-After": str(int(e.retry_after))},
        ) from e

    try:
        with global_backpressure_monitor.track_request():
            receiver = CollectorReceiver(session)
            batch_result = receiver.process_batch(
                payload=payload,
                workspace_id=principal.workspace_id,
                auto_evaluate=True,
            )
    except PayloadValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"OTLP validation failed: {e}",
        ) from e
    except BackpressureExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
            headers={"Retry-After": str(int(e.retry_after))},
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Collector ingestion failed: {e}",
        ) from e

    return OTLPCollectorResponse(
        partialSuccess=OTLPPartialSuccess(
            rejectedSpans=batch_result.rejected_spans,
            errorMessage=batch_result.error_message or "",
        ),
        tracesIngested=batch_result.traces_ingested,
        spansIngested=batch_result.spans_ingested,
        traceIds=batch_result.trace_ids,
        evaluationIds=batch_result.evaluation_ids,
        workspaceId=batch_result.workspace_id,
    )


@collector_router.post(
    "/collector",
    response_model=OTLPCollectorResponse,
    status_code=status.HTTP_200_OK,
    summary="OTLP/HTTP Collector Native Ingestion",
    description="Universal OTLP/HTTP receiver endpoint accepting standard OpenTelemetry trace batches from OTEL collectors.",
)
async def otlp_http_collector_endpoint(
    request: Request,
    payload: Annotated[dict[str, Any] | list[dict[str, Any]], Body(...)],
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
) -> OTLPCollectorResponse:
    """Standard OTLP/HTTP receiver endpoint for OpenTelemetry Collectors."""
    return await process_otlp_http_request(
        request=request,
        payload=payload,
        session=session,
        authorization=authorization,
        x_api_key=x_api_key,
    )


@standard_otlp_router.post(
    "/v1/traces",
    response_model=OTLPCollectorResponse,
    status_code=status.HTTP_200_OK,
    summary="Standard OTLP/HTTP /v1/traces Endpoint Alias",
    description="Default canonical endpoint path expected by standard OpenTelemetry collectors using otlphttp exporter.",
)
async def otlp_standard_v1_traces_endpoint(
    request: Request,
    payload: Annotated[dict[str, Any] | list[dict[str, Any]], Body(...)],
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
) -> OTLPCollectorResponse:
    """Direct alias endpoint for standard OTLP collectors configured with default /v1/traces path."""
    return await process_otlp_http_request(
        request=request,
        payload=payload,
        session=session,
        authorization=authorization,
        x_api_key=x_api_key,
    )
