"""Notifications and Alerting Hub Service.

Coordinates dispatching alerts across Microsoft Teams, Slack, and Generic Webhooks
with structured payloads, retry resiliency, failure diagnostics, and audit tracking.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from sqlmodel import Session, col, select

from app.core.webhook_security import assert_resolves_publicly, mask_webhook_url, scrub_webhook_url
from app.db.entities import (
    NotificationChannelRecord,
    NotificationDeliveryRecord,
    WorkspaceRecord,
)
from app.schemas.notification_api import (
    NotificationChannelCreateRequest,
    NotificationChannelResponse,
    NotificationChannelType,
    NotificationChannelUpdateRequest,
    NotificationDeliveryResponse,
    NotificationDeliveryStatus,
    NotificationEventType,
    NotificationTestResponse,
)
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)


@dataclass
class NotificationEvent:
    """Represents a unified alerting event ready for multi-channel formatting and delivery."""

    event_type: NotificationEventType
    workspace_id: UUID
    workspace_name: str
    severity: str  # "CRITICAL", "WARNING", "INFO", "APPROVED", "REJECTED"
    title: str
    reason: str
    risk_tier: str | None = None
    evaluation_id: str | None = None
    trace_id: str | None = None
    policy_name: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    link: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def format_teams_payload(event: NotificationEvent) -> dict[str, Any]:
    """Format alert as a Microsoft Teams MessageCard / Connector payload."""
    color_map = {
        "CRITICAL": "DC2626",
        "REJECTED": "DC2626",
        "WARNING": "D97706",
        "APPROVED": "16A34A",
        "INFO": "2563EB",
    }
    theme_color = color_map.get(event.severity.upper(), "2563EB")

    facts: list[dict[str, str]] = [
        {"name": "Workspace:", "value": event.workspace_name},
    ]
    if event.evaluation_id:
        facts.append({"name": "Evaluation:", "value": str(event.evaluation_id)})
    if event.policy_name:
        facts.append({"name": "Policy:", "value": event.policy_name})
    if event.reason:
        facts.append({"name": "Reason:", "value": event.reason})
    if event.risk_tier:
        facts.append({"name": "Risk:", "value": event.risk_tier})

    card: dict[str, Any] = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "themeColor": theme_color,
        "summary": f"[{event.event_type.value}] {event.title}",
        "title": event.title,
        "sections": [
            {
                "activityTitle": f"**Agent Evaluation Platform Alert: {event.title}**",
                "activitySubtitle": f"Timestamp: {event.timestamp}",
                "facts": facts,
                "markdown": True,
            }
        ],
    }

    if event.link:
        card["potentialAction"] = [
            {
                "@type": "OpenUri",
                "name": "View Evaluation",
                "targets": [{"os": "default", "uri": event.link}],
            }
        ]

    return card


def format_slack_payload(event: NotificationEvent) -> dict[str, Any]:
    """Format alert as a Slack Block Kit payload with color-coded severity."""
    color_map = {
        "CRITICAL": "#DC2626",
        "REJECTED": "#DC2626",
        "WARNING": "#D97706",
        "APPROVED": "#16A34A",
        "INFO": "#2563EB",
    }
    color = color_map.get(event.severity.upper(), "#2563EB")

    fields: list[dict[str, str]] = [
        {"type": "mrkdwn", "text": f"*Workspace:*\n{event.workspace_name}"},
        {"type": "mrkdwn", "text": f"*Event:*\n`{event.event_type.value}`"},
    ]
    if event.evaluation_id:
        fields.append({"type": "mrkdwn", "text": f"*Evaluation:*\n`{event.evaluation_id}`"})
    if event.policy_name:
        fields.append({"type": "mrkdwn", "text": f"*Policy:*\n{event.policy_name}"})
    if event.reason:
        fields.append({"type": "mrkdwn", "text": f"*Reason:*\n{event.reason}"})
    if event.risk_tier:
        fields.append({"type": "mrkdwn", "text": f"*Risk Tier:*\n*{event.risk_tier}*"})

    header_icon = "🚨" if event.severity in ("CRITICAL", "REJECTED") else "ℹ️"
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{header_icon} {event.title[:140]}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Agent Evaluation Platform notification for *{event.workspace_name}*.",
            },
        },
        {
            "type": "section",
            "fields": fields,
        },
    ]

    if event.link:
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Evaluation ↗", "emoji": True},
                        "url": event.link,
                        "style": "primary" if event.severity in ("APPROVED", "INFO") else "danger",
                    }
                ],
            }
        )

    return {"attachments": [{"color": color, "blocks": blocks}]}


def format_webhook_payload(event: NotificationEvent) -> dict[str, Any]:
    """Format alert as a structured JSON webhook payload."""
    return {
        "event_type": event.event_type.value,
        "workspace_id": str(event.workspace_id),
        "workspace": event.workspace_name,
        "severity": event.severity,
        "title": event.title,
        "reason": event.reason,
        "risk": event.risk_tier,
        "evaluation_id": event.evaluation_id,
        "trace_id": event.trace_id,
        "policy_name": event.policy_name,
        "details": event.details,
        "link": event.link,
        "timestamp": event.timestamp,
    }


def _to_uuid(val: UUID | str) -> UUID:
    """Coerce string or UUID into UUID instance."""
    return val if isinstance(val, UUID) else UUID(str(val))


class NotificationService:
    """Manages workspace notification channels, alert dispatching, and delivery records."""

    def __init__(self, session: Session, http_client: httpx.Client | None = None) -> None:
        self.session = session
        self._http_client = http_client

    def _get_client(self) -> httpx.Client:
        return self._http_client or httpx.Client(timeout=5.0)

    def _to_channel_response(
        self, record: NotificationChannelRecord
    ) -> NotificationChannelResponse:
        events_list: list[NotificationEventType] = []
        if record.events_json:
            try:
                raw_events = json.loads(record.events_json)
                events_list = [
                    NotificationEventType(e)
                    for e in raw_events
                    if e in NotificationEventType.__members__
                ]
            except Exception:
                events_list = []

        return NotificationChannelResponse(
            channel_id=str(record.channel_id),
            workspace_id=str(record.workspace_id),
            name=record.name,
            channel_type=NotificationChannelType(record.channel_type),
            webhook_url_masked=mask_webhook_url(record.webhook_url),
            events=events_list,
            is_active=record.is_active,
            created_at=record.created_at.isoformat(),
            updated_at=record.updated_at.isoformat(),
        )

    def create_channel(
        self,
        workspace_id: UUID | str,
        req: NotificationChannelCreateRequest,
        actor_email: str = "admin@example.com",
    ) -> NotificationChannelResponse:
        """Create a new notification destination channel."""
        ws_id = _to_uuid(workspace_id)
        workspace = self.session.get(WorkspaceRecord, ws_id)
        if not workspace:
            raise ValueError(f"Workspace {workspace_id} not found")

        events_serialized = json.dumps([e.value for e in req.events])
        record = NotificationChannelRecord(
            workspace_id=ws_id,
            name=req.name,
            channel_type=req.channel_type.value,
            webhook_url=req.webhook_url,
            events_json=events_serialized,
            is_active=req.is_active,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)

        # Audit log
        ws_service = WorkspaceService(self.session)
        ws_service.log_activity(
            workspace_id=ws_id,
            actor_email=actor_email,
            action="notification_channel_created",
            resource_type="NOTIFICATION_CHANNEL",
            resource_id=str(record.channel_id),
            details={"name": record.name, "type": record.channel_type},
        )
        self.session.commit()

        return self._to_channel_response(record)

    def list_channels(self, workspace_id: UUID | str) -> list[NotificationChannelResponse]:
        """List all notification channels configured for a workspace."""
        ws_id = _to_uuid(workspace_id)
        records = self.session.exec(
            select(NotificationChannelRecord)
            .where(NotificationChannelRecord.workspace_id == ws_id)
            .order_by(col(NotificationChannelRecord.created_at).desc())
        ).all()
        return [self._to_channel_response(r) for r in records]

    def get_channel(self, channel_id: UUID | str) -> NotificationChannelRecord | None:
        """Retrieve a notification channel record by ID."""
        ch_id = _to_uuid(channel_id)
        return self.session.get(NotificationChannelRecord, ch_id)

    def update_channel(
        self,
        channel_id: UUID | str,
        req: NotificationChannelUpdateRequest,
        actor_email: str = "admin@example.com",
    ) -> NotificationChannelResponse:
        """Update an existing notification channel."""
        ch_id = _to_uuid(channel_id)
        record = self.session.get(NotificationChannelRecord, ch_id)
        if not record:
            raise ValueError(f"Notification channel {channel_id} not found")

        if req.name is not None:
            record.name = req.name
        if req.webhook_url is not None:
            record.webhook_url = req.webhook_url
        if req.events is not None:
            record.events_json = json.dumps([e.value for e in req.events])
        if req.is_active is not None:
            record.is_active = req.is_active

        record.updated_at = datetime.now(UTC)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)

        ws_service = WorkspaceService(self.session)
        ws_service.log_activity(
            workspace_id=record.workspace_id,
            actor_email=actor_email,
            action="notification_channel_updated",
            resource_type="NOTIFICATION_CHANNEL",
            resource_id=str(record.channel_id),
            details={"name": record.name, "is_active": record.is_active},
        )
        self.session.commit()

        return self._to_channel_response(record)

    def delete_channel(
        self,
        channel_id: UUID | str,
        actor_email: str = "admin@example.com",
    ) -> bool:
        """Delete a notification channel."""
        ch_id = _to_uuid(channel_id)
        record = self.session.get(NotificationChannelRecord, ch_id)
        if not record:
            return False

        workspace_id = record.workspace_id
        channel_name = record.name

        self.session.delete(record)
        self.session.commit()

        ws_service = WorkspaceService(self.session)
        ws_service.log_activity(
            workspace_id=workspace_id,
            actor_email=actor_email,
            action="notification_channel_deleted",
            resource_type="NOTIFICATION_CHANNEL",
            resource_id=str(ch_id),
            details={"name": channel_name},
        )
        self.session.commit()
        return True

    def _deliver_payload(
        self,
        webhook_url: str,
        payload: dict[str, Any],
        max_retries: int = 1,
    ) -> tuple[bool, int | None, str | None]:
        """Post a payload to a webhook with timeout and retry backoff."""
        try:
            assert_resolves_publicly(webhook_url)
        except ValueError as exc:
            return False, None, scrub_webhook_url(str(exc), webhook_url)
        client = self._get_client()
        last_error: str | None = None
        last_status: int | None = None

        for attempt in range(max_retries + 1):
            try:
                res = client.post(
                    webhook_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "AEP-Alerting-Hub/1.1",
                    },
                )
                last_status = res.status_code
                if 200 <= res.status_code < 300:
                    return True, res.status_code, None
                last_error = scrub_webhook_url(
                    f"HTTP {res.status_code}: {res.text[:200]}", webhook_url
                )
            except httpx.TimeoutException as exc:
                last_error = f"Timeout error: {exc}"
            except Exception as exc:
                last_error = f"Delivery failed: {exc}"
            last_error = scrub_webhook_url(last_error, webhook_url)

            if attempt < max_retries:
                time.sleep(0.15 * (attempt + 1))

        return False, last_status, last_error

    def send_test_alert(
        self,
        channel_id: UUID | str,
        custom_message: str | None = None,
        actor_email: str = "admin@example.com",
    ) -> NotificationTestResponse:
        """Send an immediate test alert to verify webhook integration."""
        ch_id = _to_uuid(channel_id)
        channel = self.session.get(NotificationChannelRecord, ch_id)
        if not channel:
            raise ValueError(f"Notification channel {channel_id} not found")

        workspace = self.session.get(WorkspaceRecord, channel.workspace_id)
        ws_name = workspace.name if workspace else "Default Workspace"

        test_event = NotificationEvent(
            event_type=NotificationEventType.EVALUATION_COMPLETED,
            workspace_id=channel.workspace_id,
            workspace_name=ws_name,
            severity="INFO",
            title=custom_message or "Channel Test Alert — Agent Evaluation Platform",
            reason="Operator initiated channel diagnostic test",
            risk_tier="NOMINAL",
            evaluation_id="test-eval-00000000",
            details={"diagnostic": True, "actor": actor_email},
            link="http://localhost:3000/workspaces",
        )

        # Format based on channel type
        if channel.channel_type == NotificationChannelType.TEAMS.value:
            payload = format_teams_payload(test_event)
        elif channel.channel_type == NotificationChannelType.SLACK.value:
            payload = format_slack_payload(test_event)
        else:
            payload = format_webhook_payload(test_event)

        success, status_code, error_msg = self._deliver_payload(
            channel.webhook_url,
            payload,
            max_retries=1,
        )

        # Log delivery
        delivery = NotificationDeliveryRecord(
            workspace_id=channel.workspace_id,
            channel_id=channel.channel_id,
            event_type="TEST_ALERT",
            status=NotificationDeliveryStatus.DELIVERED.value
            if success
            else NotificationDeliveryStatus.FAILED.value,
            http_status=status_code,
            error_message=error_msg,
            payload_preview=json.dumps(payload)[:500],
            created_at=datetime.now(UTC),
        )
        self.session.add(delivery)

        # Audit log
        ws_service = WorkspaceService(self.session)
        ws_service.log_activity(
            workspace_id=channel.workspace_id,
            actor_email=actor_email,
            action="notification_test",
            resource_type="NOTIFICATION_CHANNEL",
            resource_id=str(channel.channel_id),
            details={
                "channel_name": channel.name,
                "channel_type": channel.channel_type,
                "success": success,
                "http_status": status_code,
                "error": error_msg,
            },
        )
        self.session.commit()

        return NotificationTestResponse(
            success=success,
            http_status=status_code,
            error_message=error_msg,
            details={"channel_type": channel.channel_type, "channel_name": channel.name},
        )

    def dispatch_event(
        self,
        workspace_id: UUID | str,
        event: NotificationEvent,
    ) -> list[NotificationDeliveryRecord]:
        """Dispatch a notification event to all active matching channels in the workspace."""
        ws_id = _to_uuid(workspace_id)
        channels = self.session.exec(
            select(NotificationChannelRecord).where(
                NotificationChannelRecord.workspace_id == ws_id,
                NotificationChannelRecord.is_active == True,  # noqa: E712
            )
        ).all()

        deliveries: list[NotificationDeliveryRecord] = []
        ws_service = WorkspaceService(self.session)

        for channel in channels:
            # Check subscription filter
            if channel.events_json:
                try:
                    subscribed = json.loads(channel.events_json)
                    if subscribed and event.event_type.value not in subscribed:
                        continue
                except Exception:
                    pass

            # Format payload
            if channel.channel_type == NotificationChannelType.TEAMS.value:
                payload = format_teams_payload(event)
            elif channel.channel_type == NotificationChannelType.SLACK.value:
                payload = format_slack_payload(event)
            else:
                payload = format_webhook_payload(event)

            success, status_code, error_msg = self._deliver_payload(
                channel.webhook_url,
                payload,
                max_retries=1,
            )

            status_str = (
                NotificationDeliveryStatus.DELIVERED.value
                if success
                else NotificationDeliveryStatus.FAILED.value
            )

            delivery = NotificationDeliveryRecord(
                workspace_id=ws_id,
                channel_id=channel.channel_id,
                event_type=event.event_type.value,
                status=status_str,
                http_status=status_code,
                error_message=error_msg,
                payload_preview=json.dumps(payload)[:500],
                created_at=datetime.now(UTC),
            )
            self.session.add(delivery)
            deliveries.append(delivery)

            # Audit log
            audit_action = "notification_sent" if success else "notification_failed"
            ws_service.log_activity(
                workspace_id=ws_id,
                actor_email="system@aep.alerting",
                action=audit_action,
                resource_type="NOTIFICATION_CHANNEL",
                resource_id=str(channel.channel_id),
                details={
                    "event_type": event.event_type.value,
                    "channel_name": channel.name,
                    "channel_type": channel.channel_type,
                    "success": success,
                    "http_status": status_code,
                    "error": error_msg,
                },
            )

        self.session.commit()
        return deliveries

    def list_delivery_history(
        self,
        workspace_id: UUID | str,
        limit: int = 50,
    ) -> list[NotificationDeliveryResponse]:
        """Fetch recent delivery attempts and diagnostics for a workspace."""
        ws_id = _to_uuid(workspace_id)
        deliveries = self.session.exec(
            select(NotificationDeliveryRecord)
            .where(NotificationDeliveryRecord.workspace_id == ws_id)
            .order_by(col(NotificationDeliveryRecord.created_at).desc())
            .limit(limit)
        ).all()

        channels_map = {
            c.channel_id: c
            for c in self.session.exec(
                select(NotificationChannelRecord).where(
                    NotificationChannelRecord.workspace_id == ws_id
                )
            ).all()
        }

        results: list[NotificationDeliveryResponse] = []
        for d in deliveries:
            ch = channels_map.get(d.channel_id)
            results.append(
                NotificationDeliveryResponse(
                    delivery_id=str(d.delivery_id),
                    workspace_id=str(d.workspace_id),
                    channel_id=str(d.channel_id),
                    channel_name=ch.name if ch else "Unknown Channel",
                    channel_type=NotificationChannelType(ch.channel_type) if ch else None,
                    event_type=d.event_type,
                    status=d.status,
                    http_status=d.http_status,
                    error_message=d.error_message,
                    payload_preview=d.payload_preview,
                    created_at=d.created_at.isoformat(),
                )
            )

        return results
