"""Integration tests for NotificationService alerting hub, retry handling, and audit logging."""

import httpx
from sqlmodel import Session

from app.schemas.notification_api import (
    NotificationChannelCreateRequest,
    NotificationChannelType,
    NotificationChannelUpdateRequest,
    NotificationEventType,
)
from app.services.notification_service import (
    NotificationEvent,
    NotificationService,
)
from app.services.workspace_service import WorkspaceService


def test_channel_crud_lifecycle(db_session: Session) -> None:
    """Verify channel creation, listing, updating, and deletion."""
    ws_service = WorkspaceService(db_session)
    ws = ws_service.get_default_workspace()

    service = NotificationService(db_session)

    # 1. Create channel
    create_req = NotificationChannelCreateRequest(
        name="Production Ops Slack",
        channel_type=NotificationChannelType.SLACK,
        webhook_url="https://hooks.slack.com/services/T00/B00/X00",
        events=[NotificationEventType.POLICY_REJECTED, NotificationEventType.SECRET_EXPOSURE],
        is_active=True,
    )
    ch = service.create_channel(ws.workspace_id, create_req, actor_email="admin@example.com")
    assert ch.name == "Production Ops Slack"
    assert ch.channel_type == NotificationChannelType.SLACK
    assert len(ch.events) == 2

    # 2. List channels
    channels = service.list_channels(ws.workspace_id)
    assert len(channels) == 1
    assert channels[0].channel_id == ch.channel_id

    # 3. Update channel
    up_req = NotificationChannelUpdateRequest(
        name="Renamed Slack Channel",
        is_active=False,
    )
    updated = service.update_channel(channels[0].channel_id, up_req)
    assert updated.name == "Renamed Slack Channel"
    assert updated.is_active is False

    # 4. Delete channel
    deleted = service.delete_channel(channels[0].channel_id)
    assert deleted is True
    assert len(service.list_channels(ws.workspace_id)) == 0


def test_test_alert_delivery_and_audit(db_session: Session) -> None:
    """Verify sending test alerts generates delivery records and audit logs."""
    ws_service = WorkspaceService(db_session)
    ws = ws_service.get_default_workspace()

    # Mock HTTP client returning 200
    mock_transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"ok": True}))
    mock_client = httpx.Client(transport=mock_transport)

    service = NotificationService(db_session, http_client=mock_client)

    create_req = NotificationChannelCreateRequest(
        name="Teams Release Gate",
        channel_type=NotificationChannelType.TEAMS,
        webhook_url="https://outlook.office.com/webhook/test",
        events=[],
        is_active=True,
    )
    ch = service.create_channel(ws.workspace_id, create_req)

    # Send test alert
    test_res = service.send_test_alert(ch.channel_id, custom_message="Smoke test alert")
    assert test_res.success is True
    assert test_res.http_status == 200

    # Verify delivery record
    deliveries = service.list_delivery_history(ws.workspace_id)
    assert len(deliveries) == 1
    assert deliveries[0].status == "DELIVERED"
    assert deliveries[0].event_type == "TEST_ALERT"

    # Verify audit log
    logs = ws_service.list_audit_logs(ws.workspace_id)
    test_log = next((item for item in logs if item.action == "notification_test"), None)
    assert test_log is not None
    assert test_log.details["success"] is True


def test_retry_and_failure_diagnostics(db_session: Session) -> None:
    """Verify retry handling and failure recording when webhook endpoint returns 500."""
    ws_service = WorkspaceService(db_session)
    ws = ws_service.get_default_workspace()

    # Mock HTTP client returning 500 error
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(500, text="Internal Server Error")
    )
    mock_client = httpx.Client(transport=mock_transport)

    service = NotificationService(db_session, http_client=mock_client)

    create_req = NotificationChannelCreateRequest(
        name="Flaky Webhook",
        channel_type=NotificationChannelType.WEBHOOK,
        webhook_url="https://flaky.webhook.service/events",
        events=[],
        is_active=True,
    )
    service.create_channel(ws.workspace_id, create_req)

    # Dispatch event
    event = NotificationEvent(
        event_type=NotificationEventType.EVALUATION_FAILED,
        workspace_id=ws.workspace_id,
        workspace_name=ws.name,
        severity="CRITICAL",
        title="Agent Execution Timeout",
        reason="Exceeded maximum runtime",
    )
    deliveries = service.dispatch_event(ws.workspace_id, event)

    assert len(deliveries) == 1
    assert deliveries[0].status == "FAILED"
    assert deliveries[0].http_status == 500
    assert "Internal Server Error" in (deliveries[0].error_message or "")

    # Verify audit failure record
    logs = ws_service.list_audit_logs(ws.workspace_id)
    failed_log = next((item for item in logs if item.action == "notification_failed"), None)
    assert failed_log is not None


def test_event_subscription_filtering(db_session: Session) -> None:
    """Verify channels only receive events they are subscribed to."""
    ws_service = WorkspaceService(db_session)
    ws = ws_service.get_default_workspace()

    mock_transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"received": True}))
    mock_client = httpx.Client(transport=mock_transport)
    service = NotificationService(db_session, http_client=mock_client)

    # Channel 1: Subscribed ONLY to SECRET_EXPOSURE
    service.create_channel(
        ws.workspace_id,
        NotificationChannelCreateRequest(
            name="Security Only",
            channel_type=NotificationChannelType.SLACK,
            webhook_url="https://security.slack.webhook",
            events=[NotificationEventType.SECRET_EXPOSURE],
        ),
    )

    # Channel 2: Subscribed to ALL events (empty list)
    service.create_channel(
        ws.workspace_id,
        NotificationChannelCreateRequest(
            name="General Alerts",
            channel_type=NotificationChannelType.TEAMS,
            webhook_url="https://general.teams.webhook",
            events=[],
        ),
    )

    # Dispatch POLICY_APPROVED (Channel 1 should be skipped; Channel 2 should receive)
    appr_event = NotificationEvent(
        event_type=NotificationEventType.POLICY_APPROVED,
        workspace_id=ws.workspace_id,
        workspace_name=ws.name,
        severity="APPROVED",
        title="Gate Cleared",
        reason="Passed",
    )
    deliveries = service.dispatch_event(ws.workspace_id, appr_event)
    assert len(deliveries) == 1

    # Dispatch SECRET_EXPOSURE (Both channels should receive)
    sec_event = NotificationEvent(
        event_type=NotificationEventType.SECRET_EXPOSURE,
        workspace_id=ws.workspace_id,
        workspace_name=ws.name,
        severity="CRITICAL",
        title="Secret Leaked",
        reason="API Token exposed",
    )
    deliveries_sec = service.dispatch_event(ws.workspace_id, sec_event)
    assert len(deliveries_sec) == 2
