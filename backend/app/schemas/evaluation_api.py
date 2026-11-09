"""API schemas for evaluation lifecycle endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvaluationRunRequest(BaseModel):
    """Request payload for executing trace evaluation."""

    trace_id: UUID = Field(
        ...,
        description="Unique identifier of the persisted trace to evaluate",
        examples=["a0000000-0000-0000-0000-000000000001"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "trace_id": "a0000000-0000-0000-0000-000000000001",
            }
        }
    }


class EvaluationRunResponse(BaseModel):
    """Response payload returned upon completing an evaluation run."""

    evaluation_id: UUID = Field(
        ...,
        description="Unique identifier of the executed evaluation run",
        examples=["b0000000-0000-0000-0000-000000000001"],
    )
    status: str = Field(
        ...,
        description="Execution status of the evaluation run (e.g. COMPLETED, FAILED)",
        examples=["COMPLETED"],
    )
    finding_count: int = Field(
        ...,
        description="Total number of deterministic findings detected",
        examples=[3],
    )
    overall_score: float = Field(
        ...,
        description="Calculated overall score out of 100",
        examples=[81.5],
    )
    risk_classification: str = Field(
        ...,
        description="Risk classification band",
        examples=["GOOD"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "evaluation_id": "b0000000-0000-0000-0000-000000000001",
                "status": "COMPLETED",
                "finding_count": 3,
                "overall_score": 81.5,
                "risk_classification": "GOOD",
            }
        }
    }


class EvaluationSummaryResponse(BaseModel):
    """Detailed metadata summary for an evaluation run."""

    evaluation_id: UUID = Field(
        ...,
        description="Unique identifier of the evaluation run",
        examples=["b0000000-0000-0000-0000-000000000001"],
    )
    trace_id: UUID = Field(
        ...,
        description="Unique identifier of the evaluated trace",
        examples=["a0000000-0000-0000-0000-000000000001"],
    )
    status: str = Field(
        ...,
        description="Execution status of the evaluation run",
        examples=["COMPLETED"],
    )
    started_at: datetime = Field(
        ...,
        description="Timestamp when evaluation execution started in UTC",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when evaluation execution completed in UTC",
    )
    finding_count: int = Field(
        ...,
        description="Total number of findings detected",
        examples=[3],
    )
    overall_score: float = Field(
        ...,
        description="Overall scorecard score out of 100",
        examples=[81.5],
    )
    risk_classification: str = Field(
        ...,
        description="Risk classification level",
        examples=["GOOD"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "evaluation_id": "b0000000-0000-0000-0000-000000000001",
                "trace_id": "a0000000-0000-0000-0000-000000000001",
                "status": "COMPLETED",
                "started_at": "2026-11-08T12:00:00Z",
                "completed_at": "2026-11-08T12:00:01Z",
                "finding_count": 3,
                "overall_score": 81.5,
                "risk_classification": "GOOD",
            }
        }
    }
