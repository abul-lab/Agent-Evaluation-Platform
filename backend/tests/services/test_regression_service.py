"""Unit tests for RegressionService quality gate policy checks."""

import json
from pathlib import Path
from uuid import uuid4

from sqlmodel import Session

from app.domain.models import CanonicalTrace
from app.schemas.regression_api import RegressionPolicy, RegressionStatus
from app.services.evaluation_service import EvaluationService
from app.services.regression_service import RegressionService
from app.services.trace_repository import TraceRepository

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_fixture_json(filename: str) -> dict[str, object]:
    """Helper to load fixture json."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def test_regression_check_not_found(db_session: Session) -> None:
    """Verify check_regression returns None when evaluations do not exist."""
    service = RegressionService(session=db_session)
    result = service.check_regression(base_id=uuid4(), candidate_id=uuid4())
    assert result is None


def test_regression_check_clean_baseline_and_candidate(db_session: Session) -> None:
    """Verify regression check against itself or identical clean run passes cleanly."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)
    regression_service = RegressionService(session=db_session)

    clean_trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    trace_rec = trace_repo.create_trace(clean_trace)
    evaluation = eval_service.run_evaluation(trace_rec.trace_id)
    assert evaluation is not None

    report = regression_service.check_regression(
        base_id=evaluation.evaluation_id,
        candidate_id=evaluation.evaluation_id,
    )

    assert report is not None
    assert report.status == RegressionStatus.PASSED
    assert report.is_regression is False
    assert report.violations_count == 0
    assert report.overall_score_delta == 0.0


def test_regression_check_detects_regression_on_loop_trace(db_session: Session) -> None:
    """Verify candidate with workflow loop triggers regression violations."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)
    regression_service = RegressionService(session=db_session)

    clean_trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    loop_trace = CanonicalTrace.model_validate(load_fixture_json("loop_trace.json"))

    clean_rec = trace_repo.create_trace(clean_trace)
    loop_rec = trace_repo.create_trace(loop_trace)

    clean_eval = eval_service.run_evaluation(clean_rec.trace_id)
    loop_eval = eval_service.run_evaluation(loop_rec.trace_id)
    assert clean_eval is not None
    assert loop_eval is not None

    report = regression_service.check_regression(
        base_id=clean_eval.evaluation_id,
        candidate_id=loop_eval.evaluation_id,
    )

    assert report is not None
    assert report.status == RegressionStatus.REGRESSED
    assert report.is_regression is True
    assert report.violations_count > 0
    assert report.critical_violations_count > 0

    violation_rules = {v.rule for v in report.violations}
    assert "OVERALL_SCORE_DROP" in violation_rules
    assert "RISK_ESCALATION" in violation_rules
    assert "PROHIBITED_FINDING_CODE" in violation_rules


def test_regression_check_secret_leak_triggers_safety_breach(db_session: Session) -> None:
    """Verify secret leak candidate triggers safety floor and prohibited code violations."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)
    regression_service = RegressionService(session=db_session)

    clean_trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    secret_trace = CanonicalTrace.model_validate(load_fixture_json("secret_leak_trace.json"))

    clean_rec = trace_repo.create_trace(clean_trace)
    secret_rec = trace_repo.create_trace(secret_trace)

    clean_eval = eval_service.run_evaluation(clean_rec.trace_id)
    secret_eval = eval_service.run_evaluation(secret_rec.trace_id)
    assert clean_eval is not None
    assert secret_eval is not None

    report = regression_service.check_regression(
        base_id=clean_eval.evaluation_id,
        candidate_id=secret_eval.evaluation_id,
    )

    assert report is not None
    assert report.status == RegressionStatus.REGRESSED
    assert report.is_regression is True

    violation_rules = {v.rule for v in report.violations}
    assert "MIN_SAFETY_SCORE_BREACH" in violation_rules
    assert "PROHIBITED_FINDING_CODE" in violation_rules


def test_regression_check_custom_permissive_policy(db_session: Session) -> None:
    """Verify a relaxed policy avoids failure when configured by the caller."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)
    regression_service = RegressionService(session=db_session)

    clean_trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    loop_trace = CanonicalTrace.model_validate(load_fixture_json("loop_trace.json"))

    clean_rec = trace_repo.create_trace(clean_trace)
    loop_rec = trace_repo.create_trace(loop_trace)

    clean_eval = eval_service.run_evaluation(clean_rec.trace_id)
    loop_eval = eval_service.run_evaluation(loop_rec.trace_id)
    assert clean_eval is not None
    assert loop_eval is not None

    permissive_policy = RegressionPolicy(
        name="Permissive Experimental Gate",
        max_score_drop=100.0,
        max_domain_drop=100.0,
        fail_on_risk_escalation=False,
        fail_on_new_critical_findings=False,
        prohibited_finding_codes=[],
        min_overall_score=0.0,
        min_safety_score=0.0,
    )

    report = regression_service.check_regression(
        base_id=clean_eval.evaluation_id,
        candidate_id=loop_eval.evaluation_id,
        policy=permissive_policy,
    )

    assert report is not None
    assert report.status == RegressionStatus.PASSED
    assert report.is_regression is False
    assert report.violations_count == 0
