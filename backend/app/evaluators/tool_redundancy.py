"""Deterministic evaluator for duplicate / redundant tool executions."""

import json

from app.domain.models import CanonicalTrace
from app.evaluators.base import BaseDeterministicEvaluator, EvaluationFinding, FindingSeverity


class ToolRedundancyEvaluator(BaseDeterministicEvaluator):
    """Detects repeated tool invocations with identical arguments."""

    def evaluate(self, trace: CanonicalTrace) -> list[EvaluationFinding]:
        """Scan trace for redundant tool calls."""
        findings: list[EvaluationFinding] = []
        seen_calls: dict[str, int] = {}  # signature -> first step index

        for step in trace.steps:
            for tool_call in step.tool_calls:
                # Canonical JSON representation of arguments
                try:
                    args_key = json.dumps(tool_call.raw_arguments, sort_keys=True)
                except (TypeError, ValueError):
                    args_key = str(tool_call.raw_arguments)

                call_signature = f"{tool_call.tool_name}::{args_key}"

                if call_signature in seen_calls or tool_call.is_redundant:
                    first_seen_step = seen_calls.get(call_signature, 0)
                    findings.append(
                        EvaluationFinding(
                            severity=FindingSeverity.MEDIUM,
                            code="REDUNDANT_TOOL_CALL",
                            message=(
                                f"Redundant tool invocation in step {step.step_index}: '{tool_call.tool_name}' "
                                f"was executed with identical arguments already seen in step {first_seen_step}."
                            ),
                            workflow_id=trace.workflow.workflow_id,
                            affected_steps=[first_seen_step, step.step_index],
                            metadata={
                                "tool_name": tool_call.tool_name,
                                "first_seen_step": first_seen_step,
                                "redundant_step": step.step_index,
                                "raw_arguments": tool_call.raw_arguments,
                            },
                        )
                    )
                else:
                    seen_calls[call_signature] = step.step_index

        return findings
