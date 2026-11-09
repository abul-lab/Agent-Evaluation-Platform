"""Base models and protocols for deterministic trace evaluators."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import CanonicalTrace


class FindingSeverity(StrEnum):
    """Severity classification for evaluation findings."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvaluationFinding(BaseModel):
    """Structured deterministic evaluation finding."""

    model_config = ConfigDict(extra="forbid")

    finding_id: UUID = Field(default_factory=uuid4, description="Unique finding identifier")
    severity: FindingSeverity = Field(..., description="Finding severity level")
    code: str = Field(..., min_length=1, max_length=64, description="Machine-readable code")
    message: str = Field(..., min_length=1, description="Human-readable explanation")
    workflow_id: UUID = Field(..., description="Target workflow identifier")
    affected_steps: list[int] = Field(default_factory=list, description="0-indexed step numbers")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Diagnostic contextual metadata"
    )


class DeterministicEvaluationResult(BaseModel):
    """Aggregated outcome of deterministic trace evaluation."""

    model_config = ConfigDict(extra="forbid")

    workflow_id: UUID
    session_id: UUID
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    findings: list[EvaluationFinding] = Field(default_factory=list)
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0


class BaseDeterministicEvaluator(ABC):
    """Abstract base class for all deterministic trace evaluators."""

    @abstractmethod
    def evaluate(self, trace: CanonicalTrace) -> list[EvaluationFinding]:
        """Execute deterministic evaluation against a CanonicalTrace.

        Must not make network requests, API calls, or use LLM models.
        """
        raise NotImplementedError
