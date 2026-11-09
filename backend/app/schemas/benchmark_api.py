"""API schemas for evaluation benchmarking and comparison."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.evaluators.base import EvaluationFinding


class ComparisonRequest(BaseModel):
    """Request payload for comparing two evaluation runs."""

    base_evaluation_id: UUID = Field(
        ...,
        description="Unique identifier of the baseline evaluation run",
        examples=["b0000000-0000-0000-0000-000000000001"],
    )
    target_evaluation_id: UUID = Field(
        ...,
        description="Unique identifier of the candidate/target evaluation run to compare against baseline",
        examples=["b0000000-0000-0000-0000-000000000002"],
    )


class DomainScoreDelta(BaseModel):
    """Score and status delta for a specific evaluation domain."""

    domain_name: str = Field(..., description="Evaluation domain name")
    base_score: float = Field(..., description="Domain score in baseline evaluation")
    target_score: float = Field(..., description="Domain score in candidate evaluation")
    score_delta: float = Field(..., description="Signed score change (target - base)")
    base_status: str = Field(..., description="Baseline domain status: PASS, WARN, FAIL")
    target_status: str = Field(..., description="Candidate domain status: PASS, WARN, FAIL")


class FindingDelta(BaseModel):
    """Categorized findings delta between baseline and candidate evaluations."""

    new_findings: list[EvaluationFinding] = Field(
        default_factory=list,
        description="Findings introduced in target that were not present in baseline",
    )
    resolved_findings: list[EvaluationFinding] = Field(
        default_factory=list,
        description="Findings present in baseline that are no longer detected in target",
    )
    persistent_findings: list[EvaluationFinding] = Field(
        default_factory=list,
        description="Findings detected in both baseline and target evaluations",
    )
    new_count: int = Field(default=0, description="Count of newly introduced findings")
    resolved_count: int = Field(default=0, description="Count of resolved findings")
    persistent_count: int = Field(default=0, description="Count of persistent findings")
    total_delta: int = Field(default=0, description="Net finding count change (target - base)")


class RiskTransition(BaseModel):
    """Risk tier comparison and transition outcome."""

    base_risk: str = Field(
        ..., description="Baseline risk tier: EXCELLENT, GOOD, WATCH, POOR, CRITICAL"
    )
    target_risk: str = Field(
        ..., description="Candidate risk tier: EXCELLENT, GOOD, WATCH, POOR, CRITICAL"
    )
    is_improved: bool = Field(..., description="Whether risk improved to a safer tier")
    is_degraded: bool = Field(..., description="Whether risk degraded to a more severe tier")


class EvaluationComparisonResponse(BaseModel):
    """Comprehensive comparison payload between two evaluation runs."""

    base_evaluation_id: UUID = Field(..., description="Baseline evaluation identifier")
    target_evaluation_id: UUID = Field(..., description="Candidate evaluation identifier")
    base_trace_id: UUID = Field(..., description="Baseline trace identifier")
    target_trace_id: UUID = Field(..., description="Candidate trace identifier")
    base_score: float = Field(..., description="Baseline overall score out of 100")
    target_score: float = Field(..., description="Candidate overall score out of 100")
    overall_score_delta: float = Field(
        ..., description="Signed overall score delta (target - base)"
    )
    risk_transition: RiskTransition = Field(..., description="Risk tier movement analysis")
    domain_deltas: dict[str, DomainScoreDelta] = Field(
        default_factory=dict,
        description="Domain-by-domain score and status changes",
    )
    finding_delta: FindingDelta = Field(..., description="Detailed breakdown of finding changes")
    compared_at: datetime = Field(
        ..., description="Timestamp when comparison was calculated in UTC"
    )


class BenchmarkLeaderboardItem(BaseModel):
    """Individual ranked evaluation record within a benchmark leaderboard."""

    rank: int = Field(..., ge=1, description="Ordinal rank (1 = highest score)")
    evaluation_id: UUID = Field(..., description="Unique evaluation identifier")
    trace_id: UUID = Field(..., description="Unique trace identifier")
    overall_score: float = Field(..., description="Calculated overall score out of 100")
    risk_classification: str = Field(..., description="Risk classification tier")
    finding_count: int = Field(..., description="Total deterministic findings detected")
    workflow_status: str = Field(..., description="Terminal workflow execution status")
    started_at: datetime = Field(..., description="Evaluation start timestamp")
    completed_at: datetime | None = Field(
        default=None, description="Evaluation completion timestamp"
    )


class BenchmarkSummaryResponse(BaseModel):
    """Aggregated benchmark dataset metrics and ranked leaderboard."""

    total_evaluations: int = Field(..., ge=0, description="Total number of evaluated traces")
    mean_score: float = Field(..., description="Mean overall score across all evaluations")
    min_score: float = Field(..., description="Minimum overall score recorded")
    max_score: float = Field(..., description="Maximum overall score recorded")
    pass_rate: float = Field(
        ..., description="Percentage of evaluations in EXCELLENT or GOOD tiers"
    )
    risk_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Count of evaluations per risk classification tier",
    )
    leaderboard: list[BenchmarkLeaderboardItem] = Field(
        default_factory=list,
        description="Ranked evaluation items ordered by overall score descending",
    )
