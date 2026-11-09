"""API schemas for trace endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TraceValidationResponse(BaseModel):
    """Validation outcome response."""

    valid: bool = Field(..., description="Whether the trace conforms to CATS")
    step_count: int = Field(..., description="Total execution steps in trace")
    workflow_status: str = Field(..., description="Status of the workflow run")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal warnings if any")


class TraceUploadResponse(BaseModel):
    """Trace upload and persistence response."""

    trace_id: UUID = Field(..., description="Unique identifier of persisted trace")
    stored: bool = Field(default=True, description="Whether persistence succeeded")
    step_count: int = Field(..., description="Total execution steps stored")
    workflow_status: str = Field(..., description="Status of the workflow run")


class TraceSummaryItem(BaseModel):
    """Metadata summary of a stored trace for collection listings."""

    trace_id: UUID = Field(..., description="Unique trace identifier")
    workflow_status: str = Field(..., description="Termination status of workflow")
    step_count: int = Field(..., description="Number of execution steps")
    created_at: datetime = Field(..., description="Ingestion timestamp in UTC")
    framework: str = Field(default="UNKNOWN", description="Agent framework name")


class TraceMetadataResponse(BaseModel):
    """Detailed metadata for a specific stored trace."""

    trace_id: UUID = Field(..., description="Unique trace identifier")
    created_at: datetime = Field(..., description="Ingestion timestamp in UTC")
    workflow_status: str = Field(..., description="Termination status of workflow")
    step_count: int = Field(..., description="Number of execution steps")
    framework: str = Field(default="UNKNOWN", description="Agent framework name")
