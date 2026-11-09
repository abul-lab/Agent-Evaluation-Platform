"""Unit tests for TraceRepository."""

from pathlib import Path
from uuid import UUID, uuid4

from sqlmodel import Session

from app.domain.models import CanonicalTrace
from app.services.trace_repository import TraceRepository

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_canonical_trace(filename: str) -> CanonicalTrace:
    """Helper to load a CanonicalTrace fixture."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def test_create_and_get_trace(db_session: Session) -> None:
    """Verify trace creation and retrieval via repository."""
    repo = TraceRepository(db_session)
    trace = load_canonical_trace("clean_success_trace.json")

    record = repo.create_trace(trace=trace, filename="clean_success_trace.json")
    assert isinstance(record.trace_id, UUID)
    assert record.framework == "LANGGRAPH"
    assert record.workflow_status == "SUCCESS"
    assert record.step_count == 3
    assert record.filename == "clean_success_trace.json"

    retrieved = repo.get_trace(record.trace_id)
    assert retrieved is not None
    assert retrieved.trace_id == record.trace_id
    assert retrieved.step_count == 3


def test_get_nonexistent_trace(db_session: Session) -> None:
    """Verify repository returns None for nonexistent trace IDs."""
    repo = TraceRepository(db_session)
    assert repo.get_trace(uuid4()) is None


def test_list_traces(db_session: Session) -> None:
    """Verify listing traces ordered by creation date."""
    repo = TraceRepository(db_session)
    trace1 = load_canonical_trace("clean_success_trace.json")
    trace2 = load_canonical_trace("retry_storm_trace.json")

    repo.create_trace(trace1)
    repo.create_trace(trace2)

    records = repo.list_traces(limit=10)
    assert len(records) >= 2
