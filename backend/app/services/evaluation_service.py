"""Service layer coordinating trace retrieval, evaluation execution, scorecard generation, and persistence."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlmodel import Session, col, select

from app.db.entities import EvaluationRecord, TraceRecord
from app.domain.models import CanonicalTrace
from app.evaluators.base import EvaluationFinding
from app.schemas.graph_api import (
    GraphNodeFinding,
    GraphRetry,
    GraphToolCall,
    WorkflowGraphEdge,
    WorkflowGraphNode,
    WorkflowGraphResponse,
)
from app.schemas.notification_api import NotificationEventType
from app.scorecard.aggregator import ScorecardAggregator
from app.scorecard.score_models import Scorecard
from app.semantic.adapter import get_semantic_adapter
from app.semantic.base import SemanticEvaluator
from app.semantic.models import SemanticEvaluationResult
from app.services.deterministic_evaluator import DeterministicEvaluationService
from app.services.notification_service import NotificationEvent, NotificationService
from app.services.workspace_service import WorkspaceService


class EvaluationService:
    """Orchestrates the evaluation lifecycle for stored traces."""

    def __init__(
        self,
        session: Session,
        eval_service: DeterministicEvaluationService | None = None,
        aggregator: type[ScorecardAggregator] = ScorecardAggregator,
        semantic_enabled: bool = False,
        semantic_adapter: SemanticEvaluator | None = None,
    ) -> None:
        self.session = session
        self.eval_service = eval_service or DeterministicEvaluationService()
        self.aggregator = aggregator
        self.semantic_enabled = semantic_enabled
        self.semantic_adapter = semantic_adapter

    def run_evaluation(self, trace_id: UUID) -> EvaluationRecord | None:
        """Run deterministic evaluation and scorecard generation against a persisted trace.

        Returns None if no trace with the given trace_id exists.
        """
        trace_record = self.session.get(TraceRecord, trace_id)
        if not trace_record:
            return None

        started_at = datetime.now(UTC)
        canonical_trace = CanonicalTrace.model_validate_json(trace_record.raw_trace)
        eval_result = self.eval_service.evaluate_trace(canonical_trace)
        scorecard = self.aggregator.aggregate(eval_result)

        if self.semantic_enabled:
            adapter = self.semantic_adapter or get_semantic_adapter()
            semantic_result = adapter.evaluate_trace(canonical_trace)
        else:
            semantic_result = SemanticEvaluationResult(
                provider="fallback",
                evaluation_available=False,
                metrics=[],
                reason="Semantic evaluation disabled.",
            )

        completed_at = datetime.now(UTC)

        findings_serialized = json.dumps([f.model_dump(mode="json") for f in eval_result.findings])

        eval_record = EvaluationRecord(
            evaluation_id=uuid4(),
            workspace_id=trace_record.workspace_id,
            trace_id=trace_id,
            status="COMPLETED",
            started_at=started_at,
            completed_at=completed_at,
            finding_count=len(eval_result.findings),
            overall_score=scorecard.overall_score,
            risk_classification=scorecard.risk_classification.value,
            scorecard_json=scorecard.model_dump_json(),
            findings_json=findings_serialized,
            semantic_json=semantic_result.model_dump_json(),
        )

        self.session.add(eval_record)
        self.session.commit()
        self.session.refresh(eval_record)

        # Dispatch alerting notifications
        try:
            ws_service = WorkspaceService(self.session)
            default_ws = ws_service.get_default_workspace()
            notif_service = NotificationService(self.session)

            # 1. Secret Exposure Alert
            has_secret = any(f.code == "SECRET_EXPOSURE" for f in eval_result.findings)
            if has_secret:
                notif_service.dispatch_event(
                    default_ws.workspace_id,
                    NotificationEvent(
                        event_type=NotificationEventType.SECRET_EXPOSURE,
                        workspace_id=default_ws.workspace_id,
                        workspace_name=default_ws.name,
                        severity="CRITICAL",
                        title="Security Alert: Secret Exposure in Agent Trace",
                        reason="High-entropy credential or sensitive token leaked in tool input/output",
                        risk_tier="CRITICAL",
                        evaluation_id=str(eval_record.evaluation_id),
                        trace_id=str(eval_record.trace_id),
                        details={"finding_count": len(eval_result.findings)},
                        link=f"http://localhost:3000/evaluations/{eval_record.evaluation_id}",
                    ),
                )

            # 2. Critical Finding Alert
            has_critical = (
                any(f.severity.value == "CRITICAL" for f in eval_result.findings)
                or eval_record.risk_classification == "CRITICAL"
            )
            if has_critical:
                notif_service.dispatch_event(
                    default_ws.workspace_id,
                    NotificationEvent(
                        event_type=NotificationEventType.CRITICAL_FINDING,
                        workspace_id=default_ws.workspace_id,
                        workspace_name=default_ws.name,
                        severity="CRITICAL",
                        title="Critical Finding Detected in Agent Workflow",
                        reason=(
                            f"Evaluation completed with CRITICAL risk classification: "
                            f"{eval_record.risk_classification}"
                        ),
                        risk_tier=eval_record.risk_classification,
                        evaluation_id=str(eval_record.evaluation_id),
                        trace_id=str(eval_record.trace_id),
                        details={"overall_score": scorecard.overall_score},
                        link=f"http://localhost:3000/evaluations/{eval_record.evaluation_id}",
                    ),
                )

            # 3. Standard Evaluation Completed Alert
            notif_service.dispatch_event(
                default_ws.workspace_id,
                NotificationEvent(
                    event_type=NotificationEventType.EVALUATION_COMPLETED,
                    workspace_id=default_ws.workspace_id,
                    workspace_name=default_ws.name,
                    severity="INFO",
                    title=f"Evaluation Completed: Score {scorecard.overall_score:.1f}",
                    reason=f"Completed with risk tier {eval_record.risk_classification}",
                    risk_tier=eval_record.risk_classification,
                    evaluation_id=str(eval_record.evaluation_id),
                    trace_id=str(eval_record.trace_id),
                    details={
                        "overall_score": scorecard.overall_score,
                        "finding_count": len(eval_result.findings),
                    },
                    link=f"http://localhost:3000/evaluations/{eval_record.evaluation_id}",
                ),
            )
        except Exception:
            pass

        return eval_record

    def get_evaluation(self, evaluation_id: UUID) -> EvaluationRecord | None:
        """Retrieve an evaluation record by ID."""
        return self.session.get(EvaluationRecord, evaluation_id)

    def get_scorecard(self, evaluation_id: UUID) -> Scorecard | None:
        """Retrieve the scorecard for an evaluation run by evaluation ID."""
        record = self.get_evaluation(evaluation_id)
        if not record:
            return None
        return Scorecard.model_validate_json(record.scorecard_json)

    def get_findings(self, evaluation_id: UUID) -> list[EvaluationFinding] | None:
        """Retrieve deterministic findings for an evaluation run by evaluation ID."""
        record = self.get_evaluation(evaluation_id)
        if not record:
            return None
        findings_raw: list[dict[str, object]] = json.loads(record.findings_json)
        return [EvaluationFinding.model_validate(f) for f in findings_raw]

    def get_semantic_result(self, evaluation_id: UUID) -> SemanticEvaluationResult | None:
        """Retrieve semantic evaluation outcome for an evaluation run by evaluation ID."""
        record = self.get_evaluation(evaluation_id)
        if not record:
            return None
        if record.semantic_json:
            return SemanticEvaluationResult.model_validate_json(record.semantic_json)
        return SemanticEvaluationResult(
            provider="fallback",
            evaluation_available=False,
            metrics=[],
            reason="Semantic evaluation not executed for this run.",
        )

    def list_evaluations(
        self,
        trace_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EvaluationRecord]:
        """List evaluation records with optional trace_id filtering and pagination."""
        statement = select(EvaluationRecord)
        if trace_id is not None:
            statement = statement.where(EvaluationRecord.trace_id == trace_id)
        statement = (
            statement.order_by(col(EvaluationRecord.started_at).desc()).offset(offset).limit(limit)
        )
        results = self.session.exec(statement).all()
        return list(results)

    def get_evaluation_graph(self, evaluation_id: UUID) -> WorkflowGraphResponse | None:
        """Construct the workflow execution graph with node findings, tool calls, retries, and cycle markers."""
        record = self.get_evaluation(evaluation_id)
        if not record:
            return None

        trace_record = self.session.get(TraceRecord, record.trace_id)
        if not trace_record:
            return None

        canonical_trace = CanonicalTrace.model_validate_json(trace_record.raw_trace)
        findings_raw: list[dict[str, Any]] = json.loads(record.findings_json)

        agent_map = {agent.agent_id: agent.name for agent in canonical_trace.agents}

        cycle_step_indices: set[int] = set()
        for f in findings_raw:
            if f.get("code") == "CYCLE_DETECTED":
                for step_idx in f.get("affected_steps", []):
                    cycle_step_indices.add(int(step_idx))

        nodes: list[WorkflowGraphNode] = []
        for step in canonical_trace.steps:
            node_findings: list[GraphNodeFinding] = []
            for f in findings_raw:
                affected = f.get("affected_steps", [])
                if step.step_index in affected:
                    node_findings.append(
                        GraphNodeFinding(
                            finding_id=str(f.get("finding_id", "")),
                            severity=str(f.get("severity", "MEDIUM")),
                            code=str(f.get("code", "")),
                            message=str(f.get("message", "")),
                        )
                    )

            tool_calls: list[GraphToolCall] = [
                GraphToolCall(
                    tool_call_id=t.tool_call_id,
                    tool_name=t.tool_name,
                    raw_arguments=t.raw_arguments,
                    parsed_arguments=t.parsed_arguments,
                    execution_result=t.execution_result,
                    is_error=t.is_error,
                    is_hallucinated=t.is_hallucinated,
                    is_redundant=t.is_redundant,
                    execution_time_ms=t.execution_time_ms,
                )
                for t in step.tool_calls
            ]

            retries: list[GraphRetry] = [
                GraphRetry(
                    retry_id=r.retry_id,
                    attempt_number=r.attempt_number,
                    error_type=r.error_type,
                    backoff_duration_ms=r.backoff_duration_ms,
                    resolution=r.resolution.value
                    if hasattr(r.resolution, "value")
                    else str(r.resolution),
                )
                for r in step.retries
            ]

            token_usage = {
                "prompt_tokens": step.token_usage.prompt_tokens,
                "completion_tokens": step.token_usage.completion_tokens,
                "cached_tokens": step.token_usage.cached_tokens,
                "reasoning_tokens": step.token_usage.reasoning_tokens,
                "total_tokens": step.token_usage.total_tokens,
            }

            is_cycle_node = step.step_index in cycle_step_indices

            nodes.append(
                WorkflowGraphNode(
                    id=f"step-{step.step_index}",
                    step_id=step.step_id,
                    step_index=step.step_index,
                    node_name=step.node_name,
                    agent_id=step.agent_id,
                    agent_name=agent_map.get(step.agent_id, "Agent"),
                    latency_ms=step.latency_ms,
                    token_usage=token_usage,
                    input_state=step.input_state,
                    output_state=step.output_state,
                    tool_calls=tool_calls,
                    retries=retries,
                    findings=node_findings,
                    is_cycle_node=is_cycle_node,
                )
            )

        edges: list[WorkflowGraphEdge] = []
        for i in range(len(nodes) - 1):
            src = nodes[i].id
            dst = nodes[i + 1].id
            is_cycle_edge = nodes[i].is_cycle_node and nodes[i + 1].is_cycle_node
            edges.append(
                WorkflowGraphEdge(
                    id=f"edge-{src}-{dst}",
                    source=src,
                    target=dst,
                    is_cycle_edge=is_cycle_edge,
                    label=None,
                )
            )

        return WorkflowGraphResponse(
            evaluation_id=record.evaluation_id,
            trace_id=record.trace_id,
            workflow_id=canonical_trace.workflow.workflow_id,
            workflow_status=canonical_trace.workflow.status.value,
            total_steps=len(nodes),
            has_cycles=len(cycle_step_indices) > 0,
            nodes=nodes,
            edges=edges,
        )
