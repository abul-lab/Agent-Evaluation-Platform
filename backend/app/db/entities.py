"""Database table entities for trace persistence."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class TraceRecord(SQLModel, table=True):
    """Database entity representing an ingested agent execution trace."""

    __tablename__ = "traces"

    trace_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    workspace_id: UUID | None = Field(
        default=None,
        foreign_key="workspaces.workspace_id",
        nullable=True,
        index=True,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
    filename: str | None = Field(default=None, nullable=True)
    framework: str = Field(nullable=False, max_length=64)
    workflow_status: str = Field(nullable=False, max_length=64)
    step_count: int = Field(default=0, nullable=False)
    raw_trace: str = Field(nullable=False)
    schema_version: str = Field(default="1.0.0", nullable=False, max_length=32)


class EvaluationRecord(SQLModel, table=True):
    """Database entity representing an evaluation run outcome and scorecard."""

    __tablename__ = "evaluations"

    evaluation_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    workspace_id: UUID | None = Field(
        default=None,
        foreign_key="workspaces.workspace_id",
        nullable=True,
        index=True,
    )
    trace_id: UUID = Field(
        foreign_key="traces.trace_id",
        index=True,
        nullable=False,
    )
    status: str = Field(
        default="COMPLETED",
        nullable=False,
        max_length=32,
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: datetime | None = Field(
        default=None,
        nullable=True,
    )
    finding_count: int = Field(
        default=0,
        nullable=False,
    )
    overall_score: float = Field(
        default=0.0,
        nullable=False,
    )
    risk_classification: str = Field(
        nullable=False,
        max_length=32,
    )
    scorecard_json: str = Field(
        nullable=False,
    )
    findings_json: str = Field(
        default="[]",
        nullable=False,
    )
    semantic_json: str | None = Field(
        default=None,
        nullable=True,
    )


class PolicyRecord(SQLModel, table=True):
    """Database entity representing a persistent evaluation governance policy."""

    __tablename__ = "policies"

    policy_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    name: str = Field(
        nullable=False,
        unique=True,
        index=True,
        max_length=128,
    )
    description: str = Field(
        default="",
        nullable=False,
    )
    is_active: bool = Field(
        default=True,
        nullable=False,
    )
    is_default: bool = Field(
        default=False,
        nullable=False,
    )
    rules_json: str = Field(
        nullable=False,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )


class WorkspaceRecord(SQLModel, table=True):
    """Database entity representing an organizational workspace boundary."""

    __tablename__ = "workspaces"

    workspace_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    name: str = Field(
        nullable=False,
        unique=True,
        index=True,
        max_length=128,
    )
    slug: str = Field(
        nullable=False,
        unique=True,
        index=True,
        max_length=64,
    )
    description: str = Field(
        default="",
        nullable=False,
    )
    is_default: bool = Field(
        default=False,
        nullable=False,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )


class WorkspaceMemberRecord(SQLModel, table=True):
    """Database entity representing workspace team membership and RBAC role."""

    __tablename__ = "workspace_members"

    member_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    workspace_id: UUID = Field(
        foreign_key="workspaces.workspace_id",
        index=True,
        nullable=False,
    )
    user_email: str = Field(
        nullable=False,
        index=True,
        max_length=256,
    )
    role: str = Field(
        default="ENGINEER",
        nullable=False,
        max_length=32,
    )
    joined_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )


class WorkspaceAuditLogRecord(SQLModel, table=True):
    """Database entity representing an audit log entry for workspace governance."""

    __tablename__ = "workspace_audit_logs"

    log_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    workspace_id: UUID = Field(
        foreign_key="workspaces.workspace_id",
        index=True,
        nullable=False,
    )
    actor_email: str = Field(
        nullable=False,
        max_length=256,
    )
    action: str = Field(
        nullable=False,
        max_length=64,
    )
    resource_type: str = Field(
        nullable=False,
        max_length=64,
    )
    resource_id: str = Field(
        nullable=False,
        max_length=128,
    )
    details_json: str = Field(
        default="{}",
        nullable=False,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )


class APIKeyRecord(SQLModel, table=True):
    """Database entity representing a hashed API key for service account authentication."""

    __tablename__ = "api_keys"

    key_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    workspace_id: UUID = Field(
        foreign_key="workspaces.workspace_id",
        index=True,
        nullable=False,
    )
    name: str = Field(
        nullable=False,
        max_length=128,
    )
    hashed_key: str = Field(
        nullable=False,
        index=True,
        max_length=128,
    )
    key_prefix: str = Field(
        nullable=False,
        max_length=16,
    )
    role: str = Field(
        default="ENGINEER",
        nullable=False,
        max_length=32,
    )
    created_by: str = Field(
        default="system",
        nullable=False,
        max_length=256,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
    expires_at: datetime | None = Field(
        default=None,
        nullable=True,
    )
    last_used_at: datetime | None = Field(
        default=None,
        nullable=True,
    )
    is_active: bool = Field(
        default=True,
        nullable=False,
    )


class NotificationChannelRecord(SQLModel, table=True):
    """Database entity representing an alert destination webhook channel."""

    __tablename__ = "notification_channels"

    channel_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    workspace_id: UUID = Field(
        foreign_key="workspaces.workspace_id",
        index=True,
        nullable=False,
    )
    name: str = Field(
        nullable=False,
        max_length=128,
    )
    channel_type: str = Field(
        nullable=False,
        max_length=32,
    )
    webhook_url: str = Field(
        nullable=False,
        max_length=1024,
    )
    events_json: str = Field(
        default="[]",
        nullable=False,
    )
    is_active: bool = Field(
        default=True,
        nullable=False,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )


class NotificationDeliveryRecord(SQLModel, table=True):
    """Database entity representing a notification delivery attempt and diagnostic."""

    __tablename__ = "notification_deliveries"

    delivery_id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    workspace_id: UUID = Field(
        foreign_key="workspaces.workspace_id",
        index=True,
        nullable=False,
    )
    channel_id: UUID = Field(
        foreign_key="notification_channels.channel_id",
        index=True,
        nullable=False,
    )
    event_type: str = Field(
        nullable=False,
        max_length=64,
    )
    status: str = Field(
        nullable=False,
        max_length=32,
    )
    http_status: int | None = Field(
        default=None,
        nullable=True,
    )
    error_message: str | None = Field(
        default=None,
        nullable=True,
        max_length=1024,
    )
    payload_preview: str | None = Field(
        default=None,
        nullable=True,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
