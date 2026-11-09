"""Tests for CollectorReceiver batch processing and span grouping."""

import uuid
from typing import Any

import pytest
from sqlmodel import Session, select

from app.db.entities import EvaluationRecord, TraceRecord, WorkspaceRecord
from app.otel.collector_receiver import CollectorReceiver


def _make_otlp_batch(traces_count: int, spans_per_trace: int = 2) -> dict[str, Any]:
    """Helper to generate standard OTLP payload containing multiple traces."""
    scope_spans: list[dict[str, Any]] = []

    for _t_idx in range(traces_count):
        trace_id = uuid.uuid4().hex
        trace_spans: list[dict[str, Any]] = []
        for s_idx in range(spans_per_trace):
            span_id = uuid.uuid4().hex[:16]
            trace_spans.append(
                {
                    "traceId": trace_id,
                    "spanId": span_id,
                    "parentSpanId": trace_spans[0]["spanId"] if s_idx > 0 else None,
                    "name": f"agent_step_{s_idx}",
                    "kind": "INTERNAL",
                    "startTimeUnixNano": (1700000000 + s_idx) * 1_000_000_000,
                    "endTimeUnixNano": (1700000000 + s_idx + 1) * 1_000_000_000,
                    "attributes": [
                        {"key": "agent.action", "value": {"stringValue": "tool_exec"}},
                        {"key": "tool.name", "value": {"stringValue": "fetch_data"}},
                    ],
                    "status": {"code": "OK"},
                }
            )
        scope_spans.append({"spans": trace_spans})

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "batch-agent-service"}},
                        {"key": "telemetry.sdk.language", "value": {"stringValue": "python"}},
                    ]
                },
                "scopeSpans": scope_spans,
            }
        ]
    }


def test_extract_and_group_spans_multiple_traces(session: Session) -> None:
    """Test spans for different trace IDs are grouped distinctly."""
    receiver = CollectorReceiver(session)
    payload = _make_otlp_batch(traces_count=3, spans_per_trace=2)

    grouped = receiver.extract_and_group_spans(payload)
    assert len(grouped) == 3
    for trace_id, (attrs, spans) in grouped.items():
        assert attrs.get("service.name") == "batch-agent-service"
        assert len(spans) == 2
        assert all(s.trace_id == trace_id for s in spans)


def test_process_batch_single_trace(session: Session) -> None:
    """Test ingestion of a 1-trace batch."""
    ws = WorkspaceRecord(name="Batch WS 1", slug="batch-ws-1")
    session.add(ws)
    session.commit()
    session.refresh(ws)

    receiver = CollectorReceiver(session)
    payload = _make_otlp_batch(traces_count=1, spans_per_trace=3)

    result = receiver.process_batch(
        payload=payload, workspace_id=ws.workspace_id, auto_evaluate=True
    )
    assert result.traces_ingested == 1
    assert result.spans_ingested == 3
    assert len(result.trace_ids) == 1
    assert len(result.evaluation_ids) == 1
    assert result.partial_success is False
    assert result.rejected_spans == 0

    # Verify database persistence & workspace binding
    trace_rec = session.exec(
        select(TraceRecord).where(TraceRecord.workspace_id == ws.workspace_id)
    ).first()
    assert trace_rec is not None
    assert trace_rec.step_count == 3

    eval_rec = session.exec(
        select(EvaluationRecord).where(EvaluationRecord.workspace_id == ws.workspace_id)
    ).first()
    assert eval_rec is not None
    assert str(eval_rec.evaluation_id) == result.evaluation_ids[0]


def test_process_batch_10_traces(session: Session) -> None:
    """Test ingestion of a 10-trace batch."""
    receiver = CollectorReceiver(session)
    payload = _make_otlp_batch(traces_count=10, spans_per_trace=2)

    result = receiver.process_batch(payload=payload, auto_evaluate=True)
    assert result.traces_ingested == 10
    assert result.spans_ingested == 20
    assert len(result.trace_ids) == 10
    assert len(result.evaluation_ids) == 10


def test_process_batch_100_traces(session: Session) -> None:
    """Test ingestion of a 100-trace batch without auto-evaluate overhead."""
    receiver = CollectorReceiver(session)
    payload = _make_otlp_batch(traces_count=100, spans_per_trace=1)

    result = receiver.process_batch(payload=payload, auto_evaluate=False)
    assert result.traces_ingested == 100
    assert result.spans_ingested == 100
    assert len(result.trace_ids) == 100
    assert len(result.evaluation_ids) == 0


def test_process_batch_1000_traces_scaling(session: Session) -> None:
    """Test ingestion of a 1000-trace batch scaling verification."""
    receiver = CollectorReceiver(session)
    payload = _make_otlp_batch(traces_count=1000, spans_per_trace=1)

    result = receiver.process_batch(payload=payload, auto_evaluate=False)
    assert result.traces_ingested == 1000
    assert result.spans_ingested == 1000
    assert len(result.trace_ids) == 1000


def test_process_batch_partial_success(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that a translation failure in one trace does not abort other valid traces."""
    receiver = CollectorReceiver(session)
    payload = _make_otlp_batch(traces_count=3, spans_per_trace=2)

    # Monkeypatch translate_otel_trace_to_cats to fail for the second trace
    from app.otel import collector_receiver as cr_mod

    original_translate = cr_mod.translate_otel_trace_to_cats  # type: ignore[attr-defined]

    call_count = 0

    def mock_translate(trace: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise ValueError("Corrupt synthetic trace data")
        return original_translate(trace)

    monkeypatch.setattr(cr_mod, "translate_otel_trace_to_cats", mock_translate)

    result = receiver.process_batch(payload=payload, auto_evaluate=False)
    assert result.traces_ingested == 2
    assert result.rejected_spans == 2
    assert result.partial_success is True
    assert "Corrupt synthetic trace data" in (result.error_message or "")


def test_extract_and_group_spans_from_raw_list_and_spans_dict(session: Session) -> None:
    """Test extracting spans when payload is a raw list or a dict with 'spans'."""
    receiver = CollectorReceiver(session)

    # Raw list
    raw_list = [
        {"trace_id": "trace-list-1", "span_id": "s1", "name": "step1"},
        {"trace_id": "trace-list-1", "span_id": "s2", "name": "step2"},
        {"trace_id": "trace-list-2", "span_id": "s3", "name": "step3"},
    ]
    grouped_list = receiver.extract_and_group_spans(raw_list)
    assert len(grouped_list) == 2
    assert len(grouped_list["trace-list-1"][1]) == 2
    assert len(grouped_list["trace-list-2"][1]) == 1

    # Spans dict
    spans_dict = {
        "resource": {"attributes": [{"key": "env", "value": "test"}]},
        "spans": [
            {"traceId": "trace-dict-1", "spanId": "s1", "name": "step1"},
        ],
    }
    grouped_dict = receiver.extract_and_group_spans(spans_dict)
    assert len(grouped_dict) == 1
    assert "trace-dict-1" in grouped_dict
    assert grouped_dict["trace-dict-1"][0].get("env") == "test"
