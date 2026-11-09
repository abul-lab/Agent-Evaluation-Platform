"""Service layer for computing historical analytics, time-series metrics, and quality trajectories."""

import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, select

from app.db.entities import EvaluationRecord
from app.schemas.analytics_api import (
    AnalyticsTrendsResponse,
    DailyAnalyticsBucket,
    FindingFrequency,
)
from app.scorecard.score_models import Scorecard

EVALUATION_DOMAINS = [
    "task_quality",
    "tool_usage",
    "workflow_quality",
    "reliability",
    "safety",
    "cost",
    "efficiency",
]

RISK_TIERS = ("EXCELLENT", "GOOD", "WATCH", "POOR", "CRITICAL")

FINDING_DESCRIPTIONS: dict[str, str] = {
    "CYCLE_DETECTED": "Cyclic loop detected in workflow execution sequence",
    "TOOL_CALL_HALLUCINATION": "Invoked tool not registered in agent capabilities",
    "REDUNDANT_TOOL_CALL": "Repeated invocation with identical arguments and state",
    "RETRY_STORM": "Excessive retry attempts exceeding threshold",
    "BUDGET_EXCEEDED": "Execution consumed cost, latency, or tokens beyond limits",
    "SECRET_EXPOSURE": "Potential credential or API key exposed in trace payloads",
}

SEVERITY_WEIGHT = {
    "INFO": 1,
    "LOW": 2,
    "MEDIUM": 3,
    "HIGH": 4,
    "CRITICAL": 5,
}


class AnalyticsService:
    """Computes longitudinal performance trends and quality distributions from evaluation records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_historical_trends(
        self,
        days: int = 30,
        limit: int = 500,
    ) -> AnalyticsTrendsResponse:
        """Calculate time-series analytics, score trajectories, and finding frequencies."""
        statement = select(EvaluationRecord)

        if days > 0:
            cutoff = datetime.now(UTC) - timedelta(days=days)
            statement = statement.where(EvaluationRecord.started_at >= cutoff)

        statement = statement.order_by(col(EvaluationRecord.started_at).asc()).limit(limit)
        evaluations = list(self.session.exec(statement).all())

        if not evaluations:
            return AnalyticsTrendsResponse(
                time_window_days=days,
                total_evaluations=0,
                average_score=0.0,
                score_trend_direction="STABLE",
                pass_rate=0.0,
                risk_distribution=dict.fromkeys(RISK_TIERS, 0),
                domain_averages=dict.fromkeys(EVALUATION_DOMAINS, 0.0),
                finding_distribution=[],
                daily_metrics=[],
            )

        total_count = len(evaluations)
        scores = [e.overall_score for e in evaluations]
        average_score = round(sum(scores) / total_count, 2)

        pass_count = sum(1 for e in evaluations if e.risk_classification in ("EXCELLENT", "GOOD"))
        pass_rate = round((pass_count / total_count) * 100.0, 1)

        # 1. Overall Risk Distribution
        risk_distribution = dict.fromkeys(RISK_TIERS, 0)
        for e in evaluations:
            risk_distribution[e.risk_classification] = (
                risk_distribution.get(e.risk_classification, 0) + 1
            )

        # 2. Score Trend Direction
        if total_count < 2:
            score_trend_direction = "STABLE"
        else:
            mid = total_count // 2
            first_half_avg = sum(scores[:mid]) / mid
            second_half_avg = sum(scores[mid:]) / (total_count - mid)
            delta = second_half_avg - first_half_avg
            if delta > 1.5:
                score_trend_direction = "IMPROVING"
            elif delta < -1.5:
                score_trend_direction = "DEGRADING"
            else:
                score_trend_direction = "STABLE"

        # 3. Domain Averages across all scorecards
        domain_accumulators: dict[str, list[float]] = {d: [] for d in EVALUATION_DOMAINS}
        global_finding_counts: dict[str, int] = defaultdict(int)
        global_finding_severities: dict[str, str] = {}

        # 4. Group by Calendar Date for Time Series
        date_buckets: dict[str, list[EvaluationRecord]] = defaultdict(list)
        for e in evaluations:
            date_key = e.started_at.strftime("%Y-%m-%d")
            date_buckets[date_key].append(e)

            # Parse scorecard
            try:
                scorecard = Scorecard.model_validate_json(e.scorecard_json)
                for d in EVALUATION_DOMAINS:
                    domain_obj = getattr(scorecard, d, None)
                    if domain_obj is not None:
                        domain_accumulators[d].append(domain_obj.score)
            except Exception:
                pass

            # Parse findings
            try:
                findings_raw = json.loads(e.findings_json)
                for f in findings_raw:
                    code = str(f.get("code", "UNKNOWN"))
                    severity = str(f.get("severity", "MEDIUM"))
                    global_finding_counts[code] += 1

                    current_sev = global_finding_severities.get(code, "INFO")
                    if SEVERITY_WEIGHT.get(severity, 1) > SEVERITY_WEIGHT.get(current_sev, 1):
                        global_finding_severities[code] = severity
            except Exception:
                pass

        domain_averages: dict[str, float] = {}
        for d in EVALUATION_DOMAINS:
            vals = domain_accumulators[d]
            domain_averages[d] = round(sum(vals) / len(vals), 2) if vals else 0.0

        # Construct Daily Analytics Buckets
        daily_metrics: list[DailyAnalyticsBucket] = []
        for date_str in sorted(date_buckets.keys()):
            bucket_evals = date_buckets[date_str]
            b_count = len(bucket_evals)
            b_avg_score = round(sum(be.overall_score for be in bucket_evals) / b_count, 2)

            b_risk_counts = dict.fromkeys(RISK_TIERS, 0)
            b_finding_counts: dict[str, int] = defaultdict(int)

            for be in bucket_evals:
                b_risk_counts[be.risk_classification] = (
                    b_risk_counts.get(be.risk_classification, 0) + 1
                )
                try:
                    f_list = json.loads(be.findings_json)
                    for item in f_list:
                        c_code = str(item.get("code", "UNKNOWN"))
                        b_finding_counts[c_code] += 1
                except Exception:
                    pass

            daily_metrics.append(
                DailyAnalyticsBucket(
                    date=date_str,
                    evaluation_count=b_count,
                    average_score=b_avg_score,
                    risk_counts=b_risk_counts,
                    total_findings=sum(b_finding_counts.values()),
                    finding_counts=dict(b_finding_counts),
                )
            )

        # Construct Ranked Finding Distribution
        finding_distribution: list[FindingFrequency] = []
        for code, count in sorted(global_finding_counts.items(), key=lambda x: x[1], reverse=True):
            finding_distribution.append(
                FindingFrequency(
                    code=code,
                    count=count,
                    severity=global_finding_severities.get(code, "MEDIUM"),
                    description=FINDING_DESCRIPTIONS.get(code, f"Finding rule {code}"),
                )
            )

        return AnalyticsTrendsResponse(
            time_window_days=days,
            total_evaluations=total_count,
            average_score=average_score,
            score_trend_direction=score_trend_direction,
            pass_rate=pass_rate,
            risk_distribution=risk_distribution,
            domain_averages=domain_averages,
            finding_distribution=finding_distribution,
            daily_metrics=daily_metrics,
        )
