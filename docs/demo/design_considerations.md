# System Design Considerations & Architectural Trade-offs

This document details the architectural decisions, trade-offs, and design rationales implemented in the **Agent Evaluation Platform (AEP)**.

---

## 1. Deterministic Rule-Based Evaluation vs. LLM-as-a-Judge

### Problem Statement
Evaluating multi-step autonomous agent traces requires verifying step ordering, tool invocation correctness, data leaks, and termination conditions.

### Why It Is Difficult
Agent traces contain unstructured reasoning strings mixed with structured tool payloads. Evaluating traces with an LLM judge introduces sampling variance: identical runs can receive differing scores across evaluations, leading to unstable CI/CD test gates. In addition, invoking an LLM for each evaluation step incurs network latency (2–6 seconds per run) and recurring inference costs ($0.05–$0.15 per trace).

### Constraints
- CI/CD build checks must complete quickly (< 1 second total evaluation overhead).
- Identical traces must yield identical numerical scores and verdicts across runs.
- The evaluation engine must operate without external model API keys or token billing dependencies.

### Decision Made
Implement 7 parallel, deterministic evaluator domains:
1. **Loop Detection:** Cryptographic hashing of step inputs, tool parameters, and responses with cycle-finding algorithms.
2. **Tool Fidelity:** JSON Schema validation of tool inputs against declared workspace catalogs.
3. **Safety & Policy:** Pre-compiled regular expressions auditing for credentials, API tokens, and prompt injection markers.
4. **Context & Budget:** Verification of token growth acceleration and context window saturation.
5. **Latency & Cascades:** Analysis of tool retry sequences and execution timeouts.
6. **Goal Completion:** State-machine audits of terminal step states and output schema conformity.
7. **Cost Accounting:** Deterministic token pricing models across configured provider tiers.

### Trade-offs Accepted
- **Trade-off:** Deterministic evaluation cannot assess subjective conversational tone or subtle stylistic nuances that an LLM might evaluate.
- **Mitigation:** AEP provides an optional semantic evaluation interface for scenarios where qualitative prompt grading is explicitly configured, while keeping deterministic validation as the hard gating standard.

### Measured Results
- Evaluation latency averages **approximately 2–5ms** per trace.
- Single-core throughput depends on hardware; measure it with `backend/scripts/benchmark_performance.py`.
- Scoring variance is zero for identical inputs.

---

## 2. Handling Out-of-Order OpenTelemetry (OTLP) Ingestion

### Problem Statement
Standard OpenTelemetry collectors stream spans asynchronously. Network routing can deliver child tool execution spans before the parent agent reasoning span arrives.

### Why It Is Difficult
Direct stream processing would either fail on missing parent references or misclassify tool execution sequences, creating inaccurate trajectory graphs.

### Constraints
- Must accept standard OTLP/HTTP and OTLP/gRPC streams without custom client SDKs.
- Must reconstruct accurate causal parent-child step relationships.

### Decision Made
Two-phase trajectory graph reconstruction:
1. **Adjacency Buffering:** Ingestion batches are indexed into an in-memory graph keyed by `span_id`, recording `parent_span_id`, `start_time_unix_nano`, and `end_time_unix_nano`.
2. **Topological Ordering:** The translator identifies root session spans and sorts child steps chronologically by monotonic start timestamps. Child tool spans are grouped under their respective parent step regardless of arrival order.

### Trade-offs Accepted
- **Trade-off:** Requires in-memory buffering until the trace batch completes, rather than purely reactive streaming.
- **Mitigation:** Bounded memory limits (15 MB maximum payload, 10,000 span limit per request) and TTL expiration protect against memory exhaustion.

### Measured Results
- Verified reconstruction across LangGraph, CrewAI, AutoGen, LlamaIndex, and OpenAI Agents SDK traces with correct parent-child step attribution.

---

## 3. Credential Redaction in Notification Dispatches

### Problem Statement
When an agent accidentally leaks API credentials (e.g., an AWS secret or Bearer token) and trips the Safety Evaluator, broadcasting the trace context to Slack, Microsoft Teams, or webhooks risks propagating the sensitive credential to third-party communication channels.

