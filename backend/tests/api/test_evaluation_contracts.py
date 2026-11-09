"""Contract tests evaluating all 6 Golden Fixtures through the REST API lifecycle."""

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_fixture_dict(filename: str) -> dict[str, Any]:
    """Helper to load a fixture JSON file as a dictionary."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def upload_and_run_evaluation(
    client: TestClient, fixture_name: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Uploads a golden trace fixture, triggers evaluation via API, and returns (summary, findings)."""
    payload = load_fixture_dict(fixture_name)
    upload_resp = client.post("/api/v1/traces/upload", json=payload)
    assert upload_resp.status_code == 201, f"Failed to upload fixture {fixture_name}"
    trace_id = upload_resp.json()["trace_id"]

    run_resp = client.post("/api/v1/evaluations/run", json={"trace_id": trace_id})
    assert run_resp.status_code == 200, f"Failed to run evaluation for {fixture_name}"
    eval_summary: dict[str, Any] = run_resp.json()
    eval_id = eval_summary["evaluation_id"]

    findings_resp = client.get(f"/api/v1/evaluations/{eval_id}/findings")
    assert findings_resp.status_code == 200
    findings: list[dict[str, Any]] = findings_resp.json()

    return eval_summary, findings


def test_clean_success_trace_contract(client: TestClient) -> None:
    """Contract: clean_success_trace must result in EXCELLENT risk classification."""
    summary, findings = upload_and_run_evaluation(client, "clean_success_trace.json")

    assert summary["risk_classification"] == "EXCELLENT"
    assert summary["finding_count"] == 0
    assert summary["overall_score"] == 100.0
    assert len(findings) == 0


def test_loop_trace_contract(client: TestClient) -> None:
    """Contract: loop_trace evaluation must contain CYCLE_DETECTED finding."""
    summary, findings = upload_and_run_evaluation(client, "loop_trace.json")

    codes = [f["code"] for f in findings]
    assert "CYCLE_DETECTED" in codes
    assert summary["finding_count"] >= 1


def test_hallucinated_tool_trace_contract(client: TestClient) -> None:
    """Contract: hallucinated_tool_trace evaluation must contain HALLUCINATED_TOOL finding."""
    summary, findings = upload_and_run_evaluation(client, "hallucinated_tool_trace.json")

    codes = [f["code"] for f in findings]
    assert "HALLUCINATED_TOOL" in codes
    assert summary["finding_count"] >= 1


def test_retry_storm_trace_contract(client: TestClient) -> None:
    """Contract: retry_storm_trace evaluation must contain RETRY_STORM finding."""
    summary, findings = upload_and_run_evaluation(client, "retry_storm_trace.json")

    codes = [f["code"] for f in findings]
    assert "RETRY_STORM" in codes
    assert summary["finding_count"] >= 1


def test_budget_exceeded_trace_contract(client: TestClient) -> None:
    """Contract: budget_exceeded_trace evaluation must contain BUDGET_EXCEEDED finding."""
    summary, findings = upload_and_run_evaluation(client, "budget_exceeded_trace.json")

    codes = [f["code"] for f in findings]
    assert "BUDGET_EXCEEDED" in codes
    assert summary["finding_count"] >= 1


def test_secret_leak_trace_contract(client: TestClient) -> None:
    """Contract: secret_leak_trace must trigger Safety Hard Gate resulting in CRITICAL risk."""
    summary, findings = upload_and_run_evaluation(client, "secret_leak_trace.json")

    assert summary["risk_classification"] == "CRITICAL"
    codes = [f["code"] for f in findings]
    assert "SECRET_EXPOSURE" in codes
