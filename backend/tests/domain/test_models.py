"""Unit tests for Canonical Agent Trace Schema (CATS) Pydantic models."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums import (
    FrameworkType,
    OrchestratorType,
    RetryResolution,
    RiskClassification,
    WorkflowStatus,
)
from app.domain.models import (
    Agent,
    BudgetConfig,
    CanonicalTrace,
    EvaluationResult,
    Retry,
    Session,
    Step,
    TokenUsage,
    ToolCall,
    ToolDefinition,
    Workflow,
)


def test_token_usage_total_tokens() -> None:
    """Verify total_tokens computation property."""
    usage = TokenUsage(
        prompt_tokens=150,
        completion_tokens=50,
        cached_tokens=20,
        reasoning_tokens=10,
    )
    assert usage.total_tokens == 200


def test_token_usage_negative_validation() -> None:
    """Verify negative token counts are rejected."""
    with pytest.raises(ValidationError):
        TokenUsage(prompt_tokens=-1)

    with pytest.raises(ValidationError):
        TokenUsage(completion_tokens=-5)


def test_budget_config_validation() -> None:
    """Verify budget limits validation."""
    config = BudgetConfig(max_usd=Decimal("2.50"), max_latency_ms=5000, max_tokens=20000)
    assert config.max_usd == Decimal("2.50")
    assert config.max_latency_ms == 5000
    assert config.max_tokens == 20000

    with pytest.raises(ValidationError):
        BudgetConfig(max_usd=Decimal("-0.01"))

    with pytest.raises(ValidationError):
        BudgetConfig(max_latency_ms=-1)

    with pytest.raises(ValidationError):
        BudgetConfig(max_tokens=-1)


def test_tool_definition_model() -> None:
    """Verify ToolDefinition fields, schema alias, and validation."""
    tool = ToolDefinition(
        tool_name="web_search",
        description="Performs internet search.",
        schema={"type": "object", "properties": {"query": {"type": "string"}}},
    )
    assert tool.tool_name == "web_search"
    assert tool.schema["type"] == "object"
    assert tool.parameters_schema["type"] == "object"

    with pytest.raises(ValidationError):
        ToolDefinition(tool_name="", description="Empty name")


def test_agent_model_and_temperature_bounds() -> None:
    """Verify Agent validation, temperature bounds [0.0, 2.0], and tool registry."""
    agent_id = uuid4()
    agent = Agent(
        agent_id=agent_id,
        name="Researcher",
        role="Research Assistant",
        system_prompt_hash="12345678abcdef",
        model_identifier="claude-3-5-sonnet",
        temperature=0.7,
        tool_registry=[],
    )
    assert agent.agent_id == agent_id
    assert agent.temperature == 0.7

    # Bounds: temperature < 0.0 or > 2.0
    with pytest.raises(ValidationError):
        Agent(
            agent_id=agent_id,
            name="Researcher",
            role="Research Assistant",
            system_prompt_hash="12345678abcdef",
            model_identifier="claude-3-5-sonnet",
            temperature=-0.1,
        )

    with pytest.raises(ValidationError):
        Agent(
            agent_id=agent_id,
            name="Researcher",
            role="Research Assistant",
            system_prompt_hash="12345678abcdef",
            model_identifier="claude-3-5-sonnet",
            temperature=2.1,
        )


def test_session_timezone_normalization() -> None:
    """Verify naive datetimes are normalized to UTC, and invalid types fail."""
    session_id = uuid4()
    naive_dt = datetime(2026, 11, 8, 12, 0, 0)
    session = Session(
        session_id=session_id,
        user_intent="Summarize article",
        created_at=naive_dt,
    )
    assert session.created_at.tzinfo == UTC

    # String format
    session_from_str = Session(
        session_id=session_id,
        user_intent="Summarize article",
        created_at="2026-11-08T12:00:00Z",  # type: ignore[arg-type]
    )
    assert session_from_str.created_at.tzinfo == UTC

    # Invalid type
    with pytest.raises(ValidationError):
        Session(
            session_id=session_id,
            user_intent="Summarize article",
            created_at=123456789,  # type: ignore[arg-type]
        )


def test_workflow_validation() -> None:
    """Verify Workflow cost and latency non-negativity."""
    wf_id = uuid4()
    sess_id = uuid4()
    wf = Workflow(
        workflow_id=wf_id,
        session_id=sess_id,
        framework=FrameworkType.LANGGRAPH,
        orchestrator_type=OrchestratorType.DIRECTED_ACYCLIC_GRAPH,
        status=WorkflowStatus.SUCCESS,
        total_cost_usd=Decimal("0.05"),
        total_latency_ms=1200,
    )
    assert wf.total_cost_usd == Decimal("0.05")
    assert wf.total_latency_ms == 1200

    with pytest.raises(ValidationError):
        Workflow(
            workflow_id=wf_id,
            session_id=sess_id,
            framework=FrameworkType.LANGGRAPH,
            orchestrator_type=OrchestratorType.DIRECTED_ACYCLIC_GRAPH,
            status=WorkflowStatus.SUCCESS,
            total_cost_usd=Decimal("-0.01"),
        )

    with pytest.raises(ValidationError):
        Workflow(
            workflow_id=wf_id,
            session_id=sess_id,
            framework=FrameworkType.LANGGRAPH,
            orchestrator_type=OrchestratorType.DIRECTED_ACYCLIC_GRAPH,
            status=WorkflowStatus.SUCCESS,
            total_latency_ms=-1,
        )


def test_tool_call_model() -> None:
    """Verify ToolCall model attributes and negative latency rejection."""
    tc_id = uuid4()
    step_id = uuid4()
    call = ToolCall(
        tool_call_id=tc_id,
        step_id=step_id,
        tool_name="calculator",
        raw_arguments={"expression": "2 + 2"},
        execution_time_ms=15,
    )
    assert call.tool_name == "calculator"
    assert call.is_error is False
    assert call.is_hallucinated is False

    with pytest.raises(ValidationError):
        ToolCall(
            tool_call_id=tc_id,
            step_id=step_id,
            tool_name="calculator",
            execution_time_ms=-5,
        )


def test_retry_model_attempt_validation() -> None:
    """Verify Retry requires attempt_number >= 1."""
    retry_id = uuid4()
    step_id = uuid4()
    retry = Retry(
        retry_id=retry_id,
        step_id=step_id,
        attempt_number=1,
        error_type="TIMEOUT",
        resolution=RetryResolution.RESOLVED,
    )
    assert retry.attempt_number == 1

    with pytest.raises(ValidationError):
        Retry(
            retry_id=retry_id,
            step_id=step_id,
            attempt_number=0,
            error_type="TIMEOUT",
            resolution=RetryResolution.RESOLVED,
        )


def test_step_model_validation() -> None:
    """Verify Step model validation for negative step index and latency."""
    step_id = uuid4()
    wf_id = uuid4()
    ag_id = uuid4()

    step = Step(
        step_id=step_id,
        workflow_id=wf_id,
        agent_id=ag_id,
        step_index=0,
        node_name="triage",
    )
    assert step.step_index == 0

    with pytest.raises(ValidationError):
        Step(
            step_id=step_id,
            workflow_id=wf_id,
            agent_id=ag_id,
            step_index=-1,
            node_name="triage",
        )


def test_evaluation_result_bounds() -> None:
    """Verify overall_score must be between 0.0 and 100.0."""
    eval_id = uuid4()
    wf_id = uuid4()
    res = EvaluationResult(
        eval_id=eval_id,
        workflow_id=wf_id,
        overall_score=85.5,
        risk_classification=RiskClassification.GOOD,
    )
    assert res.overall_score == 85.5

    with pytest.raises(ValidationError):
        EvaluationResult(
            eval_id=eval_id,
            workflow_id=wf_id,
            overall_score=105.0,
            risk_classification=RiskClassification.GOOD,
        )

    with pytest.raises(ValidationError):
        EvaluationResult(
            eval_id=eval_id,
            workflow_id=wf_id,
            overall_score=-5.0,
            risk_classification=RiskClassification.GOOD,
        )


def test_extra_fields_forbidden() -> None:
    """Verify that extra unknown fields raise ValidationError."""
    with pytest.raises(ValidationError):
        BudgetConfig(max_usd=Decimal("1.0"), unknown_arbitrary_key="value")  # type: ignore[call-arg]


def test_uuid_validation() -> None:
    """Verify invalid UUID string raises ValidationError."""
    with pytest.raises(ValidationError):
        Session(
            session_id="invalid-uuid-string",  # type: ignore[arg-type]
            user_intent="test",
            created_at=datetime.now(UTC),
        )


def test_serialization_roundtrip() -> None:
    """Verify JSON serialization and deserialization preserves all values."""
    session_id = uuid4()
    agent_id = uuid4()
    workflow_id = uuid4()
    step_id = uuid4()
    tool_call_id = uuid4()

    trace = CanonicalTrace(
        session=Session(
            session_id=session_id,
            user_intent="Test trace execution",
            created_at=datetime(2026, 11, 8, 10, 0, 0, tzinfo=UTC),
        ),
        agents=[
            Agent(
                agent_id=agent_id,
                name="TestAgent",
                role="Tester",
                system_prompt_hash="aabbccddeeff1122",
                model_identifier="gpt-4o",
                temperature=0.0,
            )
        ],
        workflow=Workflow(
            workflow_id=workflow_id,
            session_id=session_id,
            framework=FrameworkType.LANGGRAPH,
            orchestrator_type=OrchestratorType.DIRECTED_ACYCLIC_GRAPH,
            status=WorkflowStatus.SUCCESS,
            total_cost_usd=Decimal("0.025"),
            total_latency_ms=1500,
        ),
        steps=[
            Step(
                step_id=step_id,
                workflow_id=workflow_id,
                agent_id=agent_id,
                step_index=0,
                node_name="execute",
                tool_calls=[
                    ToolCall(
                        tool_call_id=tool_call_id,
                        step_id=step_id,
                        tool_name="query_db",
                        raw_arguments={"sql": "SELECT 1;"},
                    )
                ],
            )
        ],
    )

    json_str = trace.model_dump_json()
    assert isinstance(json_str, str)

    restored = CanonicalTrace.model_validate_json(json_str)
    assert restored.session.session_id == session_id
    assert restored.agents[0].agent_id == agent_id
    assert restored.workflow.workflow_id == workflow_id
    assert restored.steps[0].tool_calls[0].tool_call_id == tool_call_id
    assert restored.workflow.total_cost_usd == Decimal("0.025")


def test_minimal_valid_fixture() -> None:
    """Verify fixtures/minimal_valid_trace.json validates successfully."""
    fixture_path = Path(__file__).resolve().parents[3] / "fixtures" / "minimal_valid_trace.json"
    assert fixture_path.exists(), f"Fixture not found at {fixture_path}"

    with open(fixture_path, encoding="utf-8") as f:
        json_content = f.read()

    trace = CanonicalTrace.model_validate_json(json_content)
    assert isinstance(trace.session.session_id, UUID)
    assert len(trace.agents) == 1
    assert trace.workflow.framework == FrameworkType.LANGGRAPH
    assert len(trace.steps) == 1
    assert trace.steps[0].token_usage.total_tokens == 505


def test_minimal_invalid_fixture() -> None:
    """Verify fixtures/minimal_invalid_trace.json fails validation."""
    fixture_path = Path(__file__).resolve().parents[3] / "fixtures" / "minimal_invalid_trace.json"
    assert fixture_path.exists(), f"Fixture not found at {fixture_path}"

    with open(fixture_path, encoding="utf-8") as f:
        json_content = f.read()

    with pytest.raises(ValidationError) as exc_info:
        CanonicalTrace.model_validate_json(json_content)

    errors = exc_info.value.errors()
    assert len(errors) > 0
