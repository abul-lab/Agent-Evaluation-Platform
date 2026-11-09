"""Integration tests for governance policy management and evaluation audit REST endpoints."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.models import CanonicalTrace

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_fixture_json(filename: str) -> dict[str, object]:
    """Helper to load fixture json."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def test_get_active_policy(client: TestClient) -> None:
    """Verify retrieval and auto-seeding of default policy."""
    response = client.get("/api/v1/policies/active")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Standard Platform Gate"
    assert data["is_default"] is True
    assert data["is_active"] is True


def test_create_and_get_policy(client: TestClient) -> None:
    """Verify creating a custom policy profile and fetching by ID."""
    payload = {
        "name": "Custom Canary Policy",
        "description": "Canary gate for staging runs",
        "is_active": True,
        "is_default": False,
        "rules": {
            "min_overall_score": 85.0,
            "disallowed_risk_tiers": ["CRITICAL", "POOR"],
        },
    }
    create_res = client.post("/api/v1/policies", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["name"] == "Custom Canary Policy"
    policy_id = created["policy_id"]

    get_res = client.get(f"/api/v1/policies/{policy_id}")
    assert get_res.status_code == 200
    assert get_res.json()["policy_id"] == policy_id

    # List policies
    list_res = client.get("/api/v1/policies")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_update_and_delete_policy(client: TestClient) -> None:
    """Verify updating and deleting a custom policy."""
    # Create policy
    create_res = client.post(
        "/api/v1/policies",
        json={"name": "Temp Policy", "description": "To be deleted", "is_active": True},
    )
    assert create_res.status_code == 201
    policy_id = create_res.json()["policy_id"]

    # Update policy
    update_res = client.put(
        f"/api/v1/policies/{policy_id}",
        json={"name": "Updated Temp Policy", "is_active": False},
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Temp Policy"
    assert update_res.json()["is_active"] is False

    # Delete policy
    del_res = client.delete(f"/api/v1/policies/{policy_id}")
    assert del_res.status_code == 204

    # Verify 404 on subsequent get
    assert client.get(f"/api/v1/policies/{policy_id}").status_code == 404


def test_audit_evaluation_endpoint(client: TestClient) -> None:
    """Verify auditing an uploaded & evaluated trace against default policy."""
    # 1. Fetch active policy
    active_res = client.get("/api/v1/policies/active")
    assert active_res.status_code == 200
    policy_id = active_res.json()["policy_id"]

    # 2. Upload and evaluate clean trace
    clean_data = load_fixture_json("clean_success_trace.json")
    CanonicalTrace.model_validate(clean_data)
    upload_res = client.post("/api/v1/traces/upload", json=clean_data)
    assert upload_res.status_code == 201
    trace_id = upload_res.json()["trace_id"]

    eval_res = client.post("/api/v1/evaluations/run", json={"trace_id": trace_id})
    assert eval_res.status_code == 200
    evaluation_id = eval_res.json()["evaluation_id"]

    # 3. Audit evaluation
    audit_res = client.post(f"/api/v1/policies/{policy_id}/audit/{evaluation_id}")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["verdict"] == "APPROVED"
    assert audit_data["passed"] is True
    assert audit_data["violations_count"] == 0
