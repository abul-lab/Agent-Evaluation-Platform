"""Unit tests for OpenTelemetry trace hierarchy, timestamps, and structure validation."""

import pytest

from app.otel.otel_models import OTELSpan, OTELTrace
from app.otel.otel_parser import parse_otel_payload, parse_timestamp_to_seconds, validate_otel_trace


def test_validate_empty_trace_id_raises() -> None:
    trace = OTELTrace(trace_id="", spans=[OTELSpan(trace_id="", span_id="s1", name="step")])
    with pytest.raises(ValueError, match="non-empty trace_id"):
        validate_otel_trace(trace)


def test_validate_empty_spans_raises() -> None:
    trace = OTELTrace(trace_id="11111111222233334444555566667777", spans=[])
    with pytest.raises(ValueError, match="at least one span"):
        validate_otel_trace(trace)


def test_validate_detects_orphan_span() -> None:
    trace = OTELTrace(
        trace_id="11111111222233334444555566667777",
        spans=[
            OTELSpan(
                trace_id="11111111222233334444555566667777",
                span_id="s1",
                parent_span_id="nonexistent_parent",
                name="step1",
            )
        ],
    )
    warnings = validate_otel_trace(trace)
    assert any("Orphan span" in w for w in warnings)


def test_validate_detects_inverted_timestamps() -> None:
    trace = OTELTrace(
        trace_id="11111111222233334444555566667777",
        spans=[
            OTELSpan(
                trace_id="11111111222233334444555566667777",
                span_id="s1",
                name="step1",
                start_time=1731024000.0,
                end_time=1731023990.0,  # 10 seconds before start
            )
        ],
    )
    warnings = validate_otel_trace(trace)
    assert any("Inverted timestamps" in w for w in warnings)


def test_validate_detects_cyclic_span_references() -> None:
    trace = OTELTrace(
        trace_id="11111111222233334444555566667777",
        spans=[
            OTELSpan(
                trace_id="11111111222233334444555566667777",
                span_id="s1",
                parent_span_id="s2",
                name="step1",
            ),
            OTELSpan(
                trace_id="11111111222233334444555566667777",
                span_id="s2",
                parent_span_id="s1",
                name="step2",
            ),
        ],
    )
    warnings = validate_otel_trace(trace)
    assert any("Cyclic parent-child" in w for w in warnings)


def test_parse_timestamp_variations() -> None:
    # Nanoseconds
    assert parse_timestamp_to_seconds(1731024000000000000) == pytest.approx(1731024000.0)
    # Milliseconds
    assert parse_timestamp_to_seconds(1731024000000) == pytest.approx(1731024000.0)
    # Float seconds
    assert parse_timestamp_to_seconds(1731024000.5) == pytest.approx(1731024000.5)
    # ISO string
    assert parse_timestamp_to_seconds("2026-11-08T01:00:00Z") is not None
    # None or invalid
    assert parse_timestamp_to_seconds(None) is None
    assert parse_timestamp_to_seconds("not-a-timestamp") is None


def test_parse_invalid_payload_raises() -> None:
    with pytest.raises(ValueError, match="Invalid JSON payload"):
        parse_otel_payload("{ malformed json")

    with pytest.raises(ValueError, match="Unrecognized OpenTelemetry payload"):
        parse_otel_payload({"invalid_key": 123})
