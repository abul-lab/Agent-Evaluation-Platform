"""API integration tests for OpenTelemetry trace ingestion and preview translation endpoints."""

import json
from pathlib import Path
from typing import Any

from fastapi import status
from fastapi.testclient import TestClient

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "otel"


def load_otel_fixture(filename: str) -> dict[str, Any]:
    path = FIXTURES_DIR / filename
    with open(path, encoding="utf-8") as f:
        loaded: dict[str, Any] = json.load(f)
        return loaded


def test_ingest_otel_trace_success(client: TestClient) -> None:
    payload = load_otel_fixture("langgraph_trace.json")
    response = client.post("/api/v1/otel/ingest", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "trace_id" in data
    assert data["step_count"] == 4
    assert data["workflow_status"] == "SUCCESS"
    assert data["detected_framework"] == "LANGGRAPH"
    assert data["stored"] is True

    # Verify that the persisted trace can be evaluated immediately using existing evaluation APIs
    eval_res = client.post("/api/v1/evaluations/run", json={"trace_id": data["trace_id"]})
    assert eval_res.status_code == status.HTTP_200_OK
    eval_data = eval_res.json()
    assert eval_data["status"] == "COMPLETED"
    assert eval_data["overall_score"] > 0


def test_translate_otel_preview_endpoint(client: TestClient) -> None:
    payload = load_otel_fixture("crewai_trace.json")
    response = client.post("/api/v1/otel/translate", json=payload)

    assert response.status_code == status.HTTP_200_OK
    cats_data = response.json()
    assert "session" in cats_data
    assert "workflow" in cats_data
    assert "steps" in cats_data
    assert len(cats_data["steps"]) == 4
    assert cats_data["workflow"]["framework"] == "CREWAI"


def test_ingest_all_five_framework_fixtures(client: TestClient) -> None:
    fixtures = [
        ("langgraph_trace.json", "LANGGRAPH"),
        ("crewai_trace.json", "CREWAI"),
        ("autogen_trace.json", "AUTOGEN"),
        ("openai_agents_trace.json", "OPENAI_AGENTS"),
        ("llamaindex_trace.json", "LLAMAINDEX"),
    ]
    for filename, expected_framework in fixtures:
        payload = load_otel_fixture(filename)
        res = client.post("/api/v1/otel/ingest", json=payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.json()["detected_framework"] == expected_framework


def test_ingest_invalid_otel_payload_returns_422(client: TestClient) -> None:
    # Empty spans array
    res = client.post("/api/v1/otel/ingest", json={"spans": []})
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing trace ID
    res = client.post("/api/v1/otel/ingest", json={"spans": [{"span_id": "123", "name": "step"}]})
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_translate_invalid_payload_returns_422(client: TestClient) -> None:
    res = client.post("/api/v1/otel/translate", json={"invalid": True})
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
