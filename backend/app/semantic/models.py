"""Domain models for semantic evaluation findings and evaluation outcomes."""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class SemanticFinding(BaseModel):
    """Structured outcome for an individual semantic evaluation metric."""

    model_config = ConfigDict(extra="forbid")

    finding_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the semantic finding"
    )
    metric_name: str = Field(
        ..., min_length=1, max_length=64, description="Name of semantic metric"
    )
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized score between 0.0 and 1.0")
    passed: bool = Field(..., description="Whether score satisfied the pass threshold")
    explanation: str = Field(..., min_length=1, description="Reasoning for the assigned score")


class SemanticEvaluationResult(BaseModel):
    """Aggregated outcome of semantic evaluation across all configured metrics."""

    model_config = ConfigDict(extra="forbid")

    metrics: list[SemanticFinding] = Field(
        default_factory=list, description="List of semantic findings"
    )
    provider: str = Field(
        default="fallback", description="Adapter provider name ('deepeval', 'fallback')"
    )
    execution_time_ms: float = Field(
        default=0.0, ge=0.0, description="Execution time in milliseconds"
    )
    evaluation_available: bool = Field(
        default=False, description="Whether semantic evaluation completed successfully"
    )
    reason: str | None = Field(
        default=None, description="Explanation when semantic evaluation is unavailable"
    )
