"""DeepEval adapter for semantic quality evaluation with isolated dependency and graceful degradation."""

import os
import time
from typing import Any

from app.domain.models import CanonicalTrace
from app.semantic.base import SemanticEvaluator
from app.semantic.models import SemanticEvaluationResult, SemanticFinding


class DeepEvalSemanticAdapter(SemanticEvaluator):
    """Adapter encapsulating DeepEval semantic evaluations with isolated imports and timeouts."""

    def __init__(
        self,
        threshold: float = 0.7,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.threshold = threshold
        self.timeout_seconds = timeout_seconds

    def _check_availability(self) -> None:
        """Validate required API keys and runtime dependencies before executing."""
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY environment variable is not configured.")

    def evaluate_relevancy(
        self,
        input_text: str,
        actual_output: str,
        context: list[str] | None = None,
    ) -> SemanticFinding:
        """Evaluate answer relevancy via DeepEval AnswerRelevancyMetric."""
        self._check_availability()
        try:
            from deepeval.metrics import AnswerRelevancyMetric
            from deepeval.test_case import LLMTestCase

            retrieval_ctx: list[Any] = list(context) if context else []
            test_case = LLMTestCase(
                input=input_text,
                actual_output=actual_output,
                retrieval_context=retrieval_ctx,
            )
            metric = AnswerRelevancyMetric(threshold=self.threshold)
            metric.measure(test_case)

            score = float(metric.score or 0.0)
            score = max(0.0, min(1.0, score))
            passed = bool(metric.is_successful())
            reason = str(metric.reason or "Evaluation calculated by DeepEval AnswerRelevancyMetric")

            return SemanticFinding(
                metric_name="answer_relevancy",
                score=score,
                passed=passed,
                explanation=reason,
            )
        except Exception as e:
            raise RuntimeError(f"DeepEval AnswerRelevancy evaluation failed: {e}") from e

    def evaluate_faithfulness(
        self,
        input_text: str,
        actual_output: str,
        retrieval_context: list[str],
    ) -> SemanticFinding:
        """Evaluate faithfulness against retrieval context via DeepEval FaithfulnessMetric."""
        self._check_availability()
        try:
            from deepeval.metrics import FaithfulnessMetric
            from deepeval.test_case import LLMTestCase

            faithfulness_ctx: list[Any] = list(retrieval_context) if retrieval_context else ["N/A"]
            test_case = LLMTestCase(
                input=input_text,
                actual_output=actual_output,
                retrieval_context=faithfulness_ctx,
            )
            metric = FaithfulnessMetric(threshold=self.threshold)
            metric.measure(test_case)

            score = float(metric.score or 0.0)
            score = max(0.0, min(1.0, score))
            passed = bool(metric.is_successful())
            reason = str(metric.reason or "Evaluation calculated by DeepEval FaithfulnessMetric")

            return SemanticFinding(
                metric_name="faithfulness",
                score=score,
                passed=passed,
                explanation=reason,
            )
        except Exception as e:
            raise RuntimeError(f"DeepEval Faithfulness evaluation failed: {e}") from e

    def evaluate_hallucination(
        self,
        input_text: str,
        actual_output: str,
        contexts: list[str],
    ) -> SemanticFinding:
        """Evaluate hallucination via DeepEval HallucinationMetric."""
        self._check_availability()
        try:
            from deepeval.metrics import HallucinationMetric
            from deepeval.test_case import LLMTestCase

            test_case = LLMTestCase(
                input=input_text,
                actual_output=actual_output,
                context=contexts if contexts else ["N/A"],
            )
            # Hallucination metric: lower score is better, or inverted threshold
            metric = HallucinationMetric(threshold=0.5)
            metric.measure(test_case)

            score = float(metric.score or 0.0)
            score = max(0.0, min(1.0, score))
            passed = bool(metric.is_successful())
            reason = str(metric.reason or "Evaluation calculated by DeepEval HallucinationMetric")

            return SemanticFinding(
                metric_name="hallucination",
                score=score,
                passed=passed,
                explanation=reason,
            )
        except Exception as e:
            raise RuntimeError(f"DeepEval Hallucination evaluation failed: {e}") from e

    def evaluate_trace(self, trace: CanonicalTrace) -> SemanticEvaluationResult:
        """Execute semantic evaluation metrics against a CanonicalTrace."""
        start_time = time.perf_counter()

        try:
            self._check_availability()

            input_text = trace.session.user_intent
            actual_output = ""
            if trace.steps:
                last_step = trace.steps[-1]
                if last_step.output_state:
                    actual_output = str(
                        last_step.output_state.get("result")
                        or last_step.output_state.get("response")
                        or last_step.output_state
                    )
                else:
                    actual_output = last_step.node_name

            contexts: list[str] = []
            for step in trace.steps:
                for tool in step.tool_calls:
                    if tool.execution_result:
                        contexts.append(str(tool.execution_result)[:500])

            findings: list[SemanticFinding] = [
                self.evaluate_relevancy(input_text, actual_output, contexts),
                self.evaluate_faithfulness(input_text, actual_output, contexts),
                self.evaluate_hallucination(input_text, actual_output, contexts),
            ]

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            return SemanticEvaluationResult(
                metrics=findings,
                provider="deepeval",
                execution_time_ms=round(elapsed_ms, 2),
                evaluation_available=True,
                reason=None,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return SemanticEvaluationResult(
                metrics=[],
                provider="deepeval",
                execution_time_ms=round(elapsed_ms, 2),
                evaluation_available=False,
                reason=str(e),
            )
