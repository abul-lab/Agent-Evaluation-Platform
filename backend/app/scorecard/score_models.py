"""Scorecard domain models and status enums."""

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import RiskClassification
from app.evaluators.base import EvaluationFinding


class DomainStatus(StrEnum):
    """Operational status of an individual evaluation domain."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class DomainScore(BaseModel):
    """Normalized score and status for an individual evaluation domain."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Domain display name")
    score: float = Field(..., ge=0.0, le=100.0, description="Normalized score (0-100)")
    status: DomainStatus = Field(..., description="Pass, Warn, or Fail domain classification")
    findings_count: int = Field(
        default=0, ge=0, description="Number of findings attributed to this domain"
    )


class Scorecard(BaseModel):
    """Aggregated multi-domain evaluation scorecard and risk classification."""

    model_config = ConfigDict(extra="forbid")

    scorecard_id: UUID = Field(default_factory=uuid4, description="Unique scorecard identifier")
    workflow_id: UUID = Field(..., description="Evaluated workflow identifier")

    task_quality: DomainScore = Field(..., description="Task completion and outcome fidelity score")
    tool_usage: DomainScore = Field(..., description="Tool registry and execution quality score")
    workflow_quality: DomainScore = Field(
        ..., description="Graph topology and cycle avoidance score"
    )
    reliability: DomainScore = Field(..., description="Retry stability and recovery score")
    safety: DomainScore = Field(..., description="Safety and credential protection score")
    cost: DomainScore = Field(
        ..., description="Financial, token, and latency budget adherence score"
    )
    efficiency: DomainScore = Field(..., description="Execution path and resource efficiency score")

    overall_score: float = Field(..., ge=0.0, le=100.0, description="Weighted composite score")
    risk_classification: RiskClassification = Field(
        ..., description="Overall risk classification tier"
    )
    findings: list[EvaluationFinding] = Field(
        default_factory=list, description="All underlying evaluation findings"
    )
