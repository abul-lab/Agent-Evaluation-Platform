"""API schemas for historical analytics, quality trends, and execution volume."""

from pydantic import BaseModel, Field


class FindingFrequency(BaseModel):
    """Frequency count and details for a recurring evaluation finding code."""

    code: str = Field(..., description="Machine-readable finding rule code")
    count: int = Field(..., ge=0, description="Total occurrences across the analytical window")
    severity: str = Field(..., description="Highest severity level observed for this finding")
    description: str = Field(..., description="Human-readable description of the finding rule")


class DailyAnalyticsBucket(BaseModel):
    """Aggregated evaluation metrics for a specific calendar date bucket."""

    date: str = Field(..., description="Calendar date in ISO YYYY-MM-DD format")
    evaluation_count: int = Field(..., ge=0, description="Total evaluations executed on this date")
    average_score: float = Field(..., description="Mean overall score on this date (0..100)")
    risk_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of evaluations per risk classification tier",
    )
    total_findings: int = Field(default=0, ge=0, description="Total findings detected on this date")
    finding_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Count of findings per rule code on this date",
    )


class AnalyticsTrendsResponse(BaseModel):
    """Comprehensive historical analytics and quality trajectory response."""

    time_window_days: int = Field(..., description="Analysis window duration in days")
    total_evaluations: int = Field(..., ge=0, description="Total evaluations within the window")
    average_score: float = Field(..., description="Mean overall score across the entire window")
    score_trend_direction: str = Field(
        ...,
        description="Overall quality trajectory: IMPROVING, DEGRADING, or STABLE",
    )
    pass_rate: float = Field(
        ..., description="Percentage of evaluations in EXCELLENT or GOOD tiers"
    )
    risk_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Overall count of evaluations per risk classification tier",
    )
    domain_averages: dict[str, float] = Field(
        default_factory=dict,
        description="Mean score per evaluation domain across the window",
    )
    finding_distribution: list[FindingFrequency] = Field(
        default_factory=list,
        description="Ranked distribution of recurring findings across the window",
    )
    daily_metrics: list[DailyAnalyticsBucket] = Field(
        default_factory=list,
        description="Chronological time-series buckets for trend visualization",
    )
