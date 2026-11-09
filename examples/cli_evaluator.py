"""AEP Standalone CLI Evaluator — Instant local trace analysis without a server.

Usage:
    python examples/cli_evaluator.py path/to/trace.json
"""

import json
import sys
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.domain.models import CanonicalTrace
from app.scorecard.aggregator import ScorecardAggregator
from app.services.deterministic_evaluator import DeterministicEvaluationService


def evaluate_local_file(trace_file: str):
    path = Path(trace_file)
    if not path.exists():
        print(f"Error: Trace file '{trace_file}' not found.")
        sys.exit(1)

    print(f"\nAudit Target: {path.name}")
    print("=" * 65)

    with open(path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 1. Validate Schema
    try:
        trace = CanonicalTrace.model_validate(raw_data)
        print("✓ Schema Validation : PASSED (Conforms to CATS v1.0)")
        print(f"  Steps Count       : {len(trace.steps)}")
        print(f"  Workflow Status   : {trace.workflow.status}")
    except Exception as e:
        print(f"✗ Schema Validation : FAILED\n{e}")
        sys.exit(1)

    # 2. Run Deterministic Evaluators
    eval_service = DeterministicEvaluationService()
    eval_result = eval_service.evaluate_trace(trace)
    all_findings = eval_result.findings

    # 3. Synthesize Multi-Domain Scorecard
    scorecard = ScorecardAggregator.aggregate(eval_result)

    print("\nScorecard Overview:")
    print(f"  Composite Score   : {scorecard.overall_score:.1f} / 100.0 pts")
    print(f"  Risk Classification: {scorecard.risk_classification}")
    print(f"  Total Defect Findings: {len(all_findings)}")

    print("\nDomain Scores:")
    domains = [
        scorecard.task_quality,
        scorecard.tool_usage,
        scorecard.workflow_quality,
        scorecard.reliability,
        scorecard.safety,
        scorecard.cost,
        scorecard.efficiency,
    ]
    for d in domains:
        print(f"  - {d.name:<22}: {d.score:>5.1f} pts [{d.status}] ({d.findings_count} findings)")

    if all_findings:
        print("\nDefects Detected:")
        for idx, f in enumerate(all_findings, 1):
            print(f"  {idx}. [{f.severity}] {f.code}: {f.message}")
            if f.affected_steps:
                print(f"     Affected Steps: {f.affected_steps}")
    else:
        print("\n✓ No defects detected. Trace meets all deterministic quality standards.")

    print("=" * 65)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        default_fixture = str(
            Path(__file__).resolve().parent.parent / "fixtures" / "clean_success_trace.json"
        )
        print(f"No file supplied. Running evaluation against golden fixture:\n{default_fixture}")
        evaluate_local_file(default_fixture)
    else:
        evaluate_local_file(sys.argv[1])
