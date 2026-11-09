"""OpenTelemetry payload parsing, normalization, and validation."""

import json
from datetime import UTC, datetime
from typing import Any

from app.otel.otel_models import OTELResource, OTELSpan, OTELStatus, OTELTrace


def _flatten_otlp_attributes(attrs: Any) -> dict[str, Any]:
    """Flatten OTLP protobuf-style key-value attribute arrays into standard dicts."""
    if isinstance(attrs, dict):
        return attrs
    if not isinstance(attrs, list):
        return {}

    result: dict[str, Any] = {}
    for item in attrs:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        if not key:
            continue
        val = item.get("value")
        if isinstance(val, dict):
            # OTLP values: {"stringValue": "x"} or {"intValue": "1"} etc.
            if "stringValue" in val:
                result[key] = val["stringValue"]
            elif "intValue" in val:
                result[key] = int(val["intValue"])
            elif "doubleValue" in val:
                result[key] = float(val["doubleValue"])
            elif "boolValue" in val:
                result[key] = bool(val["boolValue"])
            elif "arrayValue" in val:
                result[key] = val["arrayValue"].get("values", [])
            else:
                result[key] = list(val.values())[0] if val else None
        else:
            result[key] = val
    return result


def parse_timestamp_to_seconds(ts: Any) -> float | None:
    """Parse timestamps from unix nanoseconds, milliseconds, float seconds, or ISO strings."""
    if ts is None:
        return None
    if isinstance(ts, int | float):
        # If integer is huge (e.g. > 1e16), it's nanoseconds
        if ts > 1e16:
            return float(ts) / 1e9
        # If integer is > 1e11, it's milliseconds
        if ts > 1e11:
            return float(ts) / 1e3
        return float(ts)
    if isinstance(ts, str):
        try:
            return float(ts)
        except ValueError:
            pass
        try:
            # ISO format string
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.timestamp()
        except ValueError:
            return None
    return None


def parse_otel_payload(payload: dict[str, Any] | list[dict[str, Any]] | str) -> OTELTrace:
    """Parse and normalize any generic or standard OTLP OpenTelemetry payload into an OTELTrace.

    Supports:
    - Native OTELTrace dict: {"trace_id": "...", "resource": {...}, "spans": [...]}
    - Span list dict: {"spans": [...]}
    - Direct list of spans: [{"trace_id": "...", "span_id": "..."}, ...]
    - Standard OTLP JSON: {"resourceSpans": [{"resource": {...}, "scopeSpans": [{"spans": [...]}]}]}
    - JSON string representation of any of the above.
    """
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}") from e

    # Case 1: Standard OTLP Export JSON format
    if isinstance(payload, dict) and "resourceSpans" in payload:
        resource_spans = payload.get("resourceSpans", [])
        all_spans: list[OTELSpan] = []
        global_trace_id: str | None = None
        resource_attrs: dict[str, Any] = {}

        for rs in resource_spans:
            if not isinstance(rs, dict):
                continue
            r_obj = rs.get("resource", {})
            if isinstance(r_obj, dict):
                resource_attrs.update(_flatten_otlp_attributes(r_obj.get("attributes", {})))

            for ss in rs.get("scopeSpans", []):
                if not isinstance(ss, dict):
                    continue
                for span_data in ss.get("spans", []):
                    if not isinstance(span_data, dict):
                        continue
                    t_id = str(span_data.get("traceId") or span_data.get("trace_id", ""))
                    if t_id and not global_trace_id:
                        global_trace_id = t_id

                    s_id = str(span_data.get("spanId") or span_data.get("span_id", ""))
                    p_id = span_data.get("parentSpanId") or span_data.get("parent_span_id")
                    name = str(span_data.get("name", "unnamed_step"))

                    attrs = _flatten_otlp_attributes(span_data.get("attributes", {}))
                    status_raw = span_data.get("status", {})
                    if isinstance(status_raw, dict):
                        code = str(status_raw.get("code") or status_raw.get("status_code", "UNSET"))
                        desc = status_raw.get("message") or status_raw.get("description")
                        st = OTELStatus(status_code=code, description=desc)
                    else:
                        st = OTELStatus(status_code=str(status_raw))

                    st_time = span_data.get("startTimeUnixNano") or span_data.get("start_time")
                    end_time = span_data.get("endTimeUnixNano") or span_data.get("end_time")

                    all_spans.append(
                        OTELSpan(
                            trace_id=t_id,
                            span_id=s_id,
                            parent_span_id=str(p_id) if p_id else None,
                            name=name,
                            kind=str(span_data.get("kind", "INTERNAL")),
                            start_time=st_time,
                            end_time=end_time,
                            status=st,
                            attributes=attrs,
                        )
                    )

        if not global_trace_id and all_spans:
            global_trace_id = all_spans[0].trace_id
        if not global_trace_id:
            raise ValueError("OpenTelemetry payload contains no valid trace_id.")

        return OTELTrace(
            trace_id=global_trace_id,
            resource=OTELResource(attributes=resource_attrs),
            spans=all_spans,
        )

    # Case 2: Direct list of spans
    if isinstance(payload, list):
        if not payload:
            raise ValueError("OpenTelemetry spans list cannot be empty.")
        raw_spans = payload
        first_trace_id = str(raw_spans[0].get("trace_id") or raw_spans[0].get("traceId", ""))
        if not first_trace_id:
            raise ValueError("First span in list is missing trace_id.")
        spans = [OTELSpan.model_validate(s) for s in raw_spans]
        return OTELTrace(trace_id=first_trace_id, spans=spans)

    # Case 3: Dict with trace_id / spans
    if isinstance(payload, dict):
        # Direct OTELTrace format
        if "trace_id" in payload or "traceId" in payload:
            t_id = str(payload.get("trace_id") or payload.get("traceId"))
            res_data = payload.get("resource", {})
            if isinstance(res_data, dict) and "attributes" in res_data:
                res_attrs = _flatten_otlp_attributes(res_data["attributes"])
            else:
                res_attrs = _flatten_otlp_attributes(res_data)

            raw_spans = payload.get("spans", [])
            parsed_spans = []
            for s in raw_spans:
                if isinstance(s, dict):
                    if "trace_id" not in s and "traceId" not in s:
                        s["trace_id"] = t_id
                    parsed_spans.append(OTELSpan.model_validate(s))
            return OTELTrace(
                trace_id=t_id,
                resource=OTELResource(attributes=res_attrs),
                spans=parsed_spans,
            )

        # Spans container without root trace_id
        if "spans" in payload:
            raw_spans = payload["spans"]
            if not raw_spans:
                raise ValueError("Payload spans array cannot be empty.")
            first_trace_id = str(raw_spans[0].get("trace_id") or raw_spans[0].get("traceId", ""))
            if not first_trace_id:
                raise ValueError("Missing trace_id in spans payload.")
            parsed_spans = [OTELSpan.model_validate(s) for s in raw_spans]
            return OTELTrace(trace_id=first_trace_id, spans=parsed_spans)

    raise ValueError("Unrecognized OpenTelemetry payload structure.")


