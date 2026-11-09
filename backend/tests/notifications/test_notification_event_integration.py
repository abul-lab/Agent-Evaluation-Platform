"""Integration tests verifying alerting event flows from policies and evaluations."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.entities import PolicyRecord
from app.domain.models import CanonicalTrace
from app.schemas.notification_api import (
    NotificationChannelCreateRequest,
    NotificationChannelType,
    NotificationEventType,
)
from app.services.evaluation_service import EvaluationService
from app.services.notification_service import NotificationService
from app.services.policy_service import PolicyService
from app.services.trace_repository import TraceRepository
from app.services.workspace_service import WorkspaceService

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "fixtures"


def load_fixture(name: str) -> dict[str, object]:
    with open(FIXTURES_DIR / name, encoding="utf-8") as f:
        data: dict[str, object] = json.load(f)
        return data


def test_policy_rejection_and_approval_alert_flow(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, db_session: Session
) -> None:
    """Verify that auditing an evaluation against a strict policy triggers alerts."""
    ws_service = WorkspaceService(db_session)
    ws = ws_service.get_default_workspace()

    # Capture delivered alerts via mock transport / monkeypatch
    delivered_payloads: list[dict[str, object]] = []

    def mock_post(self: Any, url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        content: Any = kwargs.get("content") or kwargs.get("json")
        if isinstance(content, (bytes, bytearray)):
            content = json.loads(content.decode("utf-8"))
        elif isinstance(content, str):
            content = json.loads(content)
        delivered_payloads.append(content)
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    notif_service = NotificationService(db_session)
    # Register channel for all events
    notif_service.create_channel(
        ws.workspace_id,
        NotificationChannelCreateRequest(
            name="Teams Governance Alerts",
            channel_type=NotificationChannelType.TEAMS,
            webhook_url="https://teams.office.com/webhook/test-gate",
            events=[NotificationEventType.POLICY_REJECTED, NotificationEventType.POLICY_APPROVED],
        ),
    )

    # Ingest clean trace and run evaluation
    trace_repo = TraceRepository(db_session)
    trace_data = load_fixture("clean_success_trace.json")
    trace = trace_repo.create_trace(CanonicalTrace.model_validate(trace_data))
    eval_service = EvaluationService(db_session)
    eval_record = eval_service.run_evaluation(trace.trace_id)
    assert eval_record is not None

    # Create a strict policy that rejects (requires min overall score 100)
    strict_policy = PolicyRecord(
        name="Ultra Strict Policy",
        description="Will reject nominal score",
        is_active=True,
        rules_json=json.dumps(
            {
                "min_overall_score": 100,
                "min_domain_scores": {"safety": 100},
                "disallowed_risk_tiers": ["CRITICAL", "POOR", "WATCH", "GOOD", "EXCELLENT"],
                "prohibited_finding_codes": [],
                "max_critical_findings": 0,
                "max_high_findings": 0,
                "require_semantic_evaluation": False,
            }
        ),
    )
    db_session.add(strict_policy)
    db_session.commit()
    db_session.refresh(strict_policy)

    policy_service = PolicyService(db_session)
    # Run audit which will reject
    audit_res = policy_service.audit_evaluation(strict_policy.policy_id, eval_record.evaluation_id)
    assert audit_res is not None and audit_res.verdict.value == "REJECTED"

    # Verify deliveries
    deliveries = notif_service.list_delivery_history(ws.workspace_id)
    rej_delivery = next((d for d in deliveries if d.event_type == "POLICY_REJECTED"), None)
    assert rej_delivery is not None
    assert rej_delivery.status == "DELIVERED"

    # Create lenient policy that approves
    lenient_policy = PolicyRecord(
        name="Permissive Release Policy",
        description="Always approves clean runs",
        is_active=True,
        rules_json=json.dumps(
            {
                "min_overall_score": 50,
                "min_domain_scores": {},
                "disallowed_risk_tiers": [],
                "prohibited_finding_codes": [],
                "max_critical_findings": 10,
                "max_high_findings": 10,
                "require_semantic_evaluation": False,
            }
        ),
    )
    db_session.add(lenient_policy)
    db_session.commit()
    db_session.refresh(lenient_policy)

    audit_res_ok = policy_service.audit_evaluation(
        lenient_policy.policy_id, eval_record.evaluation_id
    )
    assert audit_res_ok is not None and audit_res_ok.verdict.value == "APPROVED"

    deliveries_after = notif_service.list_delivery_history(ws.workspace_id)
    appr_delivery = next((d for d in deliveries_after if d.event_type == "POLICY_APPROVED"), None)
    assert appr_delivery is not None


def test_secret_exposure_and_critical_finding_alert_flow(
    monkeypatch: pytest.MonkeyPatch, db_session: Session
) -> None:
    """Verify that secret leak in trace generates SECRET_EXPOSURE and CRITICAL_FINDING alerts."""
    ws_service = WorkspaceService(db_session)
    ws = ws_service.get_default_workspace()

    delivered_payloads: list[dict[str, object]] = []

    def mock_post(self: Any, url: str, *args: Any, **kwargs: Any) -> httpx.Response:
        content: Any = kwargs.get("content") or kwargs.get("json")
        if isinstance(content, (bytes, bytearray)):
            content = json.loads(content.decode("utf-8"))
        elif isinstance(content, str):
            content = json.loads(content)
        delivered_payloads.append(content)
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    notif_service = NotificationService(db_session)

    notif_service.create_channel(
        ws.workspace_id,
        NotificationChannelCreateRequest(
            name="Slack Security Operations",
            channel_type=NotificationChannelType.SLACK,
            webhook_url="https://hooks.slack.com/services/SEC/OPS/ALERTS",
            events=[],  # All events
        ),
    )

    # Ingest secret leak trace
    trace_repo = TraceRepository(db_session)
    trace_data = load_fixture("secret_leak_trace.json")
    trace = trace_repo.create_trace(CanonicalTrace.model_validate(trace_data))

    eval_service = EvaluationService(db_session)
    eval_record = eval_service.run_evaluation(trace.trace_id)
    assert eval_record is not None
    assert eval_record.risk_classification == "CRITICAL"

    # Verify both SECRET_EXPOSURE and CRITICAL_FINDING events were dispatched
    deliveries = notif_service.list_delivery_history(ws.workspace_id)
    event_types = [d.event_type for d in deliveries]
    assert "SECRET_EXPOSURE" in event_types
    assert "CRITICAL_FINDING" in event_types
    assert "EVALUATION_COMPLETED" in event_types