### Why It Is Difficult
Notification payloads must convey actionable debugging context (the offending step, tool name, and finding description) without exposing the secret itself.

### Constraints
- Notification webhooks must execute asynchronously without blocking the evaluation response.
- Secrets must be sanitized before template formatting or webhook serialization.

### Decision Made
Pipeline-level payload scrubbing:
1. The `NotificationService` passes all event context through a dedicated `SanitizerFilter` prior to template rendering.
2. The filter applies pre-compiled patterns covering standard credential structures (OpenAI keys, AWS access keys, JWTs, Bearer tokens).
3. Matched patterns are reported as CRITICAL findings, with only a redacted sample stored.
4. Outbound generic webhooks post JSON over HTTPS. Payload signing is not implemented; webhook URLs are masked in API responses.

### Trade-offs Accepted
- **Trade-off:** Regex-based sanitization might redact non-secret tokens that resemble credential patterns (false positives in debugging text).
- **Mitigation:** Standardized replacement placeholders clearly indicate where redaction took place.

### Measured Results
- Unit and integration tests confirm credentials in trace payloads are scrubbed prior to dispatch across Teams Adaptive Cards, Slack Block Kit, and generic webhooks.

---

## 4. Horizontal Scaling and Persistence Architecture

### Problem Statement
Supporting high-volume evaluation in CI/CD and production environments requires scaling ingestion and evaluation throughput horizontally.

### Why It Is Difficult
Shared database locks during concurrent trace evaluation can create database bottlenecks and increase API latency.

### Constraints
- Development and small deployments should run self-contained without mandatory cloud dependencies.
- Clustered deployments must support horizontal pod autoscaling.

### Decision Made
Decoupled multi-tier scaling model:
1. **Stateless Evaluation Engine:** The 7 evaluation domains execute entirely in memory. Evaluation functions hold zero database locks during processing.
2. **Pluggable Storage Layer:** Built with SQLModel and SQLAlchemy, using SQLite WAL mode. Other SQL databases are not tested; multi-replica deployment is not supported.
3. **Rate Limiting:** The in-memory sliding-window limiter is per process. No Redis or other shared-store implementation exists.

### Trade-offs Accepted
- **Trade-off:** In-memory rate limiting in single-node mode does not share state across process boundaries unless configured with an external store.
- **Mitigation:** Multi-replica deployment would need a shared rate-limit store (for example Redis). That is not implemented, so run a single replica.

### Measured Results
- Latency and memory should be measured on the target hardware with `backend/scripts/benchmark_performance.py`.

---

## 5. Score Floors vs. Policy Hard Gates

### Problem Statement
Using weighted average scores alone to gate releases can allow dangerous defects to pass CI/CD checks.

### Why It Is Difficult
An agent scoring 100% in Loop Detection, 100% in Goal Completion, and 100% in Latency, but leaking credentials in a single step, may still achieve an overall score above 90%. In a score-only gating system, this agent would pass release checks.

### Constraints
- CI/CD automation requires binary pass/fail exit codes (0 for pass, 1 for block).
- Governance policies must support both gradual quality improvements (minimum score floors) and non-negotiable safety standards (hard gates).

### Decision Made
Two-stage policy evaluation:
1. **Floor Evaluation:** Validates that composite scores and individual domain scores meet configured minimums.
2. **Hard Gate Veto:** Configurable rules (e.g., secret detection, loop lockup, disallowed findings) hold absolute veto authority. If any hard gate is triggered, the verdict is forced to **BLOCKED**, overriding average numerical scores.

### Trade-offs Accepted
- **Trade-off:** Hard gates can block deployments for minor findings if policies are misconfigured.
- **Mitigation:** Policies are workspace-scoped and environment-specific, allowing permissive policies in development and strict enforcement in production staging.

### Measured Results
- Deterministic CI exit code assignment (`0` on approved, `1` on blocked) verified in integration test suites.

