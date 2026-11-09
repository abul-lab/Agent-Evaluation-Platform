"""Fallback semantic evaluation adapter used when external providers or API keys are unavailable."""

from app.domain.models import CanonicalTrace
from app.semantic.base import SemanticEvaluator
from app.semantic.models import SemanticEvaluationResult, SemanticFinding


class FallbackSemanticAdapter(SemanticEvaluator):
    """Graceful degradation adapter returning safe empty metrics without external API calls."""

    def __init__(self, reason: str = "Semantic evaluation is unavailable or disabled.") -> None:
        self.reason = reason

    def evaluate_relevancy(
        self,
        input_text: str,
        actual_output: str,
        context: list[str] | None = None,
    ) -> SemanticFinding:
        """Return fallback placeholder for relevancy metric."""
        return SemanticFinding(
            metric_name="answer_relevancy",
            score=0.0,
            passed=False,
            explanation=self.reason,
        )

    def evaluate_faithfulness(
        self,
        input_text: str,
        actual_output: str,
        retrieval_context: list[str],
    ) -> SemanticFinding:
        """Return fallback placeholder for faithfulness metric."""
        return SemanticFinding(
            metric_name="faithfulness",
            score=0.0,
            passed=False,
            explanation=self.reason,
        )

    def evaluate_hallucination(
        self,
        input_text: str,
        actual_output: str,
        contexts: list[str],
    ) -> SemanticFinding:
        """Return fallback placeholder for hallucination metric."""
        return SemanticFinding(
            metric_name="hallucination",
            score=0.0,
            passed=False,
            explanation=self.reason,
        )

    def evaluate_trace(self, trace: CanonicalTrace) -> SemanticEvaluationResult:
        """Return an unavailable semantic evaluation outcome safely without model execution."""
        return SemanticEvaluationResult(
            metrics=[],
            provider="fallback",
            execution_time_ms=0.0,
            evaluation_available=False,
            reason=self.reason,
        )
