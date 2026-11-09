"""Integration tests for regression detection REST endpoints."""

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.domain.models import CanonicalTrace

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_fixture_json(filename: str) -> dict[str, object]:
    """Helper to load fixture json."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def test_get_default_policy(client: TestClient) -> None:
    """Verify retrieval of default standard regression policy."""
    response = client.get("/api/v1/regressions/policy/default")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Standard Quality Gate"
    assert data["max_score_drop"] == 5.0
    assert data["max_domain_drop"] == 10.0
    assert data["fail_on_risk_escalation"] is True
    assert "SECRET_EXPOSURE" in data["prohibited_finding_codes"]


def test_check_regression_not_found_returns_404(client: TestClient) -> None:
    """Verify 404 returned when evaluations are not found."""
    payload = {
        "baseline_evaluation_id": str(uuid4()),
        "candidate_evaluation_id": str(uuid4()),
    }
    response = client.post("/api/v1/regressions/check", json=payload)
    assert response.status_code == 404


def test_check_regression_success(client: TestClient) -> None:
    """Verify successful regression audit over uploaded traces."""
    # 1. Upload clean and loop traces
    clean_data = load_fixture_json("clean_success_trace.json")
    CanonicalTrace.model_validate(clean_data)
    r_clean = client.post("/api/v1/traces/upload", json=clean_data)
    assert r_clean.status_code == 201
    clean_trace_id = r_clean.json()["trace_id"]

    loop_data = load_fixture_json("loop_trace.json")
    CanonicalTrace.model_validate(loop_data)
    r_loop = client.post("/api/v1/traces/upload", json=loop_data)
    assert r_loop.status_code == 201
    loop_trace_id = r_loop.json()["trace_id"]

    # 2. Run evaluations
    r_eval_clean = client.post("/api/v1/evaluations/run", json={"trace_id": clean_trace_id})
    assert r_eval_clean.status_code == 200
    clean_eval_id = r_eval_clean.json()["evaluation_id"]

    r_eval_loop = client.post("/api/v1/evaluations/run", json={"trace_id": loop_trace_id})
    assert r_eval_loop.status_code == 200
    loop_eval_id = r_eval_loop.json()["evaluation_id"]

    # 3. Check Regression: Clean vs Clean (Expect PASSED)
    check_pass = client.post(
        "/api/v1/regressions/check",
        json={
            "baseline_evaluation_id": clean_eval_id,
            "candidate_evaluation_id": clean_eval_id,
        },
    )
    assert check_pass.status_code == 200
    pass_report = check_pass.json()
    assert pass_report["status"] == "PASSED"
    assert pass_report["is_regression"] is False
    assert pass_report["violations_count"] == 0

    # 4. Check Regression: Clean vs Loop (Expect REGRESSED)
    check_regress = client.post(
        "/api/v1/regressions/check",
        json={
            "baseline_evaluation_id": clean_eval_id,
            "candidate_evaluation_id": loop_eval_id,
        },
    )
    assert check_regress.status_code == 200
    regress_report = check_regress.json()
    assert regress_report["status"] == "REGRESSED"
    assert regress_report["is_regression"] is True
    assert regress_report["violations_count"] > 0
    assert regress_report["critical_violations_count"] > 0
