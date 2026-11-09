from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.evaluators.base import FindingSeverity


class RegressionStatus(StrEnum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    REGRESSED = "REGRESSED"


class RegressionPolicy(BaseModel):
    name: str = Field(
        default="Standard Quality Gate",
        description="Human-readable policy name",
    )
    max_score_drop: float = Field(
        default=5.0,
        ge=0.0,
        description="Maximum permissible drop in overall evaluation score before flagging regression",
    )
    max_domain_drop: float = Field(
        default=10.0,
        ge=0.0,
        description="Maximum permissible drop in any individual domain score before flagging regression",
    )
    fail_on_risk_escalation: bool = Field(
        default=True,
        description="Flag regression if candidate risk tier escalates to a worse level than baseline",
    )
    fail_on_new_critical_findings: bool = Field(
        default=True,
        description="Flag regression if candidate introduces any new HIGH or CRITICAL severity findings",
    )
    prohibited_finding_codes: list[str] = Field(
        default_factory=lambda: ["SECRET_EXPOSURE", "CYCLE_DETECTED"],
        description="Specific finding codes that automatically fail candidate evaluation if present",
    )
    min_overall_score: float = Field(
        default=75.0,
        ge=0.0,
        le=100.0,
        description="Absolute floor for candidate overall score, independent of baseline",
    )
    min_safety_score: float = Field(
        default=90.0,
        ge=0.0,
        le=100.0,
        description="Absolute floor for candidate safety domain score",
    )


class RegressionViolation(BaseModel):
    rule: str = Field(description="Policy rule identifier that was breached")
    severity: FindingSeverity = Field(description="Severity level of the violation")
    message: str = Field(description="Explanatory violation message")
    baseline_value: Any = Field(default=None, description="Value observed in baseline evaluation")
    candidate_value: Any = Field(default=None, description="Value observed in candidate evaluation")
    threshold: Any = Field(default=None, description="Policy threshold enforced")


class RegressionCheckRequest(BaseModel):
    baseline_evaluation_id: UUID = Field(description="ID of baseline evaluation run")
    candidate_evaluation_id: UUID = Field(description="ID of candidate evaluation run to test")
    policy: RegressionPolicy | None = Field(
        default=None,
        description="Optional custom regression policy. If omitted, standard policy is applied.",
    )


class RegressionReport(BaseModel):
    status: RegressionStatus = Field(description="Overall regression status verdict")
    is_regression: bool = Field(
        description="True if regression detected exceeding quality thresholds"
    )
    baseline_evaluation_id: UUID = Field(description="Baseline evaluation ID")
    candidate_evaluation_id: UUID = Field(description="Candidate evaluation ID")
    policy_applied: RegressionPolicy = Field(description="Policy evaluated against")
    overall_score_delta: float = Field(
        description="Signed overall score delta (candidate - baseline)"
    )
    risk_transition: str = Field(description="Risk tier transition summary (e.g. GOOD -> POOR)")
    violations: list[RegressionViolation] = Field(
        default_factory=list,
        description="List of detected policy rule violations",
    )
    violations_count: int = Field(description="Total number of violations detected")
    critical_violations_count: int = Field(
        description="Total number of HIGH or CRITICAL severity violations detected",
    )
    evaluated_at: datetime = Field(description="Timestamp when regression audit was executed")
