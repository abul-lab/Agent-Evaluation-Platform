#!/usr/bin/env bash
# ==============================================================================
# Agent Evaluation Platform (AEP) — cURL API Walkthrough
# ==============================================================================
set -euo pipefail

BASE_URL="${AEP_BASE_URL:-http://localhost:8000}"

# Set AEP_API_KEY when the backend requires authentication (production or anonymous access disabled).
AUTH_ARGS=()
if [[ -n "${AEP_API_KEY:-}" ]]; then
  AUTH_ARGS=(-H "Authorization: Bearer ${AEP_API_KEY}")
fi

echo "======================================================================"
echo "Connecting to Agent Evaluation Platform at: ${BASE_URL}"
echo "======================================================================"

# 1. System Health & Module Readiness
echo -e "\n[1/5] Checking System Health & Version..."
curl -s "${AUTH_ARGS[@]}" "${BASE_URL}/health" | jq .
curl -s "${AUTH_ARGS[@]}" "${BASE_URL}/version" | jq .

# 2. Validate Trace Schema (Dry Run)
echo -e "\n[2/5] Validating Trace Schema against CATS (Dry Run)..."
curl -s -X POST "${AUTH_ARGS[@]}" "${BASE_URL}/api/v1/traces/validate" \
  -H "Content-Type: application/json" \
  -d @fixtures/clean_success_trace.json | jq .

# 3. Upload & Ingest Trace
echo -e "\n[3/5] Uploading and Ingesting Trace..."
UPLOAD_RES=$(curl -s -X POST "${AUTH_ARGS[@]}" "${BASE_URL}/api/v1/traces/upload" \
  -H "Content-Type: application/json" \
  -d @fixtures/clean_success_trace.json)
echo "${UPLOAD_RES}" | jq .
TRACE_ID=$(echo "${UPLOAD_RES}" | jq -r .trace_id)

# 4. Run Deterministic Evaluation
echo -e "\n[4/5] Executing Evaluation for Trace ID: ${TRACE_ID}..."
EVAL_RES=$(curl -s -X POST "${AUTH_ARGS[@]}" "${BASE_URL}/api/v1/evaluations/run" \
  -H "Content-Type: application/json" \
  -d "{\"trace_id\": \"${TRACE_ID}\"}")
echo "${EVAL_RES}" | jq .
EVAL_ID=$(echo "${EVAL_RES}" | jq -r .evaluation_id)

# 5. Audit Against Active Governance Policy
echo -e "\n[5/5] Auditing Evaluation ${EVAL_ID} Against Release Policy..."
POLICY_ID=$(curl -s "${AUTH_ARGS[@]}" "${BASE_URL}/api/v1/policies/active" | jq -r .policy_id)
curl -s -X POST "${AUTH_ARGS[@]}" "${BASE_URL}/api/v1/policies/${POLICY_ID}/audit/${EVAL_ID}" | jq .

echo -e "\n======================================================================"
echo "cURL Walkthrough Completed Successfully!"
echo "======================================================================"

