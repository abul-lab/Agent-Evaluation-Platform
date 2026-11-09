"""Unit tests for BudgetEvaluator."""

from decimal import Decimal
from pathlib import Path

from app.domain.models import CanonicalTrace
from app.evaluators.base import FindingSeverity
from app.evaluators.budget_evaluator import BudgetEvaluator

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_trace(filename: str) -> CanonicalTrace:
    """Helper to load a CanonicalTrace from fixtures."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def test_clean_trace_complies_with_budget() -> None:
    """Verify clean_success_trace raises 0 budget findings."""
    trace = load_trace("clean_success_trace.json")
    evaluator = BudgetEvaluator()
    findings = evaluator.evaluate(trace)

    assert len(findings) == 0


def test_budget_exceeded_trace_detected() -> None:
    """Verify budget_exceeded_trace flags BUDGET_EXCEEDED and TOKEN_BUDGET_EXCEEDED."""
    trace = load_trace("budget_exceeded_trace.json")
    evaluator = BudgetEvaluator()
    findings = evaluator.evaluate(trace)

    codes = {f.code for f in findings}
    assert "BUDGET_EXCEEDED" in codes
    assert "TOKEN_BUDGET_EXCEEDED" in codes

    cost_finding = next(f for f in findings if f.code == "BUDGET_EXCEEDED")
    assert cost_finding.severity == FindingSeverity.HIGH
    assert Decimal(cost_finding.metadata["actual_cost_usd"]) > Decimal(
        cost_finding.metadata["max_budget_usd"]
    )

    token_finding = next(f for f in findings if f.code == "TOKEN_BUDGET_EXCEEDED")
    assert token_finding.severity == FindingSeverity.HIGH
    assert token_finding.metadata["total_tokens"] > token_finding.metadata["max_tokens"]


def test_latency_budget_exceeded_detected() -> None:
    """Verify latency threshold breach flags LATENCY_BUDGET_EXCEEDED."""
    trace = load_trace("clean_success_trace.json")
    # Artificially lower latency ceiling to trigger breach
    trace.session.budget_constraints.max_latency_ms = 1000

    evaluator = BudgetEvaluator()
    findings = evaluator.evaluate(trace)

    latency_finding = next((f for f in findings if f.code == "LATENCY_BUDGET_EXCEEDED"), None)
    assert latency_finding is not None
    assert latency_finding.severity == FindingSeverity.MEDIUM
