# Notifications & Alerting Dispatcher

## 1. Overview & Objectives

The **Notifications & Alerting Hub** provides event dispatching across communication channels—including **Microsoft Teams, Slack, and Generic Webhooks**—when AI evaluation, quality regression, security leakage, or governance gate events occur.

By integrating automated evaluations with team chat and monitoring endpoints, teams can:
- **Accelerate MTTR (Mean Time to Resolution)**: Instant alerts when an agent trace leaks credentials, triggers recursive tool cascades, or violates budget floors.
- **Automate Release Gating**: Notify platform engineers and compliance leads when an evaluation is approved or rejected by organizational release policies.
- **Maintain High Signal-to-Noise**: Channels can subscribe to specific subsets of events (e.g., Security Operations room receives only `SECRET_EXPOSURE` and `CRITICAL_FINDING`).
- **Delivery Tracking & Retries**: Built-in exponential backoff retries (3 attempts), 5.0s HTTP timeouts, and delivery diagnostics recorded in the audit trail.

---

## 2. Architecture & Event Pipeline

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           EVENT SOURCES                                │
  │                                                                        │
  │  EvaluationEngine   PolicyService   RegressionEngine   AuthService     │
  │   (Findings/Leaks)   (Gate Verdict)   (Metric Drift)   (Key Lifecycle) │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
                      ┌───────────────────────────────┐
                      │      NotificationService      │
                      │   - Workspace Scoping         │
                      │   - Event Type Filter Matrix  │
                      │   - Payload Formatters        │
                      └───────────────┬───────────────┘
                                      │
                ┌─────────────────────┼─────────────────────┐
                ▼                     ▼                     ▼
     ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
     │  Microsoft Teams   │ │   Slack Webhook    │ │  Generic Webhook   │
     │  (MessageCard)     │ │   (Block Kit)      │ │  (Structured JSON) │
     └──────────┬─────────┘ └─────────┬──────────┘ └─────────┬──────────┘
                │                     │                      │
                └─────────────────────┼──────────────────────┘
                                      │
                                      ▼
                      ┌───────────────────────────────┐
                      │   NotificationDeliveryRecord  │
                      │   - Status (DELIVERED/FAILED) │
                      │   - HTTP Status & Diagnostics │
                      │   - WorkspaceAuditLog Event   │
                      └───────────────────────────────┘
```

---

## 3. Supported Channels & Payload Formatting

### A. Microsoft Teams (MessageCard / Adaptive Card)
Formatted specifically for Microsoft Teams incoming webhooks:
- **Theme Color**: Dynamically mapped based on severity (`#DC2626` Red for CRITICAL, `#D97706` Amber for WARNING, `#16A34A` Green for APPROVED, `#2563EB` Blue for INFO).
- **Sections & Facts**: Formatted facts for Workspace, Event Type, Severity, Evaluation ID, Trace ID, and Policy Name.
- **Action Buttons**: Direct `OpenUri` button linking operators to the evaluation scorecard in the dashboard.

#### Teams Payload Structure:
```json
{
  "@type": "MessageCard",
  "@context": "https://schema.org/extensions",
  "summary": "Policy Rejected: Strict Production Floor",
  "themeColor": "DC2626",
  "title": "🚨 Policy Rejected: Strict Production Floor",
  "text": "Overall score 62.4 falls below required threshold of 80.0",
  "sections": [
    {
      "facts": [
        {"name": "Workspace", "value": "Customer Support Swarm"},
        {"name": "Event Type", "value": "POLICY_REJECTED"},
        {"name": "Severity", "value": "CRITICAL"},
        {"name": "Risk Classification", "value": "POOR"},
        {"name": "Evaluation ID", "value": "550e8400-e29b-41d4-a716-446655440000"}
      ]
    }
  ],
  "potentialAction": [
    {
      "@type": "OpenUri",
      "name": "View Evaluation Scorecard",
      "targets": [{"os": "default", "uri": "http://localhost:3000/evaluations/550e8400-e29b-41d4-a716-446655440000"}]
    }
  ]
}
```

### B. Slack (Block Kit)
Formatted with Slack Block Kit layout elements:
- **Header Block**: Bold title with event category emoji.
- **Section Block**: High-priority alert reason with markdown formatting.
- **Fields Grid**: Multi-column key-value pairs (Workspace, Severity, Evaluation ID, Trace ID).
- **Actions Block**: Direct button link to the evaluation details view.

#### Slack Payload Structure:
```json
{
  "text": "🚨 Policy Rejected: Strict Production Floor",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "🚨 Policy Rejected: Strict Production Floor"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Reason:* Overall score 62.4 falls below required threshold of 80.0"
      }
    },
    {
      "type": "section",
      "fields": [
        {"type": "mrkdwn", "text": "*Workspace:*\nCustomer Support Swarm"},
        {"type": "mrkdwn", "text": "*Event:*\n`POLICY_REJECTED`"},
        {"type": "mrkdwn", "text": "*Severity:*\n*CRITICAL*"},
        {"type": "mrkdwn", "text": "*Risk Tier:*\nPOOR"}
      ]
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "View in AEP"},
          "url": "http://localhost:3000/evaluations/550e8400-e29b-41d4-a716-446655440000",
          "style": "danger"
        }
      ]
    }
  ]
}
```

### C. Generic Outbound Webhook (JSON)
Delivers a standard JSON payload suitable for webhook listeners, PagerDuty, or custom consumers.event buses.

