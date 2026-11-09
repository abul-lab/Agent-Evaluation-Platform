"""Unit tests for Scorecard domain models."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums import RiskClassification
from app.scorecard.score_models import DomainScore, DomainStatus, Scorecard


def test_domain_status_enum_values() -> None:
    """Verify DomainStatus enum members."""
    expected = {"PASS", "WARN", "FAIL"}
    actual = {s.value for s in DomainStatus}
    assert actual == expected


def test_domain_score_model_validation() -> None:
    """Verify DomainScore constraints and bounds."""
    score = DomainScore(name="Tool Usage", score=85.0, status=DomainStatus.PASS, findings_count=1)
    assert score.score == 85.0
    assert score.status == DomainStatus.PASS
    assert score.findings_count == 1

    # Bounds: score < 0 or > 100
    with pytest.raises(ValidationError):
        DomainScore(name="Tool Usage", score=-0.1, status=DomainStatus.FAIL)

    with pytest.raises(ValidationError):
        DomainScore(name="Tool Usage", score=100.1, status=DomainStatus.PASS)

    # Negative findings count
    with pytest.raises(ValidationError):
        DomainScore(name="Tool Usage", score=80.0, status=DomainStatus.PASS, findings_count=-1)


def test_scorecard_model_validation() -> None:
    """Verify Scorecard fields and structure."""
    workflow_id = uuid4()
    domain = DomainScore(name="Sample", score=100.0, status=DomainStatus.PASS)

    scorecard = Scorecard(
        workflow_id=workflow_id,
        task_quality=domain,
        tool_usage=domain,
        workflow_quality=domain,
        reliability=domain,
        safety=domain,
        cost=domain,
        efficiency=domain,
        overall_score=100.0,
        risk_classification=RiskClassification.EXCELLENT,
        findings=[],
    )

    assert isinstance(scorecard.scorecard_id, UUID)
    assert scorecard.workflow_id == workflow_id
    assert scorecard.overall_score == 100.0
    assert scorecard.risk_classification == RiskClassification.EXCELLENT


def test_scorecard_extra_fields_forbidden() -> None:
    """Verify extra attributes are rejected."""
    domain = DomainScore(name="Sample", score=100.0, status=DomainStatus.PASS)
    with pytest.raises(ValidationError):
        Scorecard(
            workflow_id=uuid4(),
            task_quality=domain,
            tool_usage=domain,
            workflow_quality=domain,
            reliability=domain,
            safety=domain,
            cost=domain,
            efficiency=domain,
            overall_score=100.0,
            risk_classification=RiskClassification.EXCELLENT,
            extra_field="unsupported",  # type: ignore[call-arg]
        )
