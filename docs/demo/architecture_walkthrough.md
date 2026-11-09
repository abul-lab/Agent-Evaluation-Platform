# System Architecture Presentation Guide

This guide provides speaking notes and technical callouts for presenting each of the **5 Architecture Vector Diagrams** in AEP. The vector assets are located in `docs/diagrams/` and accessible live at `/architecture`.

---

## Diagram 1: System Architecture (`system_architecture.svg`)

```
Agent Frameworks (LangGraph, CrewAI, AutoGen, LlamaIndex, OpenAI SDK)
                          ↓
         OTLP / HTTP & gRPC Native Ingestion
                          ↓
  Ingestion Gate: Workspace API Key Auth & Sliding-Window Rate Limiter
                          ↓
           OTEL → CATS Translation Pipeline
                          ↓
      7 Parallel Deterministic Evaluator Domains
                          ↓
       Governance Hard Gating & Policy Enforcement Engine
                          ↓
        Alerting Hub (Teams, Slack, generic HTTPS webhooks) & SIEM
```

### Presentation Script
* **Slide 1:** "This diagram illustrates the high-level architecture of AEP. The architecture is structured into 6 decoupled tiers to maintain predictable latency, tenant isolation, and consistent evaluation throughput."
* **Key Point to Emphasize:** Notice the separation between the **Synchronous Evaluation Core** (which executes in approximately 2–5ms for CI/CD gates) and the **Asynchronous Operations Bus** (which handles alert notifications to Slack and Teams without holding up the API).

---

## Diagram 2: Deterministic Evaluation Pipeline (`evaluation_pipeline.svg`)

### Key Components
1. **CATS Ingestion & Validation:** Pydantic v2 validates trajectory structure, non-negative tokens, and monotonic timestamps.
2. **7 Concurrent Evaluators:**
   * **Domain 1 (Loop Detection):** Cryptographic state hashing, cycle-finding.
   * **Domain 2 (Tool Fidelity):** Schema conformity, undeclared tool detection.
   * **Domain 3 (Safety & Policy):** Regex secret scrubbing, prompt injection fingerprinting.
   * **Domain 4 (Context & Budget):** Token saturation, step limits.
   * **Domain 5 (Latency Cascades):** Retry storms, step duration outliers.
   * **Domain 6 (Goal Completion):** Terminal state outcome verification.
   * **Domain 7 (Cost Accounting):** Multi-model token pricing accounting.
3. **Scorecard Assembly:** Normalizes domain subscores (0.0 to 1.0), applies weights, and enforces hard-gate vetoes.

### Presentation Script
* "Unlike LLM judges that introduce temperature noise and latency, these 7 domains are **pure algorithmic evaluators**. They evaluate a 50-step trajectory in approximately 2–5ms with reproducible scoring."

---

## Diagram 3: OTEL → CATS Translation Flow (`otel_translation_flow.svg`)

### Key Components
1. **OTLP Ingestion Gate:** Accepts standard OpenTelemetry traces without modifying agent application code.
2. **Tree Reconstruction Engine:** Sorts unordered span batches into hierarchical parent-child trees.
3. **Semantic Attribute Mapping:** Translates OpenInference / GenAI attributes into CATS step models.
4. **Canonical Agent Trace Schema (CATS):** Emits an immutable, validated trace artifact ready for scoring.

### Presentation Script
* "Platform teams prioritize open standards over proprietary SDKs. By adopting OpenTelemetry, any agent framework capable of exporting OTLP spans works with AEP directly."

---

## Diagram 4: Automated Governance & Hard-Gating Engine (`governance_flow.svg`)

### Key Components
1. **Dual Input Contract:** Evaluated scorecard + Active Policy Profile.
2. **Rule Verification Matrix:** Checks global and domain score floors.
3. **Hard Gate Enforcer:** Non-negotiable release block on secret leaks or infinite loops.
4. **Audit Trail & CI Gating:** Returns exit code 0 or 1 and snapshots policy rules to `GovernanceAuditRecord`.

### Presentation Script
* "Observability without automated verification leaves teams blind to silent regressions. AEP's governance engine acts as a deterministic release gate in CI/CD pipelines, designed to prevent flawed prompts or leaky models from shipping undetected."

---

## Diagram 5: Notifications & Alerting Dispatcher (`notification_flow.svg`)

### Key Components
1. **Event Sources:** Critical alerts triggered by hard gates, blocked evaluations, or budget overruns.
2. **Payload Sanitizer:** Redacts passwords, API keys, and private tokens before message formatting.
3. **Multi-Format Adapters:**
   * Microsoft Teams Adaptive Cards v1.5 with FactSets and action links.
   * Slack Block Kit JSON with interactive triage buttons.
   * Generic Webhooks post JSON over HTTPS. Webhook URLs are never returned by the API.
4. **Delivery Logger:** Records delivery status, latency, and response codes.

### Presentation Script
* "When a critical safety gate trips, on-call engineers receive an alert in Teams or Slack in under 25 milliseconds, complete with deep links to the offending step and zero credential leakage."

