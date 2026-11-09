"""Abstract base interface for semantic quality evaluators."""

from abc import ABC, abstractmethod

from app.domain.models import CanonicalTrace
from app.semantic.models import SemanticEvaluationResult, SemanticFinding


class SemanticEvaluator(ABC):
    """Abstract interface defining required methods for semantic evaluation adapters."""

    @abstractmethod
    def evaluate_relevancy(
        self,
        input_text: str,
        actual_output: str,
        context: list[str] | None = None,
    ) -> SemanticFinding:
        """Evaluate how relevant the actual output is to the input intent."""
        raise NotImplementedError

    @abstractmethod
    def evaluate_faithfulness(
        self,
        input_text: str,
        actual_output: str,
        retrieval_context: list[str],
    ) -> SemanticFinding:
        """Evaluate whether the actual output is grounded in the retrieved context."""
        raise NotImplementedError

    @abstractmethod
    def evaluate_hallucination(
        self,
        input_text: str,
        actual_output: str,
        contexts: list[str],
    ) -> SemanticFinding:
        """Evaluate whether the actual output contains ungrounded claims."""
        raise NotImplementedError

    @abstractmethod
    def evaluate_trace(self, trace: CanonicalTrace) -> SemanticEvaluationResult:
        """Execute semantic evaluation metrics against a CanonicalTrace."""
        raise NotImplementedError
