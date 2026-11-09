"""Contract tests verifying Scorecard and Risk Classification against Golden Fixtures."""

from pathlib import Path

import pytest

from app.domain.enums import RiskClassification
from app.domain.models import CanonicalTrace
from app.scorecard.score_models import DomainStatus
from app.services.deterministic_evaluator import DeterministicEvaluationService
from app.services.scorecard_service import ScorecardService

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_fixture_trace(filename: str) -> CanonicalTrace:
    """Load a golden fixture JSON into a validated CanonicalTrace domain model."""
    fixture_path = FIXTURES_DIR / filename
    assert fixture_path.exists(), f"Fixture file not found: {fixture_path}"
    with open(fixture_path, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


@pytest.fixture
def scorecard_service() -> ScorecardService:
    """Provides an instance of ScorecardService."""
    return ScorecardService()


def test_clean_success_trace_scorecard_contract(scorecard_service: ScorecardService) -> None:
    """Contract: clean_success_trace must produce high scores, no FAIL domains, and EXCELLENT/GOOD risk."""
    trace = load_fixture_trace("clean_success_trace.json")
    scorecard = scorecard_service.evaluate_and_generate_scorecard(trace)

    assert scorecard.overall_score > 85.0
    assert scorecard.risk_classification in (
        RiskClassification.EXCELLENT,
        RiskClassification.GOOD,
    )
    for domain in (
        scorecard.task_quality,
        scorecard.tool_usage,
        scorecard.workflow_quality,
        scorecard.reliability,
        scorecard.safety,
        scorecard.cost,
        scorecard.efficiency,
    ):
        assert domain.status != DomainStatus.FAIL
        assert domain.score >= 80.0


def test_loop_trace_scorecard_contract(scorecard_service: ScorecardService) -> None:
    """Contract: loop_trace must trigger workflow quality penalty and elevated risk."""
    trace = load_fixture_trace("loop_trace.json")
    scorecard = scorecard_service.evaluate_and_generate_scorecard(trace)

    assert scorecard.workflow_quality.score < 80.0
    assert scorecard.workflow_quality.status in (DomainStatus.WARN, DomainStatus.FAIL)
    assert scorecard.risk_classification in (RiskClassification.WATCH, RiskClassification.POOR)
    assert scorecard.efficiency.score < 100.0


def test_hallucinated_tool_trace_scorecard_contract(scorecard_service: ScorecardService) -> None:
    """Contract: hallucinated_tool_trace must penalize tool usage significantly (< 70)."""
    trace = load_fixture_trace("hallucinated_tool_trace.json")
    scorecard = scorecard_service.evaluate_and_generate_scorecard(trace)

    assert scorecard.tool_usage.score < 70.0
    assert scorecard.tool_usage.status in (DomainStatus.WARN, DomainStatus.FAIL)
    assert scorecard.tool_usage.findings_count >= 1
    assert scorecard.overall_score < 100.0


def test_retry_storm_trace_scorecard_contract(scorecard_service: ScorecardService) -> None:
    """Contract: retry_storm_trace must penalize reliability and efficiency."""
    trace = load_fixture_trace("retry_storm_trace.json")
    scorecard = scorecard_service.evaluate_and_generate_scorecard(trace)

    assert scorecard.reliability.score < 80.0
    assert scorecard.reliability.status in (DomainStatus.WARN, DomainStatus.FAIL)
    assert scorecard.efficiency.score < 100.0


def test_budget_exceeded_trace_scorecard_contract(scorecard_service: ScorecardService) -> None:
    """Contract: budget_exceeded_trace must penalize cost score (< 70)."""
    trace = load_fixture_trace("budget_exceeded_trace.json")
    scorecard = scorecard_service.evaluate_and_generate_scorecard(trace)

    assert scorecard.cost.score < 70.0
    assert scorecard.cost.status == DomainStatus.FAIL
    assert scorecard.cost.findings_count >= 1


def test_secret_leak_trace_scorecard_contract(scorecard_service: ScorecardService) -> None:
    """Contract: secret_leak_trace must trigger Safety Hard Gate: score=0, CRITICAL risk."""
    trace = load_fixture_trace("secret_leak_trace.json")
    scorecard = scorecard_service.evaluate_and_generate_scorecard(trace)

    assert scorecard.safety.score == 0.0
    assert scorecard.safety.status == DomainStatus.FAIL
    assert scorecard.risk_classification == RiskClassification.CRITICAL


def test_scorecard_service_custom_eval_service() -> None:
    """Ensure ScorecardService can be constructed with explicit eval_service."""
    eval_svc = DeterministicEvaluationService()
    svc = ScorecardService(eval_service=eval_svc)
    trace = load_fixture_trace("clean_success_trace.json")
    sc = svc.evaluate_and_generate_scorecard(trace)
    assert sc.workflow_id == trace.workflow.workflow_id
