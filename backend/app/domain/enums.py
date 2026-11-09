"""Canonical Agent Trace Schema (CATS) Enums.

Defines standard enumerations for framework classifications, workflow topologies,
execution termination statuses, retry resolutions, and risk tiers.
"""

from enum import StrEnum


class FrameworkType(StrEnum):
    """Supported agent framework orchestrator classifications."""

    LANGGRAPH = "LANGGRAPH"
    CREWAI = "CREWAI"
    AUTOGEN = "AUTOGEN"
    SEMANTIC_KERNEL = "SEMANTIC_KERNEL"
    OPENTELEMETRY = "OPENTELEMETRY"
    MCP = "MCP"
    CUSTOM = "CUSTOM"


class WorkflowStatus(StrEnum):
    """Termination status of a workflow run."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"


class OrchestratorType(StrEnum):
    """Workflow execution orchestration topology."""

    DIRECTED_ACYCLIC_GRAPH = "DIRECTED_ACYCLIC_GRAPH"
    STATE_MACHINE = "STATE_MACHINE"
    AUTONOMOUS_SWARM = "AUTONOMOUS_SWARM"
    SEQUENTIAL_CHAIN = "SEQUENTIAL_CHAIN"


class RetryResolution(StrEnum):
    """Outcome resolution of a retry sequence."""

    RESOLVED = "RESOLVED"
    EXHAUSTED = "EXHAUSTED"
    ABORTED = "ABORTED"


class RiskClassification(StrEnum):
    """Evaluation risk tier based on composite scores and safety gates."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    WATCH = "WATCH"
    POOR = "POOR"
    CRITICAL = "CRITICAL"
