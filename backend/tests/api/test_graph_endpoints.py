"""Integration and contract tests for the workflow graph endpoint GET /evaluations/{id}/graph."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.entities import TraceRecord
from app.domain.models import CanonicalTrace
from app.services.evaluation_service import EvaluationService
from app.services.trace_repository import TraceRepository

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_fixture_json(filename: str) -> dict[str, object]:
    """Helper to load a fixture JSON file as a dictionary."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def test_get_evaluation_graph_not_found(client: TestClient) -> None:
    """Verify GET /api/v1/evaluations/{id}/graph returns 404 for nonexistent evaluation."""
    random_id = uuid4()
    response = client.get(f"/api/v1/evaluations/{random_id}/graph")
    assert response.status_code == 404
    assert f"Evaluation with ID '{random_id}' not found." in response.json()["detail"]


def test_get_evaluation_graph_clean_success(client: TestClient, db_session: Session) -> None:
    """Verify graph structure for a clean successful trace with zero cycles."""
    trace_dict = load_fixture_json("clean_success_trace.json")
    trace = CanonicalTrace.model_validate(trace_dict)

    repo = TraceRepository(db_session)
    trace_record = repo.create_trace(trace)

    eval_service = EvaluationService(session=db_session)
    eval_record = eval_service.run_evaluation(trace_id=trace_record.trace_id)
    assert eval_record is not None

    response = client.get(f"/api/v1/evaluations/{eval_record.evaluation_id}/graph")
    assert response.status_code == 200
    data = response.json()

    assert data["evaluation_id"] == str(eval_record.evaluation_id)
    assert data["trace_id"] == str(trace_record.trace_id)
    assert data["workflow_status"] == "SUCCESS"
    assert data["total_steps"] == len(trace.steps)
    assert data["has_cycles"] is False
    assert len(data["nodes"]) == len(trace.steps)
    assert len(data["edges"]) == len(trace.steps) - 1

    # Inspect first node
    first_node = data["nodes"][0]
    assert first_node["id"] == "step-0"
    assert first_node["step_index"] == 0
    assert first_node["is_cycle_node"] is False
    assert "token_usage" in first_node
    assert first_node["token_usage"]["total_tokens"] >= 0

    # Ensure edge connections
    for i in range(len(data["edges"])):
        edge = data["edges"][i]
        assert edge["source"] == f"step-{i}"
        assert edge["target"] == f"step-{i + 1}"
        assert edge["is_cycle_edge"] is False


def test_get_evaluation_graph_with_cycles(client: TestClient, db_session: Session) -> None:
    """Verify graph marks has_cycles=True and tags cyclic nodes & edges for loop trace."""
    trace_dict = load_fixture_json("loop_trace.json")
    trace = CanonicalTrace.model_validate(trace_dict)

    repo = TraceRepository(db_session)
    trace_record = repo.create_trace(trace)

    eval_service = EvaluationService(session=db_session)
    eval_record = eval_service.run_evaluation(trace_id=trace_record.trace_id)
    assert eval_record is not None

    response = client.get(f"/api/v1/evaluations/{eval_record.evaluation_id}/graph")
    assert response.status_code == 200
    data = response.json()

    assert data["has_cycles"] is True
    assert data["total_steps"] == len(trace.steps)

    # Verify at least some nodes and edges are marked as cycle elements
    cycle_nodes = [node for node in data["nodes"] if node["is_cycle_node"]]
    assert len(cycle_nodes) > 0

    cycle_edges = [edge for edge in data["edges"] if edge["is_cycle_edge"]]
    assert len(cycle_edges) > 0

    # Verify findings are attached to the cyclic nodes
    nodes_with_findings = [node for node in data["nodes"] if len(node["findings"]) > 0]
    assert len(nodes_with_findings) > 0
    any_cycle_finding = any(
        finding["code"] == "CYCLE_DETECTED"
        for node in nodes_with_findings
        for finding in node["findings"]
    )
    assert any_cycle_finding is True


def test_get_evaluation_graph_with_tools_and_retries(
    client: TestClient, db_session: Session
) -> None:
    """Verify graph node tool_calls and retries are serialized accurately."""
    trace_dict = load_fixture_json("retry_storm_trace.json")
    trace = CanonicalTrace.model_validate(trace_dict)

    repo = TraceRepository(db_session)
    trace_record = repo.create_trace(trace)

    eval_service = EvaluationService(session=db_session)
    eval_record = eval_service.run_evaluation(trace_id=trace_record.trace_id)
    assert eval_record is not None

    response = client.get(f"/api/v1/evaluations/{eval_record.evaluation_id}/graph")
    assert response.status_code == 200
    data = response.json()

    # Find nodes with retries
    nodes_with_retries = [node for node in data["nodes"] if len(node["retries"]) > 0]
    assert len(nodes_with_retries) > 0
    first_retry = nodes_with_retries[0]["retries"][0]
    assert first_retry["attempt_number"] >= 1
    assert "error_type" in first_retry
    assert "resolution" in first_retry


def test_get_evaluation_graph_trace_missing(client: TestClient, db_session: Session) -> None:
    """Verify get_evaluation_graph returns None when underlying trace record is missing."""
    trace_dict = load_fixture_json("clean_success_trace.json")
    trace = CanonicalTrace.model_validate(trace_dict)

    repo = TraceRepository(db_session)
    trace_record = repo.create_trace(trace)

    eval_service = EvaluationService(session=db_session)
    eval_record = eval_service.run_evaluation(trace_id=trace_record.trace_id)
    assert eval_record is not None

    # Mock TraceRecord lookup returning None to simulate an unreachable trace
    with pytest.MonkeyPatch.context() as mp:
        original_get = db_session.get

        def mock_get(entity_cls: type, ident: object) -> object:
            if entity_cls is TraceRecord:
                return None
            return original_get(entity_cls, ident)

        mp.setattr(db_session, "get", mock_get)
        graph = eval_service.get_evaluation_graph(eval_record.evaluation_id)
        assert graph is None
