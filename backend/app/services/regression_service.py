"""Service layer for regression detection and quality gate policy evaluation."""

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session

from app.db.entities import EvaluationRecord
from app.evaluators.base import FindingSeverity
from app.schemas.notification_api import NotificationEventType
from app.schemas.regression_api import (
    RegressionPolicy,
    RegressionReport,
    RegressionStatus,
    RegressionViolation,
)
from app.scorecard.score_models import Scorecard
from app.services.notification_service import NotificationEvent, NotificationService
from app.services.workspace_service import WorkspaceService

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


class RegressionService:
    """Evaluates candidate evaluations against baselines using configurable quality gate policies."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def check_regression(
        self,
        base_id: UUID,
        candidate_id: UUID,
        policy: RegressionPolicy | None = None,
    ) -> RegressionReport | None:
        """Execute a deterministic regression audit between baseline and candidate evaluations."""
        base_record = self.session.get(EvaluationRecord, base_id)
        candidate_record = self.session.get(EvaluationRecord, candidate_id)

        if not base_record or not candidate_record:
            return None

        applied_policy = policy or RegressionPolicy()
        base_scorecard = Scorecard.model_validate_json(base_record.scorecard_json)
        cand_scorecard = Scorecard.model_validate_json(candidate_record.scorecard_json)

        violations: list[RegressionViolation] = []

        # 1. Overall Score Delta Check
        score_delta = round(cand_scorecard.overall_score - base_scorecard.overall_score, 2)
        if score_delta < -applied_policy.max_score_drop:
            violations.append(
                RegressionViolation(
                    rule="OVERALL_SCORE_DROP",
                    severity=FindingSeverity.HIGH,
                    message=(
                        f"Overall score dropped by {abs(score_delta):.1f} points "
                        f"(threshold: -{applied_policy.max_score_drop:.1f})"
                    ),
                    baseline_value=base_scorecard.overall_score,
                    candidate_value=cand_scorecard.overall_score,
                    threshold=-applied_policy.max_score_drop,
                )
            )

        # 2. Domain Score Drops
        for domain in EVALUATION_DOMAINS:
            base_domain = getattr(base_scorecard, domain, None)
            cand_domain = getattr(cand_scorecard, domain, None)
            if base_domain and cand_domain:
                dom_delta = round(cand_domain.score - base_domain.score, 2)
                if dom_delta < -applied_policy.max_domain_drop:
                    severity = (
                        FindingSeverity.HIGH if domain == "safety" else FindingSeverity.MEDIUM
                    )
                    violations.append(
                        RegressionViolation(
                            rule=f"DOMAIN_SCORE_DROP_{domain.upper()}",
                            severity=severity,
                            message=(
                                f"Domain '{domain}' score dropped by {abs(dom_delta):.1f} points "
                                f"(threshold: -{applied_policy.max_domain_drop:.1f})"
                            ),
                            baseline_value=base_domain.score,
                            candidate_value=cand_domain.score,
                            threshold=-applied_policy.max_domain_drop,
                        )
                    )

        # 3. Risk Tier Escalation Check
        base_tier_idx = RISK_TIER_ORDER.get(base_record.risk_classification, 0)
        cand_tier_idx = RISK_TIER_ORDER.get(candidate_record.risk_classification, 0)
        risk_transition = (
            f"{base_record.risk_classification} -> {candidate_record.risk_classification}"
        )

        if applied_policy.fail_on_risk_escalation and cand_tier_idx < base_tier_idx:
            tier_severity = (
                FindingSeverity.CRITICAL
                if candidate_record.risk_classification in ("CRITICAL", "POOR")
                else FindingSeverity.HIGH
            )
            violations.append(
                RegressionViolation(
                    rule="RISK_ESCALATION",
                    severity=tier_severity,
                    message=(
                        f"Risk tier escalated to worse level: "
                        f"{base_record.risk_classification} -> {candidate_record.risk_classification}"
                    ),
                    baseline_value=base_record.risk_classification,
                    candidate_value=candidate_record.risk_classification,
                    threshold="NO_ESCALATION",
                )
            )

        # 4. Finding Signatures and Critical Findings
        base_signatures = {
            (f.code, tuple(sorted(f.affected_steps))) for f in base_scorecard.findings
        }

        for finding in cand_scorecard.findings:
            cand_sig = (finding.code, tuple(sorted(finding.affected_steps)))
            is_new = cand_sig not in base_signatures

            # 4a. Check prohibited codes
            if finding.code in applied_policy.prohibited_finding_codes:
                violations.append(
                    RegressionViolation(
                        rule="PROHIBITED_FINDING_CODE",
                        severity=FindingSeverity.CRITICAL,
                        message=(
                            f"Prohibited finding code '{finding.code}' detected: {finding.message}"
                        ),
                        baseline_value=None,
                        candidate_value=finding.code,
                        threshold="PROHIBITED",
                    )
                )

            # 4b. Check new HIGH or CRITICAL findings
            if (
                is_new
                and applied_policy.fail_on_new_critical_findings
                and finding.severity in (FindingSeverity.HIGH, FindingSeverity.CRITICAL)
            ):
                violations.append(
                    RegressionViolation(
                        rule="NEW_CRITICAL_FINDING",
                        severity=finding.severity,
                        message=(
                            f"New {finding.severity.value} finding '{finding.code}' introduced: "
                            f"{finding.message}"
                        ),
                        baseline_value=None,
                        candidate_value=finding.code,
                        threshold="NO_NEW_CRITICAL_FINDINGS",
                    )
                )

        # 5. Absolute Overall Score Floor
        if cand_scorecard.overall_score < applied_policy.min_overall_score:
            violations.append(
                RegressionViolation(
                    rule="MIN_OVERALL_SCORE_BREACH",
                    severity=FindingSeverity.HIGH,
                    message=(
                        f"Candidate overall score {cand_scorecard.overall_score:.1f} "
                        f"falls below minimum requirement of {applied_policy.min_overall_score:.1f}"
                    ),
                    baseline_value=base_scorecard.overall_score,
                    candidate_value=cand_scorecard.overall_score,
                    threshold=applied_policy.min_overall_score,
                )
            )

        # 6. Minimum Safety Score Floor
        cand_safety = getattr(cand_scorecard, "safety", None)
        if cand_safety and cand_safety.score < applied_policy.min_safety_score:
            base_safety = getattr(base_scorecard, "safety", None)
            violations.append(
                RegressionViolation(
                    rule="MIN_SAFETY_SCORE_BREACH",
                    severity=FindingSeverity.CRITICAL,
                    message=(
                        f"Candidate safety score {cand_safety.score:.1f} "
                        f"falls below required safety floor of {applied_policy.min_safety_score:.1f}"
                    ),
                    baseline_value=base_safety.score if base_safety else None,
                    candidate_value=cand_safety.score,
                    threshold=applied_policy.min_safety_score,
                )
            )

        # Calculate Status & Verdict
        critical_count = sum(
            1 for v in violations if v.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH)
        )

        if critical_count > 0:
            status = RegressionStatus.REGRESSED
            is_regression = True
        elif len(violations) > 0:
            status = RegressionStatus.WARNING
            is_regression = False
        else:
            status = RegressionStatus.PASSED
            is_regression = False

        # Dispatch regression alert if regressed
        if is_regression:
            try:
                ws_service = WorkspaceService(self.session)
                default_ws = ws_service.get_default_workspace()
                notif_service = NotificationService(self.session)
                first_msg = violations[0].message if violations else "Quality regressions detected"
                notif_service.dispatch_event(
                    default_ws.workspace_id,
                    NotificationEvent(
                        event_type=NotificationEventType.REGRESSION_DETECTED,
                        workspace_id=default_ws.workspace_id,
                        workspace_name=default_ws.name,
                        severity="WARNING",
                        title="Quality Regression Detected",
                        reason=first_msg,
                        risk_tier=candidate_record.risk_classification,
                        evaluation_id=str(candidate_id),
                        details={
                            "overall_score_delta": score_delta,
                            "violations_count": len(violations),
                            "baseline_id": str(base_id),
                        },
                        link=f"http://localhost:3000/evaluations/{candidate_id}",
                    ),
                )
            except Exception:
                pass

        return RegressionReport(
            status=status,
            is_regression=is_regression,
            baseline_evaluation_id=base_id,
            candidate_evaluation_id=candidate_id,
            policy_applied=applied_policy,
            overall_score_delta=score_delta,
            risk_transition=risk_transition,
            violations=violations,
            violations_count=len(violations),
            critical_violations_count=critical_count,
            evaluated_at=datetime.now(UTC),
        )
