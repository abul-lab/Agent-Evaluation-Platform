"""Unit tests for Teams, Slack, and Webhook alert payload formatters."""

from uuid import uuid4

from app.schemas.notification_api import NotificationEventType
from app.services.notification_service import (
    NotificationEvent,
    format_slack_payload,
    format_teams_payload,
    format_webhook_payload,
)


def test_teams_payload_formatting() -> None:
    """Verify Microsoft Teams MessageCard schema conformance."""
    ws_id = uuid4()
    event = NotificationEvent(
        event_type=NotificationEventType.POLICY_REJECTED,
        workspace_id=ws_id,
        workspace_name="Production Agents",
        severity="CRITICAL",
        title="Evaluation Rejected — Release Gate",
        reason="SECRET_EXPOSURE",
        risk_tier="CRITICAL",
        evaluation_id="eval-12345",
        policy_name="Release Gate",
        link="http://localhost:3000/evaluations/eval-12345",
    )

    card = format_teams_payload(event)

    assert card["@type"] == "MessageCard"
    assert card["themeColor"] == "DC2626"
    assert "Evaluation Rejected" in card["title"]
    assert len(card["sections"]) == 1
    facts = card["sections"][0]["facts"]
    fact_dict = {f["name"]: f["value"] for f in facts}

    assert fact_dict["Workspace:"] == "Production Agents"
    assert fact_dict["Evaluation:"] == "eval-12345"
    assert fact_dict["Policy:"] == "Release Gate"
    assert fact_dict["Reason:"] == "SECRET_EXPOSURE"
    assert fact_dict["Risk:"] == "CRITICAL"

    assert len(card["potentialAction"]) == 1
    assert card["potentialAction"][0]["name"] == "View Evaluation"
    assert (
        card["potentialAction"][0]["targets"][0]["uri"]
        == "http://localhost:3000/evaluations/eval-12345"
    )


def test_slack_block_kit_payload_formatting() -> None:
    """Verify Slack Block Kit structure with color-coded severity."""
    ws_id = uuid4()
    event = NotificationEvent(
        event_type=NotificationEventType.SECRET_EXPOSURE,
        workspace_id=ws_id,
        workspace_name="Swarm Finance",
        severity="CRITICAL",
        title="Secret Exposure Detected",
        reason="High-entropy credential leaked in tool output",
        risk_tier="CRITICAL",
        evaluation_id="eval-sec-999",
        link="http://localhost:3000/evaluations/eval-sec-999",
    )

    slack_msg = format_slack_payload(event)

    assert "attachments" in slack_msg
    attachment = slack_msg["attachments"][0]
    assert attachment["color"] == "#DC2626"

    blocks = attachment["blocks"]
    assert len(blocks) >= 3
    assert blocks[0]["type"] == "header"
    assert "🚨" in blocks[0]["text"]["text"]
    assert blocks[1]["type"] == "section"
    assert blocks[2]["type"] == "section"
    assert "fields" in blocks[2]

    # Verify action button
    action_block = next((b for b in blocks if b["type"] == "actions"), None)
    assert action_block is not None
    assert action_block["elements"][0]["url"] == "http://localhost:3000/evaluations/eval-sec-999"


def test_webhook_structured_json_formatting() -> None:
    """Verify generic webhook structured JSON format."""
    ws_id = uuid4()
    event = NotificationEvent(
        event_type=NotificationEventType.POLICY_APPROVED,
        workspace_id=ws_id,
        workspace_name="Default Workspace",
        severity="APPROVED",
        title="Evaluation Approved",
        reason="Release Gate criteria satisfied",
        risk_tier="NOMINAL",
        evaluation_id="eval-app-111",
        trace_id="trace-777",
        policy_name="Strict Gate",
        details={"score": 95.0},
        link="http://localhost:3000/evaluations/eval-app-111",
    )

    payload = format_webhook_payload(event)

    assert payload["event_type"] == "POLICY_APPROVED"
    assert payload["workspace_id"] == str(ws_id)
    assert payload["workspace"] == "Default Workspace"
    assert payload["severity"] == "APPROVED"
    assert payload["evaluation_id"] == "eval-app-111"
    assert payload["trace_id"] == "trace-777"
    assert payload["policy_name"] == "Strict Gate"
    assert payload["details"]["score"] == 95.0
    assert payload["timestamp"] is not None
