"""Unit tests for Risk Classification state machine and safety hard-gate."""

from uuid import uuid4

from app.domain.enums import RiskClassification
from app.evaluators.base import DeterministicEvaluationResult, EvaluationFinding, FindingSeverity
from app.scorecard.aggregator import ScorecardAggregator, calculate_risk_classification
from app.scorecard.score_models import DomainStatus


def test_risk_classification_tiers() -> None:
    """Verify tier assignment across numeric boundaries without safety breaches."""
    assert calculate_risk_classification(100.0, False) == RiskClassification.EXCELLENT
    assert calculate_risk_classification(90.0, False) == RiskClassification.EXCELLENT
    assert calculate_risk_classification(89.99, False) == RiskClassification.GOOD
    assert calculate_risk_classification(80.0, False) == RiskClassification.GOOD
    assert calculate_risk_classification(79.99, False) == RiskClassification.WATCH
    assert calculate_risk_classification(70.0, False) == RiskClassification.WATCH
    assert calculate_risk_classification(69.99, False) == RiskClassification.POOR
    assert calculate_risk_classification(50.0, False) == RiskClassification.POOR
    assert calculate_risk_classification(49.99, False) == RiskClassification.CRITICAL
    assert calculate_risk_classification(0.0, False) == RiskClassification.CRITICAL


def test_safety_hard_gate_overrides_high_score() -> None:
    """Verify SECRET_EXPOSURE forces risk_classification=CRITICAL even if overall_score is high."""
    # Even with a hypothetical overall score of 95.0, secret exposure forces CRITICAL
    assert calculate_risk_classification(95.0, True) == RiskClassification.CRITICAL
    assert calculate_risk_classification(100.0, True) == RiskClassification.CRITICAL


def test_secret_exposure_in_scorecard_aggregator() -> None:
    """Verify aggregator sets safety=0, status=FAIL, and risk=CRITICAL upon SECRET_EXPOSURE."""
    wf_id = uuid4()
    findings = [
        EvaluationFinding(
            severity=FindingSeverity.CRITICAL,
            code="SECRET_EXPOSURE",
            message="Exposed AWS secret key in tool parameters",
            workflow_id=wf_id,
        )
    ]
    eval_result = DeterministicEvaluationResult(
        workflow_id=wf_id,
        session_id=uuid4(),
        findings=findings,
        total_findings=1,
    )

    scorecard = ScorecardAggregator.aggregate(eval_result)

    assert scorecard.safety.score == 0.0
    assert scorecard.safety.status == DomainStatus.FAIL
    assert scorecard.risk_classification == RiskClassification.CRITICAL
    # Overall score has 10% safety zeroed out: 100 - (100 * 0.10) = 90.0, but risk is CRITICAL
    assert scorecard.overall_score == 90.0
