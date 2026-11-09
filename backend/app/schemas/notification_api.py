"""Pydantic schemas for the Notifications and Alerting Hub."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.webhook_security import validate_webhook_url


class NotificationChannelType(StrEnum):
    """Supported notification delivery channel types."""

    TEAMS = "TEAMS"
    SLACK = "SLACK"
    WEBHOOK = "WEBHOOK"


class NotificationEventType(StrEnum):
    """Supported governance, evaluation, and security alerting events."""

    EVALUATION_COMPLETED = "EVALUATION_COMPLETED"
    EVALUATION_FAILED = "EVALUATION_FAILED"
    REGRESSION_DETECTED = "REGRESSION_DETECTED"
    POLICY_APPROVED = "POLICY_APPROVED"
    POLICY_REJECTED = "POLICY_REJECTED"
    SECRET_EXPOSURE = "SECRET_EXPOSURE"
    CRITICAL_FINDING = "CRITICAL_FINDING"
    API_KEY_CREATED = "API_KEY_CREATED"
    API_KEY_REVOKED = "API_KEY_REVOKED"


class NotificationDeliveryStatus(StrEnum):
    """Delivery status outcomes for notification dispatches."""

    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class NotificationChannelCreateRequest(BaseModel):
    """Payload to configure a new workspace notification channel."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128, description="Channel display name")
    channel_type: NotificationChannelType = Field(description="Destination provider type")
    webhook_url: str = Field(
        min_length=8, max_length=1024, description="Target webhook URL endpoint (https only)"
    )
    events: list[NotificationEventType] = Field(
        default_factory=list,
        description="Subscribed event types. Empty list subscribes to all events.",
    )
    is_active: bool = Field(default=True, description="Whether this channel is enabled")

    @field_validator("webhook_url")
    @classmethod
    def _check_webhook_url(cls, value: str) -> str:
        return validate_webhook_url(value)


class NotificationChannelUpdateRequest(BaseModel):
    """Payload to update an existing workspace notification channel."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=128)
    webhook_url: str | None = Field(default=None, min_length=8, max_length=1024)
    events: list[NotificationEventType] | None = None
    is_active: bool | None = None

    @field_validator("webhook_url")
    @classmethod
    def _check_webhook_url(cls, value: str | None) -> str | None:
        return validate_webhook_url(value) if value is not None else None


class NotificationChannelResponse(BaseModel):
    """Public representation of a configured notification channel."""

    channel_id: str
    workspace_id: str
    name: str
    channel_type: NotificationChannelType
    webhook_url_masked: str = Field(description="Destination host with the secret path masked")
    events: list[NotificationEventType]
    is_active: bool
    created_at: str
    updated_at: str


class NotificationDeliveryResponse(BaseModel):
    """Public representation of a notification delivery attempt."""

    delivery_id: str
    workspace_id: str
    channel_id: str
    channel_name: str | None = None
    channel_type: NotificationChannelType | None = None
    event_type: str
    status: str
    http_status: int | None = None
    error_message: str | None = None
    payload_preview: str | None = None
    created_at: str


class NotificationTestRequest(BaseModel):
    """Payload to trigger an immediate test notification."""

    model_config = ConfigDict(extra="forbid")

    custom_message: str | None = Field(
        default=None,
        description="Optional custom text for the test alert",
    )


class NotificationTestResponse(BaseModel):
    """Result of a test notification delivery."""

    success: bool
    http_status: int | None = None
    error_message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
