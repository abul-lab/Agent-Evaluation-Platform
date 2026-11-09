"""Unit tests for WorkflowCycleEvaluator."""

from pathlib import Path
from uuid import uuid4

from app.domain.models import CanonicalTrace
from app.evaluators.base import FindingSeverity
from app.evaluators.cycle_detector import WorkflowCycleEvaluator, find_repetitive_cycles

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_trace(filename: str) -> CanonicalTrace:
    """Helper to load a CanonicalTrace from fixtures."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def test_clean_trace_has_no_cycles() -> None:
    """Verify clean_success_trace raises 0 cycle findings."""
    trace = load_trace("clean_success_trace.json")
    evaluator = WorkflowCycleEvaluator()
    findings = evaluator.evaluate(trace)

    assert len(findings) == 0


def test_loop_trace_cycle_detected() -> None:
    """Verify loop_trace flags CYCLE_DETECTED with HIGH severity."""
    trace = load_trace("loop_trace.json")
    evaluator = WorkflowCycleEvaluator()
    findings = evaluator.evaluate(trace)

    cycle_findings = [f for f in findings if f.code == "CYCLE_DETECTED"]
    assert len(cycle_findings) >= 1
    finding = cycle_findings[0]
    assert finding.severity == FindingSeverity.HIGH
    assert finding.metadata["period"] == 2
    assert finding.metadata["pattern"] == ["filing_query_node", "refine_terms_node"]
    assert finding.metadata["occurrences"] >= 2


def test_find_repetitive_cycles_periods() -> None:
    """Verify cycle detection algorithm on periods 1, 2, 3."""
    # Period 1 (self loop: A -> A)
    nodes_p1 = ["A", "B", "C", "C", "C", "D"]
    cycles_p1 = find_repetitive_cycles(nodes_p1)
    assert any(c["period"] == 1 and c["pattern"] == ["C"] for c in cycles_p1)

    # Period 3 (A -> B -> C -> A -> B -> C)
    nodes_p3 = ["start", "A", "B", "C", "A", "B", "C", "end"]
    cycles_p3 = find_repetitive_cycles(nodes_p3)
    assert any(c["period"] == 3 and c["pattern"] == ["A", "B", "C"] for c in cycles_p3)


def test_synthetic_cycle_in_trace() -> None:
    """Verify custom cyclic trace flags CYCLE_DETECTED."""
    trace = load_trace("clean_success_trace.json")
    # Duplicate existing steps to produce an alternating cycle
    step_a = trace.steps[0].model_copy(
        update={"step_id": uuid4(), "step_index": 3, "node_name": "node_A"}
    )
    step_b = trace.steps[1].model_copy(
        update={"step_id": uuid4(), "step_index": 4, "node_name": "node_B"}
    )
    step_c = trace.steps[0].model_copy(
        update={"step_id": uuid4(), "step_index": 5, "node_name": "node_A"}
    )
    step_d = trace.steps[1].model_copy(
        update={"step_id": uuid4(), "step_index": 6, "node_name": "node_B"}
    )
    trace.steps.extend([step_a, step_b, step_c, step_d])

    evaluator = WorkflowCycleEvaluator()
    findings = evaluator.evaluate(trace)
    assert any(f.code == "CYCLE_DETECTED" for f in findings)
