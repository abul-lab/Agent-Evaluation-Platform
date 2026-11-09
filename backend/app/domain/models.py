"""Canonical Agent Trace Schema (CATS) Models.

Provides strictly validated Pydantic v2 domain models for agent execution traces,
tool invocations, workflow topologies, retries, and evaluation results.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import (
    FrameworkType,
    OrchestratorType,
    RetryResolution,
    RiskClassification,
    WorkflowStatus,
)


class BaseCanonicalModel(BaseModel):
    """Base model enforcing strict validation and consistent serialization."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
    )


class ToolDefinition(BaseCanonicalModel):
    """Specification of an available capability tool in an Agent registry."""

    tool_name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., min_length=1)
    parameters_schema: dict[str, Any] = Field(default_factory=dict, alias="schema")

    @property
    def schema(self) -> dict[str, Any]:  # type: ignore[override]
        """Access parameters schema dictionary."""
        return self.parameters_schema


class Agent(BaseCanonicalModel):
    """Registered agent profile executing within a workflow."""

    agent_id: UUID
    name: str = Field(..., min_length=1, max_length=128)
    role: str = Field(..., min_length=1, max_length=128)
    system_prompt_hash: str = Field(..., min_length=8, max_length=64)
    model_identifier: str = Field(..., min_length=1, max_length=128)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    tool_registry: list[ToolDefinition] = Field(default_factory=list)


class BudgetConfig(BaseCanonicalModel):
    """Execution budget constraints for cost, latency, and tokens."""

    max_usd: Decimal = Field(default=Decimal("1.0000"), ge=Decimal("0.0"))
    max_latency_ms: int = Field(default=30000, ge=0)
    max_tokens: int = Field(default=100000, ge=0)


class Session(BaseCanonicalModel):
    """Top-level contextual boundary representing user intent and constraints."""

    session_id: UUID
    user_intent: str = Field(..., min_length=1)
    context_data: dict[str, Any] = Field(default_factory=dict)
    budget_constraints: BudgetConfig = Field(default_factory=BudgetConfig)
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def ensure_utc(cls, v: Any) -> datetime:
        """Ensure created_at timestamp is timezone-aware in UTC."""
        if isinstance(v, str):
            dt = datetime.fromisoformat(v)
        elif isinstance(v, datetime):
            dt = v
        else:
            raise ValueError(f"Invalid datetime format: {v}")
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt


class Workflow(BaseCanonicalModel):
    """Workflow execution instance and overall topology."""

    workflow_id: UUID
    session_id: UUID
    framework: FrameworkType
    orchestrator_type: OrchestratorType
    status: WorkflowStatus
    total_cost_usd: Decimal = Field(default=Decimal("0.0000"), ge=Decimal("0.0"))
    total_latency_ms: int = Field(default=0, ge=0)


class TokenUsage(BaseCanonicalModel):
    """Token consumption accounting breakdown."""

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)

    @property
    def total_tokens(self) -> int:
        """Calculate aggregated total tokens."""
        return self.prompt_tokens + self.completion_tokens


class ToolCall(BaseCanonicalModel):
    """Granular execution of an external capability tool."""

    tool_call_id: UUID
    step_id: UUID
    tool_name: str = Field(..., min_length=1, max_length=128)
    declared_schema: dict[str, Any] | None = Field(default=None)
    raw_arguments: dict[str, Any] = Field(default_factory=dict)
    parsed_arguments: dict[str, Any] | None = Field(default=None)
    execution_result: dict[str, Any] | None = Field(default=None)
    is_error: bool = Field(default=False)
    is_hallucinated: bool = Field(default=False)
    is_redundant: bool = Field(default=False)
    execution_time_ms: int = Field(default=0, ge=0)


class Retry(BaseCanonicalModel):
    """Resilience and fault recovery execution record."""

    retry_id: UUID
    step_id: UUID
    attempt_number: int = Field(..., ge=1)
    error_type: str = Field(..., min_length=1)
    backoff_duration_ms: int = Field(default=0, ge=0)
    resolution: RetryResolution


class Step(BaseCanonicalModel):
    """Atomic step, decision node, or model invocation within a workflow."""

    step_id: UUID
    workflow_id: UUID
    agent_id: UUID
    step_index: int = Field(..., ge=0)
    node_name: str = Field(..., min_length=1, max_length=128)
    input_state: dict[str, Any] = Field(default_factory=dict)
    output_state: dict[str, Any] = Field(default_factory=dict)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: int = Field(default=0, ge=0)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    retries: list[Retry] = Field(default_factory=list)


class EvaluationResult(BaseCanonicalModel):
    """Synthesized scorecard and evaluation report."""

    eval_id: UUID
    workflow_id: UUID
    overall_score: float = Field(..., ge=0.0, le=100.0)
    risk_classification: RiskClassification
    domain_scores: dict[str, Any] = Field(default_factory=dict)
    failure_attributions: list[dict[str, Any]] = Field(default_factory=list)


class CanonicalTrace(BaseCanonicalModel):
    """Complete normalized canonical trace payload."""

    session: Session
    agents: list[Agent] = Field(..., min_length=1)
    workflow: Workflow
    steps: list[Step] = Field(default_factory=list)
