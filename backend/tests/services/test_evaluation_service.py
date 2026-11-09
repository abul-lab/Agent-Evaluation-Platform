"""Unit tests for EvaluationService."""

from pathlib import Path
from uuid import UUID, uuid4

from sqlmodel import Session

from app.domain.enums import RiskClassification
from app.domain.models import CanonicalTrace
from app.evaluators.base import EvaluationFinding
from app.scorecard.score_models import Scorecard
from app.services.evaluation_service import EvaluationService
from app.services.trace_repository import TraceRepository

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_canonical_trace(filename: str) -> CanonicalTrace:
    """Helper to load a CanonicalTrace fixture."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def test_run_evaluation_success(db_session: Session) -> None:
    """Verify running evaluation against a stored trace creates an EvaluationRecord."""
    trace_repo = TraceRepository(db_session)
    trace = load_canonical_trace("clean_success_trace.json")
    trace_record = trace_repo.create_trace(trace=trace)

    eval_service = EvaluationService(session=db_session)
    eval_record = eval_service.run_evaluation(trace_record.trace_id)

    assert eval_record is not None
    assert isinstance(eval_record.evaluation_id, UUID)
    assert eval_record.trace_id == trace_record.trace_id
    assert eval_record.status == "COMPLETED"
    assert eval_record.finding_count == 0
    assert eval_record.overall_score == 100.0
    assert eval_record.risk_classification == RiskClassification.EXCELLENT.value
    assert eval_record.completed_at is not None


def test_run_evaluation_nonexistent_trace(db_session: Session) -> None:
    """Verify run_evaluation returns None for nonexistent trace IDs."""
    eval_service = EvaluationService(session=db_session)
    result = eval_service.run_evaluation(uuid4())
    assert result is None


def test_get_evaluation(db_session: Session) -> None:
    """Verify retrieval of an evaluation record by ID."""
    trace_repo = TraceRepository(db_session)
    trace = load_canonical_trace("clean_success_trace.json")
    trace_record = trace_repo.create_trace(trace=trace)

    eval_service = EvaluationService(session=db_session)
    created = eval_service.run_evaluation(trace_record.trace_id)
    assert created is not None

    retrieved = eval_service.get_evaluation(created.evaluation_id)
    assert retrieved is not None
    assert retrieved.evaluation_id == created.evaluation_id
    assert retrieved.trace_id == trace_record.trace_id


def test_get_evaluation_nonexistent(db_session: Session) -> None:
    """Verify get_evaluation returns None when ID does not exist."""
    eval_service = EvaluationService(session=db_session)
    assert eval_service.get_evaluation(uuid4()) is None


def test_get_scorecard_success_and_nonexistent(db_session: Session) -> None:
    """Verify retrieval and deserialization of scorecard."""
    trace_repo = TraceRepository(db_session)
    trace = load_canonical_trace("clean_success_trace.json")
    trace_record = trace_repo.create_trace(trace=trace)

    eval_service = EvaluationService(session=db_session)
    created = eval_service.run_evaluation(trace_record.trace_id)
    assert created is not None

    scorecard = eval_service.get_scorecard(created.evaluation_id)
    assert scorecard is not None
    assert isinstance(scorecard, Scorecard)
    assert scorecard.overall_score == 100.0
    assert scorecard.workflow_id == trace.workflow.workflow_id

    # Nonexistent
    assert eval_service.get_scorecard(uuid4()) is None


def test_get_findings_success_and_nonexistent(db_session: Session) -> None:
    """Verify retrieval and deserialization of evaluation findings."""
    trace_repo = TraceRepository(db_session)
    trace = load_canonical_trace("loop_trace.json")
    trace_record = trace_repo.create_trace(trace=trace)

    eval_service = EvaluationService(session=db_session)
    created = eval_service.run_evaluation(trace_record.trace_id)
    assert created is not None

    findings = eval_service.get_findings(created.evaluation_id)
    assert findings is not None
    assert isinstance(findings, list)
    assert len(findings) >= 1
    assert all(isinstance(f, EvaluationFinding) for f in findings)
    assert any(f.code == "CYCLE_DETECTED" for f in findings)

    # Nonexistent
    assert eval_service.get_findings(uuid4()) is None


def test_list_evaluations_and_filter_by_trace(db_session: Session) -> None:
    """Verify listing evaluation records with trace_id filtering."""
    trace_repo = TraceRepository(db_session)
    trace1 = load_canonical_trace("clean_success_trace.json")
    trace2 = load_canonical_trace("loop_trace.json")
    rec1 = trace_repo.create_trace(trace=trace1)
    rec2 = trace_repo.create_trace(trace=trace2)

    eval_service = EvaluationService(session=db_session)
    e1 = eval_service.run_evaluation(rec1.trace_id)
    e2 = eval_service.run_evaluation(rec2.trace_id)
    assert e1 is not None and e2 is not None

    all_evals = eval_service.list_evaluations()
    assert len(all_evals) == 2

    filtered = eval_service.list_evaluations(trace_id=rec1.trace_id)
    assert len(filtered) == 1
    assert filtered[0].evaluation_id == e1.evaluation_id
