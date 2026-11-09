"""API router endpoints for evaluation lifecycle management, scorecard retrieval, and findings inspection."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.auth.dependencies import RequireEngineer
from app.db.session import get_session
from app.evaluators.base import EvaluationFinding
from app.schemas.evaluation_api import (
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationSummaryResponse,
)
from app.schemas.graph_api import WorkflowGraphResponse
from app.scorecard.score_models import Scorecard
from app.semantic.models import SemanticEvaluationResult
from app.services.evaluation_service import EvaluationService
from app.services.report_service import ReportService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/run",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute evaluation against stored trace",
    description="Loads a stored trace by trace_id, executes all deterministic evaluators, synthesizes the multi-domain scorecard, and persists the evaluation outcome.",
)
def run_evaluation(
    request: EvaluationRunRequest,
    session: SessionDep,
    principal: RequireEngineer,
) -> EvaluationRunResponse:
    """Execute evaluation against a persisted trace."""
    service = EvaluationService(session=session)
    record = service.run_evaluation(trace_id=request.trace_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace with ID '{request.trace_id}' not found.",
        )
    return EvaluationRunResponse(
        evaluation_id=record.evaluation_id,
        status=record.status,
        finding_count=record.finding_count,
        overall_score=record.overall_score,
        risk_classification=record.risk_classification,
    )


@router.get(
    "/{evaluation_id}",
    response_model=EvaluationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve evaluation summary",
    description="Retrieve execution metadata, overall score, and risk classification for a specific evaluation run.",
)
def get_evaluation(
    evaluation_id: UUID,
    session: SessionDep,
) -> EvaluationSummaryResponse:
    """Retrieve evaluation run summary by evaluation ID."""
    service = EvaluationService(session=session)
    record = service.get_evaluation(evaluation_id=evaluation_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation with ID '{evaluation_id}' not found.",
        )
    return EvaluationSummaryResponse(
        evaluation_id=record.evaluation_id,
        trace_id=record.trace_id,
        status=record.status,
        started_at=record.started_at,
        completed_at=record.completed_at,
        finding_count=record.finding_count,
        overall_score=record.overall_score,
        risk_classification=record.risk_classification,
    )


@router.get(
    "/{evaluation_id}/scorecard",
    response_model=Scorecard,
    status_code=status.HTTP_200_OK,
    summary="Retrieve evaluation scorecard",
    description="Retrieve the generated multi-domain scorecard containing scores, statuses, and finding counts across all 7 evaluation domains.",
)
def get_evaluation_scorecard(
    evaluation_id: UUID,
    session: SessionDep,
) -> Scorecard:
    """Retrieve the multi-domain scorecard for a specific evaluation run."""
    service = EvaluationService(session=session)
    scorecard = service.get_scorecard(evaluation_id=evaluation_id)
    if scorecard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation with ID '{evaluation_id}' not found.",
        )
    return scorecard


@router.get(
    "/{evaluation_id}/findings",
    response_model=list[EvaluationFinding],
    status_code=status.HTTP_200_OK,
    summary="Retrieve evaluation findings",
    description="Retrieve all deterministic findings and diagnostic metadata detected during trace evaluation.",
)
def get_evaluation_findings(
    evaluation_id: UUID,
    session: SessionDep,
) -> list[EvaluationFinding]:
    """Retrieve all deterministic findings emitted for a specific evaluation run."""
    service = EvaluationService(session=session)
    findings = service.get_findings(evaluation_id=evaluation_id)
    if findings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation with ID '{evaluation_id}' not found.",
        )
    return findings


@router.get(
    "/{evaluation_id}/semantic",
    response_model=SemanticEvaluationResult,
    status_code=status.HTTP_200_OK,
    summary="Retrieve semantic evaluation results",
    description="Retrieve optional semantic evaluation metrics (e.g. answer relevancy, faithfulness, hallucination) or fallback status.",
)
def get_evaluation_semantic(
    evaluation_id: UUID,
    session: SessionDep,
) -> SemanticEvaluationResult:
    """Retrieve semantic evaluation outcome for a specific evaluation run."""
    service = EvaluationService(session=session)
    result = service.get_semantic_result(evaluation_id=evaluation_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation with ID '{evaluation_id}' not found.",
        )
    return result


@router.get(
    "/{evaluation_id}/export/json",
    status_code=status.HTTP_200_OK,
    summary="Export evaluation report as JSON",
    description="Export a full structured JSON report containing evaluation summary, scorecard, findings, and metadata.",
    responses={
        200: {
            "content": {"application/json": {}},
            "description": "Portable evaluation report in JSON format.",
        },
        404: {"description": "Evaluation run not found."},
    },
)
def export_evaluation_json(
    evaluation_id: UUID,
    session: SessionDep,
) -> JSONResponse:
    """Export evaluation report as structured JSON."""
    service = ReportService(session=session)
    report = service.generate_json_report(evaluation_id=evaluation_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation with ID '{evaluation_id}' not found.",
        )
    return JSONResponse(
        content=report,
        headers={"Content-Disposition": f'attachment; filename="evaluation_{evaluation_id}.json"'},
    )


@router.get(
    "/{evaluation_id}/export/markdown",
    status_code=status.HTTP_200_OK,
    summary="Export evaluation report as Markdown",
    description="Export a human-readable Markdown evaluation report containing summary, risk classification, scorecard table, findings table, and metadata.",
    responses={
        200: {
            "content": {"text/markdown": {}},
            "description": "Human-readable Markdown evaluation report.",
        },
        404: {"description": "Evaluation run not found."},
    },
)
def export_evaluation_markdown(
    evaluation_id: UUID,
    session: SessionDep,
) -> Response:
    """Export evaluation report as formatted Markdown."""
    service = ReportService(session=session)
    report = service.generate_markdown_report(evaluation_id=evaluation_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation with ID '{evaluation_id}' not found.",
        )
    return Response(
        content=report,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="evaluation_{evaluation_id}.md"'},
    )


@router.get(
    "/{evaluation_id}/export/csv",
    status_code=status.HTTP_200_OK,
    summary="Export evaluation findings as CSV",
    description="Export flattened deterministic evaluation findings as a tabular CSV document.",
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "Flattened evaluation findings in CSV format.",
        },
        404: {"description": "Evaluation run not found."},
    },
)
def export_evaluation_csv(
    evaluation_id: UUID,
    session: SessionDep,
) -> Response:
    """Export evaluation findings as CSV."""
    service = ReportService(session=session)
    report = service.generate_csv_report(evaluation_id=evaluation_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation with ID '{evaluation_id}' not found.",
        )
    return Response(
        content=report,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="evaluation_{evaluation_id}.csv"'},
    )


@router.get(
    "/{evaluation_id}/graph",
    response_model=WorkflowGraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve workflow execution graph",
    description="Retrieve the workflow step DAG structure with node findings, tool calls, retries, and cycle indicators for React Flow visualization.",
)
def get_evaluation_graph(
    evaluation_id: UUID,
    session: SessionDep,
) -> WorkflowGraphResponse:
    """Retrieve the workflow execution graph for visual inspection."""
    service = EvaluationService(session=session)
    graph = service.get_evaluation_graph(evaluation_id=evaluation_id)
    if graph is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation with ID '{evaluation_id}' not found.",
        )
    return graph
