"""OpenTelemetry to Canonical Agent Trace Schema (CATS) translation engine."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.enums import (
    FrameworkType,
    OrchestratorType,
    RetryResolution,
    WorkflowStatus,
)
from app.domain.models import (
    Agent,
    BudgetConfig,
    CanonicalTrace,
    Retry,
    Session,
    Step,
    TokenUsage,
    ToolCall,
    ToolDefinition,
    Workflow,
)
from app.otel.otel_adapter import (
    DetectedFramework,
    FrameworkDetector,
    extract_cost_usd,
    extract_input_state,
    extract_model_name,
    extract_output_state,
    extract_span_latency_ms,
    extract_token_counts,
)
from app.otel.otel_models import OTELSpan, OTELTrace
from app.otel.otel_parser import parse_timestamp_to_seconds, validate_otel_trace


def _normalize_uuid(identifier: str, prefix: str = "otel") -> UUID:
    """Deterministically convert any string or hex identifier into a valid UUID."""
    clean = identifier.strip().replace("-", "")
    if len(clean) == 32:
        try:
            return UUID(hex=clean)
        except ValueError:
            pass
    try:
        return UUID(identifier.strip())
    except ValueError:
        return uuid5(NAMESPACE_URL, f"{prefix}:{identifier.strip()}")


def _extract_tool_calls_from_span(span: OTELSpan, step_id: UUID) -> list[ToolCall]:
    """Extract ToolCall instances from span attributes or events."""
    attrs = span.attributes or {}
    tool_calls: list[ToolCall] = []

    # 1. Attribute-based tool call
    tool_name = attrs.get("tool.name") or attrs.get("gen_ai.tool.name") or attrs.get("tool_name")
    if not tool_name and (span.kind == "TOOL" or span.name.lower().startswith("tool:")):
        tool_name = span.name.split(":", 1)[-1].strip()

    if tool_name:
        raw_args = (
            attrs.get("tool.arguments")
            or attrs.get("gen_ai.tool.arguments")
            or attrs.get("arguments")
            or {}
        )
        if isinstance(raw_args, str):
            try:
                raw_args = json.loads(raw_args)
            except Exception:
                raw_args = {"raw": raw_args}
        if not isinstance(raw_args, dict):
            raw_args = {"arguments": raw_args}

        result_data = (
            attrs.get("tool.result") or attrs.get("gen_ai.tool.result") or attrs.get("result") or {}
        )
        if isinstance(result_data, str):
            try:
                result_data = json.loads(result_data)
            except Exception:
                result_data = {"result": result_data}
        if not isinstance(result_data, dict):
            result_data = {"output": result_data}

        st_code = ""
        if isinstance(span.status, str):
            st_code = span.status
        elif hasattr(span.status, "status_code"):
            st_code = span.status.status_code
        elif isinstance(span.status, dict):
            st_code = span.status.get("status_code", "UNSET")

        is_err = st_code.upper() in ("ERROR", "2") or bool(attrs.get("error"))

        tool_calls.append(
            ToolCall(
                tool_call_id=uuid5(step_id, f"tool:{tool_name}"),
                step_id=step_id,
                tool_name=str(tool_name),
                raw_arguments=raw_args,
                parsed_arguments=raw_args,
                execution_result=result_data,
                is_error=is_err,
                execution_time_ms=extract_span_latency_ms(span),
            )
        )

    # 2. Multi-tool calls array in attributes (e.g. OpenAI function/tool calling)
    raw_tool_calls = attrs.get("tool_calls") or attrs.get("tool.calls")
    if raw_tool_calls:
        if isinstance(raw_tool_calls, str):
            try:
                raw_tool_calls = json.loads(raw_tool_calls)
            except Exception:
                raw_tool_calls = []
        if isinstance(raw_tool_calls, dict):
            raw_tool_calls = [raw_tool_calls]
        if isinstance(raw_tool_calls, list):
            for idx, tc in enumerate(raw_tool_calls):
                if isinstance(tc, dict):
                    t_name = tc.get("name") or tc.get("tool_name") or f"tool_{idx}"
                    t_args = tc.get("input") or tc.get("arguments") or tc.get("raw_arguments") or {}
                    tool_calls.append(
                        ToolCall(
                            tool_call_id=uuid5(step_id, f"tool_call:{idx}:{t_name}"),
                            step_id=step_id,
                            tool_name=str(t_name),
                            raw_arguments=t_args
                            if isinstance(t_args, dict)
                            else {"arguments": t_args},
                            parsed_arguments=t_args
                            if isinstance(t_args, dict)
                            else {"arguments": t_args},
                            execution_result=tc.get("result") or tc.get("output"),
                            is_error=bool(tc.get("is_error")),
                            execution_time_ms=0,
                        )
                    )

    # 3. Event-based tool calls (e.g. tool execution events within an agent span)
    for idx, ev in enumerate(span.events):
        if "tool" in ev.name.lower():
            ev_attrs = ev.attributes or {}
            ev_tool_name = ev_attrs.get("tool.name") or ev_attrs.get("tool_name") or ev.name
            tool_calls.append(
                ToolCall(
                    tool_call_id=uuid5(step_id, f"event_tool:{idx}:{ev_tool_name}"),
                    step_id=step_id,
                    tool_name=str(ev_tool_name),
                    raw_arguments=ev_attrs,
                    parsed_arguments=ev_attrs,
                    execution_result={"event": ev.name},
                    is_error=False,
                    execution_time_ms=0,
                )
            )

    return tool_calls


def _extract_retries_from_span(span: OTELSpan, step_id: UUID) -> list[Retry]:
    """Extract Retry instances from span attributes or events."""
    attrs = span.attributes or {}
    retries: list[Retry] = []

    retry_count = (
        attrs.get("retry.count")
        or attrs.get("retry_count")
        or attrs.get("retries")
        or attrs.get("attempt")
        or attrs.get("retry_number")
    )
    if retry_count and isinstance(retry_count, int | float) and int(retry_count) > 1:
        attempts = int(retry_count)
        for att in range(1, attempts):
            retries.append(
                Retry(
                    retry_id=uuid5(step_id, f"retry:{att}"),
                    step_id=step_id,
                    attempt_number=att,
                    error_type=str(attrs.get("error.type", "ExecutionTransientFailure")),
                    backoff_duration_ms=int(attrs.get("retry.backoff_ms", 100)),
                    resolution=RetryResolution.RESOLVED
                    if att == attempts - 1
                    else RetryResolution.EXHAUSTED,
                )
            )

    for idx, ev in enumerate(span.events):
        if "retry" in ev.name.lower():
            ev_attrs = ev.attributes or {}
            retries.append(
                Retry(
                    retry_id=uuid5(step_id, f"event_retry:{idx}"),
                    step_id=step_id,
                    attempt_number=idx + 1,
                    error_type=str(ev_attrs.get("error.type", "RetryEvent")),
                    backoff_duration_ms=int(ev_attrs.get("backoff_ms", 100)),
                    resolution=RetryResolution.RESOLVED,
                )
            )

    return retries


def translate_otel_trace_to_cats(otel_trace: OTELTrace) -> CanonicalTrace:
    """Translate an OpenTelemetry trace into a Canonical Agent Trace Schema (CATS) object."""
    # 1. Structural Validation
    validate_otel_trace(otel_trace)

    # 2. Framework Detection
    detected = FrameworkDetector.detect(otel_trace)

    # Map detected framework to CATS FrameworkType enum
    if detected == DetectedFramework.LANGGRAPH:
        framework = FrameworkType.LANGGRAPH
        orchestrator = OrchestratorType.DIRECTED_ACYCLIC_GRAPH
    elif detected == DetectedFramework.CREWAI:
        framework = FrameworkType.CREWAI
        orchestrator = OrchestratorType.AUTONOMOUS_SWARM
    elif detected == DetectedFramework.AUTOGEN:
        framework = FrameworkType.AUTOGEN
        orchestrator = OrchestratorType.AUTONOMOUS_SWARM
    elif detected == DetectedFramework.LLAMAINDEX or detected == DetectedFramework.OPENAI_AGENTS:
        framework = FrameworkType.CUSTOM
        orchestrator = OrchestratorType.DIRECTED_ACYCLIC_GRAPH
    else:
        framework = FrameworkType.OPENTELEMETRY
        orchestrator = OrchestratorType.DIRECTED_ACYCLIC_GRAPH

    # 3. Deterministic UUID Normalization
    session_id = _normalize_uuid(otel_trace.trace_id, prefix="session")
    workflow_id = uuid5(session_id, "workflow")

    # 4. Agent Profiling
    primary_model = "gpt-4o"
    agent_names: set[str] = set()
    for span in otel_trace.spans:
        m = extract_model_name(span, default="")
        if m and not primary_model:
            primary_model = m
        ag_name = (
            span.attributes.get("agent.name")
            or span.attributes.get("crewai.agent_name")
            or span.attributes.get("autogen.agent_name")
            or span.attributes.get("agent")
        )
        if ag_name and isinstance(ag_name, str):
            agent_names.add(ag_name.strip())

    if not agent_names:
        agent_names.add(f"{detected.value.title()}Agent")

    agents: list[Agent] = []
    agent_id_map: dict[str, UUID] = {}
    for ag_name in sorted(agent_names):
        ag_id = uuid5(session_id, f"agent:{ag_name}")
        agent_id_map[ag_name] = ag_id
        agents.append(
            Agent(
                agent_id=ag_id,
                name=ag_name,
                role="Autonomous Agent Worker",
                system_prompt_hash="0" * 64,
                model_identifier=primary_model or "gpt-4o",
                temperature=0.0,
                tool_registry=[],
            )
        )
    default_agent_id = agents[0].agent_id

    # 5. Spans to Steps Mapping (Preserving DAG & Parent Hierarchy)
    def span_sort_key(s: OTELSpan) -> float:
        t = parse_timestamp_to_seconds(s.start_time)
        return t if t is not None else 0.0

    sorted_spans = sorted(otel_trace.spans, key=span_sort_key)

    steps: list[Step] = []
    has_workflow_error = False
    total_cost = Decimal("0.0000")
    total_latency_ms = 0
    declared_tools: dict[str, ToolDefinition] = {}

    for idx, span in enumerate(sorted_spans):
        step_id = uuid5(session_id, f"step:{span.span_id}")
        latency = extract_span_latency_ms(span)
        total_latency_ms += latency
        total_cost += extract_cost_usd(span)

        # Check status
        st_code = ""
        if isinstance(span.status, str):
            st_code = span.status
        elif hasattr(span.status, "status_code"):
            st_code = span.status.status_code
        elif isinstance(span.status, dict):
            st_code = span.status.get("status_code", "UNSET")

        if st_code.upper() in ("ERROR", "2"):
            has_workflow_error = True

        # Assign Agent ID
        span_ag = span.attributes.get("agent.name") or span.attributes.get("crewai.agent_name")
        assigned_agent_id = (
            agent_id_map.get(str(span_ag), default_agent_id) if span_ag else default_agent_id
        )

        # Tool calls & Retries
        tool_calls = _extract_tool_calls_from_span(span, step_id)
        for tc in tool_calls:
            if tc.tool_name not in declared_tools:
                declared_tools[tc.tool_name] = ToolDefinition(
                    tool_name=tc.tool_name,
                    description=f"Auto-registered tool capability: {tc.tool_name}",
                    schema=tc.raw_arguments,
                )

        retries = _extract_retries_from_span(span, step_id)

        # Token usage
        p_tokens, c_tokens = extract_token_counts(span)

        # Input & Output States (with DAG parent references for React Flow Graph)
        input_st = extract_input_state(span)
        input_st["_otel_span_id"] = span.span_id
        if span.parent_span_id:
            input_st["_otel_parent_span_id"] = span.parent_span_id

        output_st = extract_output_state(span)

        steps.append(
            Step(
                step_id=step_id,
                workflow_id=workflow_id,
                agent_id=assigned_agent_id,
                step_index=idx,
                node_name=span.name,
                input_state=input_st,
                output_state=output_st,
                token_usage=TokenUsage(prompt_tokens=p_tokens, completion_tokens=c_tokens),
                latency_ms=latency,
                tool_calls=tool_calls,
                retries=retries,
            )
        )

    # Populate registered tools on agents
    agents[0].tool_registry = list(declared_tools.values())

    # 6. Overall Workflow Status
    wf_status = WorkflowStatus.FAILED if has_workflow_error else WorkflowStatus.SUCCESS

    # 7. Session Creation
    first_input = steps[0].input_state if steps else {}
    user_intent = (
        first_input.get("prompt")
        or first_input.get("query")
        or first_input.get("raw_input")
        or f"Execute agent workflow via {detected.value}"
    )
    if isinstance(user_intent, dict | list):
        user_intent = json.dumps(user_intent)

    earliest_time = None
    if sorted_spans and sorted_spans[0].start_time is not None:
        t_sec = parse_timestamp_to_seconds(sorted_spans[0].start_time)
        if t_sec is not None:
            earliest_time = datetime.fromtimestamp(t_sec, tz=UTC)

    session = Session(
        session_id=session_id,
        user_intent=str(user_intent),
        context_data={"detected_framework": detected.value, "otel_trace_id": otel_trace.trace_id},
        budget_constraints=BudgetConfig(),
        created_at=earliest_time or datetime.now(UTC),
    )

    workflow = Workflow(
        workflow_id=workflow_id,
        session_id=session_id,
        framework=framework,
        orchestrator_type=orchestrator,
        status=wf_status,
        total_cost_usd=total_cost,
        total_latency_ms=total_latency_ms,
    )

    return CanonicalTrace(
        session=session,
        agents=agents,
        workflow=workflow,
        steps=steps,
    )
