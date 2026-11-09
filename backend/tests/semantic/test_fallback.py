"""Unit tests for FallbackSemanticAdapter."""

from pathlib import Path

from app.domain.models import CanonicalTrace
from app.semantic.fallback import FallbackSemanticAdapter

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_canonical_trace(filename: str) -> CanonicalTrace:
    """Helper to load fixture as CanonicalTrace."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def test_fallback_adapter_evaluate_trace() -> None:
    """Verify FallbackSemanticAdapter safely returns unavailable outcome."""
    adapter = FallbackSemanticAdapter(reason="Air-gapped execution.")
    trace = load_canonical_trace("clean_success_trace.json")

    result = adapter.evaluate_trace(trace)
    assert result.evaluation_available is False
    assert result.provider == "fallback"
    assert result.metrics == []
    assert result.execution_time_ms == 0.0
    assert result.reason == "Air-gapped execution."


def test_fallback_adapter_metric_methods() -> None:
    """Verify individual metric fallback methods return safe default findings."""
    adapter = FallbackSemanticAdapter(reason="Fallback active")

    rel = adapter.evaluate_relevancy("input", "output")
    assert rel.metric_name == "answer_relevancy"
    assert rel.score == 0.0
    assert rel.passed is False
    assert rel.explanation == "Fallback active"

    faith = adapter.evaluate_faithfulness("input", "output", ["context"])
    assert faith.metric_name == "faithfulness"
    assert faith.score == 0.0
    assert faith.passed is False

    halluc = adapter.evaluate_hallucination("input", "output", ["context"])
    assert halluc.metric_name == "hallucination"
    assert halluc.score == 0.0
    assert halluc.passed is False
