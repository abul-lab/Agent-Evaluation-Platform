"""Integration tests for benchmark endpoints POST /benchmarks/compare and GET /benchmarks/summary."""

import json
from pathlib import Path
from uuid import uuid4

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


def test_compare_evaluations_endpoint_404(client: TestClient) -> None:
    """Verify POST /api/v1/benchmarks/compare returns 404 when evaluations are not found."""
    payload = {
        "base_evaluation_id": str(uuid4()),
        "target_evaluation_id": str(uuid4()),
    }
    response = client.post("/api/v1/benchmarks/compare", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_compare_evaluations_endpoint_success(client: TestClient, db_session: Session) -> None:
    """Verify POST /api/v1/benchmarks/compare returns HTTP 200 and comprehensive comparison payload."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)

    clean_trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    loop_trace = CanonicalTrace.model_validate(load_fixture_json("loop_trace.json"))

    t_clean = trace_repo.create_trace(clean_trace)
    t_loop = trace_repo.create_trace(loop_trace)

    e_clean = eval_service.run_evaluation(t_clean.trace_id)
    e_loop = eval_service.run_evaluation(t_loop.trace_id)
    assert e_clean is not None
    assert e_loop is not None

    payload = {
        "base_evaluation_id": str(e_loop.evaluation_id),
        "target_evaluation_id": str(e_clean.evaluation_id),
    }
    response = client.post("/api/v1/benchmarks/compare", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["base_evaluation_id"] == str(e_loop.evaluation_id)
    assert data["target_evaluation_id"] == str(e_clean.evaluation_id)
    assert data["overall_score_delta"] > 0
    assert data["risk_transition"]["is_improved"] is True
    assert "workflow_quality" in data["domain_deltas"]
    assert data["finding_delta"]["resolved_count"] > 0


def test_benchmark_summary_endpoint(client: TestClient, db_session: Session) -> None:
    """Verify GET /api/v1/benchmarks/summary returns aggregated leaderboard."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)

    trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    t = trace_repo.create_trace(trace)
    eval_service.run_evaluation(t.trace_id)

    response = client.get("/api/v1/benchmarks/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["total_evaluations"] >= 1
    assert data["mean_score"] > 0
    assert len(data["leaderboard"]) >= 1
    assert data["leaderboard"][0]["rank"] == 1
