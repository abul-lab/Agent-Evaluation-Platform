"""Unit tests for semantic adapter factory and DeepEvalSemanticAdapter isolation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.domain.models import CanonicalTrace
from app.semantic.adapter import get_semantic_adapter, is_deepeval_available
from app.semantic.deepeval_adapter import DeepEvalSemanticAdapter
from app.semantic.fallback import FallbackSemanticAdapter
from app.semantic.models import SemanticFinding

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_canonical_trace(filename: str) -> CanonicalTrace:
    """Helper to load fixture as CanonicalTrace."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def test_is_deepeval_available() -> None:
    """Verify deepeval detection helper."""
    # Since deepeval 4.1.0 is installed in environment
    assert is_deepeval_available() is True


def test_is_deepeval_available_import_error() -> None:
    """Verify deepeval detection returns False when import fails."""
    with patch("builtins.__import__", side_effect=ImportError("No deepeval")):
        assert is_deepeval_available() is False


def test_get_semantic_adapter_deepeval_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify fallback when deepeval is not installed even if key is set."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    with patch("app.semantic.adapter.is_deepeval_available", return_value=False):
        resolved = get_semantic_adapter()
        assert isinstance(resolved, FallbackSemanticAdapter)
        assert "DeepEval library is not available" in (resolved.reason or "")


def test_get_semantic_adapter_override() -> None:
    """Verify override_adapter parameter takes precedence."""
    mock_adapter = FallbackSemanticAdapter(reason="Custom mock")
    resolved = get_semantic_adapter(override_adapter=mock_adapter)
    assert resolved is mock_adapter


def test_get_semantic_adapter_force_fallback() -> None:
    """Verify force_fallback flag resolves to FallbackSemanticAdapter."""
    resolved = get_semantic_adapter(force_fallback=True)
    assert isinstance(resolved, FallbackSemanticAdapter)
    assert "fallback mode" in (resolved.reason or "")


def test_get_semantic_adapter_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify missing OPENAI_API_KEY resolves to FallbackSemanticAdapter."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resolved = get_semantic_adapter()
    assert isinstance(resolved, FallbackSemanticAdapter)
    assert "OPENAI_API_KEY is not set" in (resolved.reason or "")


def test_get_semantic_adapter_with_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify presence of OPENAI_API_KEY resolves to DeepEvalSemanticAdapter."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-test-key")
    resolved = get_semantic_adapter()
    assert isinstance(resolved, DeepEvalSemanticAdapter)


def test_deepeval_adapter_check_availability_raises_when_no_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify _check_availability raises RuntimeError when key is missing."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    adapter = DeepEvalSemanticAdapter()
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        adapter._check_availability()


def test_deepeval_adapter_evaluate_trace_degrades_gracefully_when_no_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify evaluate_trace returns evaluation_available=False gracefully without unhandled exception."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    adapter = DeepEvalSemanticAdapter()
    trace = load_canonical_trace("clean_success_trace.json")

    result = adapter.evaluate_trace(trace)
    assert result.evaluation_available is False
    assert result.provider == "deepeval"
    assert result.metrics == []
    assert "OPENAI_API_KEY" in (result.reason or "")


def test_deepeval_adapter_mocked_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify evaluation methods produce valid SemanticFinding when DeepEval succeeds."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    adapter = DeepEvalSemanticAdapter(threshold=0.7)

    mock_metric = MagicMock()
    mock_metric.score = 0.88
    mock_metric.is_successful.return_value = True
    mock_metric.reason = "High semantic relevancy verified."

    with (
        patch("deepeval.metrics.AnswerRelevancyMetric", return_value=mock_metric),
        patch("deepeval.test_case.LLMTestCase", return_value=MagicMock()),
    ):
        finding = adapter.evaluate_relevancy("What is order status?", "Order is delivered.")
        assert finding.metric_name == "answer_relevancy"
        assert finding.score == 0.88
        assert finding.passed is True
        assert "High semantic relevancy" in finding.explanation


def test_deepeval_adapter_relevancy_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify evaluate_relevancy handles exceptions by raising RuntimeError."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    adapter = DeepEvalSemanticAdapter()
    with (
        patch("deepeval.metrics.AnswerRelevancyMetric", side_effect=ValueError("LLM timeout")),
        pytest.raises(RuntimeError, match="DeepEval AnswerRelevancy evaluation failed"),
    ):
        adapter.evaluate_relevancy("input", "output")


