"""Service to populate a showcase demonstration workspace."""

import contextlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.db.entities import (
    APIKeyRecord,
    EvaluationRecord,
    NotificationChannelRecord,
    NotificationDeliveryRecord,
    PolicyRecord,
    TraceRecord,
    WorkspaceAuditLogRecord,
    WorkspaceMemberRecord,
    WorkspaceRecord,
)
from app.domain.models import CanonicalTrace
from app.otel.otel_parser import parse_otel_payload
from app.otel.otel_to_cats import translate_otel_trace_to_cats
from app.schemas.auth_api import ServiceAccountRole
from app.schemas.notification_api import NotificationChannelType, NotificationEventType
from app.schemas.policy_api import PolicyRules
from app.schemas.workspace_api import DemoSeedResponse
from app.services.auth_service import generate_api_key
from app.services.evaluation_service import EvaluationService
from app.services.policy_service import PolicyService
from app.services.trace_repository import TraceRepository

logger = logging.getLogger(__name__)


class DemoService:
    """Manages creation, reset, and seeding of the showcase demo workspace."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.trace_repo = TraceRepository(session)
        self.eval_service = EvaluationService(session)
        self.policy_service = PolicyService(session)

    def _resolve_fixtures_dir(self) -> Path:
        """Locate fixtures directory across local root and package contexts."""
        candidates = [
            Path("fixtures"),
            Path(__file__).resolve().parents[3] / "fixtures",
            Path(__file__).resolve().parents[2] / "fixtures",
        ]
        for p in candidates:
            if p.exists() and (p / "clean_success_trace.json").exists():
                return p
        raise FileNotFoundError("Fixtures directory not found in candidate paths.")

    def seed_demo_workspace(self) -> DemoSeedResponse:
        """Seed or refresh the showcase demo workspace with traces, scorecards, policies, and notifications."""
        slug = "demo-workspace"
        name = "Demonstration Workspace"
        description = (
            "Pre-configured agent evaluation workspace with representative benchmarks, "
            "evaluation scorecards, governance policies, and notification channels."
        )

        # 1. Fetch or create workspace
        ws = self.session.exec(select(WorkspaceRecord).where(WorkspaceRecord.slug == slug)).first()
        now = datetime.now(UTC)

        if not ws:
            ws = WorkspaceRecord(
                name=name,
                slug=slug,
                description=description,
                is_default=False,
                created_at=now,
                updated_at=now,
            )
            self.session.add(ws)
            self.session.commit()
            self.session.refresh(ws)

            # Add demo members with RFC 2606 standard mock identity
            member = WorkspaceMemberRecord(
                workspace_id=ws.workspace_id,
                user_email="admin@example.com",
                role="ADMIN",
                joined_at=now,
            )
            self.session.add(member)
            self.session.commit()
        else:
            # Clean up existing workspace records to prevent duplicate bloat upon re-seed
            ws_id = ws.workspace_id
            for deliv_rec in self.session.exec(
                select(NotificationDeliveryRecord).where(
                    NotificationDeliveryRecord.workspace_id == ws_id
                )
            ).all():
                self.session.delete(deliv_rec)
            for chan_rec in self.session.exec(
                select(NotificationChannelRecord).where(
                    NotificationChannelRecord.workspace_id == ws_id
                )
            ).all():
                self.session.delete(chan_rec)
            for key_rec in self.session.exec(
                select(APIKeyRecord).where(APIKeyRecord.workspace_id == ws_id)
            ).all():
                self.session.delete(key_rec)
            for eval_rec in self.session.exec(
                select(EvaluationRecord).where(EvaluationRecord.workspace_id == ws_id)
            ).all():
                self.session.delete(eval_rec)
            for trace_rec in self.session.exec(
                select(TraceRecord).where(TraceRecord.workspace_id == ws_id)
            ).all():
                self.session.delete(trace_rec)
            self.session.commit()

        fixtures_dir = self._resolve_fixtures_dir()
        traces_seeded = 0
        evaluations_seeded = 0
        created_eval_ids: list[UUID] = []

        # 2. Seed Golden CATS Fixtures
        golden_files = [
            "clean_success_trace.json",
            "loop_trace.json",
            "hallucinated_tool_trace.json",
            "retry_storm_trace.json",
            "budget_exceeded_trace.json",
            "secret_leak_trace.json",
        ]

        for g_file in golden_files:
            file_path = fixtures_dir / g_file
            if not file_path.exists():
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
                trace_model = CanonicalTrace.model_validate_json(content)
                rec = self.trace_repo.create_trace(
                    trace=trace_model,
                    filename=g_file,
                    workspace_id=ws.workspace_id,
                )
                traces_seeded += 1
                eval_record = self.eval_service.run_evaluation(rec.trace_id)
                if eval_record:
                    evaluations_seeded += 1
                    created_eval_ids.append(eval_record.evaluation_id)
            except Exception as e:
                logger.warning("Failed seeding golden trace %s: %s", g_file, e)

        # 3. Seed OpenTelemetry Framework Fixtures
        otel_dir = fixtures_dir / "otel"
        if otel_dir.exists():
            otel_files = [
                ("langgraph_trace.json", "langgraph"),
                ("crewai_trace.json", "crewai"),
                ("autogen_trace.json", "autogen"),
                ("llamaindex_trace.json", "llamaindex"),
                ("openai_agents_trace.json", "openai_agents"),
            ]
            for o_file, _fw_name in otel_files:
                f_path = otel_dir / o_file
                if not f_path.exists():
                    continue
                try:
                    payload = json.loads(f_path.read_text(encoding="utf-8"))
                    parsed_otel = parse_otel_payload(payload)
                    cats_trace = translate_otel_trace_to_cats(parsed_otel)
                    rec = self.trace_repo.create_trace(
                        trace=cats_trace,
                        filename=f"otel_{o_file}",
                        workspace_id=ws.workspace_id,
                    )
                    traces_seeded += 1
                    eval_record = self.eval_service.run_evaluation(rec.trace_id)
                    if eval_record:
                        evaluations_seeded += 1
                        created_eval_ids.append(eval_record.evaluation_id)
                except Exception as e:
                    logger.warning("Failed seeding OTEL trace %s: %s", o_file, e)

        # 4. Seed Governance Policies
        policies_seeded = 0
        policy_gate = self.session.exec(
            select(PolicyRecord).where(
                PolicyRecord.name == "Release Policy (Demo)",
            )
        ).first()

        if not policy_gate:
            rules_1 = PolicyRules(
                min_overall_score=80.0,
                disallowed_risk_tiers=["CRITICAL", "POOR"],
                prohibited_finding_codes=["SECRET_EXPOSURE", "CYCLE_DETECTED"],
            )
            policy_gate = PolicyRecord(
                name="Release Policy (Demo)",
                description="Showcase release policy enforcing score floor and zero critical findings.",
                is_active=True,
                is_default=True,
                rules_json=rules_1.model_dump_json(),
                created_at=now,
                updated_at=now,
            )
            self.session.add(policy_gate)
            self.session.commit()
            self.session.refresh(policy_gate)
            policies_seeded += 1

        policy_sec = self.session.exec(
            select(PolicyRecord).where(
                PolicyRecord.name == "Security & Secret Leak Floor (Demo)",
            )
        ).first()

        if not policy_sec:
            rules_2 = PolicyRules(
                min_overall_score=75.0,
                disallowed_risk_tiers=["CRITICAL"],
                prohibited_finding_codes=["SECRET_EXPOSURE"],
            )
            policy_sec = PolicyRecord(
                name="Security & Secret Leak Floor (Demo)",
                description="Strict security audit gate rejecting any credential leakage.",
                is_active=True,
                is_default=False,
                rules_json=rules_2.model_dump_json(),
                created_at=now,
                updated_at=now,
            )
            self.session.add(policy_sec)
            self.session.commit()
            self.session.refresh(policy_sec)
            policies_seeded += 1

        # Audit evaluations against policy
        if policy_gate and created_eval_ids:
            for eid in created_eval_ids[:4]:
                with contextlib.suppress(Exception):
                    self.policy_service.audit_evaluation(policy_gate.policy_id, eid)

        # 5. Seed Notification Channels & Deliveries (Mock test endpoints for demonstration)
        channels_seeded = 0
        chan_slack = NotificationChannelRecord(
            channel_id=uuid4(),
            workspace_id=ws.workspace_id,
            name="Slack #agent-ops-alerts",
            channel_type=NotificationChannelType.SLACK.value,
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/demo-slack-token",  # Mock webhook URL
            events_json=json.dumps(
                [
                    NotificationEventType.EVALUATION_COMPLETED.value,
                    NotificationEventType.POLICY_REJECTED.value,
                    NotificationEventType.SECRET_EXPOSURE.value,
                    NotificationEventType.CRITICAL_FINDING.value,
                ]
            ),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.session.add(chan_slack)

        chan_teams = NotificationChannelRecord(
            channel_id=uuid4(),
            workspace_id=ws.workspace_id,
            name="Teams AI Incident Gate",
            channel_type=NotificationChannelType.TEAMS.value,
            webhook_url="https://company.webhook.office.com/webhookb2/demo-teams-token",  # Mock webhook URL
            events_json=json.dumps(
                [
                    NotificationEventType.POLICY_REJECTED.value,
                    NotificationEventType.REGRESSION_DETECTED.value,
                ]
            ),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.session.add(chan_teams)
        self.session.commit()
        channels_seeded = 2

        # Seed sample delivery logs
        for ch in [chan_slack, chan_teams]:
            deliv = NotificationDeliveryRecord(
                delivery_id=uuid4(),
                channel_id=ch.channel_id,
                workspace_id=ws.workspace_id,
                event_type=NotificationEventType.POLICY_REJECTED.value,
                status="DELIVERED",
                http_status=200,
                error_message=None,
                payload_preview="Demo notification alert delivered successfully.",
                created_at=now,
            )
            self.session.add(deliv)

        # 6. Seed Demo API Key (Mock synthetic test key for demonstration)
        _raw_key, prefix, hashed = generate_api_key()
        api_key_rec = APIKeyRecord(
            workspace_id=ws.workspace_id,
            name="GitHub Actions CI Runner",
            hashed_key=hashed,
            key_prefix=prefix,
            role=ServiceAccountRole.ENGINEER.value,
            created_by="admin@example.com",
            created_at=now,
            is_active=True,
        )
        self.session.add(api_key_rec)

        # 7. Add Audit Log Entry
        audit = WorkspaceAuditLogRecord(
            workspace_id=ws.workspace_id,
            actor_email="system@example.com",
            action="WORKSPACE_DEMO_SEEDED",
            resource_type="WORKSPACE",
            resource_id=str(ws.workspace_id),
            details_json=json.dumps(
                {
                    "traces_seeded": traces_seeded,
                    "evaluations_seeded": evaluations_seeded,
                    "policies_seeded": policies_seeded,
                    "channels_seeded": channels_seeded,
                }
            ),
            created_at=now,
        )
        self.session.add(audit)
        self.session.commit()

        return DemoSeedResponse(
            workspace_id=ws.workspace_id,
            name=ws.name,
            slug=ws.slug,
            traces_seeded=traces_seeded,
            evaluations_seeded=evaluations_seeded,
            policies_seeded=policies_seeded,
            channels_seeded=channels_seeded,
            api_key_prefix=prefix,
            status="ready",
        )
