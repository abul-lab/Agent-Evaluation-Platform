"""API schemas for evaluation workflow graph visualization."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class GraphNodeFinding(BaseModel):
    """Evaluation finding associated with a specific graph node/step."""

    finding_id: str = Field(..., description="Unique finding ID")
    severity: str = Field(..., description="Severity level: INFO, LOW, MEDIUM, HIGH, CRITICAL")
    code: str = Field(..., description="Machine-readable finding rule code")
    message: str = Field(..., description="Explanatory message describing the finding")


class GraphToolCall(BaseModel):
    """External tool execution record associated with a step node."""

    tool_call_id: UUID = Field(..., description="Unique tool call identifier")
    tool_name: str = Field(..., description="Name of the invoked tool")
    raw_arguments: dict[str, Any] = Field(
        default_factory=dict, description="Raw arguments passed to tool"
    )
    parsed_arguments: dict[str, Any] | None = Field(
        default=None, description="Parsed arguments if available"
    )
    execution_result: dict[str, Any] | None = Field(
        default=None, description="Output payload or execution result"
    )
    is_error: bool = Field(default=False, description="Whether tool execution failed")
    is_hallucinated: bool = Field(
        default=False, description="Whether tool was not present in registry"
    )
    is_redundant: bool = Field(
        default=False, description="Whether tool execution was an unnecessary duplicate"
    )
    execution_time_ms: int = Field(default=0, description="Tool execution duration in milliseconds")


class GraphRetry(BaseModel):
    """Fault-recovery retry record associated with a step node."""

    retry_id: UUID = Field(..., description="Unique retry execution identifier")
    attempt_number: int = Field(..., ge=1, description="Attempt number (1-indexed)")
    error_type: str = Field(..., description="Exception or error type that triggered retry")
    backoff_duration_ms: int = Field(
        default=0, description="Backoff sleep duration in milliseconds"
    )
    resolution: str = Field(..., description="Retry outcome: SUCCESS, FAILED, EXHAUSTED")


class WorkflowGraphNode(BaseModel):
    """Node representing an atomic step within an agent execution workflow graph."""

    id: str = Field(..., description="React Flow node identifier, e.g. step-0")
    step_id: UUID = Field(..., description="UUID of the underlying step")
    step_index: int = Field(..., ge=0, description="Zero-indexed chronological step sequence")
    node_name: str = Field(..., description="Semantic node name in the execution workflow")
    agent_id: UUID = Field(..., description="UUID of the agent responsible for this step")
    agent_name: str = Field(..., description="Display name of the agent executing this step")
    latency_ms: int = Field(default=0, ge=0, description="Step execution duration in milliseconds")
    token_usage: dict[str, int] = Field(
        default_factory=dict, description="Token consumption accounting breakdown"
    )
    input_state: dict[str, Any] = Field(
        default_factory=dict, description="Input state payload for this step"
    )
    output_state: dict[str, Any] = Field(
        default_factory=dict, description="Output state delta or result payload"
    )
    tool_calls: list[GraphToolCall] = Field(
        default_factory=list, description="Tool executions performed during step"
    )
    retries: list[GraphRetry] = Field(
        default_factory=list, description="Retry attempts executed during step"
    )
    findings: list[GraphNodeFinding] = Field(
        default_factory=list, description="Evaluation findings affecting this step"
    )
    is_cycle_node: bool = Field(
        default=False, description="Whether this node participates in an execution loop"
    )


class WorkflowGraphEdge(BaseModel):
    """Directed edge representing flow transition between workflow step nodes."""

    id: str = Field(..., description="Unique edge identifier, e.g. edge-step-0-step-1")
    source: str = Field(..., description="Source node identifier")
    target: str = Field(..., description="Target node identifier")
    is_cycle_edge: bool = Field(
        default=False, description="Whether this edge represents a cyclic loop transition"
    )
    label: str | None = Field(default=None, description="Optional transition label or condition")


class WorkflowGraphResponse(BaseModel):
    """Full workflow graph payload ready for React Flow visualization."""

    evaluation_id: UUID = Field(..., description="Unique identifier of the evaluation run")
    trace_id: UUID = Field(..., description="Unique identifier of the evaluated trace")
    workflow_id: UUID = Field(..., description="Unique identifier of the workflow execution")
    workflow_status: str = Field(..., description="Terminal workflow execution status")
    total_steps: int = Field(..., ge=0, description="Total number of steps in the workflow")
    has_cycles: bool = Field(
        default=False, description="Whether any cyclic execution loops were detected"
    )
    nodes: list[WorkflowGraphNode] = Field(
        default_factory=list, description="List of workflow graph nodes"
    )
    edges: list[WorkflowGraphEdge] = Field(
        default_factory=list, description="List of workflow graph edges"
    )