#### Generic Webhook Payload:
```json
{
  "event_type": "SECRET_EXPOSURE",
  "workspace_id": "11111111-1111-1111-1111-111111111111",
  "workspace_name": "Production Agents",
  "severity": "CRITICAL",
  "title": "Secret Exposure Detected",
  "reason": "AWS Secret Access Key pattern discovered in agent tool parameters",
  "risk_tier": "CRITICAL",
  "evaluation_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "999e8400-e29b-41d4-a716-446655440000",
  "policy_name": null,
  "details": {
    "finding_code": "SEC_001",
    "rule": "SECRET_EXPOSURE_PREVENTION"
  },
  "link": "http://localhost:3000/evaluations/550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-11-08T16:30:00Z"
}
```

---

## 4. Supported Event Triggers

| Event Trigger | Default Severity | Description / Dispatch Condition |
|---|:---:|---|
| `EVALUATION_COMPLETED` | `INFO` | Nominal completion of an agent trace evaluation scorecard. |
| `EVALUATION_FAILED` | `CRITICAL` | Evaluator or sandbox engine failure during execution. |
| `REGRESSION_DETECTED` | `WARNING` | Benchmark or baseline comparison breaches score drift or latency thresholds. |
| `POLICY_APPROVED` | `APPROVED` | Evaluation passed all gate conditions in active governance policy profile. |
| `POLICY_REJECTED` | `CRITICAL` | Evaluation violated mandatory score floors, risk tiers, or disallowed finding codes. |
| `SECRET_EXPOSURE` | `CRITICAL` | Evaluator detected raw credentials, API tokens, or secrets in step traces. |
| `CRITICAL_FINDING` | `CRITICAL` | Hard-gate findings (e.g., infinite loop lockups, severe budget exhaustion). |
| `API_KEY_CREATED` | `INFO` | A new service account API key was generated for CI/CD runners. |
| `API_KEY_REVOKED` | `WARNING` | An active service account API key was revoked by an administrator. |

---

## 5. REST API Reference

All notification endpoints are workspace-scoped under `/api/v1/workspaces/{workspace_id}/notifications`.

### 1. List Channels
```http
GET /api/v1/workspaces/{workspace_id}/notifications/channels
Authorization: Bearer <api_key> (RequireViewer)
```

### 2. Create Channel
```http
POST /api/v1/workspaces/{workspace_id}/notifications/channels
Authorization: Bearer <api_key> (RequireAdmin)
Content-Type: application/json

{
  "name": "SecOps Slack Alerts",
  "channel_type": "SLACK",
  "webhook_url": "https://hooks.slack.com/services/T00/B00/XXXXX",
  "events": [
    "SECRET_EXPOSURE",
    "CRITICAL_FINDING",
    "POLICY_REJECTED"
  ]
}
```

### 3. Update Channel
```http
PUT /api/v1/workspaces/{workspace_id}/notifications/channels/{channel_id}
Authorization: Bearer <api_key> (RequireAdmin)
Content-Type: application/json

{
  "name": "SecOps Slack Alerts (Updated)",
  "is_active": true,
  "events": ["SECRET_EXPOSURE"]
}
```

### 4. Delete Channel
```http
DELETE /api/v1/workspaces/{workspace_id}/notifications/channels/{channel_id}
Authorization: Bearer <api_key> (RequireAdmin)
```

### 5. Dispatch Immediate Test Alert
```http
POST /api/v1/workspaces/{workspace_id}/notifications/channels/{channel_id}/test
Authorization: Bearer <api_key> (RequireAdmin)
Content-Type: application/json

{
  "custom_message": "Ping from CI/CD pipeline smoke test"
}
```
*Returns:*
```json
{
  "status": "DELIVERED",
  "channel_id": "chan-1234",
  "channel_name": "SecOps Slack Alerts",
  "channel_type": "SLACK",
  "http_status": 200,
  "message": "Test alert dispatched to Slack"
}
```

### 6. Delivery History & Diagnostics
```http
GET /api/v1/workspaces/{workspace_id}/notifications/history?limit=50
Authorization: Bearer <api_key> (RequireViewer)
```
*Returns:*
```json
[
  {
    "delivery_id": "del-1234",
    "channel_id": "chan-1234",
    "workspace_id": "11111111-1111-1111-1111-111111111111",
    "event_type": "POLICY_REJECTED",
    "status": "DELIVERED",
    "http_status": 200,
    "error_message": null,
    "delivered_at": "2026-11-08T16:30:00Z",
    "created_at": "2026-11-08T16:30:00Z"
  }
]
```

---

## 6. Security & Credential Protection

- **Webhook URL Masking**: Webhook URLs contain secret tokens (e.g. `https://hooks.slack.com/services/T00/B00/X89...`). To prevent credential exposure, the API automatically masks the URL in all read responses:
  ```json
  "webhook_url_masked": "https://hooks.slack.com/services/****"
  ```
- **RBAC Enforcement**:
  - Creating, updating, deleting, or sending test alerts requires `ADMIN` role.
  - Viewing configured channels and delivery history is accessible to `VIEWER`, `ENGINEER`, and `ADMIN`.
- **Immutable Audit Logging**:
  - `notification_channel_created`
  - `notification_channel_updated`
  - `notification_channel_deleted`
  - `notification_test`
  - `notification_sent`
  - `notification_failed` (includes error diagnostics and HTTP status codes)

---

## 7. Reliability & Retry Policy

- **Connection Timeout**: Strict 5.0s HTTP timeout helps prevent outbound webhooks from blocking background evaluation loops.
- **Exponential Backoff**: Transient errors (e.g., HTTP 429 rate limits, 500/502/503 upstream gateway errors, connection timeouts) are retried up to **3 attempts** with exponential backoff (0.5s, 1.0s, 2.0s).
- **Delivery Logging**: Every dispatch attempt records a permanent row in `NotificationDeliveryRecord` tracking the HTTP status code and response body for rapid troubleshooting.

