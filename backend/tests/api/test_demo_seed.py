"""Tests for showcase demo workspace seeding endpoint."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.entities import (
    APIKeyRecord,
    EvaluationRecord,
    NotificationChannelRecord,
    PolicyRecord,
    TraceRecord,
)


def test_seed_demo_workspace_endpoint(client: TestClient, db_session: Session) -> None:
    """Test seeding demo workspace generates all showcase entities."""
    resp = client.post("/api/v1/workspaces/demo/seed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "demo-workspace"
    assert data["traces_seeded"] >= 6
    assert data["evaluations_seeded"] >= 6
    assert data["policies_seeded"] >= 2
    assert data["channels_seeded"] >= 2
    assert data["status"] == "ready"

    ws_id = UUID(data["workspace_id"])

    # Verify database persistence
    traces = db_session.exec(select(TraceRecord).where(TraceRecord.workspace_id == ws_id)).all()
    assert len(traces) >= 6

    evals = db_session.exec(
        select(EvaluationRecord).where(EvaluationRecord.workspace_id == ws_id)
    ).all()
    assert len(evals) >= 6

    policies = db_session.exec(select(PolicyRecord)).all()
    assert len(policies) >= 2

    channels = db_session.exec(
        select(NotificationChannelRecord).where(NotificationChannelRecord.workspace_id == ws_id)
    ).all()
    assert len(channels) >= 2

    keys = db_session.exec(select(APIKeyRecord).where(APIKeyRecord.workspace_id == ws_id)).all()
    assert len(keys) >= 1
