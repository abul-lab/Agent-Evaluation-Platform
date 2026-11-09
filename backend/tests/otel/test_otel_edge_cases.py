"""Edge case tests for OpenTelemetry parser, adapter, translation, and error handling."""

import json
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.domain.enums import WorkflowStatus
from app.otel.otel_adapter import (
    extract_cost_usd,
    extract_input_state,
    extract_output_state,
    extract_span_latency_ms,
    extract_token_counts,
)
from app.otel.otel_models import OTELSpan, OTELTrace
from app.otel.otel_parser import _flatten_otlp_attributes, parse_otel_payload, validate_otel_trace
from app.otel.otel_to_cats import translate_otel_trace_to_cats


def test_flatten_otlp_attributes_variations() -> None:
    # 1. Direct dict
    assert _flatten_otlp_attributes({"a": 1}) == {"a": 1}
    # 2. Non-list / non-dict
    assert _flatten_otlp_attributes("invalid") == {}
    assert _flatten_otlp_attributes(None) == {}

    # 3. List with various protobuf-style value types
    attrs_list = [
        {"key": "str_key", "value": {"stringValue": "hello"}},
        {"key": "int_key", "value": {"intValue": "42"}},
        {"key": "double_key", "value": {"doubleValue": "3.14"}},
        {"key": "bool_key", "value": {"boolValue": True}},
        {"key": "arr_key", "value": {"arrayValue": {"values": ["x", "y"]}}},
        {"key": "other_dict", "value": {"customValue": "val"}},
        {"key": "raw_key", "value": "direct_val"},
        "not_a_dict",
        {"no_key": 123},
        {"key": "", "value": "empty_key"},
    ]
    flattened = _flatten_otlp_attributes(attrs_list)
    assert flattened["str_key"] == "hello"
    assert flattened["int_key"] == 42
    assert flattened["double_key"] == pytest.approx(3.14)
    assert flattened["bool_key"] is True
    assert flattened["arr_key"] == ["x", "y"]
    assert flattened["other_dict"] == "val"
    assert flattened["raw_key"] == "direct_val"
    assert "no_key" not in flattened


def test_parse_otlp_export_json_format() -> None:
    otlp_payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "langgraph-agent"}},
                        {"key": "service.version", "value": {"stringValue": "2.1.0"}},
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
                                "spanId": "00f067aa0ba902b7",
                                "name": "agent.plan",
                                "kind": 1,
                                "startTimeUnixNano": 1731024000000000000,
                                "endTimeUnixNano": 1731024001000000000,
                                "status": {"code": "OK", "message": "Done"},
                                "attributes": [
                                    {"key": "llm.model", "value": {"stringValue": "gpt-4o"}},
                                    {
                                        "key": "gen_ai.usage.input_tokens",
                                        "value": {"intValue": 150},
                                    },
                                    {
                                        "key": "gen_ai.usage.output_tokens",
                                        "value": {"intValue": 45},
                                    },
                                ],
                            },
                            {
                                "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
                                "spanId": "5fb397be34d23b0f",
                                "parentSpanId": "00f067aa0ba902b7",
                                "name": "tools.search",
                                "startTimeUnixNano": 1731024001100000000,
                                "endTimeUnixNano": 1731024002000000000,
                                "status": "ERROR",
                                "attributes": [
                                    {"key": "error.message", "value": {"stringValue": "timeout"}},
                                ],
                            },
                        ]
                    }
                ],
            }
        ]
    }

    trace = parse_otel_payload(otlp_payload)
    assert trace.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert len(trace.spans) == 2
    assert trace.resource.attributes["service.name"] == "langgraph-agent"
    assert trace.spans[0].name == "agent.plan"
    assert trace.spans[1].parent_span_id == "00f067aa0ba902b7"


def test_parse_direct_span_list_and_spans_dict() -> None:
    # Direct list of spans
    span_list = [
        {"trace_id": "trace123", "span_id": "span1", "name": "step1"},
        {"trace_id": "trace123", "span_id": "span2", "name": "step2"},
    ]
    trace1 = parse_otel_payload(span_list)
    assert trace1.trace_id == "trace123"
    assert len(trace1.spans) == 2

    # Spans dict
    spans_dict = {"spans": span_list}
    trace2 = parse_otel_payload(spans_dict)
    assert trace2.trace_id == "trace123"
    assert len(trace2.spans) == 2

    # Errors on empty lists or missing trace_id
    with pytest.raises(ValueError, match="cannot be empty"):
        parse_otel_payload([])

    with pytest.raises(ValueError, match="cannot be empty"):
        parse_otel_payload({"spans": []})

    with pytest.raises(ValueError, match="missing trace_id"):
        parse_otel_payload([{"span_id": "span1", "name": "step"}])

    with pytest.raises(ValueError, match="Missing trace_id in spans payload"):
        parse_otel_payload({"spans": [{"span_id": "span1", "name": "step"}]})


def test_validate_duplicate_span_id_warning() -> None:
    trace = OTELTrace(
        trace_id="trace123",
        spans=[
            OTELSpan(trace_id="trace123", span_id="s1", name="step1"),
            OTELSpan(trace_id="trace123", span_id="s1", name="step2"),
        ],
    )
    warnings = validate_otel_trace(trace)
    assert any("Duplicate span_id" in w for w in warnings)


