"""Integration tests for workspace, membership RBAC, and audit log REST endpoints."""

from uuid import uuid4

from fastapi.testclient import TestClient


def test_get_default_workspace_endpoint(client: TestClient) -> None:
    """Verify retrieval and auto-bootstrapping of default workspace."""
    response = client.get("/api/v1/workspaces/default")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Default Workspace"
    assert data["slug"] == "default"
    assert data["is_default"] is True
    assert data["member_count"] >= 1


def test_create_and_get_workspace_endpoints(client: TestClient) -> None:
    """Verify creating a custom workspace and fetching by ID."""
    payload = {
        "name": "FinOps Swarm Workspace",
        "description": "Financial and token budget tracking",
        "is_default": False,
    }
    create_res = client.post("/api/v1/workspaces", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["name"] == "FinOps Swarm Workspace"
    assert created["slug"] == "finops-swarm-workspace"
    workspace_id = created["workspace_id"]

    # Fetch by ID
    get_res = client.get(f"/api/v1/workspaces/{workspace_id}")
    assert get_res.status_code == 200
    assert get_res.json()["workspace_id"] == workspace_id

    # List workspaces
    list_res = client.get("/api/v1/workspaces")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_update_and_delete_workspace_endpoints(client: TestClient) -> None:
    """Verify updating and deleting a custom workspace."""
    # Create temp workspace
    create_res = client.post(
        "/api/v1/workspaces",
        json={"name": "Temp WS", "description": "To be removed"},
    )
    assert create_res.status_code == 201
    workspace_id = create_res.json()["workspace_id"]

    # Update
    update_res = client.put(
        f"/api/v1/workspaces/{workspace_id}",
        json={"description": "Updated description"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["description"] == "Updated description"

    # Delete
    del_res = client.delete(f"/api/v1/workspaces/{workspace_id}")
    assert del_res.status_code == 204

    # Verify 404
    assert client.get(f"/api/v1/workspaces/{workspace_id}").status_code == 404


def test_workspace_membership_endpoints(client: TestClient) -> None:
    """Verify adding, listing, and removing members via REST APIs."""
    # 1. Fetch default workspace
    ws_res = client.get("/api/v1/workspaces/default")
    assert ws_res.status_code == 200
    workspace_id = ws_res.json()["workspace_id"]

    # 2. Add member
    add_res = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"user_email": "dev@example.com", "role": "ENGINEER"},
    )
    assert add_res.status_code == 201
    member = add_res.json()
    assert member["user_email"] == "dev@example.com"
    assert member["role"] == "ENGINEER"
    member_id = member["member_id"]

    # 3. List members
    list_res = client.get(f"/api/v1/workspaces/{workspace_id}/members")
    assert list_res.status_code == 200
    members = list_res.json()
    assert len(members) >= 2

    # 4. Remove member
    del_member_res = client.delete(f"/api/v1/workspaces/{workspace_id}/members/{member_id}")
    assert del_member_res.status_code == 204

    # 5. List audit logs
    audit_res = client.get(f"/api/v1/workspaces/{workspace_id}/audit-logs")
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 2
    actions = {log["action"] for log in logs}
    assert "MEMBER_ADDED" in actions
    assert "MEMBER_REMOVED" in actions


def test_nonexistent_workspace_endpoints(client: TestClient) -> None:
    """Verify 404 responses for nonexistent workspace operations."""
    random_id = uuid4()
    assert client.get(f"/api/v1/workspaces/{random_id}").status_code == 404
    assert (
        client.put(f"/api/v1/workspaces/{random_id}", json={"name": "New Name"}).status_code == 404
    )
    assert client.delete(f"/api/v1/workspaces/{random_id}").status_code == 404
    assert client.get(f"/api/v1/workspaces/{random_id}/members").status_code == 404
    assert (
        client.post(
            f"/api/v1/workspaces/{random_id}/members",
            json={"user_email": "a@b.com", "role": "VIEWER"},
        ).status_code
        == 404
    )