def validate_otel_trace(trace: OTELTrace) -> list[str]:
    """Validate OpenTelemetry trace hierarchy, timestamps, and tree consistency.

    Returns a list of warning messages if issues are detected (orphan spans,
    timestamp inversions, cycles). Raises ValueError if structurally invalid.
    """
    if not trace.trace_id or not trace.trace_id.strip():
        raise ValueError("OTELTrace must have a non-empty trace_id.")

    if not trace.spans:
        raise ValueError("OTELTrace must contain at least one span.")

    warnings: list[str] = []
    span_ids: set[str] = {s.span_id for s in trace.spans}

    # 1. Duplicate span ID check
    if len(span_ids) != len(trace.spans):
        warnings.append("Duplicate span_id detected within trace.")

    # 2. Check for orphan spans & timestamp validity
    parent_map: dict[str, str | None] = {}
    for span in trace.spans:
        parent_map[span.span_id] = span.parent_span_id
        if span.parent_span_id and span.parent_span_id not in span_ids:
            warnings.append(
                f"Orphan span '{span.span_id}': parent_span_id '{span.parent_span_id}' not found in trace."
            )

        # Timestamp check
        t_start = parse_timestamp_to_seconds(span.start_time)
        t_end = parse_timestamp_to_seconds(span.end_time)
        if t_start is not None and t_end is not None and t_start > t_end:
            warnings.append(f"Inverted timestamps on span '{span.span_id}': start_time > end_time.")

    # 3. Detect cyclic parent-child span relationships
    visited: set[str] = set()
    recursion_stack: set[str] = set()

    def has_cycle(sid: str) -> bool:
        visited.add(sid)
        recursion_stack.add(sid)
        parent = parent_map.get(sid)
        if parent and parent in span_ids:
            if parent not in visited:
                if has_cycle(parent):
                    return True
            elif parent in recursion_stack:
                return True
        recursion_stack.remove(sid)
        return False

    for sid in span_ids:
        if sid not in visited and has_cycle(sid):
            warnings.append("Cyclic parent-child span reference detected in trace hierarchy.")
            break

    return warnings
