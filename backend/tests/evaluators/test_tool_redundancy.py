"""Unit tests for ToolRedundancyEvaluator."""

from pathlib import Path

from app.domain.models import CanonicalTrace
from app.evaluators.base import FindingSeverity
from app.evaluators.tool_redundancy import ToolRedundancyEvaluator

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_trace(filename: str) -> CanonicalTrace:
    """Helper to load a CanonicalTrace from fixtures."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def test_clean_trace_has_no_redundant_tools() -> None:
    """Verify clean_success_trace has 0 redundant tool executions."""
    trace = load_trace("clean_success_trace.json")
    evaluator = ToolRedundancyEvaluator()
    findings = evaluator.evaluate(trace)

    assert len(findings) == 0


def test_loop_trace_has_redundant_tools() -> None:
    """Verify loop_trace flags REDUNDANT_TOOL_CALL for repeated tool executions."""
    trace = load_trace("loop_trace.json")
    evaluator = ToolRedundancyEvaluator()
    findings = evaluator.evaluate(trace)

    redundant_findings = [f for f in findings if f.code == "REDUNDANT_TOOL_CALL"]
    assert len(redundant_findings) >= 2

    for finding in redundant_findings:
        assert finding.severity == FindingSeverity.MEDIUM
        assert "tool_name" in finding.metadata
        assert "first_seen_step" in finding.metadata
