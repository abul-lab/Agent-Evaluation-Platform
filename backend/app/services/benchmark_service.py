"""Service layer for evaluation benchmarking, comparison analysis, and ranking leaderboards."""

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, col, select

from app.db.entities import EvaluationRecord, TraceRecord
from app.evaluators.base import EvaluationFinding
from app.schemas.benchmark_api import (
    BenchmarkLeaderboardItem,
    BenchmarkSummaryResponse,
    DomainScoreDelta,
    EvaluationComparisonResponse,
    FindingDelta,
    RiskTransition,
)
from app.scorecard.score_models import Scorecard

RISK_TIER_ORDER: dict[str, int] = {
    "CRITICAL": 0,
    "POOR": 1,
    "WATCH": 2,
    "GOOD": 3,
    "EXCELLENT": 4,
}

EVALUATION_DOMAINS = [
    "task_quality",
    "tool_usage",
    "workflow_quality",
    "reliability",
    "safety",
    "cost",
    "efficiency",
]


class BenchmarkService:
    """Coordinates comparative analysis and benchmark dataset reporting across evaluation runs."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def compare_evaluations(
        self,
        base_id: UUID,
        target_id: UUID,
    ) -> EvaluationComparisonResponse | None:
        """Execute mathematical and qualitative delta comparison between a baseline and target evaluation."""
        base_record = self.session.get(EvaluationRecord, base_id)
        target_record = self.session.get(EvaluationRecord, target_id)

        if not base_record or not target_record:
            return None

        base_scorecard = Scorecard.model_validate_json(base_record.scorecard_json)
        target_scorecard = Scorecard.model_validate_json(target_record.scorecard_json)

        base_findings_raw: list[dict[str, object]] = json.loads(base_record.findings_json)
        target_findings_raw: list[dict[str, object]] = json.loads(target_record.findings_json)

        base_findings = [EvaluationFinding.model_validate(f) for f in base_findings_raw]
        target_findings = [EvaluationFinding.model_validate(f) for f in target_findings_raw]

        # 1. Overall Score Delta
        overall_score_delta = round(target_record.overall_score - base_record.overall_score, 2)

        # 2. Risk Transition
        base_tier_idx = RISK_TIER_ORDER.get(base_record.risk_classification, 2)
        target_tier_idx = RISK_TIER_ORDER.get(target_record.risk_classification, 2)
        risk_transition = RiskTransition(
            base_risk=base_record.risk_classification,
            target_risk=target_record.risk_classification,
            is_improved=target_tier_idx > base_tier_idx,
            is_degraded=target_tier_idx < base_tier_idx,
        )

        # 3. Domain Deltas
        domain_deltas: dict[str, DomainScoreDelta] = {}
        for domain in EVALUATION_DOMAINS:
            base_domain = getattr(base_scorecard, domain)
            target_domain = getattr(target_scorecard, domain)
            score_delta = round(target_domain.score - base_domain.score, 2)
            domain_deltas[domain] = DomainScoreDelta(
                domain_name=domain,
                base_score=base_domain.score,
                target_score=target_domain.score,
                score_delta=score_delta,
                base_status=base_domain.status.value,
                target_status=target_domain.status.value,
            )

        # 4. Finding Deltas (by code and affected_steps signature)
        base_sigs = {(f.code, tuple(sorted(f.affected_steps))): f for f in base_findings}
        target_sigs = {(f.code, tuple(sorted(f.affected_steps))): f for f in target_findings}

        new_findings = [f for sig, f in target_sigs.items() if sig not in base_sigs]
        resolved_findings = [f for sig, f in base_sigs.items() if sig not in target_sigs]
        persistent_findings = [f for sig, f in target_sigs.items() if sig in base_sigs]

        finding_delta = FindingDelta(
            new_findings=new_findings,
            resolved_findings=resolved_findings,
            persistent_findings=persistent_findings,
            new_count=len(new_findings),
            resolved_count=len(resolved_findings),
            persistent_count=len(persistent_findings),
            total_delta=len(target_findings) - len(base_findings),
        )

        return EvaluationComparisonResponse(
            base_evaluation_id=base_record.evaluation_id,
            target_evaluation_id=target_record.evaluation_id,
            base_trace_id=base_record.trace_id,
            target_trace_id=target_record.trace_id,
            base_score=base_record.overall_score,
            target_score=target_record.overall_score,
            overall_score_delta=overall_score_delta,
            risk_transition=risk_transition,
            domain_deltas=domain_deltas,
            finding_delta=finding_delta,
            compared_at=datetime.now(UTC),
        )

    def get_benchmark_summary(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> BenchmarkSummaryResponse:
        """Calculate statistical aggregates and ranked evaluation leaderboard across the database."""
        statement = select(EvaluationRecord).order_by(
            col(EvaluationRecord.overall_score).desc(),
            col(EvaluationRecord.started_at).desc(),
        )
        all_evaluations = list(self.session.exec(statement).all())

        if not all_evaluations:
            return BenchmarkSummaryResponse(
                total_evaluations=0,
                mean_score=0.0,
                min_score=0.0,
                max_score=0.0,
                pass_rate=0.0,
                risk_distribution=dict.fromkeys(RISK_TIER_ORDER, 0),
                leaderboard=[],
            )

        # Preload traces for workflow_status mapping
        trace_ids = [e.trace_id for e in all_evaluations]
        trace_stmt = select(TraceRecord).where(col(TraceRecord.trace_id).in_(trace_ids))
        trace_records = list(self.session.exec(trace_stmt).all())
        trace_map = {t.trace_id: t.workflow_status for t in trace_records}

        scores = [e.overall_score for e in all_evaluations]
        total_count = len(scores)
        mean_score = round(sum(scores) / total_count, 2)
        min_score = round(min(scores), 2)
        max_score = round(max(scores), 2)

        pass_count = sum(
            1 for e in all_evaluations if e.risk_classification in ("EXCELLENT", "GOOD")
        )
        pass_rate = round((pass_count / total_count) * 100.0, 1)

        risk_distribution = dict.fromkeys(("EXCELLENT", "GOOD", "WATCH", "POOR", "CRITICAL"), 0)
        for e in all_evaluations:
            risk_distribution[e.risk_classification] = (
                risk_distribution.get(e.risk_classification, 0) + 1
            )

        # Build ranked leaderboard items with pagination
        sliced = all_evaluations[offset : offset + limit]
        leaderboard: list[BenchmarkLeaderboardItem] = []
        for idx, eval_rec in enumerate(sliced, start=offset + 1):
            leaderboard.append(
                BenchmarkLeaderboardItem(
                    rank=idx,
                    evaluation_id=eval_rec.evaluation_id,
                    trace_id=eval_rec.trace_id,
                    overall_score=eval_rec.overall_score,
                    risk_classification=eval_rec.risk_classification,
                    finding_count=eval_rec.finding_count,
                    workflow_status=trace_map.get(eval_rec.trace_id, "SUCCESS"),
                    started_at=eval_rec.started_at,
                    completed_at=eval_rec.completed_at,
                )
            )

        return BenchmarkSummaryResponse(
            total_evaluations=total_count,
            mean_score=mean_score,
            min_score=min_score,
            max_score=max_score,
            pass_rate=pass_rate,
            risk_distribution=risk_distribution,
            leaderboard=leaderboard,
        )
