"""Integration tests for Evaluation Lifecycle API endpoints."""

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_fixture_dict(filename: str) -> dict[str, object]:
    """Helper to load a fixture JSON file as a dictionary."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def upload_trace_fixture(client: TestClient, filename: str) -> str:
    """Helper to upload a golden trace and return its trace_id string."""
    payload = load_fixture_dict(filename)
    response = client.post("/api/v1/traces/upload", json=payload)
    assert response.status_code == 201
    return str(response.json()["trace_id"])


def test_run_evaluation_success(client: TestClient) -> None:
    """Verify POST /api/v1/evaluations/run successfully evaluates a stored trace."""
    trace_id = upload_trace_fixture(client, "clean_success_trace.json")

    response = client.post("/api/v1/evaluations/run", json={"trace_id": trace_id})
    assert response.status_code == 200

    data = response.json()
    assert "evaluation_id" in data
    assert data["status"] == "COMPLETED"
    assert data["finding_count"] == 0
    assert data["overall_score"] == 100.0
    assert data["risk_classification"] == "EXCELLENT"


def test_run_evaluation_missing_trace_returns_404(client: TestClient) -> None:
    """Verify POST /api/v1/evaluations/run returns 404 when trace_id does not exist."""
    nonexistent_id = str(uuid4())
    response = client.post("/api/v1/evaluations/run", json={"trace_id": nonexistent_id})
    assert response.status_code == 404
    assert f"Trace with ID '{nonexistent_id}' not found." in response.json()["detail"]


def test_run_evaluation_invalid_uuid_returns_422(client: TestClient) -> None:
    """Verify POST /api/v1/evaluations/run returns 422 for malformed UUID string."""
    response = client.post("/api/v1/evaluations/run", json={"trace_id": "not-a-valid-uuid"})
    assert response.status_code == 422


def test_get_evaluation_summary_success(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{evaluation_id} returns the evaluation run summary."""
    trace_id = upload_trace_fixture(client, "clean_success_trace.json")
    run_resp = client.post("/api/v1/evaluations/run", json={"trace_id": trace_id})
    eval_id = run_resp.json()["evaluation_id"]

    response = client.get(f"/api/v1/evaluations/{eval_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["evaluation_id"] == eval_id
    assert data["trace_id"] == trace_id
    assert data["status"] == "COMPLETED"
    assert data["finding_count"] == 0
    assert data["overall_score"] == 100.0
    assert data["risk_classification"] == "EXCELLENT"
    assert "started_at" in data
    assert "completed_at" in data


def test_get_evaluation_summary_not_found_returns_404(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{evaluation_id} returns 404 when ID does not exist."""
    nonexistent_id = str(uuid4())
    response = client.get(f"/api/v1/evaluations/{nonexistent_id}")
    assert response.status_code == 404
    assert f"Evaluation with ID '{nonexistent_id}' not found." in response.json()["detail"]


def test_get_evaluation_summary_invalid_uuid_returns_422(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{evaluation_id} returns 422 for invalid UUID."""
    response = client.get("/api/v1/evaluations/invalid-id")
    assert response.status_code == 422


def test_get_scorecard_success(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{evaluation_id}/scorecard returns the complete Scorecard."""
    trace_id = upload_trace_fixture(client, "clean_success_trace.json")
    run_resp = client.post("/api/v1/evaluations/run", json={"trace_id": trace_id})
    eval_id = run_resp.json()["evaluation_id"]

    response = client.get(f"/api/v1/evaluations/{eval_id}/scorecard")
    assert response.status_code == 200

    data = response.json()
    assert "scorecard_id" in data
    assert "workflow_id" in data
    assert data["overall_score"] == 100.0
    assert data["risk_classification"] == "EXCELLENT"

    # All 7 domains must be present
    for domain in (
        "task_quality",
        "tool_usage",
        "workflow_quality",
        "reliability",
        "safety",
        "cost",
        "efficiency",
    ):
        assert domain in data
        assert data[domain]["score"] == 100.0
        assert data[domain]["status"] == "PASS"


def test_get_scorecard_not_found_returns_404(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{evaluation_id}/scorecard returns 404 when not found."""
    nonexistent_id = str(uuid4())
    response = client.get(f"/api/v1/evaluations/{nonexistent_id}/scorecard")
    assert response.status_code == 404


def test_get_findings_success(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{evaluation_id}/findings returns detected findings."""
    trace_id = upload_trace_fixture(client, "loop_trace.json")
    run_resp = client.post("/api/v1/evaluations/run", json={"trace_id": trace_id})
    eval_id = run_resp.json()["evaluation_id"]

    response = client.get(f"/api/v1/evaluations/{eval_id}/findings")
    assert response.status_code == 200

    findings = response.json()
    assert isinstance(findings, list)
    assert len(findings) >= 1
    codes = [f["code"] for f in findings]
    assert "CYCLE_DETECTED" in codes


def test_get_findings_not_found_returns_404(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{evaluation_id}/findings returns 404 when not found."""
    nonexistent_id = str(uuid4())
    response = client.get(f"/api/v1/evaluations/{nonexistent_id}/findings")
    assert response.status_code == 404
