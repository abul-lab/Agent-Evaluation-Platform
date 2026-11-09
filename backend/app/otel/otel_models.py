"""OpenTelemetry (OTEL) data models for agent execution traces.

Provides lightweight, flexible models representing OTEL spans, events,
resources, and traces before normalization into Canonical Agent Trace Schema (CATS).
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OTELEvent(BaseModel):
    """An event recorded within an OpenTelemetry span."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1, description="Event name, e.g. exception or tool_call")
    time_unix_nano: int | None = Field(
        default=None, description="Event timestamp in unix nanoseconds"
    )
    timestamp: str | None = Field(default=None, description="ISO8601 timestamp string if provided")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Event attributes")


class OTELLink(BaseModel):
    """Causal link to another OpenTelemetry span."""

    model_config = ConfigDict(extra="ignore")

    trace_id: str | None = Field(default=None, description="Linked trace identifier")
    span_id: str | None = Field(default=None, description="Linked span identifier")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Link attributes")


class OTELStatus(BaseModel):
    """Status of an OpenTelemetry span."""

    model_config = ConfigDict(extra="ignore")

    status_code: str = Field(default="UNSET", description="Status code: OK, ERROR, or UNSET")
    description: str | None = Field(default=None, description="Status error description if failed")


class OTELSpan(BaseModel):
    """A single execution unit or step within an OpenTelemetry trace."""

    model_config = ConfigDict(extra="ignore")

    trace_id: str = Field(default="", description="Root trace identifier")
    span_id: str = Field(..., min_length=1, description="Unique span identifier")
    parent_span_id: str | None = Field(
        default=None, description="Parent span ID for DAG reconstruction"
    )
    name: str = Field(..., min_length=1, description="Span operation name or agent step name")
    kind: str | None = Field(
        default="INTERNAL", description="Span kind: INTERNAL, CLIENT, SERVER, etc."
    )
    start_time: str | int | float | None = Field(default=None, description="Span start timestamp")
    end_time: str | int | float | None = Field(default=None, description="Span end timestamp")
    status: OTELStatus | str | dict[str, Any] = Field(
        default_factory=OTELStatus, description="Execution status"
    )
    attributes: dict[str, Any] = Field(default_factory=dict, description="Semantic attributes")
    events: list[OTELEvent] = Field(default_factory=list, description="Span events")
    links: list[OTELLink] = Field(default_factory=list, description="Span links")


class OTELResource(BaseModel):
    """Metadata describing the entity generating the OpenTelemetry trace."""

    model_config = ConfigDict(extra="ignore")

    attributes: dict[str, Any] = Field(default_factory=dict, description="Resource attributes")


class OTELTrace(BaseModel):
    """A complete OpenTelemetry trace container with resource metadata and spans."""

    model_config = ConfigDict(extra="ignore")

    trace_id: str = Field(default="", description="Global trace identifier")
    resource: OTELResource = Field(
        default_factory=OTELResource, description="Service and environment metadata"
    )
    spans: list[OTELSpan] = Field(
        default_factory=list, description="All spans belonging to this trace"
    )


class OTELIngestResponse(BaseModel):
    """API response model after successful OTEL ingestion and CATS persistence."""

    model_config = ConfigDict(extra="forbid")

    trace_id: UUID = Field(..., description="Persisted CATS trace identifier")
    session_id: UUID = Field(..., description="Normalized session identifier")
    workflow_id: UUID = Field(..., description="Workflow execution identifier")
    step_count: int = Field(..., ge=0, description="Total translated workflow steps")
    workflow_status: str = Field(..., description="Normalized workflow termination status")
    detected_framework: str = Field(..., description="Auto-detected agent framework")
    stored: bool = Field(default=True, description="Persistence confirmation")
