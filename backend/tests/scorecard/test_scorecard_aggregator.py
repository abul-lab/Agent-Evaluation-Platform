"""Unit tests for ScorecardAggregator deduction rules and domain scoring."""

from uuid import uuid4

from app.evaluators.base import DeterministicEvaluationResult, EvaluationFinding, FindingSeverity
from app.scorecard.aggregator import ScorecardAggregator, get_domain_status
from app.scorecard.score_models import DomainStatus


def create_eval_result(findings: list[EvaluationFinding]) -> DeterministicEvaluationResult:
    """Helper to construct a DeterministicEvaluationResult from findings."""
    return DeterministicEvaluationResult(
        workflow_id=uuid4(),
        session_id=uuid4(),
        findings=findings,
        total_findings=len(findings),
    )


def test_clean_evaluation_produces_perfect_scores() -> None:
    """Verify empty findings produce 100.0 across all domains."""
    eval_result = create_eval_result([])
    scorecard = ScorecardAggregator.aggregate(eval_result)

    assert scorecard.task_quality.score == 100.0
    assert scorecard.tool_usage.score == 100.0
    assert scorecard.workflow_quality.score == 100.0
    assert scorecard.reliability.score == 100.0
    assert scorecard.safety.score == 100.0
    assert scorecard.cost.score == 100.0
    assert scorecard.efficiency.score == 100.0
    assert scorecard.overall_score == 100.0


def test_tool_usage_deductions() -> None:
    """Verify tool usage deduction rules: -40, -15, -10 and clamp at 0."""
    wf_id = uuid4()
    findings = [
        EvaluationFinding(
            severity=FindingSeverity.HIGH,
            code="HALLUCINATED_TOOL",
            message="Hallucinated tool",
            workflow_id=wf_id,
        ),
        EvaluationFinding(
            severity=FindingSeverity.MEDIUM,
            code="REDUNDANT_TOOL_CALL",
            message="Duplicate tool call",
            workflow_id=wf_id,
        ),
        EvaluationFinding(
            severity=FindingSeverity.MEDIUM,
            code="MISSING_TOOL_SCHEMA",
            message="Missing schema",
            workflow_id=wf_id,
        ),
    ]
    # 100 - 40 - 15 - 10 = 35.0
    scorecard = ScorecardAggregator.aggregate(create_eval_result(findings))
    assert scorecard.tool_usage.score == 35.0
    assert scorecard.tool_usage.status == DomainStatus.FAIL
    assert scorecard.tool_usage.findings_count == 3


def test_tool_usage_clamp_at_zero() -> None:
    """Verify tool usage score cannot drop below 0."""
    wf_id = uuid4()
    # 3 hallucinated tools = -120 -> clamp to 0
    findings = [
        EvaluationFinding(
            severity=FindingSeverity.HIGH, code="HALLUCINATED_TOOL", message="H", workflow_id=wf_id
        )
        for _ in range(3)
    ]
    scorecard = ScorecardAggregator.aggregate(create_eval_result(findings))
    assert scorecard.tool_usage.score == 0.0
    assert scorecard.tool_usage.status == DomainStatus.FAIL


def test_workflow_quality_deductions_single_and_multiple_cycles() -> None:
    """Verify workflow quality: first cycle -30, additional cycles -15 each."""
    wf_id = uuid4()
    # 1 cycle: 100 - 30 = 70.0 (WARN)
    findings_1 = [
        EvaluationFinding(
            severity=FindingSeverity.HIGH, code="CYCLE_DETECTED", message="C1", workflow_id=wf_id
        )
    ]
    scorecard_1 = ScorecardAggregator.aggregate(create_eval_result(findings_1))
    assert scorecard_1.workflow_quality.score == 70.0
    assert scorecard_1.workflow_quality.status == DomainStatus.WARN

    # 3 cycles: 100 - 30 - 15 - 15 = 40.0 (FAIL)
    findings_3 = [
        EvaluationFinding(
            severity=FindingSeverity.HIGH, code="CYCLE_DETECTED", message=f"C{i}", workflow_id=wf_id
        )
        for i in range(3)
    ]
    scorecard_3 = ScorecardAggregator.aggregate(create_eval_result(findings_3))
    assert scorecard_3.workflow_quality.score == 40.0
    assert scorecard_3.workflow_quality.status == DomainStatus.FAIL


