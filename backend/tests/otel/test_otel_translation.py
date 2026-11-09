"""Comprehensive tests for OpenTelemetry to Canonical Agent Trace Schema (CATS) translation."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from app.domain.enums import FrameworkType, WorkflowStatus
from app.domain.models import CanonicalTrace
from app.otel.otel_parser import parse_otel_payload
from app.otel.otel_to_cats import translate_otel_trace_to_cats
from app.scorecard.aggregator import ScorecardAggregator
from app.services.deterministic_evaluator import DeterministicEvaluationService

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "otel"


def load_otel_fixture(filename: str) -> dict[str, Any]:
    path = FIXTURES_DIR / filename
    with open(path, encoding="utf-8") as f:
        loaded: dict[str, Any] = json.load(f)
        return loaded


def test_translate_langgraph_trace() -> None:
    raw = load_otel_fixture("langgraph_trace.json")
    otel_trace = parse_otel_payload(raw)
    cats = translate_otel_trace_to_cats(otel_trace)

    assert isinstance(cats, CanonicalTrace)
    assert cats.workflow.framework == FrameworkType.LANGGRAPH
    assert cats.workflow.status == WorkflowStatus.SUCCESS
    assert len(cats.steps) == 4
    assert len(cats.agents) >= 1
    assert cats.session.session_id is not None
    assert isinstance(cats.session.session_id, UUID)

    # Verify tool extraction
    tool_steps = [s for s in cats.steps if s.tool_calls]
    assert len(tool_steps) == 1
    tc = tool_steps[0].tool_calls[0]
    assert tc.tool_name == "fetch_delivery_status"
    assert tc.raw_arguments.get("order_id") == "ORD-9912"
    assert not tc.is_error

    # Verify DAG hierarchy retention
    assert cats.steps[1].input_state.get("_otel_parent_span_id") == "00f067aa0ba902b7"


def test_translate_crewai_trace() -> None:
    raw = load_otel_fixture("crewai_trace.json")
    otel_trace = parse_otel_payload(raw)
    cats = translate_otel_trace_to_cats(otel_trace)

    assert isinstance(cats, CanonicalTrace)
    assert cats.workflow.framework == FrameworkType.CREWAI
    assert len(cats.steps) == 4
    assert len(cats.agents) >= 1

    # Verify tool calls and tokens
    tool_steps = [s for s in cats.steps if s.tool_calls]
    assert len(tool_steps) >= 1
    assert tool_steps[0].tool_calls[0].tool_name == "sec_filing_scraper"

    total_prompt_tokens = sum(s.token_usage.prompt_tokens for s in cats.steps)
    assert total_prompt_tokens == 750


def test_translate_autogen_trace() -> None:
    raw = load_otel_fixture("autogen_trace.json")
    otel_trace = parse_otel_payload(raw)
    cats = translate_otel_trace_to_cats(otel_trace)

    assert isinstance(cats, CanonicalTrace)
    assert cats.workflow.framework == FrameworkType.AUTOGEN
    assert len(cats.steps) == 3
    assert cats.workflow.total_cost_usd > 0


def test_translate_openai_agents_trace() -> None:
    raw = load_otel_fixture("openai_agents_trace.json")
    otel_trace = parse_otel_payload(raw)
    cats = translate_otel_trace_to_cats(otel_trace)

    assert isinstance(cats, CanonicalTrace)
    assert cats.workflow.framework in (FrameworkType.CUSTOM, FrameworkType.OPENTELEMETRY)
    assert len(cats.steps) == 4

    weather_step = [
        s for s in cats.steps if any(tc.tool_name == "get_current_weather" for tc in s.tool_calls)
    ]
    assert len(weather_step) == 1


def test_translate_llamaindex_trace() -> None:
    raw = load_otel_fixture("llamaindex_trace.json")
    otel_trace = parse_otel_payload(raw)
    cats = translate_otel_trace_to_cats(otel_trace)

    assert isinstance(cats, CanonicalTrace)
    assert len(cats.steps) == 3
    assert "remote work" in cats.session.user_intent.lower()


def test_evaluator_compatibility_with_translated_cats() -> None:
    """Verify that CATS generated from OTEL runs through the existing evaluation pipeline."""
    raw = load_otel_fixture("langgraph_trace.json")
    otel_trace = parse_otel_payload(raw)
    cats = translate_otel_trace_to_cats(otel_trace)

    eval_service = DeterministicEvaluationService()
    eval_result = eval_service.evaluate_trace(cats)
    assert eval_result is not None

    scorecard = ScorecardAggregator.aggregate(eval_result)
    assert scorecard.overall_score >= 80.0
    assert scorecard.risk_classification.value in ("EXCELLENT", "GOOD")
