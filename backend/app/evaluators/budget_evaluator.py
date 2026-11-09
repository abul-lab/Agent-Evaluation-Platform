"""Deterministic evaluator for financial cost, token, and latency budget compliance."""

from app.domain.models import CanonicalTrace
from app.evaluators.base import BaseDeterministicEvaluator, EvaluationFinding, FindingSeverity


class BudgetEvaluator(BaseDeterministicEvaluator):
    """Audits trace execution cost, token consumption, and duration against configured budgets."""

    def evaluate(self, trace: CanonicalTrace) -> list[EvaluationFinding]:
        """Check trace metrics against Session budget constraints."""
        findings: list[EvaluationFinding] = []
        budget = trace.session.budget_constraints
        workflow = trace.workflow

        # 1. Cost Budget Check
        actual_cost = workflow.total_cost_usd
        max_cost = budget.max_usd
        if actual_cost > max_cost:
            overrun = actual_cost - max_cost
            findings.append(
                EvaluationFinding(
                    severity=FindingSeverity.HIGH,
                    code="BUDGET_EXCEEDED",
                    message=(
                        f"Financial budget breached: execution cost ${actual_cost:.4f} "
                        f"exceeded maximum allowed budget of ${max_cost:.4f} (overrun: ${overrun:.4f})."
                    ),
                    workflow_id=workflow.workflow_id,
                    affected_steps=[],
                    metadata={
                        "actual_cost_usd": str(actual_cost),
                        "max_budget_usd": str(max_cost),
                        "overrun_usd": str(overrun),
                    },
                )
            )

        # 2. Token Budget Check
        total_tokens = sum(s.token_usage.total_tokens for s in trace.steps)
        max_tokens = budget.max_tokens
        if total_tokens > max_tokens:
            token_overrun = total_tokens - max_tokens
            findings.append(
                EvaluationFinding(
                    severity=FindingSeverity.HIGH,
                    code="TOKEN_BUDGET_EXCEEDED",
                    message=(
                        f"Token consumption budget breached: consumed {total_tokens:,} tokens, "
                        f"exceeding ceiling of {max_tokens:,} tokens (overrun: {token_overrun:,})."
                    ),
                    workflow_id=workflow.workflow_id,
                    affected_steps=[],
                    metadata={
                        "total_tokens": total_tokens,
                        "max_tokens": max_tokens,
                        "overrun_tokens": token_overrun,
                    },
                )
            )

        # 3. Latency Budget Check
        actual_latency_ms = workflow.total_latency_ms
        max_latency_ms = budget.max_latency_ms
        if actual_latency_ms > max_latency_ms:
            latency_overrun_ms = actual_latency_ms - max_latency_ms
            findings.append(
                EvaluationFinding(
                    severity=FindingSeverity.MEDIUM,
                    code="LATENCY_BUDGET_EXCEEDED",
                    message=(
                        f"Wall-clock duration budget breached: total latency {actual_latency_ms}ms "
                        f"exceeded threshold of {max_latency_ms}ms (overrun: {latency_overrun_ms}ms)."
                    ),
                    workflow_id=workflow.workflow_id,
                    affected_steps=[],
                    metadata={
                        "actual_latency_ms": actual_latency_ms,
                        "max_latency_ms": max_latency_ms,
                        "overrun_ms": latency_overrun_ms,
                    },
                )
            )

        return findings
