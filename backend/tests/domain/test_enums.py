"""Unit tests for Canonical Agent Trace Schema enums."""

import pytest

from app.domain.enums import (
    FrameworkType,
    OrchestratorType,
    RetryResolution,
    RiskClassification,
    WorkflowStatus,
)


def test_framework_type_members() -> None:
    """Verify all supported framework types exist."""
    expected = {
        "LANGGRAPH",
        "CREWAI",
        "AUTOGEN",
        "SEMANTIC_KERNEL",
        "OPENTELEMETRY",
        "MCP",
        "CUSTOM",
    }
    actual = {m.value for m in FrameworkType}
    assert actual == expected


def test_workflow_status_members() -> None:
    """Verify all workflow termination statuses exist."""
    expected = {
        "SUCCESS",
        "FAILED",
        "TIMEOUT",
        "BUDGET_EXCEEDED",
        "UNHANDLED_EXCEPTION",
    }
    actual = {m.value for m in WorkflowStatus}
    assert actual == expected


def test_orchestrator_type_members() -> None:
    """Verify all workflow orchestration topologies exist."""
    expected = {
        "DIRECTED_ACYCLIC_GRAPH",
        "STATE_MACHINE",
        "AUTONOMOUS_SWARM",
        "SEQUENTIAL_CHAIN",
    }
    actual = {m.value for m in OrchestratorType}
    assert actual == expected


def test_retry_resolution_members() -> None:
    """Verify retry resolution outcomes."""
    expected = {"RESOLVED", "EXHAUSTED", "ABORTED"}
    actual = {m.value for m in RetryResolution}
    assert actual == expected


def test_risk_classification_members() -> None:
    """Verify risk classification tiers."""
    expected = {"EXCELLENT", "GOOD", "WATCH", "POOR", "CRITICAL"}
    actual = {m.value for m in RiskClassification}
    assert actual == expected


def test_invalid_enum_instantiation() -> None:
    """Verify invalid values raise ValueError."""
    with pytest.raises(ValueError):
        FrameworkType("INVALID_FRAMEWORK")

    with pytest.raises(ValueError):
        WorkflowStatus("INVALID_STATUS")

    with pytest.raises(ValueError):
        OrchestratorType("INVALID_ORCHESTRATOR")

    with pytest.raises(ValueError):
        RetryResolution("INVALID_RESOLUTION")

    with pytest.raises(ValueError):
        RiskClassification("INVALID_TIER")
