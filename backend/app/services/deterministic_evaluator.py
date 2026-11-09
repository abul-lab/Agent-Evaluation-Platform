"""Service orchestrator executing all deterministic evaluators on canonical traces."""

from datetime import UTC, datetime

from app.domain.models import CanonicalTrace
from app.evaluators.base import (
    BaseDeterministicEvaluator,
    DeterministicEvaluationResult,
    EvaluationFinding,
    FindingSeverity,
)
from app.evaluators.budget_evaluator import BudgetEvaluator
from app.evaluators.cycle_detector import WorkflowCycleEvaluator
from app.evaluators.retry_evaluator import RetryEvaluator
from app.evaluators.secret_scanner import SecretExposureEvaluator
from app.evaluators.tool_redundancy import ToolRedundancyEvaluator
from app.evaluators.tool_registry import ToolRegistryEvaluator


class DeterministicEvaluationService:
    """Orchestrates deterministic trace audits and aggregates findings."""

    def __init__(
        self,
        evaluators: list[BaseDeterministicEvaluator] | None = None,
    ) -> None:
        self.evaluators = evaluators or [
            ToolRegistryEvaluator(),
            ToolRedundancyEvaluator(),
            WorkflowCycleEvaluator(),
            RetryEvaluator(),
            BudgetEvaluator(),
            SecretExposureEvaluator(),
        ]

    def evaluate_trace(self, trace: CanonicalTrace) -> DeterministicEvaluationResult:
        """Run all registered deterministic evaluators against a CanonicalTrace."""
        all_findings: list[EvaluationFinding] = []

        for evaluator in self.evaluators:
            findings = evaluator.evaluate(trace)
            all_findings.extend(findings)

        critical_count = sum(1 for f in all_findings if f.severity == FindingSeverity.CRITICAL)
        high_count = sum(1 for f in all_findings if f.severity == FindingSeverity.HIGH)
        medium_count = sum(1 for f in all_findings if f.severity == FindingSeverity.MEDIUM)
        low_count = sum(1 for f in all_findings if f.severity == FindingSeverity.LOW)
        info_count = sum(1 for f in all_findings if f.severity == FindingSeverity.INFO)

        return DeterministicEvaluationResult(
            workflow_id=trace.workflow.workflow_id,
            session_id=trace.session.session_id,
            evaluated_at=datetime.now(UTC),
            findings=all_findings,
            total_findings=len(all_findings),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            info_count=info_count,
        )
