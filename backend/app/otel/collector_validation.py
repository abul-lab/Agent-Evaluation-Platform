"""OpenTelemetry Collector validation, rate limiting, and backpressure protection."""

import json
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any


class PayloadValidationError(ValueError):
    """Raised when an incoming OTLP payload fails structural or boundary validation."""


class RateLimitExceededError(Exception):
    """Raised when request volume exceeds token-bucket limits."""

    def __init__(self, message: str, retry_after: float = 1.0) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class BackpressureExceededError(Exception):
    """Raised when active concurrency or payload sizes exceed server capacity."""

    def __init__(self, message: str, retry_after: float = 2.0) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class CollectorRateLimiter:
    """Thread-safe Token Bucket rate limiter per workspace or key."""

    def __init__(self, rate: float = 2.0, capacity: float = 60.0) -> None:
        """Initialize rate limiter.

        Args:
            rate: Token refill rate in tokens per second (default: 2.0 tokens/sec = 120 req/min).
            capacity: Max burst capacity in tokens (default: 60 tokens).
        """
        self.rate = rate
        self.capacity = capacity
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_refill_ts)
        self._lock = threading.Lock()

    def check_rate_limit(self, key: str, tokens_required: float = 1.0) -> None:
        """Consume tokens for given key or raise RateLimitExceededError."""
        now = time.monotonic()
        with self._lock:
            current_tokens, last_refill = self._buckets.get(key, (self.capacity, now))

            # Refill tokens based on elapsed time
            elapsed = now - last_refill
            refilled = current_tokens + (elapsed * self.rate)
            current_tokens = min(self.capacity, refilled)

            if current_tokens < tokens_required:
                deficit = tokens_required - current_tokens
                retry_after = max(0.5, deficit / self.rate)
                self._buckets[key] = (current_tokens, now)
                raise RateLimitExceededError(
                    f"Rate limit exceeded for workspace. Try again in {retry_after:.1f}s",
                    retry_after=round(retry_after, 2),
                )

            # Consume token
            self._buckets[key] = (current_tokens - tokens_required, now)

    def reset(self) -> None:
        """Reset all rate limiter buckets (used in test fixtures)."""
        with self._lock:
            self._buckets.clear()


class BackpressureMonitor:
    """Tracks active requests and payload sizes to prevent thread starvation and memory exhaustion."""

    def __init__(self, max_concurrent: int = 50, max_payload_bytes: int = 15 * 1024 * 1024) -> None:
        """Initialize backpressure monitor.

        Args:
            max_concurrent: Maximum active concurrent collector executions allowed (default: 50).
            max_payload_bytes: Maximum payload size in bytes (default: 15MB).
        """
        self.max_concurrent = max_concurrent
        self.max_payload_bytes = max_payload_bytes
        self.active_requests = 0
        self._lock = threading.Lock()

    def check_payload_size(self, size_bytes: int) -> None:
        """Ensure payload size does not exceed maximum allowable threshold."""
        if size_bytes > self.max_payload_bytes:
            raise BackpressureExceededError(
                f"Payload size {size_bytes} bytes exceeds maximum allowable limit of {self.max_payload_bytes} bytes.",
                retry_after=5.0,
            )

    @contextmanager
    def track_request(self) -> Generator[None, None, None]:
        """Context manager tracking active requests with backpressure threshold gating."""
        with self._lock:
            if self.active_requests >= self.max_concurrent:
                raise BackpressureExceededError(
                    f"Server is under high load ({self.active_requests}/{self.max_concurrent} active). Backpressure triggered.",
                    retry_after=2.0,
                )
            self.active_requests += 1

        try:
            yield
        finally:
            with self._lock:
                self.active_requests = max(0, self.active_requests - 1)

    def reset(self) -> None:
        """Reset backpressure active counter."""
        with self._lock:
            self.active_requests = 0


# Global collector limiter and backpressure instances
global_rate_limiter = CollectorRateLimiter(rate=2.0, capacity=60.0)
global_backpressure_monitor = BackpressureMonitor(
    max_concurrent=50, max_payload_bytes=15 * 1024 * 1024
)


def validate_collector_payload(
    payload: Any, max_spans: int = 10000
) -> dict[str, Any] | list[dict[str, Any]]:
    """Validate structure, non-emptiness, and span volume limits of an incoming OTLP payload.

    Returns the parsed dictionary or list.
    Raises PayloadValidationError if invalid.
    """
    if payload is None:
        raise PayloadValidationError("OTLP collector payload cannot be null/empty.")

    if isinstance(payload, str):
        if not payload.strip():
            raise PayloadValidationError("OTLP collector payload string is empty.")
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as e:
            raise PayloadValidationError(f"Invalid JSON in OTLP collector payload: {e}") from e

    if not isinstance(payload, (dict, list)):
        raise PayloadValidationError(
            f"Expected dict or list for OTLP payload, received {type(payload).__name__}."
        )

    if isinstance(payload, list):
        if not payload:
            raise PayloadValidationError("OTLP spans array cannot be empty.")
        if len(payload) > max_spans:
            raise PayloadValidationError(
                f"Batch contains {len(payload)} spans, exceeding maximum allowed limit of {max_spans}."
            )
        for i, span in enumerate(payload):
            if not isinstance(span, dict):
                raise PayloadValidationError(f"Span at index {i} is not a valid object.")
            t_id = span.get("traceId") or span.get("trace_id")
            if not t_id:
                raise PayloadValidationError(
                    f"Span at index {i} is missing 'traceId' or 'trace_id'."
                )
        return payload

    # Dict payload
    if "resourceSpans" in payload:
        resource_spans = payload.get("resourceSpans")
        if not isinstance(resource_spans, list) or not resource_spans:
            raise PayloadValidationError("OTLP payload 'resourceSpans' must be a non-empty array.")

        total_spans = 0
        for rs in resource_spans:
            if not isinstance(rs, dict):
                continue
            scope_spans = rs.get("scopeSpans", [])
            if not isinstance(scope_spans, list):
                continue
            for ss in scope_spans:
                if not isinstance(ss, dict):
                    continue
                spans = ss.get("spans", [])
                if isinstance(spans, list):
                    total_spans += len(spans)

        if total_spans == 0:
            raise PayloadValidationError("OTLP payload 'resourceSpans' contains no valid spans.")
        if total_spans > max_spans:
            raise PayloadValidationError(
                f"Batch contains {total_spans} spans across resource scopes, exceeding maximum allowed limit of {max_spans}."
            )
        return payload

    if "spans" in payload:
        spans = payload.get("spans")
        if not isinstance(spans, list) or not spans:
            raise PayloadValidationError("OTLP payload 'spans' must be a non-empty array.")
        if len(spans) > max_spans:
            raise PayloadValidationError(
                f"Batch contains {len(spans)} spans, exceeding maximum allowed limit of {max_spans}."
            )
        return payload

    raise PayloadValidationError(
        "Unrecognized OTLP payload format. Expected 'resourceSpans', 'spans', or raw span array."
    )
