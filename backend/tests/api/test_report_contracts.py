"""Contract tests verifying Report and Export generation across all 6 Golden Fixtures."""

import csv
import io
import json
from pathlib import Path

from fastapi.testclient import TestClient

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_fixture_dict(filename: str) -> dict[str, object]:
    """Helper to load a fixture JSON file as a dictionary."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def prepare_evaluation_id(client: TestClient, fixture_name: str) -> str:
    """Helper to upload a fixture and execute its evaluation, returning evaluation_id."""
    payload = load_fixture_dict(fixture_name)
    upload_res = client.post("/api/v1/traces/upload", json=payload)
    assert upload_res.status_code == 201
    trace_id = upload_res.json()["trace_id"]

    eval_res = client.post("/api/v1/evaluations/run", json={"trace_id": trace_id})
    assert eval_res.status_code == 200
    return str(eval_res.json()["evaluation_id"])


def test_clean_success_trace_export_contract(client: TestClient) -> None:
    """Contract: clean_success_trace exports JSON, Markdown, CSV with EXCELLENT risk and 0 findings."""
    eval_id = prepare_evaluation_id(client, "clean_success_trace.json")

    # JSON
    json_res = client.get(f"/api/v1/evaluations/{eval_id}/export/json")
    assert json_res.status_code == 200
    json_data = json_res.json()
    assert json_data["summary"]["risk_classification"] == "EXCELLENT"
    assert len(json_data["findings"]) == 0

    # Markdown
    md_res = client.get(f"/api/v1/evaluations/{eval_id}/export/markdown")
    assert md_res.status_code == 200
    assert "EXCELLENT" in md_res.text
    assert "No findings detected" in md_res.text
    assert "| Task Quality |" in md_res.text

    # CSV
    csv_res = client.get(f"/api/v1/evaluations/{eval_id}/export/csv")
    assert csv_res.status_code == 200
    rows = list(csv.DictReader(io.StringIO(csv_res.text)))
    assert len(rows) == 0


def test_loop_trace_export_contract(client: TestClient) -> None:
    """Contract: loop_trace exports contain CYCLE_DETECTED in JSON, Markdown, and CSV."""
    eval_id = prepare_evaluation_id(client, "loop_trace.json")

    json_res = client.get(f"/api/v1/evaluations/{eval_id}/export/json")
    assert json_res.status_code == 200
    codes = [f["code"] for f in json_res.json()["findings"]]
    assert "CYCLE_DETECTED" in codes

    md_res = client.get(f"/api/v1/evaluations/{eval_id}/export/markdown")
    assert md_res.status_code == 200
    assert "CYCLE_DETECTED" in md_res.text

    csv_res = client.get(f"/api/v1/evaluations/{eval_id}/export/csv")
    assert csv_res.status_code == 200
    rows = list(csv.DictReader(io.StringIO(csv_res.text)))
    assert any(r["finding_code"] == "CYCLE_DETECTED" for r in rows)


def test_hallucinated_tool_trace_export_contract(client: TestClient) -> None:
    """Contract: hallucinated_tool_trace exports contain HALLUCINATED_TOOL."""
    eval_id = prepare_evaluation_id(client, "hallucinated_tool_trace.json")

    json_res = client.get(f"/api/v1/evaluations/{eval_id}/export/json")
    assert json_res.status_code == 200
    codes = [f["code"] for f in json_res.json()["findings"]]
    assert "HALLUCINATED_TOOL" in codes

    md_res = client.get(f"/api/v1/evaluations/{eval_id}/export/markdown")
    assert md_res.status_code == 200
    assert "HALLUCINATED_TOOL" in md_res.text

    csv_res = client.get(f"/api/v1/evaluations/{eval_id}/export/csv")
    assert csv_res.status_code == 200
    rows = list(csv.DictReader(io.StringIO(csv_res.text)))
    assert any(r["finding_code"] == "HALLUCINATED_TOOL" for r in rows)


def test_retry_storm_trace_export_contract(client: TestClient) -> None:
    """Contract: retry_storm_trace exports contain RETRY_STORM."""
    eval_id = prepare_evaluation_id(client, "retry_storm_trace.json")

    json_res = client.get(f"/api/v1/evaluations/{eval_id}/export/json")
    assert json_res.status_code == 200
    codes = [f["code"] for f in json_res.json()["findings"]]
    assert "RETRY_STORM" in codes

    md_res = client.get(f"/api/v1/evaluations/{eval_id}/export/markdown")
    assert md_res.status_code == 200
    assert "RETRY_STORM" in md_res.text

    csv_res = client.get(f"/api/v1/evaluations/{eval_id}/export/csv")
    assert csv_res.status_code == 200
    rows = list(csv.DictReader(io.StringIO(csv_res.text)))
    assert any(r["finding_code"] == "RETRY_STORM" for r in rows)


def test_budget_exceeded_trace_export_contract(client: TestClient) -> None:
    """Contract: budget_exceeded_trace exports contain BUDGET_EXCEEDED."""
    eval_id = prepare_evaluation_id(client, "budget_exceeded_trace.json")

    json_res = client.get(f"/api/v1/evaluations/{eval_id}/export/json")
    assert json_res.status_code == 200
    codes = [f["code"] for f in json_res.json()["findings"]]
    assert "BUDGET_EXCEEDED" in codes

    md_res = client.get(f"/api/v1/evaluations/{eval_id}/export/markdown")
    assert md_res.status_code == 200
    assert "BUDGET_EXCEEDED" in md_res.text

    csv_res = client.get(f"/api/v1/evaluations/{eval_id}/export/csv")
    assert csv_res.status_code == 200
    rows = list(csv.DictReader(io.StringIO(csv_res.text)))
    assert any(r["finding_code"] == "BUDGET_EXCEEDED" for r in rows)


def test_secret_leak_trace_export_contract(client: TestClient) -> None:
    """Contract: secret_leak_trace exports contain SECRET_EXPOSURE and CRITICAL risk."""
    eval_id = prepare_evaluation_id(client, "secret_leak_trace.json")

    json_res = client.get(f"/api/v1/evaluations/{eval_id}/export/json")
    assert json_res.status_code == 200
    assert json_res.json()["summary"]["risk_classification"] == "CRITICAL"

    md_res = client.get(f"/api/v1/evaluations/{eval_id}/export/markdown")
    assert md_res.status_code == 200
    assert "CRITICAL" in md_res.text
    assert "SECRET_EXPOSURE" in md_res.text

    csv_res = client.get(f"/api/v1/evaluations/{eval_id}/export/csv")
    assert csv_res.status_code == 200
    rows = list(csv.DictReader(io.StringIO(csv_res.text)))
    assert any(r["finding_code"] == "SECRET_EXPOSURE" for r in rows)
