"""Integration tests for Report and Export API endpoints."""

import csv
import io
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


def create_and_evaluate_trace(client: TestClient, fixture_name: str) -> str:
    """Helper to upload a fixture trace, trigger evaluation, and return evaluation_id."""
    payload = load_fixture_dict(fixture_name)
    upload_res = client.post("/api/v1/traces/upload", json=payload)
    assert upload_res.status_code == 201
    trace_id = upload_res.json()["trace_id"]

    eval_res = client.post("/api/v1/evaluations/run", json={"trace_id": trace_id})
    assert eval_res.status_code == 200
    return str(eval_res.json()["evaluation_id"])


def test_export_json_endpoint_success(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{id}/export/json returns structured JSON and attachment headers."""
    eval_id = create_and_evaluate_trace(client, "loop_trace.json")

    res = client.get(f"/api/v1/evaluations/{eval_id}/export/json")
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]
    assert f'filename="evaluation_{eval_id}.json"' in res.headers["content-disposition"]

    data = res.json()
    assert "summary" in data
    assert "scorecard" in data
    assert "findings" in data
    assert "metadata" in data


def test_export_json_endpoint_not_found(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{id}/export/json returns 404 for nonexistent evaluation."""
    nonexistent_id = str(uuid4())
    res = client.get(f"/api/v1/evaluations/{nonexistent_id}/export/json")
    assert res.status_code == 404


def test_export_markdown_endpoint_success(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{id}/export/markdown returns Markdown document."""
    eval_id = create_and_evaluate_trace(client, "clean_success_trace.json")

    res = client.get(f"/api/v1/evaluations/{eval_id}/export/markdown")
    assert res.status_code == 200
    assert "text/markdown" in res.headers["content-type"]
    assert f'filename="evaluation_{eval_id}.md"' in res.headers["content-disposition"]

    body = res.text
    assert "# Evaluation Report" in body
    assert "## Summary" in body
    assert "## Risk Classification" in body
    assert "## Scorecard" in body
    assert "## Findings" in body


def test_export_markdown_endpoint_not_found(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{id}/export/markdown returns 404 for nonexistent evaluation."""
    nonexistent_id = str(uuid4())
    res = client.get(f"/api/v1/evaluations/{nonexistent_id}/export/markdown")
    assert res.status_code == 404


def test_export_csv_endpoint_success(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{id}/export/csv returns valid CSV output."""
    eval_id = create_and_evaluate_trace(client, "hallucinated_tool_trace.json")

    res = client.get(f"/api/v1/evaluations/{eval_id}/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert f'filename="evaluation_{eval_id}.csv"' in res.headers["content-disposition"]

    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    assert len(rows) >= 1
    assert "HALLUCINATED_TOOL" in [r["finding_code"] for r in rows]


def test_export_csv_endpoint_not_found(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{id}/export/csv returns 404 for nonexistent evaluation."""
    nonexistent_id = str(uuid4())
    res = client.get(f"/api/v1/evaluations/{nonexistent_id}/export/csv")
    assert res.status_code == 404
