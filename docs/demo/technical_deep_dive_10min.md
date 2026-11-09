# Agent Evaluation Platform (AEP) — 10-Minute Technical Walkthrough

**Scope:** Code-level walkthrough of ingestion architecture, translation graph mechanics, deterministic scoring logic, and governance enforcement.  
**Objective:** Walk through AEP's ingestion pipeline, translation graph mechanics, deterministic scoring logic, and governance enforcement.

---

## System Flow & Architecture Walkthrough

### 0:00 – 1:30 | Agent Failure Modes & Evaluation Approaches
* **Context Setting:**
  * When multi-step agent systems transition from single prompts to state machines (LangGraph, CrewAI, AutoGen), failure modes become multidimensional.
  * Standard APM captures HTTP spans and service latencies, but does not model agent step trajectories or tool selection fidelity.
  * Prompt-based evaluation using LLMs introduces operational challenges:
    1. **Sampling Variance:** Temperature and model updates introduce scoring drift into test runs.
    2. **Latency:** Multi-second roundtrips per evaluation increase CI/CD pipeline duration.
    3. **Operational Cost:** Token inference costs scale with the volume of evaluation runs.
* **Design Rationale:** Core trajectory evaluation benefits from deterministic execution, predictable latency, and reproducible scoring.

---

### 1:30 – 3:30 | OpenTelemetry Ingestion & Semantic Graph Assembly
* **Code Reference:** `backend/app/otel/collector_receiver.py` & `backend/app/otel/translator.py`
* **Technical Details:**
  * **Intake Endpoint:** `POST /api/v1/otel/collector` accepts OTLP v1/traces payloads over HTTP/JSON or streaming gRPC.
  * **Workspace API Key Authentication:** Validates incoming `Authorization: Bearer` (or `x-api-key`) headers using SHA-256 digests against the `APIKeyRecord` table with role checking (ENGINEER or ADMIN required).
  * **Sliding Window Rate Limiter:** Protects the ingestion gate against trace flooding with a memory-resident 60-second sliding window per API key.
  * **Span Graph Reconstruction:**
    * OTLP batches arrive out of order. The `OtelCatsTranslator` constructs an in-memory graph keyed by `span_id`.
    * Spans with `SpanKind.INTERNAL` are mapped to discrete agent reasoning steps.
    * Spans with `SpanKind.CLIENT` are classified as tool executions or model calls.
    * GenAI semantic attributes (`gen_ai.prompt`, `gen_ai.completion`, `gen_ai.usage.prompt_tokens`) are parsed and mapped to CATS fields.
    * Monotonic microsecond timestamps order step indexes sequentially.

---

### 3:30 – 6:00 | The 7 Parallel Deterministic Evaluator Domains
* **Code Reference:** `backend/app/evaluators/`
* **Core Domains:**
  1. **Loop Detection (`loop_detector.py`):**
     * Detects cyclic repetition in step parameters, tool invocations, and responses.
     * Uses cycle-finding algorithms to detect:
       - Exact repetitions (same tool called with identical inputs 3+ consecutive times).
       - Alternating state oscillations (Tool A → Tool B → Tool A → Tool B).
       - Semantic loop markers.
  2. **Tool Fidelity (`tool_fidelity.py`):**
     * Checks if invoked tools exist in the workspace's declared tool manifest.
     * Validates input JSON arguments against registered JSON Schema definitions.
     * Flags runtime syntax exceptions, unparsed strings, or tool execution timeouts.
  3. **Safety & Policy (`safety_evaluator.py`):**
     * Compiled regex patterns scan step inputs and outputs for API secrets (OpenAI, AWS, GCP, Slack, JWTs).
     * Analyzes prompts for known prompt injection vectors and jailbreak attempts.
     * Flags policy violations immediately.
  4. **Context & Budget (`context_budget.py`):**
     * Audits token growth rates. Trajectories exhibiting superlinear token consumption are flagged for context saturation.
  5. **Latency Cascades (`latency_evaluator.py`):**
     * Identifies tool retry sequences where an initial tool failure triggers repeated retries without exponential backoff.
  6. **Goal Completion (`goal_completion.py`):**
     * Audits terminal states to verify output schema conformity.
  7. **Cost Accounting (`cost_accountant.py`):**
     * Calculates dollar cost based on model token pricing tables (e.g. GPT-4o input/output costs) and checks against budget caps.

---

### 6:00 – 7:45 | Governance Hard Gates & CI/CD Gating Mechanics
* **Code Reference:** `backend/app/services/policy_engine.py` & `backend/app/schemas/governance.py`
* **Operational Mechanics:**
  * Evaluated scorecards are checked against an active `PolicyRecord`.
  * **Composite Score Floor:** e.g., Requires an overall score of ≥ 85.0.
  * **Domain Subscore Floors:** e.g., Requires Safety = 1.00 and Tool Fidelity ≥ 0.90.
  * **Configurable Hard Gates:** If `block_on_critical_findings` is enabled, a single secret leak or loop lockup overrides subscores and produces a **BLOCKED** verdict.
  * **Exit Code Integration:** AEP CLI and CI integrations exit with code `0` on PASS and `1` on BLOCK, providing a deterministic PR check for GitHub Actions, GitLab CI, or Jenkins.
  * **Version-Snapshotted Audit Provenance:** Creates a `GovernanceAuditRecord` with an immutable snapshot of the exact policy rules active at evaluation time.

---

### 7:45 – 9:00 | Multi-Channel Notifications & Sanitization
* **Code Reference:** `backend/app/services/notification_service.py`
* **Dispatch Architecture:**
  * Dispatches asynchronously to decouple notification latency from evaluation responses.
  * **Microsoft Teams:** Generates Adaptive Cards v1.5 with severity indicators, FactSet metadata, and deep links.
  * **Slack:** Generates Block Kit JSON with action buttons for triage.
  * **Generic Webhooks:** Posts JSON payloads over HTTPS. Webhook URLs are masked in API responses; payload signing is not implemented.
  * **Secret Redaction Filter:** Scrubs sensitive credentials before serialization, intended to filter keys or tokens prior to transmission.

---

### 9:00 – 10:00 | System Metrics & Quality Baseline
* **System Metrics:**
  * **Throughput:** Depends on hardware and workload; measure with `backend/scripts/benchmark_performance.py`.
  * **Evaluation Latency:** Approximately 2–5ms across benchmark runs.
  * **Test Suite:** 368 backend tests (92% coverage), 50 frontend tests.
  * **Type Rigor:** Strict TypeScript and MyPy configurations without untyped escapes.

