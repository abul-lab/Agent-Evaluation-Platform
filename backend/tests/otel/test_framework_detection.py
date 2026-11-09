"""Unit tests for OpenTelemetry framework auto-detection."""

from app.otel.otel_adapter import DetectedFramework, FrameworkDetector
from app.otel.otel_models import OTELResource, OTELSpan, OTELTrace


def test_detect_langgraph_from_resource() -> None:
    trace = OTELTrace(
        trace_id="11111111222233334444555566667777",
        resource=OTELResource(
            attributes={"service.name": "customer-graph", "framework": "langgraph"}
        ),
        spans=[
            OTELSpan(trace_id="11111111222233334444555566667777", span_id="s1", name="step_node")
        ],
    )
    assert FrameworkDetector.detect(trace) == DetectedFramework.LANGGRAPH


def test_detect_langgraph_from_span_name() -> None:
    trace = OTELTrace(
        trace_id="11111111222233334444555566667777",
        spans=[
            OTELSpan(
                trace_id="11111111222233334444555566667777",
                span_id="s1",
                name="langgraph.node: agent",
            )
        ],
    )
    assert FrameworkDetector.detect(trace) == DetectedFramework.LANGGRAPH


def test_detect_crewai() -> None:
    trace = OTELTrace(
        trace_id="11111111222233334444555566667777",
        spans=[
            OTELSpan(
                trace_id="11111111222233334444555566667777",
                span_id="s1",
                name="execute_task",
                attributes={"crewai.agent_name": "Senior Analyst", "crewai.task": "research"},
            )
        ],
    )
    assert FrameworkDetector.detect(trace) == DetectedFramework.CREWAI


def test_detect_autogen() -> None:
    trace = OTELTrace(
        trace_id="11111111222233334444555566667777",
        spans=[
            OTELSpan(
                trace_id="11111111222233334444555566667777",
                span_id="s1",
                name="chat_step",
                attributes={
                    "autogen.agent": "Coder",
                    "sender": "user_proxy",
                    "recipient": "assistant",
                },
            )
        ],
    )
    assert FrameworkDetector.detect(trace) == DetectedFramework.AUTOGEN


def test_detect_llamaindex() -> None:
    trace = OTELTrace(
        trace_id="11111111222233334444555566667777",
        spans=[
            OTELSpan(
                trace_id="11111111222233334444555566667777", span_id="s1", name="query_engine.query"
            )
        ],
    )
    assert FrameworkDetector.detect(trace) == DetectedFramework.LLAMAINDEX


def test_detect_openai_agents() -> None:
    trace = OTELTrace(
        trace_id="11111111222233334444555566667777",
        spans=[
            OTELSpan(
                trace_id="11111111222233334444555566667777",
                span_id="s1",
                name="thread.run",
                attributes={"openai.assistant_id": "asst_123"},
            )
        ],
    )
    assert FrameworkDetector.detect(trace) == DetectedFramework.OPENAI_AGENTS


def test_detect_generic_otel() -> None:
    trace = OTELTrace(
        trace_id="11111111222233334444555566667777",
        resource=OTELResource(attributes={"service.name": "custom-service"}),
        spans=[
            OTELSpan(
                trace_id="11111111222233334444555566667777", span_id="s1", name="HTTP GET /users"
            )
        ],
    )
    assert FrameworkDetector.detect(trace) == DetectedFramework.GENERIC_OTEL
