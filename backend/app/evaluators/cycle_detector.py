"""Deterministic evaluator for detecting repetitive cycles and execution loops."""

from typing import Any

from app.domain.models import CanonicalTrace
from app.evaluators.base import BaseDeterministicEvaluator, EvaluationFinding, FindingSeverity


def find_repetitive_cycles(nodes: list[str], max_period: int = 5) -> list[dict[str, Any]]:
    """Detect contiguous repeating patterns of length 1..max_period in a sequence of node names."""
    cycles: list[dict[str, Any]] = []
    n = len(nodes)
    seen_step_spans: set[tuple[int, int]] = set()

    for period in range(1, max_period + 1):
        if 2 * period > n:
            break

        idx = 0
        while idx + 2 * period <= n:
            pattern = nodes[idx : idx + period]
            repeats = 1
            next_idx = idx + period

            while next_idx + period <= n and nodes[next_idx : next_idx + period] == pattern:
                repeats += 1
                next_idx += period

            if repeats >= 2:
                span = (idx, next_idx)
                if span not in seen_step_spans:
                    seen_step_spans.add(span)
                    cycles.append(
                        {
                            "period": period,
                            "pattern": pattern,
                            "occurrences": repeats,
                            "start_step": idx,
                            "end_step": next_idx - 1,
                            "affected_steps": list(range(idx, next_idx)),
                        }
                    )
                idx = next_idx
            else:
                idx += 1

    return cycles


class WorkflowCycleEvaluator(BaseDeterministicEvaluator):
    """Detects cyclic node oscillations and non-terminating loops in execution DAGs."""

    def evaluate(self, trace: CanonicalTrace) -> list[EvaluationFinding]:
        """Audit workflow step sequence for cyclic loop execution."""
        findings: list[EvaluationFinding] = []
        node_names = [step.node_name for step in trace.steps]

        detected_cycles = find_repetitive_cycles(node_names, max_period=5)

        for cycle in detected_cycles:
            pattern_str = " -> ".join(cycle["pattern"])
            findings.append(
                EvaluationFinding(
                    severity=FindingSeverity.HIGH,
                    code="CYCLE_DETECTED",
                    message=(
                        f"Cyclic execution loop detected across steps {cycle['start_step']}..{cycle['end_step']}: "
                        f"sequence [{pattern_str}] repeated {cycle['occurrences']} times."
                    ),
                    workflow_id=trace.workflow.workflow_id,
                    affected_steps=cycle["affected_steps"],
                    metadata={
                        "period": cycle["period"],
                        "pattern": cycle["pattern"],
                        "occurrences": cycle["occurrences"],
                        "start_step": cycle["start_step"],
                        "end_step": cycle["end_step"],
                    },
                )
            )

        return findings
