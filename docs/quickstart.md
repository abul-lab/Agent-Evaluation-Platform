# Quickstart Guide — Agent Evaluation Platform (AEP)

Get started evaluating agent execution traces in less than 5 minutes.

---

## 1. Quick Verification via Docker

The quickest way to run the full stack is via Docker Compose:

```bash
git clone https://github.com/abul-lab/Agent-Evaluation-Platform.git
cd Agent-Evaluation-Platform
docker compose up -d
```

- **Frontend UI**: When running the application locally: [http://localhost:3000](http://localhost:3000)
- **API Documentation**: When running the local development environment: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)

---

## 2. Quick Verification via Native Python & Node.js

### Step 1: Start Backend API
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Start API server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 2: Start Frontend Dashboard
```bash
cd frontend
npm ci
npm run dev
```

---

## 3. End-to-End Workflow in 3 API Calls

All API calls need an API key. Create an ADMIN or ENGINEER key with `backend/scripts/create_admin_key.py` (see [DEPLOYMENT.md](DEPLOYMENT.md)) and export it:

```bash
export AEP_API_KEY="aep_..."
```

### Step A: Ingest a Reference Trace
```bash
curl -X POST "http://localhost:8000/api/v1/traces/upload" \
  -H "Authorization: Bearer $AEP_API_KEY" \
  -H "Content-Type: application/json" \
  -d @fixtures/clean_success_trace.json
```
Response:
```json
{
  "trace_id": "11111111-1111-4111-8111-111111111111",
  "stored": true,
  "step_count": 4,
  "workflow_status": "SUCCESS"
}
```

### Step B: Run Deterministic Evaluation
```bash
curl -X POST "http://localhost:8000/api/v1/evaluations/run" \
  -H "Authorization: Bearer $AEP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"trace_id": "11111111-1111-4111-8111-111111111111"}'
```
Response:
```json
{
  "evaluation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "finding_count": 0,
  "overall_score": 94.2,
  "risk_classification": "EXCELLENT"
}
```

### Step C: Audit Against Governance Policy
```bash
# Get active policy ID
POLICY_ID=$(curl -s -H "Authorization: Bearer $AEP_API_KEY" "http://localhost:8000/api/v1/policies/active" | jq -r '.policy_id')

# Audit evaluation run
curl -X POST -H "Authorization: Bearer $AEP_API_KEY" "http://localhost:8000/api/v1/policies/${POLICY_ID}/audit/550e8400-e29b-41d4-a716-446655440000"
```
Response:
```json
{
  "verdict": "APPROVED",
  "overall_score": 94.2,
  "risk_classification": "EXCELLENT",
  "violations_count": 0,
  "critical_violations_count": 0,
  "violations": []
}
```

---

## 4. Using the Web Dashboard

1. While running the application locally, open `http://localhost:3000` in your browser.
2. Inspect the **Overview** page for global throughput volume and recent ingested traces.
3. Click on any trace ID or use the **Traces** tab to audit runs.
4. On the **Evaluation Detail** page:
   - Review the 7-domain scorecard and risk tier.
   - Click **View Execution Graph** to view the interactive React Flow DAG.
   - Click **Export JSON**, **Export Markdown**, or **Export CSV** to download auditable reports.
5. Visit **Benchmarks** to compare two runs head-to-head or review the dataset leaderboard.
6. Visit **Policies** to test release gating criteria in the interactive audit console.