def test_reliability_deductions() -> None:
    """Verify reliability: RETRY_STORM (-25), EXCESSIVE_RETRIES (-10)."""
    wf_id = uuid4()
    findings = [
        EvaluationFinding(
            severity=FindingSeverity.HIGH, code="RETRY_STORM", message="RS", workflow_id=wf_id
        ),
        EvaluationFinding(
            severity=FindingSeverity.MEDIUM,
            code="EXCESSIVE_RETRIES",
            message="ER",
            workflow_id=wf_id,
        ),
    ]
    # 100 - 25 - 10 = 65.0 (WARN)
    scorecard = ScorecardAggregator.aggregate(create_eval_result(findings))
    assert scorecard.reliability.score == 65.0
    assert scorecard.reliability.status == DomainStatus.WARN


def test_cost_deductions() -> None:
    """Verify cost deductions: BUDGET_EXCEEDED (-30), TOKEN_BUDGET_EXCEEDED (-20), LATENCY_BUDGET_EXCEEDED (-10)."""
    wf_id = uuid4()
    findings = [
        EvaluationFinding(
            severity=FindingSeverity.HIGH, code="BUDGET_EXCEEDED", message="B", workflow_id=wf_id
        ),
        EvaluationFinding(
            severity=FindingSeverity.HIGH,
            code="TOKEN_BUDGET_EXCEEDED",
            message="TB",
            workflow_id=wf_id,
        ),
        EvaluationFinding(
            severity=FindingSeverity.MEDIUM,
            code="LATENCY_BUDGET_EXCEEDED",
            message="LB",
            workflow_id=wf_id,
        ),
    ]
    # 100 - 30 - 20 - 10 = 40.0 (FAIL)
    scorecard = ScorecardAggregator.aggregate(create_eval_result(findings))
    assert scorecard.cost.score == 40.0
    assert scorecard.cost.status == DomainStatus.FAIL


def test_efficiency_deductions() -> None:
    """Verify efficiency derived deductions: REDUNDANT_TOOL_CALL (-15), RETRY_STORM (-15), CYCLE_DETECTED (-15)."""
    wf_id = uuid4()
    findings = [
        EvaluationFinding(
            severity=FindingSeverity.MEDIUM,
            code="REDUNDANT_TOOL_CALL",
            message="R",
            workflow_id=wf_id,
        ),
        EvaluationFinding(
            severity=FindingSeverity.HIGH, code="RETRY_STORM", message="RS", workflow_id=wf_id
        ),
        EvaluationFinding(
            severity=FindingSeverity.HIGH, code="CYCLE_DETECTED", message="C", workflow_id=wf_id
        ),
    ]
    # 100 - 15 - 15 - 15 = 55.0 (FAIL)
    scorecard = ScorecardAggregator.aggregate(create_eval_result(findings))
    assert scorecard.efficiency.score == 55.0
    assert scorecard.efficiency.status == DomainStatus.FAIL


def test_get_domain_status_boundaries() -> None:
    """Verify get_domain_status threshold logic."""
    assert get_domain_status(100.0) == DomainStatus.PASS
    assert get_domain_status(80.0) == DomainStatus.PASS
    assert get_domain_status(79.9) == DomainStatus.WARN
    assert get_domain_status(60.0) == DomainStatus.WARN
    assert get_domain_status(59.9) == DomainStatus.FAIL
    assert get_domain_status(0.0) == DomainStatus.FAIL
