# OpenTelemetry (OTEL) → CATS Translation Pipeline

The **OpenTelemetry Connector** enables direct, universal ingestion of multi-agent and LLM execution traces into the **Agent Evaluation Platform (AEP)** without requiring engineers to manually conform to the Canonical Agent Trace Schema (CATS).

Any framework emitting OpenTelemetry spans—including **LangGraph**, **CrewAI**, **AutoGen**, **OpenAI Agents SDK**, and **LlamaIndex**—can stream spans directly to AEP. The connector parses the payloads, auto-detects the framework, normalizes the spans into CATS, persists the canonical trace, and unlocks full deterministic evaluations, scorecard aggregation, regression testing, and policy governance.

---

## 1. Architecture Overview

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      OpenTelemetry Producers                           │
 │   LangGraph   │   CrewAI   │   AutoGen   │ OpenAI Agents │  LlamaIndex │
 └───────┬───────────┴───┬────┴──────┬──────┴───────┬───────┴──────┬──────┘
         │               │           │              │              │
         ▼               ▼           ▼              ▼              ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │                 POST /api/v1/otel/ingest (or /translate)             │
  │                  (Generic OTEL JSON, OTLP Protobuf Export)           │
  └──────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                   AEP OpenTelemetry Ingestion Engine                   │
 │                                                                        │
 │  1. otel_parser.py: Validates trace envelope, parses timestamps,       │
 │     flattens OTLP attributes, performs cycle & orphan checks.          │
 │                                                                        │
 │  2. otel_adapter.py: FrameworkDetector identifies orchestrator         │
 │     and extracts tokens, models, costs, latencies, and tool calls.     │
 │                                                                        │
 │  3. otel_to_cats.py: Maps spans to CATS Steps, derives Session,        │
 │     Agent profiles, Tool registries, Retries, and preserves DAG tree.  │
 └──────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                 Standard AEP Persistence & Evaluation Layer            │
 │                                                                        │
 │   - CanonicalTrace Repository (SQLite)                    │
 │   - Deterministic Evaluators (Cycles, Budgets, Retries, Tools, Safety) │
 │   - DeepEval Semantic Evaluators (Faithfulness, Relevance, Halluc.)   │
 │   - Evaluation Scorecards & Policy Compliance Auditing                │
 │   - Interactive React Flow DAG Visualization (/evaluations/[id]/graph) │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Ingestion Endpoints

### 2.1 Ingest & Persist: `POST /api/v1/otel/ingest`
Ingests an OpenTelemetry trace, converts it into a `CanonicalTrace`, validates the CATS domain constraints, saves it to the trace repository, and returns trace metadata.

#### Request Headers
```http
Content-Type: application/json
```

#### Request Body
Accepts:
- Standard OTLP Export JSON: `{"resourceSpans": [...]}`
- Generic OTEL Container: `{"trace_id": "...", "resource": {...}, "spans": [...]}`
- Flat Span Array: `[{"trace_id": "...", "span_id": "...", ...}]`

#### Response: `201 Created`
```json
{
  "trace_id": "0d20ef77-a85c-5cf1-8a82-f32f3c7e096f",
  "session_id": "67b848c7-43ca-59ef-8718-d99ea5a5857e",
  "workflow_id": "998dfc0a-6e69-5a1e-84b2-03d6d5ef0a5d",
  "step_count": 3,
  "workflow_status": "SUCCESS",
  "detected_framework": "LANGGRAPH",
  "stored": true
}
```

---

### 2.2 Preview Translation (Dry Run): `POST /api/v1/otel/translate`
Allows engineers and CI pipelines to test trace conversion without writing to the database. Returns the complete `CanonicalTrace` JSON payload.

#### Response: `200 OK`
```json
{
  "session": {
    "session_id": "67b848c7-43ca-59ef-8718-d99ea5a5857e",
    "user_intent": "Analyze quarterly customer sentiment and generate report",
    "budget_constraints": {
      "max_usd": 1.0,
      "max_latency_ms": 30000,
      "max_tokens": 100000
    },
    "created_at": "2026-11-08T00:00:00Z"
  },
  "agents": [
    {
      "agent_id": "b6f5cf21-2a62-5c4d-bdf0-4b31a89c9d74",
      "name": "ResearchAnalyst",
      "role": "Agent",
      "system_prompt_hash": "a1b2c3d4e5f67890",
      "model_identifier": "gpt-4o",
      "temperature": 0.0,
      "tool_registry": []
    }
  ],
  "workflow": {
    "workflow_id": "998dfc0a-6e69-5a1e-84b2-03d6d5ef0a5d",
    "framework": "LANGGRAPH",
    "orchestrator": "DIRECTED_ACYCLIC_GRAPH",
    "status": "SUCCESS",
    "total_latency_ms": 3200,
    "total_cost_usd": 0.0076,
    "root_trace_id": "0d20ef77-a85c-5cf1-8a82-f32f3c7e096f"
  },
  "steps": [ ... ]
}
```

