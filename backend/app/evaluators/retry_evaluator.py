"""Deterministic evaluator for workflow retry behavior and instability."""

from app.domain.models import CanonicalTrace
from app.evaluators.base import BaseDeterministicEvaluator, EvaluationFinding, FindingSeverity


class RetryEvaluator(BaseDeterministicEvaluator):
    """Measures workflow instability by evaluating step retries and backoff bursts."""

    def evaluate(self, trace: CanonicalTrace) -> list[EvaluationFinding]:
        """Audit retries across workflow steps."""
        findings: list[EvaluationFinding] = []

        total_retries = 0
        steps_with_retries: list[int] = []
        max_step_retries = 0

        for step in trace.steps:
            retry_count = len(step.retries)
            if retry_count > 0:
                total_retries += retry_count
                steps_with_retries.append(step.step_index)
                if retry_count > max_step_retries:
                    max_step_retries = retry_count

        step_count = len(trace.steps)
        retry_density = (total_retries / step_count) if step_count > 0 else 0.0

        if total_retries >= 3 or max_step_retries >= 3 or retry_density >= 0.5:
            findings.append(
                EvaluationFinding(
                    severity=FindingSeverity.HIGH,
                    code="RETRY_STORM",
                    message=(
                        f"Retry storm detected across {len(steps_with_retries)} step(s): "
                        f"{total_retries} total retries observed (max {max_step_retries} on a single step)."
                    ),
                    workflow_id=trace.workflow.workflow_id,
                    affected_steps=steps_with_retries,
                    metadata={
                        "total_retries": total_retries,
                        "max_step_retries": max_step_retries,
                        "retry_density": round(retry_density, 3),
                        "steps_affected": steps_with_retries,
                    },
                )
            )
        elif total_retries > 0:
            findings.append(
                EvaluationFinding(
                    severity=FindingSeverity.MEDIUM,
                    code="EXCESSIVE_RETRIES",
                    message=(
                        f"Excessive retries observed: workflow executed {total_retries} retries "
                        f"across {len(steps_with_retries)} step(s)."
                    ),
                    workflow_id=trace.workflow.workflow_id,
                    affected_steps=steps_with_retries,
                    metadata={
                        "total_retries": total_retries,
                        "retry_density": round(retry_density, 3),
                        "steps_affected": steps_with_retries,
                    },
                )
            )

        return findings
