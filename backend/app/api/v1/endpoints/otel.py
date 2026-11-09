"""API router endpoints for OpenTelemetry trace ingestion and CATS translation."""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlmodel import Session

from app.auth.dependencies import RequireEngineer
from app.db.session import get_session
from app.domain.models import CanonicalTrace
from app.otel.otel_adapter import FrameworkDetector
from app.otel.otel_models import OTELIngestResponse
from app.otel.otel_parser import parse_otel_payload
from app.otel.otel_to_cats import translate_otel_trace_to_cats
from app.services.trace_repository import TraceRepository

router = APIRouter(prefix="/otel", tags=["otel"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/ingest",
    response_model=OTELIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest OpenTelemetry trace",
    description="Accept generic or standard OTLP OpenTelemetry trace payload, translate to Canonical Agent Trace Schema (CATS), and persist into the evaluation repository.",
)
def ingest_otel_trace(
    payload: Annotated[
        dict[str, Any] | list[dict[str, Any]],
        Body(..., description="OpenTelemetry trace payload or span array"),
    ],
    session: SessionDep,
    principal: RequireEngineer,
) -> OTELIngestResponse:
    """Ingest OpenTelemetry trace, auto-detect framework, translate to CATS, and persist."""
    try:
        otel_trace = parse_otel_payload(payload)
        cats_trace = translate_otel_trace_to_cats(otel_trace)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid OpenTelemetry payload: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to translate OpenTelemetry trace to CATS: {e}",
        ) from e

    detected_framework = FrameworkDetector.detect(otel_trace)

    repository = TraceRepository(session)
    record = repository.create_trace(trace=cats_trace)

    return OTELIngestResponse(
        trace_id=record.trace_id,
        session_id=cats_trace.session.session_id,
        workflow_id=cats_trace.workflow.workflow_id,
        step_count=record.step_count,
        workflow_status=record.workflow_status,
        detected_framework=detected_framework.value,
        stored=True,
    )


@router.post(
    "/translate",
    response_model=CanonicalTrace,
    status_code=status.HTTP_200_OK,
    summary="Preview OpenTelemetry to CATS translation",
    description="Dry-run translation of OpenTelemetry trace payload into Canonical Agent Trace Schema without persisting to database.",
)
def preview_otel_translation(
    principal: RequireEngineer,
    payload: Annotated[
        dict[str, Any] | list[dict[str, Any]],
        Body(..., description="OpenTelemetry trace payload or span array"),
    ],
) -> CanonicalTrace:
    """Preview Canonical Agent Trace Schema generated from an OpenTelemetry trace."""
    try:
        otel_trace = parse_otel_payload(payload)
        return translate_otel_trace_to_cats(otel_trace)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid OpenTelemetry payload: {e}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to translate OpenTelemetry trace to CATS: {e}",
        ) from e