def test_deepeval_adapter_faithfulness(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify evaluate_faithfulness returns valid SemanticFinding."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    adapter = DeepEvalSemanticAdapter()

    mock_metric = MagicMock()
    mock_metric.score = 0.95
    mock_metric.is_successful.return_value = True
    mock_metric.reason = "Faithful output based on context."

    with (
        patch("deepeval.metrics.FaithfulnessMetric", return_value=mock_metric),
        patch("deepeval.test_case.LLMTestCase", return_value=MagicMock()),
    ):
        finding = adapter.evaluate_faithfulness("input", "output", ["context1", "context2"])
        assert finding.metric_name == "faithfulness"
        assert finding.score == 0.95
        assert finding.passed is True
        assert "Faithful output" in finding.explanation


def test_deepeval_adapter_faithfulness_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify evaluate_faithfulness handles exceptions by raising RuntimeError."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    adapter = DeepEvalSemanticAdapter()
    with (
        patch("deepeval.metrics.FaithfulnessMetric", side_effect=Exception("Failed to measure")),
        pytest.raises(RuntimeError, match="DeepEval Faithfulness evaluation failed"),
    ):
        adapter.evaluate_faithfulness("input", "output", [])


def test_deepeval_adapter_hallucination(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify evaluate_hallucination returns valid SemanticFinding."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    adapter = DeepEvalSemanticAdapter()

    mock_metric = MagicMock()
    mock_metric.score = 0.1
    mock_metric.is_successful.return_value = True
    mock_metric.reason = "No hallucination detected."

    with (
        patch("deepeval.metrics.HallucinationMetric", return_value=mock_metric),
        patch("deepeval.test_case.LLMTestCase", return_value=MagicMock()),
    ):
        finding = adapter.evaluate_hallucination("input", "output", ["context1"])
        assert finding.metric_name == "hallucination"
        assert finding.score == 0.1
        assert finding.passed is True
        assert "No hallucination" in finding.explanation


def test_deepeval_adapter_hallucination_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify evaluate_hallucination handles exceptions by raising RuntimeError."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    adapter = DeepEvalSemanticAdapter()
    with (
        patch("deepeval.metrics.HallucinationMetric", side_effect=Exception("API error")),
        pytest.raises(RuntimeError, match="DeepEval Hallucination evaluation failed"),
    ):
        adapter.evaluate_hallucination("input", "output", [])


def test_deepeval_adapter_evaluate_trace_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify evaluate_trace executes all metrics and returns complete result."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    adapter = DeepEvalSemanticAdapter()
    trace = load_canonical_trace("clean_success_trace.json")

    mock_finding = SemanticFinding(
        metric_name="answer_relevancy",
        score=0.9,
        passed=True,
        explanation="High relevancy",
    )

    with (
        patch.object(adapter, "evaluate_relevancy", return_value=mock_finding),
        patch.object(adapter, "evaluate_faithfulness", return_value=mock_finding),
        patch.object(adapter, "evaluate_hallucination", return_value=mock_finding),
    ):
        result = adapter.evaluate_trace(trace)
        assert result.evaluation_available is True
        assert result.provider == "deepeval"
        assert len(result.metrics) == 3
        assert result.execution_time_ms >= 0
        assert result.reason is None


def test_deepeval_adapter_evaluate_trace_fallback_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify evaluate_trace extracts node_name if step output_state is empty."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    adapter = DeepEvalSemanticAdapter()
    trace = load_canonical_trace("clean_success_trace.json")
    for step in trace.steps:
        step.output_state = {}

    mock_finding = SemanticFinding(
        metric_name="answer_relevancy",
        score=0.9,
        passed=True,
        explanation="High relevancy",
    )

    with (
        patch.object(adapter, "evaluate_relevancy", return_value=mock_finding) as mock_rel,
        patch.object(adapter, "evaluate_faithfulness", return_value=mock_finding),
        patch.object(adapter, "evaluate_hallucination", return_value=mock_finding),
    ):
        result = adapter.evaluate_trace(trace)
        assert result.evaluation_available is True
        mock_rel.assert_called_once()
        call_args = mock_rel.call_args[0]
        assert call_args[1] == trace.steps[-1].node_name
