"""Unit tests for RetryEvaluator."""

from pathlib import Path
from uuid import uuid4

from app.domain.enums import RetryResolution
from app.domain.models import CanonicalTrace, Retry, Step
from app.evaluators.base import FindingSeverity
from app.evaluators.retry_evaluator import RetryEvaluator

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_trace(filename: str) -> CanonicalTrace:
    """Helper to load a CanonicalTrace from fixtures."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def test_clean_trace_has_no_retry_findings() -> None:
    """Verify clean_success_trace has 0 retry issues."""
    trace = load_trace("clean_success_trace.json")
    evaluator = RetryEvaluator()
    findings = evaluator.evaluate(trace)

    assert len(findings) == 0


def test_retry_storm_trace_detected() -> None:
    """Verify retry_storm_trace flags RETRY_STORM with HIGH severity."""
    trace = load_trace("retry_storm_trace.json")
    evaluator = RetryEvaluator()
    findings = evaluator.evaluate(trace)

    storm_findings = [f for f in findings if f.code == "RETRY_STORM"]
    assert len(storm_findings) == 1
    finding = storm_findings[0]
    assert finding.severity == FindingSeverity.HIGH
    assert finding.metadata["total_retries"] >= 3
    assert 1 in finding.affected_steps


def test_excessive_retries_detected() -> None:
    """Verify 1-2 retries with low density flags EXCESSIVE_RETRIES."""
    trace = load_trace("clean_success_trace.json")
    # Add 1 retry to step 0
    trace.steps[0].retries.append(
        Retry(
            retry_id=uuid4(),
            step_id=trace.steps[0].step_id,
            attempt_number=1,
            error_type="TIMEOUT",
            backoff_duration_ms=100,
            resolution=RetryResolution.RESOLVED,
        )
    )
    # Add dummy steps to keep retry_density low
    for i in range(10):
        trace.steps.append(
            Step(
                step_id=uuid4(),
                workflow_id=trace.workflow.workflow_id,
                agent_id=trace.agents[0].agent_id,
                step_index=len(trace.steps),
                node_name=f"extra_step_{i}",
            )
        )

    evaluator = RetryEvaluator()
    findings = evaluator.evaluate(trace)

    excessive = [f for f in findings if f.code == "EXCESSIVE_RETRIES"]
    assert len(excessive) == 1
    assert excessive[0].severity == FindingSeverity.MEDIUM
