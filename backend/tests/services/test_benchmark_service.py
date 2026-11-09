"""Unit tests for BenchmarkService comparison and leaderboard aggregation."""

import json
from pathlib import Path
from uuid import uuid4

from sqlmodel import Session

from app.domain.models import CanonicalTrace
from app.services.benchmark_service import BenchmarkService
from app.services.evaluation_service import EvaluationService
from app.services.trace_repository import TraceRepository

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_fixture_json(filename: str) -> dict[str, object]:
    """Helper to load fixture json."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def test_compare_evaluations_not_found(db_session: Session) -> None:
    """Verify compare_evaluations returns None when either evaluation does not exist."""
    service = BenchmarkService(session=db_session)
    result = service.compare_evaluations(base_id=uuid4(), target_id=uuid4())
    assert result is None


def test_compare_evaluations_improvement_and_regression(db_session: Session) -> None:
    """Verify delta calculations, risk transitions, and finding categorization."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)
    benchmark_service = BenchmarkService(session=db_session)

    # Ingest clean and loop traces
    clean_trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    loop_trace = CanonicalTrace.model_validate(load_fixture_json("loop_trace.json"))

    clean_trace_rec = trace_repo.create_trace(clean_trace)
    loop_trace_rec = trace_repo.create_trace(loop_trace)

    clean_eval = eval_service.run_evaluation(clean_trace_rec.trace_id)
    loop_eval = eval_service.run_evaluation(loop_trace_rec.trace_id)
    assert clean_eval is not None
    assert loop_eval is not None

    # Test Improvement: Loop (Base) -> Clean (Target)
    improvement = benchmark_service.compare_evaluations(
        base_id=loop_eval.evaluation_id,
        target_id=clean_eval.evaluation_id,
    )
    assert improvement is not None
    assert improvement.overall_score_delta > 0
    assert improvement.risk_transition.is_improved is True
    assert improvement.risk_transition.is_degraded is False
    assert improvement.finding_delta.resolved_count > 0
    assert improvement.finding_delta.total_delta < 0
    assert improvement.domain_deltas["workflow_quality"].score_delta > 0

    # Test Regression: Clean (Base) -> Loop (Target)
    regression = benchmark_service.compare_evaluations(
        base_id=clean_eval.evaluation_id,
        target_id=loop_eval.evaluation_id,
    )
    assert regression is not None
    assert regression.overall_score_delta < 0
    assert regression.risk_transition.is_improved is False
    assert regression.risk_transition.is_degraded is True
    assert regression.finding_delta.new_count > 0
    assert regression.finding_delta.total_delta > 0


def test_compare_evaluations_identical(db_session: Session) -> None:
    """Verify comparing an evaluation against itself yields zero deltas."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)
    benchmark_service = BenchmarkService(session=db_session)

    trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    trace_rec = trace_repo.create_trace(trace)
    eval_rec = eval_service.run_evaluation(trace_rec.trace_id)
    assert eval_rec is not None

    identical = benchmark_service.compare_evaluations(
        base_id=eval_rec.evaluation_id,
        target_id=eval_rec.evaluation_id,
    )
    assert identical is not None
    assert identical.overall_score_delta == 0.0
    assert identical.risk_transition.is_improved is False
    assert identical.risk_transition.is_degraded is False
    assert identical.finding_delta.new_count == 0
    assert identical.finding_delta.resolved_count == 0
    assert identical.finding_delta.total_delta == 0
    assert identical.finding_delta.persistent_count == eval_rec.finding_count


def test_get_benchmark_summary_empty(db_session: Session) -> None:
    """Verify get_benchmark_summary handles an empty database gracefully."""
    service = BenchmarkService(session=db_session)
    summary = service.get_benchmark_summary()
    assert summary.total_evaluations == 0
    assert summary.mean_score == 0.0
    assert summary.min_score == 0.0
    assert summary.max_score == 0.0
    assert summary.pass_rate == 0.0
    assert summary.leaderboard == []


def test_get_benchmark_summary_populated(db_session: Session) -> None:
    """Verify leaderboard ranking and summary statistics for multiple evaluations."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)
    benchmark_service = BenchmarkService(session=db_session)

    # Ingest clean, loop, and budget fixtures
    clean_trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    loop_trace = CanonicalTrace.model_validate(load_fixture_json("loop_trace.json"))
    budget_trace = CanonicalTrace.model_validate(load_fixture_json("budget_exceeded_trace.json"))

    t1 = trace_repo.create_trace(clean_trace)
    t2 = trace_repo.create_trace(loop_trace)
    t3 = trace_repo.create_trace(budget_trace)

    eval_service.run_evaluation(t1.trace_id)
    eval_service.run_evaluation(t2.trace_id)
    eval_service.run_evaluation(t3.trace_id)

    summary = benchmark_service.get_benchmark_summary(limit=10)
    assert summary.total_evaluations == 3
    assert summary.max_score >= summary.mean_score >= summary.min_score
    assert len(summary.leaderboard) == 3

    # Ensure leaderboard is sorted by score descending
    scores = [item.overall_score for item in summary.leaderboard]
    assert scores == sorted(scores, reverse=True)
    assert summary.leaderboard[0].rank == 1
    assert summary.leaderboard[1].rank == 2
    assert summary.leaderboard[2].rank == 3
