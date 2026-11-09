"""Semantic evaluation package providing isolated adapters and graceful degradation."""

from app.semantic.adapter import get_semantic_adapter, is_deepeval_available
from app.semantic.base import SemanticEvaluator
from app.semantic.deepeval_adapter import DeepEvalSemanticAdapter
from app.semantic.fallback import FallbackSemanticAdapter
from app.semantic.models import SemanticEvaluationResult, SemanticFinding

__all__ = [
    "DeepEvalSemanticAdapter",
    "FallbackSemanticAdapter",
    "SemanticEvaluationResult",
    "SemanticEvaluator",
    "SemanticFinding",
    "get_semantic_adapter",
    "is_deepeval_available",
]
