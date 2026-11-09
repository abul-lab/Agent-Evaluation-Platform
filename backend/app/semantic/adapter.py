"""Factory and resolver for semantic evaluation adapters."""

import os

from app.semantic.base import SemanticEvaluator
from app.semantic.deepeval_adapter import DeepEvalSemanticAdapter
from app.semantic.fallback import FallbackSemanticAdapter


def is_deepeval_available() -> bool:
    """Check if DeepEval library is importable in the runtime."""
    try:
        import deepeval  # noqa: F401

        return True
    except ImportError:
        return False


def get_semantic_adapter(
    force_fallback: bool = False,
    override_adapter: SemanticEvaluator | None = None,
) -> SemanticEvaluator:
    """Resolve and instantiate the appropriate semantic evaluation adapter.

    Returns DeepEvalSemanticAdapter only if DeepEval is installed and OPENAI_API_KEY is configured.
    Otherwise gracefully resolves to FallbackSemanticAdapter.
    """
    if override_adapter is not None:
        return override_adapter

    if force_fallback:
        return FallbackSemanticAdapter(
            reason="Semantic evaluation explicitly configured to fallback mode."
        )

    has_key = bool(os.environ.get("OPENAI_API_KEY"))
    if not has_key:
        return FallbackSemanticAdapter(
            reason="OPENAI_API_KEY is not set. Operating in fallback mode."
        )

    if not is_deepeval_available():
        return FallbackSemanticAdapter(reason="DeepEval library is not available in runtime.")

    return DeepEvalSemanticAdapter()
