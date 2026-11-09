"""Unit tests for ToolRegistryEvaluator."""

from pathlib import Path

from app.domain.models import CanonicalTrace
from app.evaluators.base import FindingSeverity
from app.evaluators.tool_registry import ToolRegistryEvaluator

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_trace(filename: str) -> CanonicalTrace:
    """Helper to load a CanonicalTrace from fixtures."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def test_clean_trace_has_no_hallucinated_tools() -> None:
    """Verify clean_success_trace has 0 tool hallucination findings."""
    trace = load_trace("clean_success_trace.json")
    evaluator = ToolRegistryEvaluator()
    findings = evaluator.evaluate(trace)

    assert len(findings) == 0


def test_hallucinated_tool_trace_detected() -> None:
    """Verify hallucinated_tool_trace flags HALLUCINATED_TOOL with HIGH severity."""
    trace = load_trace("hallucinated_tool_trace.json")
    evaluator = ToolRegistryEvaluator()
    findings = evaluator.evaluate(trace)

    assert len(findings) >= 1
    hallucinated_findings = [f for f in findings if f.code == "HALLUCINATED_TOOL"]
    assert len(hallucinated_findings) == 1

    finding = hallucinated_findings[0]
    assert finding.severity == FindingSeverity.HIGH
    assert finding.metadata["tool_name"] == "execute_bash_shell"
    assert 1 in finding.affected_steps


def test_missing_tool_schema_finding() -> None:
    """Verify tool with empty schema in registry flags MISSING_TOOL_SCHEMA."""
    trace = load_trace("clean_success_trace.json")
    # Artificially empty the schema for registered tool
    trace.agents[0].tool_registry[0].parameters_schema = {}

    evaluator = ToolRegistryEvaluator()
    findings = evaluator.evaluate(trace)

    schema_findings = [f for f in findings if f.code == "MISSING_TOOL_SCHEMA"]
    assert len(schema_findings) >= 1
    assert schema_findings[0].severity == FindingSeverity.MEDIUM
