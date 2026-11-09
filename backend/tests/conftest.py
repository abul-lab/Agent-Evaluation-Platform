"""Pytest fixtures for backend test suite."""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

# Isolate the suite from any developer database and run in the development environment
# (so local CORS defaults apply). These must be set before the application is imported.
_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="aep_tests_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DB_DIR / 'aep_test.db').as_posix()}"
os.environ["ENVIRONMENT"] = "development"
os.environ.pop("ALLOW_ANONYMOUS_VIEWER", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app.db.session import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas.auth_api import APIKeyCreateRequest, ServiceAccountRole  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> None:
    """Initialize database tables for the test session."""
    init_db()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provide a database session fixture for isolated service testing."""
    with Session(engine) as session:
        yield session


@pytest.fixture(scope="function")
def session(db_session: Session) -> Session:
    """Provide an alias fixture named 'session' pointing to db_session."""
    return db_session


@pytest.fixture(scope="function", autouse=True)
def clean_database(db_session: Session) -> Generator[None, None, None]:
    """Ensure a clean database state before and after each test function."""
    db_session.execute(text("DELETE FROM notification_deliveries;"))
    db_session.execute(text("DELETE FROM notification_channels;"))
    db_session.execute(text("DELETE FROM workspace_audit_logs;"))
    db_session.execute(text("DELETE FROM workspace_members;"))
    db_session.execute(text("DELETE FROM api_keys;"))
    db_session.execute(text("DELETE FROM evaluations;"))
    db_session.execute(text("DELETE FROM traces;"))
    db_session.execute(text("DELETE FROM workspaces;"))
    db_session.execute(text("DELETE FROM policies;"))
    db_session.commit()
    yield
    db_session.execute(text("DELETE FROM notification_deliveries;"))
    db_session.execute(text("DELETE FROM notification_channels;"))
    db_session.execute(text("DELETE FROM workspace_audit_logs;"))
    db_session.execute(text("DELETE FROM workspace_members;"))
    db_session.execute(text("DELETE FROM api_keys;"))
    db_session.execute(text("DELETE FROM evaluations;"))
    db_session.execute(text("DELETE FROM traces;"))
    db_session.execute(text("DELETE FROM workspaces;"))
    db_session.execute(text("DELETE FROM policies;"))
    db_session.commit()


@pytest.fixture(scope="function")
def admin_api_key(db_session: Session) -> str:
    """Issue a fresh ADMIN API key in the default workspace for the current test."""
    created = AuthService(db_session).create_api_key(
        APIKeyCreateRequest(
            name="pytest-admin",
            role=ServiceAccountRole.ADMIN,
            created_by="pytest",
        ),
        actor_email="pytest",
    )
    return created.raw_key


@pytest.fixture(scope="function")
def client(admin_api_key: str) -> Generator[TestClient, None, None]:
    """Authenticated ASGI test client (ADMIN key). Use ``anon_client`` for unauthenticated calls."""
    with TestClient(app, headers={"Authorization": f"Bearer {admin_api_key}"}) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def anon_client() -> Generator[TestClient, None, None]:
    """Unauthenticated ASGI test client."""
    with TestClient(app) as test_client:
        yield test_client
