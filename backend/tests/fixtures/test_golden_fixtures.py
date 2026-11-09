"""Contract tests for Golden Evaluation Trace Fixtures.

Verifies that all reference fixtures strictly conform to the Canonical Agent Trace Schema (CATS)
and satisfy the behavioral contract properties required for future evaluation engines.
"""

import json
import re
from pathlib import Path

import pytest

from app.domain.enums import RetryResolution, WorkflowStatus
from app.domain.models import CanonicalTrace

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"

GOLDEN_FIXTURES = [
    "clean_success_trace.json",
    "loop_trace.json",
    "hallucinated_tool_trace.json",
    "retry_storm_trace.json",
    "budget_exceeded_trace.json",
    "secret_leak_trace.json",
]


def load_fixture_json(filename: str) -> str:
    """Helper to load fixture file as a raw JSON string."""
    fixture_path = FIXTURES_DIR / filename
    assert fixture_path.exists(), f"Fixture file not found: {fixture_path}"
    with open(fixture_path, encoding="utf-8") as f:
        return f.read()


@pytest.mark.parametrize("fixture_name", GOLDEN_FIXTURES)
def test_fixture_loads_and_validates_against_cats(fixture_name: str) -> None:
    """Contract: Every golden fixture must strictly validate against CanonicalTrace."""
    raw_json = load_fixture_json(fixture_name)
    trace = CanonicalTrace.model_validate_json(raw_json)
    assert trace is not None
    assert len(trace.agents) >= 1
    assert len(trace.steps) >= 1


def test_clean_success_trace_contract() -> None:
    """Contract: clean_success_trace must represent nominal, valid, budget-compliant execution."""
    raw_json = load_fixture_json("clean_success_trace.json")
    trace = CanonicalTrace.model_validate_json(raw_json)

    # 1. Successful workflow status
    assert trace.workflow.status == WorkflowStatus.SUCCESS

    # 2. Within budget constraints
    assert trace.workflow.total_cost_usd <= trace.session.budget_constraints.max_usd
    assert trace.workflow.total_latency_ms <= trace.session.budget_constraints.max_latency_ms
    total_tokens = sum(s.token_usage.total_tokens for s in trace.steps)
    assert total_tokens <= trace.session.budget_constraints.max_tokens

    # 3. Valid tools and zero hallucinations
    registered_tools = {t.tool_name for a in trace.agents for t in a.tool_registry}
    for step in trace.steps:
        assert len(step.retries) == 0, f"Expected 0 retries in step {step.step_index}"
        for tool_call in step.tool_calls:
            assert tool_call.is_hallucinated is False
            assert tool_call.is_redundant is False
            assert tool_call.is_error is False
            assert tool_call.tool_name in registered_tools


def test_loop_trace_contract() -> None:
    """Contract: loop_trace must contain cyclic node sequences and redundant calls."""
    raw_json = load_fixture_json("loop_trace.json")
    trace = CanonicalTrace.model_validate_json(raw_json)

    # 1. Eventual timeout or failure
    assert trace.workflow.status in (WorkflowStatus.TIMEOUT, WorkflowStatus.FAILED)

    # 2. Repeated node sequences (cycles)
    node_sequence = [s.node_name for s in trace.steps]
    assert len(node_sequence) >= 4

    # Check for alternating cycle (A -> B -> A -> B)
    cycle_detected = False
    for i in range(len(node_sequence) - 2):
        if node_sequence[i] == node_sequence[i + 2]:
            cycle_detected = True
            break
    assert cycle_detected, "Expected cyclic oscillation in node sequence"

    # 3. Redundant tool calls present
    redundant_calls = [tc for s in trace.steps for tc in s.tool_calls if tc.is_redundant]
    assert len(redundant_calls) >= 2, "Expected redundant tool invocations"


def test_hallucinated_tool_trace_contract() -> None:
    """Contract: hallucinated_tool_trace must call a tool absent from the agent's registry."""
    raw_json = load_fixture_json("hallucinated_tool_trace.json")
    trace = CanonicalTrace.model_validate_json(raw_json)

    # 1. Workflow failure
    assert trace.workflow.status == WorkflowStatus.FAILED

    # 2. Tool call references unregistered tool
    registered_tools = {t.tool_name for a in trace.agents for t in a.tool_registry}
    hallucinated_calls = [tc for s in trace.steps for tc in s.tool_calls if tc.is_hallucinated]
    assert len(hallucinated_calls) >= 1, "Expected at least one hallucinated tool call"

    for h_call in hallucinated_calls:
        assert h_call.tool_name not in registered_tools
        assert h_call.is_error is True


def test_retry_storm_trace_contract() -> None:
    """Contract: retry_storm_trace must have multiple retries with eventual success."""
    raw_json = load_fixture_json("retry_storm_trace.json")
    trace = CanonicalTrace.model_validate_json(raw_json)

    # 1. Eventual success
    assert trace.workflow.status == WorkflowStatus.SUCCESS

    # 2. Multiple retries executed
    all_retries = [r for s in trace.steps for r in s.retries]
    assert len(all_retries) >= 3, "Expected at least 3 retries in storm scenario"

    # 3. Resolution resolves eventually
    resolutions = [r.resolution for r in all_retries]
    assert RetryResolution.RESOLVED in resolutions
    assert any(r.error_type == "RATE_LIMIT" for r in all_retries)


def test_budget_exceeded_trace_contract() -> None:
    """Contract: budget_exceeded_trace must exceed cost or token budget limits."""
    raw_json = load_fixture_json("budget_exceeded_trace.json")
    trace = CanonicalTrace.model_validate_json(raw_json)

    # 1. Budget exceeded status
    assert trace.workflow.status == WorkflowStatus.BUDGET_EXCEEDED

    # 2. Cost exceeds limit
    assert trace.workflow.total_cost_usd > trace.session.budget_constraints.max_usd

    # 3. Total tokens exceed limit
    total_tokens = sum(s.token_usage.total_tokens for s in trace.steps)
    assert total_tokens > trace.session.budget_constraints.max_tokens


def test_secret_leak_trace_contract() -> None:
    """Contract: secret_leak_trace must contain credential patterns in tool arguments."""
    raw_json = load_fixture_json("secret_leak_trace.json")
    trace = CanonicalTrace.model_validate_json(raw_json)

    # AWS Access Key ID regex: AKIA[0-9A-Z]{16}
    aws_key_pattern = re.compile(r"AKIA[0-9A-Z]{16}")
    # Fixture bearer token (a placeholder, not a real credential)
    api_token_pattern = re.compile(r"tok_fixture_bearer_[0-9]+")

    found_aws_key = False
    found_api_token = False

    for step in trace.steps:
        for tool_call in step.tool_calls:
            args_str = json.dumps(tool_call.raw_arguments)
            if aws_key_pattern.search(args_str):
                found_aws_key = True
            if api_token_pattern.search(args_str):
                found_api_token = True

    assert found_aws_key, "Expected AWS Access Key ID pattern in tool arguments"
    assert found_api_token, "Expected API secret token pattern in tool arguments"
