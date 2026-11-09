"""OpenTelemetry Collector batch ingestion, span grouping, and evaluation processor."""

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.domain.models import CanonicalTrace
from app.otel.collector_validation import validate_collector_payload
from app.otel.otel_models import OTELResource, OTELSpan, OTELStatus, OTELTrace
from app.otel.otel_parser import _flatten_otlp_attributes
from app.otel.otel_to_cats import translate_otel_trace_to_cats
from app.services.evaluation_service import EvaluationService
from app.services.trace_repository import TraceRepository

logger = logging.getLogger(__name__)


@dataclass
class CollectorBatchResult:
    """Result of processing a collector batch ingestion."""

    traces_ingested: int
    spans_ingested: int
    trace_ids: list[str] = field(default_factory=list)
    evaluation_ids: list[str] = field(default_factory=list)
    partial_success: bool = False
    rejected_spans: int = 0
    error_message: str | None = None
    workspace_id: str | None = None


class CollectorReceiver:
    """Receives, groups, translates, and evaluates batches of spans streamed from OTEL Collectors."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.trace_repository = TraceRepository(session)
        self.evaluation_service = EvaluationService(session)

    def extract_and_group_spans(
        self, payload: dict[str, Any] | list[dict[str, Any]]
    ) -> dict[str, tuple[dict[str, Any], list[OTELSpan]]]:
        """Extract all spans from standard OTLP structure or list and group by trace_id.

        Returns:
            Dict mapping trace_id -> (merged_resource_attributes, list_of_OTELSpan).
        """
        grouped: dict[str, tuple[dict[str, Any], list[OTELSpan]]] = {}

        if isinstance(payload, dict) and "resourceSpans" in payload:
            resource_spans = payload.get("resourceSpans", [])
            for rs in resource_spans:
                if not isinstance(rs, dict):
                    continue
                res_obj = rs.get("resource", {})
                res_attrs: dict[str, Any] = {}
                if isinstance(res_obj, dict):
                    res_attrs = _flatten_otlp_attributes(res_obj.get("attributes", {}))

                for ss in rs.get("scopeSpans", []):
                    if not isinstance(ss, dict):
                        continue
                    for s_data in ss.get("spans", []):
                        if not isinstance(s_data, dict):
                            continue
                        t_id = str(s_data.get("traceId") or s_data.get("trace_id", "")).strip()
                        if not t_id:
                            continue

                        span = self._parse_single_span(s_data, t_id)

                        if t_id not in grouped:
                            grouped[t_id] = (dict(res_attrs), [])
                        else:
                            # Merge resource attributes if new ones present
                            grouped[t_id][0].update(res_attrs)
                        grouped[t_id][1].append(span)

        elif isinstance(payload, list) or (isinstance(payload, dict) and "spans" in payload):
            raw_spans = payload if isinstance(payload, list) else payload.get("spans", [])
            common_attrs = (
                payload.get("resource", {}).get("attributes", {})
                if isinstance(payload, dict)
                else {}
            )
            flat_common = _flatten_otlp_attributes(common_attrs)

            for s_data in raw_spans:
                if not isinstance(s_data, dict):
                    continue
                t_id = str(s_data.get("traceId") or s_data.get("trace_id", "")).strip()
                if not t_id:
                    continue

                span = self._parse_single_span(s_data, t_id)
                if t_id not in grouped:
                    grouped[t_id] = (dict(flat_common), [])
                grouped[t_id][1].append(span)

        return grouped

    def _parse_single_span(self, s_data: dict[str, Any], trace_id: str) -> OTELSpan:
        """Parse raw dictionary into typed OTELSpan."""
        s_id = str(s_data.get("spanId") or s_data.get("span_id", "")).strip()
        p_id = s_data.get("parentSpanId") or s_data.get("parent_span_id")
        name = str(s_data.get("name", "unnamed_step"))
        attrs = _flatten_otlp_attributes(s_data.get("attributes", {}))

        status_raw = s_data.get("status", {})
        if isinstance(status_raw, dict):
            code = str(status_raw.get("code") or status_raw.get("status_code", "UNSET"))
            desc = status_raw.get("message") or status_raw.get("description")
            st = OTELStatus(status_code=code, description=desc)
        else:
            st = OTELStatus(status_code=str(status_raw))

        st_time = s_data.get("startTimeUnixNano") or s_data.get("start_time")
        end_time = s_data.get("endTimeUnixNano") or s_data.get("end_time")

        return OTELSpan(
            trace_id=trace_id,
            span_id=s_id,
            parent_span_id=str(p_id) if p_id else None,
            name=name,
            kind=str(s_data.get("kind", "INTERNAL")),
            start_time=st_time,
            end_time=end_time,
            status=st,
            attributes=attrs,
        )

    def process_batch(
        self,
        payload: Any,
        workspace_id: UUID | None = None,
        auto_evaluate: bool = True,
    ) -> CollectorBatchResult:
        """Process incoming OTLP batch: group by trace, translate to CATS, persist, and run evaluations."""
        validated_payload = validate_collector_payload(payload)
        grouped_traces = self.extract_and_group_spans(validated_payload)

        total_traces = 0
        total_spans = 0
        trace_ids: list[str] = []
        evaluation_ids: list[str] = []
        rejected_spans = 0
        errors: list[str] = []

        for trace_id, (res_attrs, spans) in grouped_traces.items():
            if not spans:
                continue

            try:
                otel_trace = OTELTrace(
                    trace_id=trace_id,
                    resource=OTELResource(attributes=res_attrs),
                    spans=spans,
                )
                cats_trace: CanonicalTrace = translate_otel_trace_to_cats(otel_trace)

                # Persist trace scoped to authenticated workspace
                trace_record = self.trace_repository.create_trace(
                    trace=cats_trace,
                    workspace_id=workspace_id,
                )

                total_traces += 1
                total_spans += len(spans)
                trace_ids.append(str(trace_record.trace_id))

                if auto_evaluate:
                    eval_result = self.evaluation_service.run_evaluation(trace_record.trace_id)
                    if eval_result and eval_result.evaluation_id:
                        evaluation_ids.append(str(eval_result.evaluation_id))

            except Exception as e:
                logger.warning("Failed to translate/evaluate OTEL trace %s: %s", trace_id, e)
                rejected_spans += len(spans)
                errors.append(f"Trace {trace_id}: {str(e)}")

        is_partial = rejected_spans > 0 and total_traces > 0
        err_msg = "; ".join(errors) if errors else None

        return CollectorBatchResult(
            traces_ingested=total_traces,
            spans_ingested=total_spans,
            trace_ids=trace_ids,
            evaluation_ids=evaluation_ids,
            partial_success=is_partial,
            rejected_spans=rejected_spans,
            error_message=err_msg,
            workspace_id=str(workspace_id) if workspace_id else None,
        )
