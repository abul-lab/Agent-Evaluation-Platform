# Workspace-Scoped API Authentication & Service Accounts

## 1. Overview & Business Goal

To enable continuous integration and automated evaluation pipelines—such as **GitHub Actions, Azure DevOps, GitLab CI, Jenkins, ArgoCD**, and headless ingestion scripts—the Agent Evaluation Platform (AEP) provides workspace-scoped API keys and programmatic service accounts.

This authorization layer introduces:
- **Workspace-Scoped Tokens**: Each key is bound to one workspace.
- **Service Account Roles (`ADMIN`, `ENGINEER`, `VIEWER`)**: Role-based access control (see Section 2).
- **Zero Plaintext Key Storage**: Only the SHA-256 digest of each key is stored. Plaintext keys are shown once, at creation.
- **Configurable Expiration**: Keys can expire after N days (1-3650), or never expire.
- **Audit Logging**: `api_key_created`, `api_key_revoked`, `api_key_used` and `service_account_created` events are written to the workspace audit log.
- **Authentication is required by default.** Anonymous callers receive HTTP 401 on every endpoint except the health and version probes. The only anonymous access is an explicit development opt-in (see Section 2.1). Anonymous callers never receive ADMIN or ENGINEER rights.

---

## 2. Service Account Roles & Permission Matrix

```
       ┌────────────────────────┐
       │         ADMIN          │  Key creation & revocation, workspace and member
       └───────────┬────────────┘  management, governance policy changes, notification channels
                   │
                   ▼
       ┌────────────────────────┐
       │        ENGINEER        │  Ingest traces (REST and OTLP), run evaluations and
       └───────────┬────────────┘  benchmarks, run policy audits and regression checks
                   │
                   ▼
       ┌────────────────────────┐
       │         VIEWER         │  Read-only access to traces, evaluations, scorecards,
       └────────────────────────┘  benchmarks, analytics, policies and workspace data
```

### 2.1. Anonymous access (development only)

| `ENVIRONMENT` | `ALLOW_ANONYMOUS_VIEWER` | Anonymous caller on a read endpoint | Anonymous caller on a write endpoint |
|---|---|---|---|
| `production` (default), `staging`, `test` | any | HTTP 401 | HTTP 401 |
| `development` | `false` (default) | HTTP 401 | HTTP 401 |
| `development` | `true` | Allowed, as read-only **VIEWER** | HTTP 401 |

Anonymous callers never receive ADMIN or ENGINEER rights, in any configuration.

### 2.2. Endpoint requirements

"401" means no credential or an anonymous caller. "403" means an authenticated key whose role is too low.

| Endpoint scope | Anonymous | VIEWER key | ENGINEER key | ADMIN key |
|---|:---:|:---:|:---:|:---:|
| `GET` reads: `/traces`, `/evaluations/*`, `/benchmarks/summary`, `/analytics/*`, `/policies`, `/policies/*`, `/workspaces`, `/workspaces/*`, `/workspaces/*/audit-logs`, `/workspaces/*/notifications/*` | 401 (dev opt-in: ✓) | ✓ | ✓ | ✓ |
| `GET /api/v1/auth/verify` | 401 (dev opt-in: ✓) | ✓ | ✓ | ✓ |
| `POST /api/v1/traces/validate`, `POST /api/v1/otel/translate` | 401 | 403 | ✓ | ✓ |
| `POST /api/v1/traces/upload`, `POST /api/v1/evaluations/run` | 401 | 403 | ✓ | ✓ |
| `POST /api/v1/otel/ingest`, `POST /api/v1/otel/collector`, `POST /v1/traces` (OTLP) | 401 | 403 | ✓ | ✓ |
| `POST /api/v1/benchmarks/compare`, `POST /api/v1/regressions/check` | 401 | 403 | ✓ | ✓ |
| `POST /api/v1/policies/{id}/audit/{evaluation_id}` | 401 | 403 | ✓ | ✓ |
| `GET /api/v1/auth/api-keys` | 401 | 403 | ✓ | ✓ |
| `POST /api/v1/auth/api-keys`, `DELETE /api/v1/auth/api-keys/{id}` | 401 | 403 | 403 | ✓ |
| `POST /api/v1/policies`, `PUT` / `DELETE /api/v1/policies/{id}` | 401 | 403 | 403 | ✓ |
| `POST /api/v1/workspaces`, `PUT` / `DELETE /api/v1/workspaces/{id}`, member add/remove, `POST /api/v1/workspaces/demo/seed` | 401 | 403 | 403 | ✓ |
| Notification channel create / update / delete / test | 401 | 403 | 403 | ✓ |

Unauthenticated public endpoints: `GET /health`, `GET /api/v1/health`, `GET /version`, `GET /api/v1/version`, `GET /api/v1/system/info`.

---

## 3. Token Format & Cryptographic Security

Each generated API key follows this format:
```
aep_<40 lowercase hex characters>
```

- **Prefix**: `aep_` lets secret scanners (for example GitHub secret scanning) recognise exposed keys. Register a custom pattern if you want stronger detection.
- **Entropy**: 40 hex characters provide 160 bits of randomness (`secrets.token_hex(20)`).
- **Storage**: The database stores `hashed_key = SHA-256(raw_key)` and `key_prefix` (the first 12 characters followed by `...`, for example `aep_9f83a1b2c3...`). The plaintext key is never stored.
- **Revocation**: `DELETE /api/v1/auth/api-keys/{key_id}` takes effect immediately; later use of the key returns HTTP 401.
- **Expiry**: Expired keys return HTTP 401 at authentication time.

