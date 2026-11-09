"""Unit tests for AnalyticsService longitudinal metrics and trend algorithms."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlmodel import Session

from app.db.entities import EvaluationRecord
from app.domain.models import CanonicalTrace
from app.services.analytics_service import AnalyticsService
from app.services.evaluation_service import EvaluationService
from app.services.trace_repository import TraceRepository

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_fixture_json(filename: str) -> dict[str, object]:
    """Helper to load a fixture JSON file as a dictionary."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def test_analytics_empty_database(db_session: Session) -> None:
    """Verify get_historical_trends handles an empty database safely."""
    service = AnalyticsService(session=db_session)
    trends = service.get_historical_trends(days=30)
    assert trends.total_evaluations == 0
    assert trends.average_score == 0.0
    assert trends.score_trend_direction == "STABLE"
    assert trends.pass_rate == 0.0
    assert trends.daily_metrics == []
    assert trends.finding_distribution == []


def test_analytics_populated_database(db_session: Session) -> None:
    """Verify time-series daily buckets, domain averages, and finding frequency aggregation."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)
    analytics_service = AnalyticsService(session=db_session)

    # Ingest clean and loop traces
    clean_trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    loop_trace = CanonicalTrace.model_validate(load_fixture_json("loop_trace.json"))

    t_clean = trace_repo.create_trace(clean_trace)
    t_loop = trace_repo.create_trace(loop_trace)

    eval_service.run_evaluation(t_clean.trace_id)
    eval_service.run_evaluation(t_loop.trace_id)

    trends = analytics_service.get_historical_trends(days=30)
    assert trends.total_evaluations == 2
    assert trends.average_score > 0
    assert len(trends.daily_metrics) >= 1

    # Check daily bucket structure
    bucket = trends.daily_metrics[0]
    assert bucket.evaluation_count == 2
    assert bucket.average_score > 0
    assert "EXCELLENT" in bucket.risk_counts or "GOOD" in bucket.risk_counts

    # Check finding distributions
    assert len(trends.finding_distribution) >= 1
    cycle_finding = next(
        (f for f in trends.finding_distribution if f.code == "CYCLE_DETECTED"), None
    )
    assert cycle_finding is not None
    assert cycle_finding.count >= 1

    # Check domain averages
    assert "task_quality" in trends.domain_averages
    assert "workflow_quality" in trends.domain_averages
    assert trends.domain_averages["task_quality"] > 0


def test_analytics_trend_improving(db_session: Session) -> None:
    """Verify score_trend_direction classifies IMPROVING when scores increase over time."""
    trace_repo = TraceRepository(db_session)
    clean_trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    t1 = trace_repo.create_trace(clean_trace)
    t2 = trace_repo.create_trace(clean_trace)

    analytics_service = AnalyticsService(session=db_session)
    now = datetime.now(UTC)

    # Older low-scoring evaluation
    rec1 = EvaluationRecord(
        evaluation_id=uuid4(),
        trace_id=t1.trace_id,
        status="COMPLETED",
        started_at=now - timedelta(days=2),
        overall_score=50.0,
        risk_classification="POOR",
        scorecard_json="{}",
        findings_json="[]",
    )
    # Newer high-scoring evaluation
    rec2 = EvaluationRecord(
        evaluation_id=uuid4(),
        trace_id=t2.trace_id,
        status="COMPLETED",
        started_at=now - timedelta(days=1),
        overall_score=90.0,
        risk_classification="EXCELLENT",
        scorecard_json="{}",
        findings_json="[]",
    )
    db_session.add(rec1)
    db_session.add(rec2)
    db_session.commit()

    trends = analytics_service.get_historical_trends(days=30)
    assert trends.total_evaluations == 2
    assert trends.score_trend_direction == "IMPROVING"


def test_analytics_trend_degrading(db_session: Session) -> None:
    """Verify score_trend_direction classifies DEGRADING when scores decrease over time."""
    trace_repo = TraceRepository(db_session)
    clean_trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    t1 = trace_repo.create_trace(clean_trace)
    t2 = trace_repo.create_trace(clean_trace)

    analytics_service = AnalyticsService(session=db_session)
    now = datetime.now(UTC)

    # Older high-scoring evaluation
    rec1 = EvaluationRecord(
        evaluation_id=uuid4(),
        trace_id=t1.trace_id,
        status="COMPLETED",
        started_at=now - timedelta(days=2),
        overall_score=95.0,
        risk_classification="EXCELLENT",
        scorecard_json="{}",
        findings_json="[]",
    )
    # Newer low-scoring evaluation
    rec2 = EvaluationRecord(
        evaluation_id=uuid4(),
        trace_id=t2.trace_id,
        status="COMPLETED",
        started_at=now - timedelta(days=1),
        overall_score=60.0,
        risk_classification="WATCH",
        scorecard_json="{}",
        findings_json="[]",
    )
    db_session.add(rec1)
    db_session.add(rec2)
    db_session.commit()

    trends = analytics_service.get_historical_trends(days=30)
    assert trends.total_evaluations == 2
    assert trends.score_trend_direction == "DEGRADING"
