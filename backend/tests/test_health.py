"""Test suite for health endpoints."""

from fastapi.testclient import TestClient

from app.core.config import settings


def test_root_health(client: TestClient) -> None:
    """Test the root /health liveness probe."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == settings.PROJECT_NAME


def test_api_v1_health(client: TestClient) -> None:
    """Test the /api/v1/health operational endpoint."""
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == settings.VERSION
    assert data["environment"] == settings.ENVIRONMENT


def test_root_version(client: TestClient) -> None:
    """Test the root /version endpoint."""
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert "build_date" in data
    assert "commit_sha" in data
    assert data["environment"] == settings.ENVIRONMENT


def test_api_v1_version(client: TestClient) -> None:
    """Test the /api/v1/version endpoint."""
    response = client.get(f"{settings.API_V1_STR}/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert "build_date" in data
    assert "commit_sha" in data


def test_root_system_info(client: TestClient) -> None:
    """Test the root /system/info endpoint."""
    response = client.get("/system/info")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert isinstance(data["feature_modules"], list)
    assert len(data["feature_modules"]) >= 10
    assert data["database_status"] == "connected"
    assert data["api_status"] == "operational"


def test_api_v1_system_info(client: TestClient) -> None:
    """Test the /api/v1/system/info endpoint."""
    response = client.get(f"{settings.API_V1_STR}/system/info")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0.0"
    assert data["database_status"] == "connected"