### 3.1. Bootstrapping the first ADMIN key

Because authentication is required by default, the first ADMIN key is created on the server:

```bash
cd backend
DATABASE_URL="sqlite:///./agent_eval.db" python scripts/create_admin_key.py --name "bootstrap-admin"
```

The raw key is printed once. Store it in your secret manager. Use it to create the keys for CI jobs and engineers, then keep the admin key offline.

---

## 4. API Endpoints Reference

### 4.1. Verify Credential (`GET /api/v1/auth/verify`)
Returns the caller's principal: whether it is authenticated, its workspace, role and key identifier. Anonymous callers receive HTTP 401 unless development anonymous access is enabled.

**Request:**
```bash
curl -H "Authorization: Bearer aep_9f83a1b2c3d4e5f6..." \
  http://localhost:8000/api/v1/auth/verify
```

**Response (`200 OK`):**
```json
{
  "is_authenticated": true,
  "key_id": "8a32d184-e1d2-4011-872e-d09618a80293",
  "workspace_id": "11111111-1111-1111-1111-111111111111",
  "role": "ENGINEER",
  "name": "Production Ingestion Runner",
  "is_service_account": true
}
```

### 4.2. Create Secret API Key (`POST /api/v1/auth/api-keys`)
Generates a new programmatic key scoped to a target workspace. *(Requires ADMIN)*

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer <admin_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "11111111-1111-1111-1111-111111111111",
    "name": "Production Ingestion Runner",
    "role": "ENGINEER",
    "expires_in_days": 90
  }'
```

**Response (`201 Created`):**
```json
{
  "key_id": "8a32d184-e1d2-4011-872e-d09618a80293",
  "workspace_id": "11111111-1111-1111-1111-111111111111",
  "name": "Production Ingestion Runner",
  "key_prefix": "aep_9f83a1b2c3...",
  "role": "ENGINEER",
  "raw_key": "aep_9f83a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2",
  "created_at": "2026-11-08T18:45:00Z",
  "expires_at": "2027-02-06T18:45:00Z"
}
```
> [!WARNING]
> The `raw_key` attribute is returned **strictly once** in this response payload.

### 4.3. List API Keys (`GET /api/v1/auth/api-keys`)
Lists non-sensitive metadata for all active and revoked keys in a workspace. *(Requires ADMIN)*

**Response (`200 OK`):**
```json
[
  {
    "key_id": "8a32d184-e1d2-4011-872e-d09618a80293",
    "workspace_id": "11111111-1111-1111-1111-111111111111",
    "name": "Production Ingestion Runner",
    "key_prefix": "aep_9f83a1b2c3...",
    "role": "ENGINEER",
    "created_by": "admin@example.com",
    "created_at": "2026-11-08T18:45:00Z",
    "expires_at": "2027-02-06T18:45:00Z",
    "last_used_at": "2026-11-08T19:02:14Z",
    "is_active": true
  }
]
```

### 4.4. Revoke API Key (`DELETE /api/v1/auth/api-keys/{key_id}`)
Immediately marks a key inactive and records an audit revocation entry. *(Requires ADMIN)*

**Response (`200 OK`):**
```json
{
  "key_id": "8a32d184-e1d2-4011-872e-d09618a80293",
  "revoked": true
}
```

---

## 5. CI/CD Integration Examples

### 5.1. GitHub Actions Workflow
```yaml
name: Agent Evaluation & Quality Gate

on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  evaluate-agent:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Execute Agent Integration Tests & Produce OTEL / CATS Trace
        run: |
          python run_agent_test.py --export-trace trace.json

      - name: Ingest Trace into AEP
        env:
          AEP_API_KEY: ${{ secrets.AEP_CI_API_KEY }}
          AEP_HOST: "https://aep.example.com"
        run: |
          RESPONSE=$(curl -s -f -X POST "$AEP_HOST/api/v1/traces/upload" \
            -H "Authorization: Bearer $AEP_API_KEY" \
            -H "Content-Type: application/json" \
            -d @trace.json)
          
          TRACE_ID=$(echo "$RESPONSE" | jq -r '.trace_id')
          echo "Ingested Trace ID: $TRACE_ID"

          EVAL_RES=$(curl -s -f -X POST "$AEP_HOST/api/v1/evaluations/run" \
            -H "Authorization: Bearer $AEP_API_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"trace_id\": \"$TRACE_ID\"}")

          SCORE=$(echo "$EVAL_RES" | jq -r '.scorecard.overall_score')
          STATUS=$(echo "$EVAL_RES" | jq -r '.risk_tier')
          echo "Evaluation Score: $SCORE | Risk Tier: $STATUS"

          if [ "$STATUS" = "CRITICAL" ] || [ "$STATUS" = "POOR" ]; then
            echo "Quality gate failed!"
            exit 1
          fi
```

### 5.2. GitLab CI / Jenkins Shell Snippet
```bash
#!/usr/bin/env bash
set -euo pipefail

# Ingest trace via OpenTelemetry endpoint using workspace-scoped key
curl -X POST "${AEP_ENDPOINT}/api/v1/otel/ingest" \
  -H "Authorization: Bearer ${AEP_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @"otel_spans.json"
```

