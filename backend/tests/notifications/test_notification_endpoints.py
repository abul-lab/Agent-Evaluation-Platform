"""API endpoint integration tests for notification channels and test alerting."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.services.workspace_service import WorkspaceService


def test_notification_channels_api_crud(client: TestClient, db_session: Session) -> None:
    """Verify HTTP CRUD endpoints for workspace notification channels."""
    ws_service = WorkspaceService(db_session)
    ws = ws_service.get_default_workspace()

    # 1. Create channel via API
    payload = {
        "name": "SecOps Slack",
        "channel_type": "SLACK",
        "webhook_url": "https://hooks.slack.com/services/SEC/OPS/001",
        "events": ["SECRET_EXPOSURE", "CRITICAL_FINDING"],
        "is_active": True,
    }
    res = client.post(f"/api/v1/workspaces/{ws.workspace_id}/notifications/channels", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "SecOps Slack"
    assert data["channel_type"] == "SLACK"
    assert len(data["events"]) == 2
    channel_id = data["channel_id"]

    # 2. List channels via API
    list_res = client.get(f"/api/v1/workspaces/{ws.workspace_id}/notifications/channels")
    assert list_res.status_code == 200
    channels = list_res.json()
    assert len(channels) == 1
    assert channels[0]["channel_id"] == channel_id

    # 3. Update channel via API
    up_res = client.put(
        f"/api/v1/workspaces/{ws.workspace_id}/notifications/channels/{channel_id}",
        json={"name": "SecOps Priority Alerts"},
    )
    assert up_res.status_code == 200
    assert up_res.json()["name"] == "SecOps Priority Alerts"

    # 4. List history (initially empty)
    hist_res = client.get(f"/api/v1/workspaces/{ws.workspace_id}/notifications/history")
    assert hist_res.status_code == 200
    assert isinstance(hist_res.json(), list)

    # 5. Delete channel via API
    del_res = client.delete(
        f"/api/v1/workspaces/{ws.workspace_id}/notifications/channels/{channel_id}"
    )
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

    # 6. Verify channel is gone
    list_res_after = client.get(f"/api/v1/workspaces/{ws.workspace_id}/notifications/channels")
    assert len(list_res_after.json()) == 0


def test_notification_channels_not_found_handling(client: TestClient, db_session: Session) -> None:
    """Verify 404 behavior for non-existent workspace or channel IDs."""
    fake_id = "00000000-0000-0000-0000-000000000000"

    # Non-existent workspace create
    res = client.post(
        f"/api/v1/workspaces/{fake_id}/notifications/channels",
        json={
            "name": "Invalid",
            "channel_type": "WEBHOOK",
            "webhook_url": "https://example.com/hook",
            "events": [],
            "is_active": True,
        },
    )
    assert res.status_code == 404

    # Non-existent channel delete
    del_res = client.delete(f"/api/v1/workspaces/{fake_id}/notifications/channels/{fake_id}")
    assert del_res.status_code == 404