---

## 3. Supported Frameworks & Auto-Detection

The `FrameworkDetector` inspects resource attributes (`service.name`, `instrumentation.name`), span naming conventions, and payload keys:

| Framework | Detection Criteria | Derived CATS Orchestrator |
| :--- | :--- | :--- |
| **LangGraph** | `service.name: *langgraph*` or spans starting with `langgraph.` or `node.` | `DIRECTED_ACYCLIC_GRAPH` |
| **CrewAI** | `service.name: *crewai*` or spans matching `crewai.kickoff`, `crewai.agent` | `AUTONOMOUS_SWARM` |
| **AutoGen** | `service.name: *autogen*` or `autogen.conversation` | `AUTONOMOUS_SWARM` |
| **OpenAI Agents** | `openai.agent`, `run.step`, `tool_calls` | `DIRECTED_ACYCLIC_GRAPH` |
| **LlamaIndex** | `llamaindex`, `query_engine`, `synthesizer` | `DIRECTED_ACYCLIC_GRAPH` |
| **Generic OTEL** | Any valid OpenTelemetry spans without framework markers | `DIRECTED_ACYCLIC_GRAPH` |

---

## 4. Semantic Mapping Reference

| OpenTelemetry Attribute / Span Property | Canonical Agent Trace Schema (CATS) Target |
| :--- | :--- |
| `trace_id` / `traceId` | `session_id`, `workflow.root_trace_id`, `trace_id` |
| `span_id` / `spanId` | `Step.step_id` (deterministic UUID5), `_otel_span_id` |
| `parent_span_id` | `Step.input_state["_otel_parent_span_id"]` (Preserves DAG tree for React Flow) |
| `name` | `Step.node_name` |
| `startTimeUnixNano` / `endTimeUnixNano` | `Step.latency_ms` = `(end - start) * 1000` |
| `gen_ai.usage.prompt_tokens`, `prompt_tokens` | `Step.token_usage.prompt_tokens` |
| `gen_ai.usage.completion_tokens`, `completion_tokens`| `Step.token_usage.completion_tokens` |
| `gen_ai.usage.cost`, `usd_cost`, `total_cost` | `workflow.total_cost_usd` |
| `tool.name`, `tool_name`, `span.events[tool]` | `Step.tool_calls` and auto-populated agent `tool_registry` |
| `retry.count`, `retry_number`, `attempt` | `Step.retries` (`RetryResolution.RESOLVED` or `EXHAUSTED`) |
| `status.code == ERROR` or `error == true` | `Step.output_state["error"]` & `workflow.status = FAILED` |

---

## 5. Quickstart Ingest Scripts

Sample ingestion scripts are provided in `examples/otel/`:

- `examples/otel/langgraph_ingest.py`
- `examples/otel/crewai_ingest.py`
- `examples/otel/autogen_ingest.py`
- `examples/otel/openai_agents_ingest.py`
- `examples/otel/llamaindex_ingest.py`

Run any example:
```bash
py examples/otel/langgraph_ingest.py
```

Output:
```text
[+] Loading LangGraph OTEL trace fixture: .../fixtures/otel/langgraph_trace.json
[+] Posting to http://localhost:8000/api/v1/otel/ingest...

[SUCCESS] LangGraph Trace Translated and Ingested:
  - CATS Trace ID:        0d20ef77-a85c-5cf1-8a82-f32f3c7e096f
  - Session ID:           67b848c7-43ca-59ef-8718-d99ea5a5857e
  - Workflow ID:          998dfc0a-6e69-5a1e-84b2-03d6d5ef0a5d
  - Detected Framework:   LANGGRAPH
  - Step Count:           3
  - Workflow Status:      SUCCESS

While running the application locally, view details at: http://localhost:3000/traces/0d20ef77-a85c-5cf1-8a82-f32f3c7e096f
```

---

## 6. Verification & Test Suite

The OpenTelemetry connector includes unit and integration tests:

```bash
# Run OTEL test suite
pytest backend/tests/otel

# Run complete platform verification
pytest backend/tests
```

**Quality Standards:**
- Test pass rate: **100% (251 / 251 tests passed)**
- Backend coverage: **95.61%**
- Linter: **Ruff clean**
- Type Checker: **MyPy strict clean**

