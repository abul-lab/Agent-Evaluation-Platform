"""Service layer generating portable reports (JSON, Markdown, CSV) from evaluation records."""

import csv
import io
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.db.entities import EvaluationRecord

CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value: Any) -> Any:
    """Neutralize spreadsheet formula injection by prefixing risky text cells with a quote."""
    if isinstance(value, str) and value.startswith(CSV_FORMULA_PREFIXES):
        return "'" + value
    return value


class ReportService:
    """Coordinates generation of portable export reports for evaluation runs."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _get_record(self, evaluation_id: UUID) -> EvaluationRecord | None:
        return self.session.get(EvaluationRecord, evaluation_id)

    def generate_json_report(self, evaluation_id: UUID) -> dict[str, Any] | None:
        """Generate a complete structured JSON export report for an evaluation run."""
        record = self._get_record(evaluation_id)
        if not record:
            return None

        scorecard: dict[str, Any] = json.loads(record.scorecard_json)
        findings: list[dict[str, Any]] = json.loads(record.findings_json)

        return {
            "summary": {
                "evaluation_id": str(record.evaluation_id),
                "trace_id": str(record.trace_id),
                "status": record.status,
                "started_at": record.started_at.isoformat(),
                "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                "finding_count": record.finding_count,
                "overall_score": record.overall_score,
                "risk_classification": record.risk_classification,
            },
            "scorecard": scorecard,
            "risk_classification": record.risk_classification,
            "findings": findings,
            "metadata": {
                "schema_version": "1.0.0",
                "exported_at": datetime.now(UTC).isoformat(),
            },
        }

    def generate_markdown_report(self, evaluation_id: UUID) -> str | None:
        """Generate a human-readable Markdown evaluation report."""
        record = self._get_record(evaluation_id)
        if not record:
            return None

        scorecard: dict[str, Any] = json.loads(record.scorecard_json)
        findings: list[dict[str, Any]] = json.loads(record.findings_json)
        started_iso = record.started_at.isoformat()
        completed_iso = record.completed_at.isoformat() if record.completed_at else "In Progress"
        exported_iso = datetime.now(UTC).isoformat()

        domains = [
            ("Task Quality", scorecard.get("task_quality", {})),
            ("Tool Usage", scorecard.get("tool_usage", {})),
            ("Workflow Quality", scorecard.get("workflow_quality", {})),
            ("Reliability", scorecard.get("reliability", {})),
            ("Safety", scorecard.get("safety", {})),
            ("Cost", scorecard.get("cost", {})),
            ("Efficiency", scorecard.get("efficiency", {})),
        ]

        scorecard_rows = "\n".join(
            f"| {name} | {d.get('score', 0):.1f} | {d.get('status', 'UNKNOWN')} | {d.get('findings_count', 0)} |"
            for name, d in domains
        )

        if findings:
            findings_rows = "\n".join(
                f"| {f.get('severity', 'UNKNOWN')} | `{f.get('code', 'UNKNOWN')}` | {f.get('message', '').replace('|', '-')} | `{f.get('affected_steps', [])}` |"
                for f in findings
            )
            findings_section = f"""| Severity | Code | Message | Affected Steps |
| :--- | :--- | :--- | :--- |
{findings_rows}"""
        else:
            findings_section = "_No findings detected. Evaluation passed without defects._"

        return f"""# Evaluation Report

## Summary
- **Evaluation ID:** `{record.evaluation_id}`
- **Trace ID:** `{record.trace_id}`
- **Status:** `{record.status}`
- **Started At:** `{started_iso}`
- **Completed At:** `{completed_iso}`
- **Total Findings:** `{record.finding_count}`
- **Overall Score:** `{record.overall_score:.2f} / 100`

## Risk Classification
**Tier:** `{record.risk_classification}`

## Scorecard
| Domain | Score | Status | Findings |
| :--- | :---: | :---: | :---: |
{scorecard_rows}

## Findings
{findings_section}

## Metadata
- **Schema Version:** `1.0.0`
- **Exported At:** `{exported_iso}`
"""

    def generate_csv_report(self, evaluation_id: UUID) -> str | None:
        """Generate a flattened CSV export of all findings for an evaluation run."""
        record = self._get_record(evaluation_id)
        if not record:
            return None

        findings: list[dict[str, Any]] = json.loads(record.findings_json)

        output = io.StringIO()
        fieldnames = [
            "evaluation_id",
            "finding_code",
            "severity",
            "message",
            "affected_steps",
            "workflow_id",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for f in findings:
            steps_str = json.dumps(f.get("affected_steps", []))
            writer.writerow(
                {
                    "evaluation_id": csv_safe(str(record.evaluation_id)),
                    "finding_code": csv_safe(f.get("code", "")),
                    "severity": csv_safe(f.get("severity", "")),
                    "message": csv_safe(f.get("message", "")),
                    "affected_steps": csv_safe(steps_str),
                    "workflow_id": csv_safe(f.get("workflow_id", "")),
                }
            )

        return output.getvalue()
