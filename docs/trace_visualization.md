# Trace Visualization Engine

## 1. Overview & Objectives

The **Trace Visualization Engine** provides visual workflow DAG inspection for autonomous agent execution traces.

Rather than relying on static JSON inspection or simulated mock diagrams, the visualization engine builds an interactive directed acyclic/cyclic graph directly from persisted **Canonical Agent Trace Schema (CATS)** execution traces and **Evaluation Findings**.

### Core Capabilities:
- **Interactive Workflow Graph**: Powered by React Flow (`@xyflow/react`), rendering sequential steps and transitions.
- **Node Inspection Panel**: A slide-over drawer detailing step metadata, agent identity, input/output states, latency, and token consumption.
- **Retries Visualization**: Visualizes retry attempts, error categories, backoff durations, and resolution outcomes on each step node and in the inspection drawer.
- **Findings Overlay**: Highlights steps affected by evaluation findings with severity indicators (`INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Tool Call Visualization**: Deep inspection of external tool invocations, showing parameters, execution outputs, and warning flags for hallucinations (`is_hallucinated`), redundancy (`is_redundant`), or failures (`is_error`).
- **Cycle Highlighting**: Automatically detects and visually highlights repetitive execution loops (cyclic patterns) on both nodes and edges with an active loop toggle.

---

## 2. Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                 Trace Persistence (SQLite)                  │
│    Canonical Agent Trace Schema (CATS) Record               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               Evaluation Lifecycle Service                  │
│  - Reads canonical steps, tool calls, and retries           │
│  - Parses evaluation findings (CYCLE_DETECTED, etc.)        │
│  - Synthesizes WorkflowGraphResponse                        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                   GET /evaluations/{id}/graph
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Next.js 14 Web Frontend                     │
│  - Route: /evaluations/{id}/graph                           │
│  - React Flow Canvas with Custom StepNode                   │
│  - Interactive NodeInspectionPanel                          │
│  - Cycle Highlighting Mode Toggle                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. API Contract: `GET /api/v1/evaluations/{evaluation_id}/graph`

Returns the complete graph data structure for an evaluation run.

### Response Schema (`WorkflowGraphResponse`):
```json
{
  "evaluation_id": "b0000000-0000-0000-0000-000000000001",
  "trace_id": "a0000000-0000-0000-0000-000000000001",
  "workflow_id": "w0000000-0000-0000-0000-000000000001",
  "workflow_status": "SUCCESS",
  "total_steps": 4,
  "has_cycles": true,
  "nodes": [
    {
      "id": "step-0",
      "step_id": "s0000000-0000-0000-0000-000000000001",
      "step_index": 0,
      "node_name": "PlannerNode",
      "agent_id": "ag000000-0000-0000-0000-000000000001",
      "agent_name": "PlannerAgent",
      "latency_ms": 420,
      "token_usage": {
        "prompt_tokens": 120,
        "completion_tokens": 50,
        "cached_tokens": 0,
        "reasoning_tokens": 10,
        "total_tokens": 170
      },
      "input_state": { "intent": "Analyze quarterly revenue" },
      "output_state": { "tasks": ["fetch_data", "calculate_margin"] },
      "tool_calls": [
        {
          "tool_call_id": "t0000000-0000-0000-0000-000000000001",
          "tool_name": "sql_query_runner",
          "raw_arguments": { "query": "SELECT revenue FROM metrics;" },
          "parsed_arguments": null,
          "execution_result": { "rows": 4 },
          "is_error": false,
          "is_hallucinated": false,
          "is_redundant": false,
          "execution_time_ms": 115
        }
      ],
      "retries": [
        {
          "retry_id": "r0000000-0000-0000-0000-000000000001",
          "attempt_number": 1,
          "error_type": "ConnectionTimeout",
          "backoff_duration_ms": 300,
          "resolution": "SUCCESS"
        }
      ],
      "findings": [
        {
          "finding_id": "f0000000-0000-0000-0000-000000000001",
          "severity": "HIGH",
          "code": "CYCLE_DETECTED",
          "message": "Cyclic execution loop detected across steps 0..2"
        }
      ],
      "is_cycle_node": true
    }
  ],
  "edges": [
    {
      "id": "edge-step-0-step-1",
      "source": "step-0",
      "target": "step-1",
      "is_cycle_edge": true,
      "label": null
    }
  ]
}
```

---

## 4. Cycle Detection & Highlighting

The engine cross-references deterministic `CYCLE_DETECTED` findings emitted during evaluation:
1. Steps whose indices match `affected_steps` are marked `is_cycle_node = true`.
2. Edges connecting adjacent cyclic steps are marked `is_cycle_edge = true`.
3. In the frontend:
   - Cyclic nodes display a pulsing `LOOP` warning pill and crimson border styling.
   - Cyclic edges render with a rose color stroke and animated flow.
   - Users can toggle cycle highlighting via the `Highlight Cycles: ON/OFF` control.

---

## 5. Frontend Visualizer (`/evaluations/{id}/graph`)

The visualizer view provides:
- **Navigation**: Directly linked from the evaluation detail page via the `Inspect Workflow Graph →` button.
- **Interactive Canvas**:
  - Zoom & Pan controls
  - MiniMap navigation preview
  - Responsive layout positioning
- **Node Selection & Inspection Drawer**:
  - Clicking any node opens the `NodeInspectionPanel`.
  - **Overview tab**: Step metadata, latency, total tokens, prompt/completion breakdown, and step findings.
  - **Tools tab**: Explores every tool call with arguments, return payload, execution time, and error/hallucination flags.
  - **Retries tab**: Displays retry attempts, backoff duration, and resolution status.
  - **State tab**: JSON inspector for input and output state dictionaries.

---

## 6. Capability Maturity Model

| Capability | Maturity Status | Notes |
| :--- | :---: | :--- |
| **Workflow Graph Generation** | `IMPLEMENTED` | Live API serialization from CATS traces and findings. |
| **React Flow DAG Canvas** | `IMPLEMENTED` | Custom StepNode, Minimap, Controls, and Background. |
| **Node Inspection Drawer** | `IMPLEMENTED` | Overview, Tool Calls, Retries, and State inspection. |
| **Cycle & Loop Highlighting** | `IMPLEMENTED` | Node badges, animated edges, and toggle controls. |
| **Automated Test Coverage** | `IMPLEMENTED` | Pytest integration tests & Vitest UI tests. |

