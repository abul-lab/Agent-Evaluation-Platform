"""API router endpoints for trace validation, upload, and metadata inspection."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.auth.dependencies import RequireEngineer
from app.db.session import get_session
from app.domain.models import CanonicalTrace
from app.schemas.trace_api import (
    TraceMetadataResponse,
    TraceSummaryItem,
    TraceUploadResponse,
    TraceValidationResponse,
)
from app.services.trace_repository import TraceRepository

router = APIRouter(prefix="/traces", tags=["traces"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/validate",
    response_model=TraceValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate trace schema",
    description="Validate an execution trace against the Canonical Agent Trace Schema (CATS) without persisting.",
)
def validate_trace(
    trace: CanonicalTrace,
    principal: RequireEngineer,
) -> TraceValidationResponse:
    """Validate a CanonicalTrace payload without persisting."""
    return TraceValidationResponse(
        valid=True,
        step_count=len(trace.steps),
        workflow_status=trace.workflow.status.value,
        warnings=[],
    )


@router.post(
    "/upload",
    response_model=TraceUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and persist trace",
    description="Validate an execution trace against CATS and persist it to the SQLite trace store.",
)
def upload_trace(
    trace: CanonicalTrace,
    session: SessionDep,
    principal: RequireEngineer,
) -> TraceUploadResponse:
    """Validate and persist a CanonicalTrace."""
    repository = TraceRepository(session)
    record = repository.create_trace(trace=trace)
    return TraceUploadResponse(
        trace_id=record.trace_id,
        stored=True,
        step_count=record.step_count,
        workflow_status=record.workflow_status,
    )


@router.get(
    "",
    response_model=list[TraceSummaryItem],
    status_code=status.HTTP_200_OK,
    summary="List uploaded traces",
    description="Retrieve a summary list of all ingested execution traces.",
)
def list_traces(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TraceSummaryItem]:
    """Retrieve metadata list of all stored traces."""
    repository = TraceRepository(session)
    records = repository.list_traces(limit=limit, offset=offset)
    return [
        TraceSummaryItem(
            trace_id=record.trace_id,
            workflow_status=record.workflow_status,
            step_count=record.step_count,
            created_at=record.created_at,
            framework=record.framework,
        )
        for record in records
    ]


@router.get(
    "/{trace_id}",
    response_model=TraceMetadataResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve trace metadata",
    description="Retrieve metadata for a specific ingested execution trace by its trace ID.",
)
def get_trace_metadata(
    trace_id: UUID,
    session: SessionDep,
) -> TraceMetadataResponse:
    """Retrieve metadata for a single stored trace."""
    repository = TraceRepository(session)
    record = repository.get_trace(trace_id=trace_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace with ID '{trace_id}' not found.",
        )
    return TraceMetadataResponse(
        trace_id=record.trace_id,
        created_at=record.created_at,
        workflow_status=record.workflow_status,
        step_count=record.step_count,
        framework=record.framework,
    )