def test_adapter_attribute_extraction_fallbacks() -> None:
    # Token count fallbacks
    span_tokens = OTELSpan(
        trace_id="t1",
        span_id="s1",
        name="step",
        attributes={"gen_ai.usage.prompt_tokens": 12, "gen_ai.usage.completion_tokens": 8},
    )
    p, c = extract_token_counts(span_tokens)
    assert p == 12
    assert c == 8

    span_tokens_alt = OTELSpan(
        trace_id="t1",
        span_id="s1",
        name="step",
        attributes={"prompt_tokens": "15", "completion_tokens": "16"},
    )
    p, c = extract_token_counts(span_tokens_alt)
    assert p == 15
    assert c == 16

    span_tokens_empty = OTELSpan(trace_id="t1", span_id="s1", name="step", attributes={})
    p, c = extract_token_counts(span_tokens_empty)
    assert p == 0
    assert c == 0

    # Cost fallbacks
    assert extract_cost_usd(
        OTELSpan(trace_id="t1", span_id="s1", name="step", attributes={"cost": "0.015"})
    ) == Decimal("0.015")
    assert extract_cost_usd(
        OTELSpan(trace_id="t1", span_id="s1", name="step", attributes={"usd_cost": 0.02})
    ) == Decimal("0.02")
    assert extract_cost_usd(
        OTELSpan(trace_id="t1", span_id="s1", name="step", attributes={})
    ) == Decimal("0.0000")

    # Latency fallback
    span_lat = OTELSpan(trace_id="t1", span_id="s1", name="step", start_time=100.0, end_time=100.25)
    assert extract_span_latency_ms(span_lat) == 250
    span_invalid_lat = OTELSpan(
        trace_id="t1", span_id="s1", name="step", start_time=100.0, end_time=90.0
    )
    assert extract_span_latency_ms(span_invalid_lat) == 0

    # Input/Output state fallbacks
    span_in = OTELSpan(
        trace_id="t1", span_id="s1", name="step", attributes={"input": '{"query": "hello"}'}
    )
    assert extract_input_state(span_in) == {"query": "hello"}
    span_in_raw = OTELSpan(
        trace_id="t1", span_id="s1", name="step", attributes={"query": "what is AI?"}
    )
    assert extract_input_state(span_in_raw) == {"prompt": "what is AI?"}
    span_in_empty = OTELSpan(trace_id="t1", span_id="s1", name="step", attributes={})
    assert extract_input_state(span_in_empty) == {"raw_input": "step"}

    span_out = OTELSpan(
        trace_id="t1", span_id="s1", name="step", attributes={"output": '{"reply": "world"}'}
    )
    assert extract_output_state(span_out) == {"reply": "world"}
    span_out_raw = OTELSpan(trace_id="t1", span_id="s1", name="step", attributes={"result": "done"})
    assert extract_output_state(span_out_raw) == {"response": "done"}
    span_out_empty = OTELSpan(trace_id="t1", span_id="s1", name="step", attributes={})
    assert extract_output_state(span_out_empty) == {"raw_output": "Step 'step' completed."}


def test_translate_span_status_and_tool_call_variations() -> None:
    otel_trace = OTELTrace(
        trace_id="trace_advanced",
        spans=[
            OTELSpan(
                trace_id="trace_advanced",
                span_id="s1",
                name="step_with_tool_call",
                status={"status_code": "ERROR", "description": "Model call failure"},
                attributes={
                    "tool_calls": json.dumps([{"name": "fetch_data", "input": {"id": 1}}]),
                    "retry_count": 2,
                    "retries": 1,
                },
            ),
            OTELSpan(
                trace_id="trace_advanced",
                span_id="s2",
                parent_span_id="s1",
                name="step_cancelled",
                status="CANCELLED",
                attributes={
                    "tool_calls": {"name": "single_tool", "arguments": {}},
                    "function_call": "calc_tax()",
                },
            ),
        ],
    )

    cats = translate_otel_trace_to_cats(otel_trace)
    assert len(cats.steps) == 2
    assert len(cats.steps[0].tool_calls) == 1
    assert cats.steps[0].tool_calls[0].tool_name == "fetch_data"
    assert len(cats.steps[0].retries) == 1
    assert cats.workflow.status == WorkflowStatus.FAILED


def test_api_internal_server_error_handling(client: TestClient) -> None:
    with patch(
        "app.api.v1.endpoints.otel.parse_otel_payload",
        side_effect=Exception("Database lock failure"),
    ):
        res = client.post("/api/v1/otel/ingest", json={"trace_id": "test", "spans": []})
        assert res.status_code == 400
        assert "Database lock failure" in res.json()["detail"]

    with patch(
        "app.api.v1.endpoints.otel.parse_otel_payload", side_effect=Exception("Preview failure")
    ):
        res = client.post("/api/v1/otel/translate", json={"trace_id": "test", "spans": []})
        assert res.status_code == 400
        assert "Preview failure" in res.json()["detail"]
