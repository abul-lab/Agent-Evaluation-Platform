"""Tests for OpenTelemetry Collector validation, rate limiting, and backpressure protection."""

import time

import pytest

from app.otel.collector_validation import (
    BackpressureExceededError,
    BackpressureMonitor,
    CollectorRateLimiter,
    PayloadValidationError,
    RateLimitExceededError,
    validate_collector_payload,
)


def test_rate_limiter_token_consumption_and_refill() -> None:
    """Test rate limiter allows requests within capacity and triggers RateLimitExceededError when exhausted."""
    limiter = CollectorRateLimiter(rate=10.0, capacity=2.0)
    key = "test_ws"

    # Consume available tokens
    limiter.check_rate_limit(key, tokens_required=1.0)
    limiter.check_rate_limit(key, tokens_required=1.0)

    # Next immediate check should raise RateLimitExceededError
    with pytest.raises(RateLimitExceededError) as exc_info:
        limiter.check_rate_limit(key, tokens_required=1.0)
    assert "Rate limit exceeded" in str(exc_info.value)
    assert exc_info.value.retry_after > 0

    # Wait for refill
    time.sleep(0.15)
    limiter.check_rate_limit(key, tokens_required=1.0)


def test_rate_limiter_reset() -> None:
    """Test resetting rate limiter buckets."""
    limiter = CollectorRateLimiter(rate=1.0, capacity=1.0)
    limiter.check_rate_limit("ws_1", 1.0)
    limiter.reset()
    assert len(limiter._buckets) == 0


def test_backpressure_monitor_payload_size() -> None:
    """Test backpressure monitors payload size limits."""
    monitor = BackpressureMonitor(max_concurrent=5, max_payload_bytes=1000)

    # Within limit
    monitor.check_payload_size(500)

    # Exceeds limit
    with pytest.raises(BackpressureExceededError) as exc_info:
        monitor.check_payload_size(2000)
    assert "exceeds maximum allowable limit" in str(exc_info.value)
    assert exc_info.value.retry_after == 5.0


def test_backpressure_monitor_concurrency() -> None:
    """Test backpressure tracks active requests and sheds load beyond max concurrency."""
    monitor = BackpressureMonitor(max_concurrent=2, max_payload_bytes=10000)

    with monitor.track_request():
        assert monitor.active_requests == 1
        with monitor.track_request():
            assert monitor.active_requests == 2

            # Third concurrent request exceeds limit
            with pytest.raises(BackpressureExceededError) as exc_info, monitor.track_request():
                pass
            assert "Backpressure triggered" in str(exc_info.value)

    assert monitor.active_requests == 0
    monitor.reset()
    assert monitor.active_requests == 0


def test_validate_collector_payload_null_or_empty() -> None:
    """Test rejection of null or empty payloads."""
    with pytest.raises(PayloadValidationError, match="cannot be null/empty"):
        validate_collector_payload(None)

    with pytest.raises(PayloadValidationError, match="string is empty"):
        validate_collector_payload("   ")

    with pytest.raises(PayloadValidationError, match="Invalid JSON"):
        validate_collector_payload("{not-json}")

    with pytest.raises(PayloadValidationError, match="Expected dict or list"):
        validate_collector_payload(12345)


def test_validate_collector_payload_list_validations() -> None:
    """Test validation of raw span array payloads."""
    with pytest.raises(PayloadValidationError, match="spans array cannot be empty"):
        validate_collector_payload([])

    # Max spans exceeded
    big_list = [{"traceId": "1", "spanId": str(i)} for i in range(10)]
    with pytest.raises(PayloadValidationError, match="exceeding maximum allowed limit"):
        validate_collector_payload(big_list, max_spans=5)

    # Invalid span item
    with pytest.raises(PayloadValidationError, match="is not a valid object"):
        validate_collector_payload(["not-a-dict"])

    # Missing trace ID
    with pytest.raises(PayloadValidationError, match="missing 'traceId'"):
        validate_collector_payload([{"spanId": "s1"}])

    # Valid span list
    valid = [{"traceId": "t1", "spanId": "s1"}]
    assert validate_collector_payload(valid) == valid


def test_validate_collector_payload_resource_spans() -> None:
    """Test validation of standard OTLP resourceSpans payload."""
    with pytest.raises(PayloadValidationError, match="'resourceSpans' must be a non-empty array"):
        validate_collector_payload({"resourceSpans": []})

    with pytest.raises(PayloadValidationError, match="contains no valid spans"):
        validate_collector_payload({"resourceSpans": [{"scopeSpans": [{"spans": []}]}]})

    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [{"key": "service.name", "value": {"stringValue": "agent"}}]
                },
                "scopeSpans": [
                    {"spans": [{"traceId": "t100", "spanId": "s100", "name": "step_1"}]}
                ],
            }
        ]
    }
    validated = validate_collector_payload(payload)
    assert validated == payload


def test_validate_collector_payload_spans_dict() -> None:
    """Test validation of spans dict payload."""
    with pytest.raises(PayloadValidationError, match="'spans' must be a non-empty array"):
        validate_collector_payload({"spans": []})

    payload = {"spans": [{"trace_id": "t1", "span_id": "s1"}]}
    assert validate_collector_payload(payload) == payload


def test_validate_collector_payload_unrecognized() -> None:
    """Test rejection of arbitrary dict without spans."""
    with pytest.raises(PayloadValidationError, match="Unrecognized OTLP payload format"):
        validate_collector_payload({"foo": "bar"})
