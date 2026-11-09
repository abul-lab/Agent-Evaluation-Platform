"""Service layer for evaluation governance and policy profile management."""

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, col, select

from app.db.entities import EvaluationRecord, PolicyRecord
from app.evaluators.base import FindingSeverity
from app.schemas.notification_api import NotificationEventType
from app.schemas.policy_api import (
    GovernanceVerdict,
    PolicyAuditResponse,
    PolicyCreateRequest,
    PolicyResponse,
    PolicyRules,
    PolicyUpdateRequest,
    PolicyViolation,
)
from app.scorecard.score_models import Scorecard
from app.services.notification_service import NotificationEvent, NotificationService
from app.services.workspace_service import WorkspaceService


class PolicyService:
    """Manages persistent governance policies and audits evaluation outcomes against release criteria."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _to_response(self, record: PolicyRecord) -> PolicyResponse:
        """Map PolicyRecord SQL entity to PolicyResponse schema."""
        rules = PolicyRules.model_validate_json(record.rules_json)
        return PolicyResponse(
            policy_id=record.policy_id,
            name=record.name,
            description=record.description,
            is_active=record.is_active,
            is_default=record.is_default,
            rules=rules,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def list_policies(self, active_only: bool = False) -> list[PolicyResponse]:
        """List stored governance policy profiles."""
        statement = select(PolicyRecord).order_by(
            col(PolicyRecord.is_default).desc(),
            col(PolicyRecord.created_at).desc(),
        )
        if active_only:
            statement = statement.where(col(PolicyRecord.is_active).is_(True))
        records = self.session.exec(statement).all()
        return [self._to_response(rec) for rec in records]

    def get_policy(self, policy_id: UUID) -> PolicyResponse | None:
        """Fetch a specific governance policy profile by UUID."""
        record = self.session.get(PolicyRecord, policy_id)
        if not record:
            return None
        return self._to_response(record)

    def get_active_default_policy(self) -> PolicyResponse:
        """Fetch the platform default governance policy, auto-seeding if not yet initialized."""
        statement = select(PolicyRecord).where(
            col(PolicyRecord.is_default).is_(True),
            col(PolicyRecord.is_active).is_(True),
        )
        record = self.session.exec(statement).first()
        if record:
            return self._to_response(record)

        # Seed default platform policy if absent
        default_rules = PolicyRules()
        seed_record = PolicyRecord(
            name="Standard Platform Gate",
            description="Default release governance policy enforcing baseline quality and zero critical findings.",
            is_active=True,
            is_default=True,
            rules_json=default_rules.model_dump_json(),
        )
        self.session.add(seed_record)
        self.session.commit()
        self.session.refresh(seed_record)
        return self._to_response(seed_record)

    def create_policy(self, request: PolicyCreateRequest) -> PolicyResponse:
        """Create and persist a new governance policy profile."""
        if request.is_default:
            # Unset any existing default policy
            existing_defaults = self.session.exec(
                select(PolicyRecord).where(col(PolicyRecord.is_default).is_(True))
            ).all()
            for rec in existing_defaults:
                rec.is_default = False
                self.session.add(rec)

        now = datetime.now(UTC)
        record = PolicyRecord(
            name=request.name,
            description=request.description,
            is_active=request.is_active,
            is_default=request.is_default,
            rules_json=request.rules.model_dump_json(),
            created_at=now,
            updated_at=now,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return self._to_response(record)

    def update_policy(self, policy_id: UUID, request: PolicyUpdateRequest) -> PolicyResponse | None:
        """Update an existing governance policy profile."""
        record = self.session.get(PolicyRecord, policy_id)
        if not record:
            return None

        if request.is_default:
            existing_defaults = self.session.exec(
                select(PolicyRecord).where(
                    col(PolicyRecord.is_default).is_(True),
                    PolicyRecord.policy_id != policy_id,
                )
            ).all()
            for existing in existing_defaults:
                existing.is_default = False
                self.session.add(existing)

        if request.name is not None:
            record.name = request.name
        if request.description is not None:
            record.description = request.description
        if request.is_active is not None:
            record.is_active = request.is_active
        if request.is_default is not None:
            record.is_default = request.is_default
        if request.rules is not None:
            record.rules_json = request.rules.model_dump_json()

        record.updated_at = datetime.now(UTC)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return self._to_response(record)

    def delete_policy(self, policy_id: UUID) -> bool:
        """Delete a non-default governance policy profile."""
        record = self.session.get(PolicyRecord, policy_id)
        if not record:
            return False
        if record.is_default:
            raise ValueError("Cannot delete the default platform governance policy.")
        self.session.delete(record)
        self.session.commit()
        return True

    def audit_evaluation(
        self,
        policy_id: UUID,
        evaluation_id: UUID,
    ) -> PolicyAuditResponse | None:
        """Execute a formal governance audit on an evaluation record using the specified policy."""
        policy_record = self.session.get(PolicyRecord, policy_id)
        eval_record = self.session.get(EvaluationRecord, evaluation_id)

        if not policy_record or not eval_record:
            return None

        rules = PolicyRules.model_validate_json(policy_record.rules_json)
        scorecard = Scorecard.model_validate_json(eval_record.scorecard_json)

        violations: list[PolicyViolation] = []

        # 1. Minimum Overall Score Check
        if scorecard.overall_score < rules.min_overall_score:
            violations.append(
                PolicyViolation(
                    rule_name="MIN_OVERALL_SCORE_BREACH",
                    severity="HIGH",
                    message=(
                        f"Overall score {scorecard.overall_score:.1f} is below mandatory "
                        f"policy floor of {rules.min_overall_score:.1f}."
                    ),
                    actual_value=scorecard.overall_score,
                    expected_threshold=rules.min_overall_score,
                )
            )

        # 2. Minimum Domain Scores Check
        for domain, min_score in rules.min_domain_scores.items():
            domain_score = getattr(scorecard, domain, None)
            if domain_score and domain_score.score < min_score:
                sev = "CRITICAL" if domain == "safety" else "HIGH"
                violations.append(
                    PolicyViolation(
                        rule_name=f"DOMAIN_SCORE_FLOOR_{domain.upper()}",
                        severity=sev,
                        message=(
                            f"Domain '{domain}' score {domain_score.score:.1f} is below mandatory "
                            f"policy floor of {min_score:.1f}."
                        ),
                        actual_value=domain_score.score,
                        expected_threshold=min_score,
                    )
                )

        # 3. Disallowed Risk Tiers Check
        if eval_record.risk_classification in rules.disallowed_risk_tiers:
            violations.append(
                PolicyViolation(
                    rule_name="DISALLOWED_RISK_TIER",
                    severity="CRITICAL",
                    message=(
                        f"Evaluation risk classification '{eval_record.risk_classification}' "
                        f"is strictly prohibited by governance policy."
                    ),
                    actual_value=eval_record.risk_classification,
                    expected_threshold=f"NOT IN {rules.disallowed_risk_tiers}",
                )
            )

        # 4. Prohibited Finding Codes Check
        for finding in scorecard.findings:
            if finding.code in rules.prohibited_finding_codes:
                violations.append(
                    PolicyViolation(
                        rule_name="PROHIBITED_FINDING_CODE",
                        severity="CRITICAL",
                        message=(
                            f"Prohibited finding code '{finding.code}' detected: {finding.message}"
                        ),
                        actual_value=finding.code,
                        expected_threshold="PROHIBITED",
                    )
                )

        # 5. Finding Counts Severity Checks
        critical_findings = [
            f for f in scorecard.findings if f.severity == FindingSeverity.CRITICAL
        ]
        high_findings = [f for f in scorecard.findings if f.severity == FindingSeverity.HIGH]

        if len(critical_findings) > rules.max_critical_findings:
            violations.append(
                PolicyViolation(
                    rule_name="EXCESSIVE_CRITICAL_FINDINGS",
                    severity="CRITICAL",
                    message=(
                        f"Observed {len(critical_findings)} CRITICAL findings "
                        f"(max permitted: {rules.max_critical_findings})."
                    ),
                    actual_value=len(critical_findings),
                    expected_threshold=rules.max_critical_findings,
                )
            )

        if len(high_findings) > rules.max_high_findings:
            violations.append(
                PolicyViolation(
                    rule_name="EXCESSIVE_HIGH_FINDINGS",
                    severity="HIGH",
                    message=(
                        f"Observed {len(high_findings)} HIGH findings "
                        f"(max permitted: {rules.max_high_findings})."
                    ),
                    actual_value=len(high_findings),
                    expected_threshold=rules.max_high_findings,
                )
            )

        # 6. Semantic Evaluation Requirement
        if rules.require_semantic_evaluation and not eval_record.semantic_json:
            violations.append(
                PolicyViolation(
                    rule_name="MISSING_SEMANTIC_EVALUATION",
                    severity="MEDIUM",
                    message="Governance policy requires a completed semantic evaluation run.",
                    actual_value=None,
                    expected_threshold="REQUIRED",
                )
            )

        # Compute Verdict
        critical_count = sum(1 for v in violations if v.severity == "CRITICAL")
        high_count = sum(1 for v in violations if v.severity == "HIGH")

        if critical_count > 0:
            verdict = GovernanceVerdict.REJECTED
            passed = False
        elif high_count > 0 or len(violations) > 0:
            verdict = GovernanceVerdict.FLAGGED_FOR_REVIEW
            passed = False
        else:
            verdict = GovernanceVerdict.APPROVED
            passed = True

        # Dispatch governance alerting notifications
        try:
            ws_service = WorkspaceService(self.session)
            default_ws = ws_service.get_default_workspace()
            notif_service = NotificationService(self.session)

            if verdict == GovernanceVerdict.REJECTED:
                first_reason = (
                    violations[0].message if violations else "Policy evaluation criteria breached"
                )
                notif_service.dispatch_event(
                    default_ws.workspace_id,
                    NotificationEvent(
                        event_type=NotificationEventType.POLICY_REJECTED,
                        workspace_id=default_ws.workspace_id,
                        workspace_name=default_ws.name,
                        severity="CRITICAL",
                        title=f"Evaluation Rejected by Policy: {policy_record.name}",
                        reason=first_reason,
                        risk_tier=eval_record.risk_classification,
                        evaluation_id=str(eval_record.evaluation_id),
                        trace_id=str(eval_record.trace_id),
                        policy_name=policy_record.name,
                        details={"verdict": verdict.value, "violations_count": len(violations)},
                        link=f"http://localhost:3000/evaluations/{eval_record.evaluation_id}",
                    ),
                )
            elif verdict == GovernanceVerdict.APPROVED:
                notif_service.dispatch_event(
                    default_ws.workspace_id,
                    NotificationEvent(
                        event_type=NotificationEventType.POLICY_APPROVED,
                        workspace_id=default_ws.workspace_id,
                        workspace_name=default_ws.name,
                        severity="APPROVED",
                        title=f"Evaluation Approved by Policy: {policy_record.name}",
                        reason="All release gate rules satisfied",
                        risk_tier=eval_record.risk_classification,
                        evaluation_id=str(eval_record.evaluation_id),
                        trace_id=str(eval_record.trace_id),
                        policy_name=policy_record.name,
                        details={"verdict": verdict.value},
                        link=f"http://localhost:3000/evaluations/{eval_record.evaluation_id}",
                    ),
                )
        except Exception:
            pass

        return PolicyAuditResponse(
            policy_id=policy_record.policy_id,
            policy_name=policy_record.name,
            evaluation_id=eval_record.evaluation_id,
            verdict=verdict,
            passed=passed,
            violations=violations,
            violations_count=len(violations),
            critical_violations_count=critical_count,
            overall_score=eval_record.overall_score,
            risk_classification=eval_record.risk_classification,
            audited_at=datetime.now(UTC),
        )
