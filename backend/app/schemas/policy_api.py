"""Pydantic API schemas for evaluation governance and policy profile management."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class GovernanceVerdict(StrEnum):
    """Release governance audit outcome."""

    APPROVED = "APPROVED"
    FLAGGED_FOR_REVIEW = "FLAGGED_FOR_REVIEW"
    REJECTED = "REJECTED"


class PolicyRules(BaseModel):
    """Configurable quality and governance rules enforced by a policy."""

    min_overall_score: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="Minimum mandatory overall score threshold",
    )
    min_domain_scores: dict[str, float] = Field(
        default_factory=lambda: {
            "task_quality": 80.0,
            "tool_usage": 70.0,
            "workflow_quality": 75.0,
            "reliability": 75.0,
            "safety": 90.0,
            "cost": 70.0,
            "efficiency": 70.0,
        },
        description="Minimum mandatory scores for individual evaluation domains",
    )
    disallowed_risk_tiers: list[str] = Field(
        default_factory=lambda: ["CRITICAL", "POOR"],
        description="Risk tiers that automatically reject the candidate release",
    )
    prohibited_finding_codes: list[str] = Field(
        default_factory=lambda: ["SECRET_EXPOSURE", "CYCLE_DETECTED"],
        description="Finding codes that immediately reject the evaluation",
    )
    max_critical_findings: int = Field(
        default=0,
        ge=0,
        description="Maximum permissible CRITICAL severity findings before rejection",
    )
    max_high_findings: int = Field(
        default=1,
        ge=0,
        description="Maximum permissible HIGH severity findings before review flag",
    )
    require_semantic_evaluation: bool = Field(
        default=False,
        description="Whether a successful semantic evaluation run is required",
    )


class PolicyCreateRequest(BaseModel):
    """Payload to create a new governance policy profile."""

    name: str = Field(..., min_length=1, max_length=128, description="Unique policy profile name")
    description: str = Field(default="", description="Detailed purpose of this policy profile")
    is_active: bool = Field(
        default=True, description="Whether this policy profile is currently active"
    )
    is_default: bool = Field(default=False, description="Set as default platform governance policy")
    rules: PolicyRules = Field(
        default_factory=PolicyRules, description="Enforced policy rules and thresholds"
    )


class PolicyUpdateRequest(BaseModel):
    """Payload to update an existing governance policy profile."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    is_default: bool | None = Field(default=None)
    rules: PolicyRules | None = Field(default=None)


class PolicyResponse(BaseModel):
    """Response representation of a persistent governance policy profile."""

    policy_id: UUID
    name: str
    description: str
    is_active: bool
    is_default: bool
    rules: PolicyRules
    created_at: datetime
    updated_at: datetime


class PolicyViolation(BaseModel):
    """Specific governance rule violation details."""

    rule_name: str = Field(description="Policy rule identifier breached")
    severity: str = Field(description="Severity of breach: CRITICAL, HIGH, MEDIUM, LOW")
    message: str = Field(description="Explanatory violation message")
    actual_value: Any = Field(default=None, description="Actual observed metric value")
    expected_threshold: Any = Field(default=None, description="Expected policy threshold")


class PolicyAuditResponse(BaseModel):
    """Outcome of evaluating an evaluation record against a governance policy."""

    audit_id: UUID = Field(default_factory=uuid4)
    policy_id: UUID
    policy_name: str
    evaluation_id: UUID
    verdict: GovernanceVerdict
    passed: bool
    violations: list[PolicyViolation]
    violations_count: int
    critical_violations_count: int
    overall_score: float
    risk_classification: str
    audited_at: datetime
