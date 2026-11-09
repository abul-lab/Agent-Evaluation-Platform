"""Integration tests for trace validation, upload, and metadata inspection endpoints."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"

GOLDEN_FIXTURES = [
    "clean_success_trace.json",
    "loop_trace.json",
    "hallucinated_tool_trace.json",
    "retry_storm_trace.json",
    "budget_exceeded_trace.json",
    "secret_leak_trace.json",
]


def load_fixture_dict(filename: str) -> dict[str, object]:
    """Helper to load a fixture JSON file as a dictionary."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def test_validate_valid_trace(client: TestClient) -> None:
    """Verify /validate endpoint with a valid canonical trace."""
    payload = load_fixture_dict("clean_success_trace.json")
    response = client.post("/api/v1/traces/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["step_count"] == 3
    assert data["workflow_status"] == "SUCCESS"
    assert data["warnings"] == []


def test_validate_invalid_trace_returns_422(client: TestClient) -> None:
    """Verify /validate endpoint returns HTTP 422 on invalid schema."""
    payload = load_fixture_dict("minimal_invalid_trace.json")
    response = client.post("/api/v1/traces/validate", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_upload_valid_trace(client: TestClient) -> None:
    """Verify /upload endpoint persists trace and returns 201 Created."""
    payload = load_fixture_dict("clean_success_trace.json")
    response = client.post("/api/v1/traces/upload", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["stored"] is True
    assert data["step_count"] == 3
    assert data["workflow_status"] == "SUCCESS"
    assert "trace_id" in data


def test_upload_invalid_trace_returns_422(client: TestClient) -> None:
    """Verify /upload endpoint returns HTTP 422 on invalid schema without 500 error."""
    payload = load_fixture_dict("minimal_invalid_trace.json")
    response = client.post("/api/v1/traces/upload", json=payload)
    assert response.status_code == 422
    assert response.status_code != 500


def test_get_trace_metadata_success(client: TestClient) -> None:
    """Verify retrieving trace metadata by trace_id."""
    payload = load_fixture_dict("clean_success_trace.json")
    upload_res = client.post("/api/v1/traces/upload", json=payload)
    trace_id = upload_res.json()["trace_id"]

    get_res = client.get(f"/api/v1/traces/{trace_id}")
    assert get_res.status_code == 200
    meta = get_res.json()
    assert meta["trace_id"] == trace_id
    assert meta["workflow_status"] == "SUCCESS"
    assert meta["step_count"] == 3
    assert "created_at" in meta


def test_get_nonexistent_trace_returns_404(client: TestClient) -> None:
    """Verify nonexistent trace ID returns 404."""
    nonexistent_id = uuid4()
    response = client.get(f"/api/v1/traces/{nonexistent_id}")
    assert response.status_code == 404
    assert f"Trace with ID '{nonexistent_id}' not found." in response.json()["detail"]


def test_get_invalid_uuid_returns_422(client: TestClient) -> None:
    """Verify malformed UUID parameter returns 422."""
    response = client.get("/api/v1/traces/not-a-valid-uuid")
    assert response.status_code == 422


def test_list_traces(client: TestClient) -> None:
    """Verify listing uploaded traces."""
    payload = load_fixture_dict("retry_storm_trace.json")
    client.post("/api/v1/traces/upload", json=payload)

    response = client.get("/api/v1/traces")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    item = data[0]
    assert "trace_id" in item
    assert "workflow_status" in item
    assert "step_count" in item
    assert "created_at" in item


@pytest.mark.parametrize("fixture_name", GOLDEN_FIXTURES)
def test_all_six_golden_fixtures_upload_successfully(client: TestClient, fixture_name: str) -> None:
    """Integration test: All 6 golden fixtures must upload and persist successfully."""
    payload = load_fixture_dict(fixture_name)
    response = client.post("/api/v1/traces/upload", json=payload)
    assert response.status_code == 201, f"Failed to upload {fixture_name}: {response.text}"
    data = response.json()
    assert data["stored"] is True
    assert data["step_count"] >= 1
