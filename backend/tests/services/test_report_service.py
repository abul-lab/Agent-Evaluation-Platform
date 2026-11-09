"""Unit tests for ReportService."""

import csv
import io
from pathlib import Path
from uuid import uuid4

from sqlmodel import Session

from app.domain.models import CanonicalTrace
from app.services.evaluation_service import EvaluationService
from app.services.report_service import ReportService
from app.services.trace_repository import TraceRepository

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


def load_canonical_trace(filename: str) -> CanonicalTrace:
    """Helper to load a fixture JSON file as CanonicalTrace."""
    fixture_path = FIXTURES_DIR / filename
    with open(fixture_path, encoding="utf-8") as f:
        return CanonicalTrace.model_validate_json(f.read())


def test_generate_json_report_success(db_session: Session) -> None:
    """Verify JSON report generation contains summary, scorecard, findings, and metadata."""
    trace_repo = TraceRepository(db_session)
    trace = load_canonical_trace("loop_trace.json")
    trace_rec = trace_repo.create_trace(trace=trace)

    eval_svc = EvaluationService(db_session)
    eval_rec = eval_svc.run_evaluation(trace_rec.trace_id)
    assert eval_rec is not None

    rep_svc = ReportService(db_session)
    report = rep_svc.generate_json_report(eval_rec.evaluation_id)

    assert report is not None
    assert "summary" in report
    assert report["summary"]["evaluation_id"] == str(eval_rec.evaluation_id)
    assert report["summary"]["trace_id"] == str(trace_rec.trace_id)
    assert report["summary"]["status"] == "COMPLETED"

    assert "scorecard" in report
    assert "overall_score" in report["scorecard"]
    assert "workflow_quality" in report["scorecard"]

    assert "findings" in report
    assert isinstance(report["findings"], list)
    assert len(report["findings"]) >= 1
    assert any(f["code"] == "CYCLE_DETECTED" for f in report["findings"])

    assert "metadata" in report
    assert report["metadata"]["schema_version"] == "1.0.0"


def test_generate_json_report_not_found(db_session: Session) -> None:
    """Verify JSON report returns None when evaluation ID does not exist."""
    rep_svc = ReportService(db_session)
    assert rep_svc.generate_json_report(uuid4()) is None


def test_generate_markdown_report_success(db_session: Session) -> None:
    """Verify Markdown report generation contains all required sections."""
    trace_repo = TraceRepository(db_session)
    trace = load_canonical_trace("hallucinated_tool_trace.json")
    trace_rec = trace_repo.create_trace(trace=trace)

    eval_svc = EvaluationService(db_session)
    eval_rec = eval_svc.run_evaluation(trace_rec.trace_id)
    assert eval_rec is not None

    rep_svc = ReportService(db_session)
    md = rep_svc.generate_markdown_report(eval_rec.evaluation_id)

    assert md is not None
    assert "# Evaluation Report" in md
    assert "## Summary" in md
    assert "## Risk Classification" in md
    assert "## Scorecard" in md
    assert "## Findings" in md
    assert "## Metadata" in md
    assert "HALLUCINATED_TOOL" in md
    assert "| Tool Usage |" in md


def test_generate_markdown_report_clean_trace_no_findings(db_session: Session) -> None:
    """Verify Markdown report renders clean message when no findings exist."""
    trace_repo = TraceRepository(db_session)
    trace = load_canonical_trace("clean_success_trace.json")
    trace_rec = trace_repo.create_trace(trace=trace)

    eval_svc = EvaluationService(db_session)
    eval_rec = eval_svc.run_evaluation(trace_rec.trace_id)
    assert eval_rec is not None

    rep_svc = ReportService(db_session)
    md = rep_svc.generate_markdown_report(eval_rec.evaluation_id)

    assert md is not None
    assert "No findings detected" in md


def test_generate_markdown_report_not_found(db_session: Session) -> None:
    """Verify Markdown report returns None for nonexistent evaluation ID."""
    rep_svc = ReportService(db_session)
    assert rep_svc.generate_markdown_report(uuid4()) is None


def test_generate_csv_report_success(db_session: Session) -> None:
    """Verify CSV report generation produces correct headers and rows."""
    trace_repo = TraceRepository(db_session)
    trace = load_canonical_trace("retry_storm_trace.json")
    trace_rec = trace_repo.create_trace(trace=trace)

    eval_svc = EvaluationService(db_session)
    eval_rec = eval_svc.run_evaluation(trace_rec.trace_id)
    assert eval_rec is not None

    rep_svc = ReportService(db_session)
    csv_str = rep_svc.generate_csv_report(eval_rec.evaluation_id)

    assert csv_str is not None
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)

    assert reader.fieldnames == [
        "evaluation_id",
        "finding_code",
        "severity",
        "message",
        "affected_steps",
        "workflow_id",
    ]
    assert len(rows) >= 1
    codes = [r["finding_code"] for r in rows]
    assert "RETRY_STORM" in codes
    assert rows[0]["evaluation_id"] == str(eval_rec.evaluation_id)


def test_generate_csv_report_empty_findings(db_session: Session) -> None:
    """Verify CSV report produces header row and zero data rows when findings are empty."""
    trace_repo = TraceRepository(db_session)
    trace = load_canonical_trace("clean_success_trace.json")
    trace_rec = trace_repo.create_trace(trace=trace)

    eval_svc = EvaluationService(db_session)
    eval_rec = eval_svc.run_evaluation(trace_rec.trace_id)
    assert eval_rec is not None

    rep_svc = ReportService(db_session)
    csv_str = rep_svc.generate_csv_report(eval_rec.evaluation_id)

    assert csv_str is not None
    reader = csv.DictReader(io.StringIO(csv_str))
    rows = list(reader)
    assert len(rows) == 0


def test_generate_csv_report_not_found(db_session: Session) -> None:
    """Verify CSV report returns None for nonexistent evaluation ID."""
    rep_svc = ReportService(db_session)
    assert rep_svc.generate_csv_report(uuid4()) is None
