"""Integration tests for analytics endpoint GET /api/v1/analytics/trends."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.domain.models import CanonicalTrace
from app.services.evaluation_service import EvaluationService
from app.services.trace_repository import TraceRepository

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_fixture_json(filename: str) -> dict[str, object]:
    """Helper to load fixture json."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def test_get_analytics_trends_endpoint_empty(client: TestClient) -> None:
    """Verify GET /api/v1/analytics/trends returns valid response when database has no evaluations."""
    response = client.get("/api/v1/analytics/trends?days=30")
    assert response.status_code == 200
    data = response.json()
    assert data["total_evaluations"] == 0
    assert data["average_score"] == 0.0
    assert data["score_trend_direction"] == "STABLE"
    assert data["daily_metrics"] == []


def test_get_analytics_trends_endpoint_populated(client: TestClient, db_session: Session) -> None:
    """Verify GET /api/v1/analytics/trends returns computed analytics when data exists."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)

    trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    t = trace_repo.create_trace(trace)
    eval_service.run_evaluation(t.trace_id)

    response = client.get("/api/v1/analytics/trends?days=30")
    assert response.status_code == 200
    data = response.json()

    assert data["total_evaluations"] >= 1
    assert data["average_score"] > 0
    assert len(data["daily_metrics"]) >= 1
    assert "task_quality" in data["domain_averages"]
