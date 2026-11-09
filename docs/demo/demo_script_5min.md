# Agent Evaluation Platform (AEP) — 5-Minute Technical Overview Script

**Scope:** Walkthrough of universal ingestion, deterministic evaluation, and CI/CD release gating.  
**Objective:** Walk through how AEP provides an evaluation and governance gatekeeper for autonomous AI agents to validate behavior before deployment.

---

## ⏱️ Walkthrough Sequence

### 0:00 – 0:45 | Telemetry and Agent Failure Modes
* **Visual:** While running the application locally, open `http://localhost:3000/architecture` in your browser.
* **Technical Discussion:**
  * "When multi-step agent systems execute tools and iterative loops, operational failure modes arise that traditional HTTP monitoring does not model."
  * "An agent that loops continuously or calls an invalid tool interface can still return HTTP 200 responses from upstream model providers while consuming tokens without making progress."
  * "The Agent Evaluation Platform provides deterministic evaluation and automated release gating for autonomous agent workflows."

---

### 0:45 – 1:30 | Ingestion: OpenTelemetry Without Custom SDKs
* **Visual:** Scroll to the OTEL Translation Flow diagram or click the **OTEL Translation Flow** tab on `/architecture`.
* **Technical Discussion:**
  * "A design priority was zero client SDK lock-in."
  * "AEP exposes a standard OpenTelemetry Collector endpoint supporting OTLP over HTTP and gRPC."
  * "Agents running on LangGraph, CrewAI, AutoGen, LlamaIndex, or OpenAI SDK emit standard telemetry. The ingestion pipeline authenticates workspace API keys, checks rate limits, and reconstructs the span hierarchy into the Canonical Agent Trace Schema (CATS)."

---

### 1:30 – 2:45 | Deterministic Evaluation & Domain Scoring
* **Visual:** Navigate to the top navbar and click **✨ Load Demo Data**.
* **Action:** Review loaded traces. Navigate to **Traces** (`/traces`).
* **Technical Discussion:**
  * "The platform populates a set of sample agent traces reflecting common operational scenarios."
  * "Traces are audited across 7 parallel deterministic domains:
    1. Loop Detection (state machine hashing & oscillation detection)
    2. Tool Fidelity (schema validation against tool manifests)
    3. Safety & Policy (regex secret detection and prompt injection filters)
    4. Context & Budget (token growth rates and context limits)
    5. Latency Cascades (retry sequences and timeout analysis)
    6. Goal Completion (terminal state outcome checks)
    7. Cost Accounting (token pricing models across provider tiers)"
  * "Evaluation runs in approximately 2–5 milliseconds per trace, enabling execution within synchronous CI/CD checks."

---

### 2:45 – 3:45 | Automated CI/CD Governance & Policy Gating
* **Visual:** Navigate to **Policies** (`/policies`).
* **Technical Discussion:**
  * "A weighted average score can mask critical violations: an agent with a high composite score might still leak credentials in a single step."
  * "Governance Policies allow teams to define environment-specific score floors alongside configurable hard gates."
  * "If a hard gate is tripped—such as a detected secret leak or loop lockup—the policy engine produces a **BLOCKED** verdict."
  * "Integrated into CI/CD pipelines, an exit code `1` prevents unverified changes from deploying to staging or production."

---

### 3:45 – 4:30 | Notifications & Webhook Dispatch (Teams, Slack, Webhooks)
* **Visual:** Navigate to **Workspaces** (`/workspaces`), select the workspace, and view **Settings → Notifications**.
* **Technical Discussion:**
  * "When policy gates fail, AEP dispatches alerts out-of-band."
  * "AEP includes an asynchronous Notification Dispatcher supporting Microsoft Teams Adaptive Cards, Slack Block Kit, and generic JSON webhooks over HTTPS."
  * "Credential exposure is a CRITICAL finding. The finding stores only a redacted sample of the secret, and it blocks the release."
  * "Delivery logs record HTTP status codes and roundtrip latency for auditability."

---

### 4:30 – 5:00 | Architecture & Platform Summary
* **Visual:** Navigate to `/about` (Platform Metrics).
* **Technical Discussion:**
  * "Platform verification summary:
    * 368 automated backend tests with 92% code coverage
    * 50 frontend component tests with strict TypeScript
    * Throughput depends on hardware; measure it locally with `backend/scripts/benchmark_performance.py`
    * Validated ingestion across multiple agent frameworks"
  * "This concludes the technical walkthrough."

