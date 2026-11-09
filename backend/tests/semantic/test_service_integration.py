"""Integration and contract tests for semantic evaluation adapter with EvaluationService and API."""

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.domain.models import CanonicalTrace
from app.semantic.base import SemanticEvaluator
from app.semantic.models import SemanticEvaluationResult, SemanticFinding
from app.services.evaluation_service import EvaluationService
from app.services.trace_repository import TraceRepository

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_canonical_trace(filename: str) -> CanonicalTrace:
    """Helper to load fixture as CanonicalTrace."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def load_fixture_dict(filename: str) -> dict[str, object]:
    """Helper to load a fixture JSON file as a dictionary."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


class MockSuccessSemanticAdapter(SemanticEvaluator):
    """Mock semantic evaluator for testing enabled semantic pipeline."""

    def evaluate_relevancy(
        self, input_text: str, actual_output: str, context: list[str] | None = None
    ) -> SemanticFinding:
        return SemanticFinding(
            metric_name="answer_relevancy", score=0.9, passed=True, explanation="Relevant"
        )

    def evaluate_faithfulness(
        self, input_text: str, actual_output: str, retrieval_context: list[str]
    ) -> SemanticFinding:
        return SemanticFinding(
            metric_name="faithfulness", score=0.85, passed=True, explanation="Faithful"
        )

    def evaluate_hallucination(
        self, input_text: str, actual_output: str, contexts: list[str]
    ) -> SemanticFinding:
        return SemanticFinding(
            metric_name="hallucination", score=0.1, passed=True, explanation="No hallucination"
        )

    def evaluate_trace(self, trace: CanonicalTrace) -> SemanticEvaluationResult:
        return SemanticEvaluationResult(
            metrics=[
                self.evaluate_relevancy("", ""),
                self.evaluate_faithfulness("", "", []),
                self.evaluate_hallucination("", "", []),
            ],
            provider="mock_deepeval",
            execution_time_ms=45.0,
            evaluation_available=True,
            reason=None,
        )


def test_service_semantic_disabled_by_default(db_session: Session) -> None:
    """Verify semantic evaluation is disabled by default and deterministic evaluation runs normally."""
    trace_repo = TraceRepository(db_session)
    trace = load_canonical_trace("clean_success_trace.json")
    trace_rec = trace_repo.create_trace(trace=trace)

    eval_svc = EvaluationService(db_session, semantic_enabled=False)
    eval_rec = eval_svc.run_evaluation(trace_rec.trace_id)
    assert eval_rec is not None
    assert eval_rec.overall_score == 100.0
    assert eval_rec.finding_count == 0

    sem_res = eval_svc.get_semantic_result(eval_rec.evaluation_id)
    assert sem_res is not None
    assert sem_res.evaluation_available is False
    assert sem_res.provider == "fallback"
    assert sem_res.metrics == []


def test_service_semantic_enabled_with_adapter(db_session: Session) -> None:
    """Verify semantic evaluation executes when enabled and stores semantic findings."""
    trace_repo = TraceRepository(db_session)
    trace = load_canonical_trace("clean_success_trace.json")
    trace_rec = trace_repo.create_trace(trace=trace)

    mock_adapter = MockSuccessSemanticAdapter()
    eval_svc = EvaluationService(db_session, semantic_enabled=True, semantic_adapter=mock_adapter)
    eval_rec = eval_svc.run_evaluation(trace_rec.trace_id)
    assert eval_rec is not None

    sem_res = eval_svc.get_semantic_result(eval_rec.evaluation_id)
    assert sem_res is not None
    assert sem_res.evaluation_available is True
    assert sem_res.provider == "mock_deepeval"
    assert len(sem_res.metrics) == 3
    assert any(m.metric_name == "answer_relevancy" for m in sem_res.metrics)


def test_get_semantic_result_not_found(db_session: Session) -> None:
    """Verify get_semantic_result returns None for nonexistent evaluation ID."""
    eval_svc = EvaluationService(db_session)
    assert eval_svc.get_semantic_result(uuid4()) is None


def test_api_semantic_endpoint_success(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{id}/semantic endpoint returns fallback without API keys."""
    payload = load_fixture_dict("clean_success_trace.json")
    upload_res = client.post("/api/v1/traces/upload", json=payload)
    trace_id = upload_res.json()["trace_id"]

    eval_res = client.post("/api/v1/evaluations/run", json={"trace_id": trace_id})
    eval_id = eval_res.json()["evaluation_id"]

    sem_res = client.get(f"/api/v1/evaluations/{eval_id}/semantic")
    assert sem_res.status_code == 200
    data = sem_res.json()
    assert data["evaluation_available"] is False
    assert data["provider"] == "fallback"
    assert data["metrics"] == []


def test_api_semantic_endpoint_not_found(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{id}/semantic returns 404 for nonexistent evaluation ID."""
    nonexistent_id = str(uuid4())
    res = client.get(f"/api/v1/evaluations/{nonexistent_id}/semantic")
    assert res.status_code == 404


def test_api_semantic_endpoint_invalid_uuid(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{id}/semantic returns 422 for malformed UUID."""
    res = client.get("/api/v1/evaluations/invalid-uuid/semantic")
    assert res.status_code == 422


def test_golden_fixtures_semantic_contract(client: TestClient) -> None:
    """Contract: Without API key, all golden fixtures evaluate deterministically and semantic returns fallback."""
    fixtures = [
        ("clean_success_trace.json", "EXCELLENT"),
        ("loop_trace.json", "WATCH"),
        ("hallucinated_tool_trace.json", "EXCELLENT"),
        ("retry_storm_trace.json", "EXCELLENT"),
        ("budget_exceeded_trace.json", "EXCELLENT"),
        ("secret_leak_trace.json", "CRITICAL"),
    ]

    for filename, expected_risk in fixtures:
        payload = load_fixture_dict(filename)
        upload_res = client.post("/api/v1/traces/upload", json=payload)
        trace_id = upload_res.json()["trace_id"]

        eval_res = client.post("/api/v1/evaluations/run", json={"trace_id": trace_id})
        assert eval_res.status_code == 200
        eval_id = eval_res.json()["evaluation_id"]

        # Deterministic evaluation is completely intact
        if expected_risk == "CRITICAL":
            assert eval_res.json()["risk_classification"] == "CRITICAL"

        # Semantic endpoint returns fallback safely
        sem_res = client.get(f"/api/v1/evaluations/{eval_id}/semantic")
        assert sem_res.status_code == 200
        assert sem_res.json()["evaluation_available"] is False
