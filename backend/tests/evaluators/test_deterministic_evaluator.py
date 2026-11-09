"""Contract and integration tests for the DeterministicEvaluationService."""

from pathlib import Path

from app.domain.models import CanonicalTrace
from app.services.deterministic_evaluator import DeterministicEvaluationService

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_trace(filename: str) -> CanonicalTrace:
    """Helper to load a CanonicalTrace from fixtures."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def test_clean_success_trace_contract() -> None:
    """Contract: clean_success_trace has 0 critical and 0 high severity findings."""
    trace = load_trace("clean_success_trace.json")
    service = DeterministicEvaluationService()
    result = service.evaluate_trace(trace)

    assert result.critical_count == 0
    assert result.high_count == 0
    assert result.workflow_id == trace.workflow.workflow_id
    assert result.session_id == trace.session.session_id


def test_loop_trace_contract() -> None:
    """Contract: loop_trace flags CYCLE_DETECTED."""
    trace = load_trace("loop_trace.json")
    service = DeterministicEvaluationService()
    result = service.evaluate_trace(trace)

    codes = {f.code for f in result.findings}
    assert "CYCLE_DETECTED" in codes
    assert result.high_count >= 1


def test_hallucinated_tool_trace_contract() -> None:
    """Contract: hallucinated_tool_trace flags HALLUCINATED_TOOL."""
    trace = load_trace("hallucinated_tool_trace.json")
    service = DeterministicEvaluationService()
    result = service.evaluate_trace(trace)

    codes = {f.code for f in result.findings}
    assert "HALLUCINATED_TOOL" in codes
    assert result.high_count >= 1


def test_retry_storm_trace_contract() -> None:
    """Contract: retry_storm_trace flags RETRY_STORM."""
    trace = load_trace("retry_storm_trace.json")
    service = DeterministicEvaluationService()
    result = service.evaluate_trace(trace)

    codes = {f.code for f in result.findings}
    assert "RETRY_STORM" in codes
    assert result.high_count >= 1


def test_budget_exceeded_trace_contract() -> None:
    """Contract: budget_exceeded_trace flags BUDGET_EXCEEDED and TOKEN_BUDGET_EXCEEDED."""
    trace = load_trace("budget_exceeded_trace.json")
    service = DeterministicEvaluationService()
    result = service.evaluate_trace(trace)

    codes = {f.code for f in result.findings}
    assert "BUDGET_EXCEEDED" in codes
    assert "TOKEN_BUDGET_EXCEEDED" in codes
    assert result.high_count >= 1


def test_secret_leak_trace_contract() -> None:
    """Contract: secret_leak_trace flags SECRET_EXPOSURE with critical_count >= 1."""
    trace = load_trace("secret_leak_trace.json")
    service = DeterministicEvaluationService()
    result = service.evaluate_trace(trace)

    codes = {f.code for f in result.findings}
    assert "SECRET_EXPOSURE" in codes
    assert result.critical_count >= 1
