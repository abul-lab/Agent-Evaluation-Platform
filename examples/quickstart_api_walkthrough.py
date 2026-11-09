"""AEP Python SDK Walkthrough — Programmatic Trace Evaluation & Governance Gating.

Demonstrates:
1. Verifying system health and active modules
2. Loading and validating a Canonical Agent Trace Schema (CATS) trace
3. Uploading trace to the AEP persistence repository
4. Executing multi-domain deterministic evaluation
5. Retrieving scorecards, risk tiers, and findings
6. Auditing candidate evaluation against governance release policies
"""

import json
import os
import sys
import requests

AEP_API_KEY = os.getenv("AEP_API_KEY")
# Required when the backend runs with ENVIRONMENT=production (or anonymous access is disabled).
AUTH_HEADERS = {"Authorization": f"Bearer {AEP_API_KEY}"} if AEP_API_KEY else {}

BASE_URL = os.getenv("AEP_BASE_URL", "http://localhost:8000")


def print_step(title: str):
    print(f"\n{'='*70}\n[STEP] {title}\n{'='*70}")


def main():
    print(f"Connecting to Agent Evaluation Platform at: {BASE_URL}")

    # 1. System Health & Version Verification
    print_step("1. Checking System Health & Version")
    health_res = requests.get(f"{BASE_URL}/health", headers=AUTH_HEADERS)
    version_res = requests.get(f"{BASE_URL}/version", headers=AUTH_HEADERS)
    print(f"Health Response : {health_res.status_code} -> {health_res.json()}")
    print(f"Version Response: {version_res.status_code} -> {version_res.json()}")
    assert health_res.status_code == 200, "Backend API is not healthy"

    # 2. Upload Reference Trace
    print_step("2. Uploading Candidate Trace to Repository")
    fixture_path = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "clean_success_trace.json"
    )
    with open(fixture_path, "r", encoding="utf-8") as f:
        trace_payload = json.load(f)

    # Validate trace schema first (dry run)
    val_res = requests.post(f"{BASE_URL}/api/v1/traces/validate", headers=AUTH_HEADERS, json=trace_payload)
    print(f"Schema Validation -> Valid: {val_res.json().get('valid')}, Steps: {val_res.json().get('step_count')}")

    # Upload and persist
    upload_res = requests.post(f"{BASE_URL}/api/v1/traces/upload", headers=AUTH_HEADERS, json=trace_payload)
    upload_data = upload_res.json()
    trace_id = upload_data["trace_id"]
    print(f"Trace Ingested Successfully! ID: {trace_id}")

    # 3. Execute Deterministic Evaluation
    print_step("3. Executing Deterministic Evaluation Engine")
    eval_res = requests.post(f"{BASE_URL}/api/v1/evaluations/run", headers=AUTH_HEADERS, json={"trace_id": trace_id}
    )
    eval_data = eval_res.json()
    eval_id = eval_data["evaluation_id"]
    print(f"Evaluation Completed! ID: {eval_id}")
    print(f"  Overall Score       : {eval_data['overall_score']} / 100.0 pts")
    print(f"  Risk Classification : {eval_data['risk_classification']}")
    print(f"  Total Defect Findings: {eval_data['finding_count']}")

    # 4. Fetch Multi-Domain Scorecard
    print_step("4. Retrieving 7-Domain Scorecard Breakdown")
    scorecard_res = requests.get(f"{BASE_URL}/api/v1/evaluations/{eval_id}/scorecard", headers=AUTH_HEADERS)
    scorecard = scorecard_res.json()
    domain_keys = [
        "task_quality",
        "tool_usage",
        "workflow_quality",
        "reliability",
        "safety",
        "cost",
        "efficiency",
    ]
    for key in domain_keys:
        dom = scorecard.get(key, {})
        print(f"  - {dom.get('name', key.replace('_', ' ').title()):<22}: {dom.get('score', 0.0):>5.1f} pts ({dom.get('status', 'N/A')})")

    # 5. Audit Against Active Release Policy
    print_step("5. Auditing Run Against Release Policy")
    active_pol_res = requests.get(f"{BASE_URL}/api/v1/policies/active", headers=AUTH_HEADERS)
    policy_id = active_pol_res.json()["policy_id"]
    policy_name = active_pol_res.json()["name"]

    audit_res = requests.post(f"{BASE_URL}/api/v1/policies/{policy_id}/audit/{eval_id}", headers=AUTH_HEADERS)
    audit_data = audit_res.json()

    print(f"Policy Profile Applied: '{policy_name}' (ID: {policy_id})")
    print(f"  Verdict             : {audit_data['verdict']}")
    print(f"  Violations Count    : {audit_data['violations_count']}")
    print(f"  Critical Breaches   : {audit_data['critical_violations_count']}")

    if audit_data["verdict"] == "APPROVED":
        print("\n>>> RELEASE CLEARED: Candidate agent run satisfies all policy criteria! <<<")
    else:
        print("\n>>> RELEASE BLOCKED: Quality or safety policy violations detected! <<<")


if __name__ == "__main__":
    main()
