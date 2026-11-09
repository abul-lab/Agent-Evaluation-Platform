"""Unit tests for PolicyService governance policy lifecycle and evaluation audits."""

import json
from pathlib import Path

import pytest
from sqlmodel import Session

from app.domain.models import CanonicalTrace
from app.schemas.policy_api import (
    GovernanceVerdict,
    PolicyCreateRequest,
    PolicyRules,
    PolicyUpdateRequest,
)
from app.services.evaluation_service import EvaluationService
from app.services.policy_service import PolicyService
from app.services.trace_repository import TraceRepository

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_fixture_json(filename: str) -> dict[str, object]:
    """Helper to load fixture json."""
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def test_get_active_default_policy_seeds_when_empty(db_session: Session) -> None:
    """Verify that get_active_default_policy auto-seeds the platform default policy."""
    service = PolicyService(session=db_session)
    default_policy = service.get_active_default_policy()

    assert default_policy is not None
    assert default_policy.name == "Standard Platform Gate"
    assert default_policy.is_default is True
    assert default_policy.is_active is True
    assert default_policy.rules.min_overall_score == 80.0


def test_create_and_list_policies(db_session: Session) -> None:
    """Verify creating custom policies and listing them."""
    service = PolicyService(session=db_session)

    # Auto-seed default first
    service.get_active_default_policy()

    custom_rules = PolicyRules(
        min_overall_score=95.0,
        disallowed_risk_tiers=["CRITICAL", "POOR", "WATCH"],
    )
    req = PolicyCreateRequest(
        name="Strict Release Gate",
        description="High-assurance production safety gate",
        is_active=True,
        is_default=False,
        rules=custom_rules,
    )
    created = service.create_policy(req)
    assert created.name == "Strict Release Gate"
    assert created.rules.min_overall_score == 95.0

    all_policies = service.list_policies()
    assert len(all_policies) >= 2

    fetched = service.get_policy(created.policy_id)
    assert fetched is not None
    assert fetched.name == "Strict Release Gate"


def test_update_and_delete_policy(db_session: Session) -> None:
    """Verify updating fields and deleting non-default policy."""
    service = PolicyService(session=db_session)
    default_pol = service.get_active_default_policy()

    # Attempt to delete default policy should raise ValueError
    with pytest.raises(ValueError, match="Cannot delete the default"):
        service.delete_policy(default_pol.policy_id)

    # Create temporary policy
    temp = service.create_policy(
        PolicyCreateRequest(
            name="Temporary Staging Policy",
            description="Staging test",
            is_active=False,
            is_default=False,
        )
    )

    # Update policy to make it active
    updated = service.update_policy(
        temp.policy_id,
        PolicyUpdateRequest(name="Active Staging Policy", is_active=True),
    )
    assert updated is not None
    assert updated.name == "Active Staging Policy"
    assert updated.is_active is True

    # Delete custom policy
    assert service.delete_policy(temp.policy_id) is True
    assert service.get_policy(temp.policy_id) is None


def test_audit_evaluation_clean_trace_approved(db_session: Session) -> None:
    """Verify that a clean evaluation passes governance audit with APPROVED status."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)
    policy_service = PolicyService(session=db_session)

    policy = policy_service.get_active_default_policy()

    clean_trace = CanonicalTrace.model_validate(load_fixture_json("clean_success_trace.json"))
    trace_rec = trace_repo.create_trace(clean_trace)
    evaluation = eval_service.run_evaluation(trace_rec.trace_id)
    assert evaluation is not None

    audit_result = policy_service.audit_evaluation(
        policy_id=policy.policy_id,
        evaluation_id=evaluation.evaluation_id,
    )
    assert audit_result is not None
    assert audit_result.verdict == GovernanceVerdict.APPROVED
    assert audit_result.passed is True
    assert audit_result.violations_count == 0


def test_audit_evaluation_loop_trace_rejected(db_session: Session) -> None:
    """Verify that a trace with execution cycles is REJECTED by governance policy."""
    trace_repo = TraceRepository(db_session)
    eval_service = EvaluationService(session=db_session)
    policy_service = PolicyService(session=db_session)

    policy = policy_service.get_active_default_policy()

    loop_trace = CanonicalTrace.model_validate(load_fixture_json("loop_trace.json"))
    trace_rec = trace_repo.create_trace(loop_trace)
    evaluation = eval_service.run_evaluation(trace_rec.trace_id)
    assert evaluation is not None

    audit_result = policy_service.audit_evaluation(
        policy_id=policy.policy_id,
        evaluation_id=evaluation.evaluation_id,
    )
    assert audit_result is not None
    assert audit_result.verdict == GovernanceVerdict.REJECTED
    assert audit_result.passed is False
    assert audit_result.critical_violations_count > 0

    violation_rules = {v.rule_name for v in audit_result.violations}
    assert "PROHIBITED_FINDING_CODE" in violation_rules
