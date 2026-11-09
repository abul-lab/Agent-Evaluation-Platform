"""Repository for persisting and querying ingested traces."""

from collections.abc import Sequence
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.db.entities import TraceRecord
from app.domain.models import CanonicalTrace


class TraceRepository:
    """Repository handling database operations for TraceRecord entities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_trace(
        self,
        trace: CanonicalTrace,
        filename: str | None = None,
        workspace_id: UUID | None = None,
    ) -> TraceRecord:
        """Persist a canonical trace into the database."""
        record = TraceRecord(
            trace_id=uuid4(),
            workspace_id=workspace_id,
            filename=filename,
            framework=trace.workflow.framework.value,
            workflow_status=trace.workflow.status.value,
            step_count=len(trace.steps),
            raw_trace=trace.model_dump_json(),
            schema_version="1.0.0",
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_trace(self, trace_id: UUID) -> TraceRecord | None:
        """Retrieve a trace record by its unique trace identifier."""
        statement = select(TraceRecord).where(TraceRecord.trace_id == trace_id)
        return self.session.exec(statement).first()

    def list_traces(
        self,
        limit: int = 100,
        offset: int = 0,
        workspace_id: UUID | None = None,
    ) -> Sequence[TraceRecord]:
        """List stored trace records ordered by creation date descending."""
        statement = select(TraceRecord)
        if workspace_id is not None:
            statement = statement.where(TraceRecord.workspace_id == workspace_id)
        statement = (
            statement.order_by(TraceRecord.created_at.desc())  # type: ignore[attr-defined]
            .offset(offset)
            .limit(limit)
        )
        return self.session.exec(statement).all()
