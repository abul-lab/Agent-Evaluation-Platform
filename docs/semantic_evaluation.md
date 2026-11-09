# Semantic Evaluation Adapter Layer

## 1. Overview & Philosophy

The Agent Evaluation Platform uses a **two-tier evaluation architecture**:

1. **Deterministic Evaluation (Mandatory & Primary):**
   - Structural validation (graph loops, tool registry hallucination, redundant tool invocations, retry cascade bounds, budget consumption, secret leaks) is computed mathematically and deterministically.
   - Zero model calls, zero external API keys, zero token costs, and 100% reproducible.

2. **Semantic Evaluation (Optional & Additive):**
   - Evaluates qualitative and semantic properties of agent inputs, context, and outputs (such as prompt relevancy, factual faithfulness, and hallucination).
   - Operates strictly downstream of deterministic evaluation.
   - Does **NOT** alter deterministic findings or overall scorecard risk calculations.
   - Degrades gracefully and safely when external models, API keys, or dependencies are unavailable.

```
┌────────────────────────────────────────────────────────┐
│               Canonical Agent Trace (CATS)             │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
   ┌──────────────────────┐    ┌──────────────────────┐
   │    Deterministic     │    │   Semantic Adapter   │
   │      Evaluator       │    │      (Additive)      │
   └──────────┬───────────┘    └──────────┬───────────┘
              │                           │
              ▼                           ▼
   ┌──────────────────────┐    ┌──────────────────────┐
   │  Scorecard & Risk    │    │   Semantic Quality   │
   │    Classification    │    │       Findings       │
   └──────────────────────┘    └──────────────────────┘
```

---

## 2. Architecture & Dependency Isolation

To maintain platform stability across air-gapped, offline, and multi-tenant environments:

- **Strict Subsystem Isolation:** The third-party evaluation library (`deepeval`) is not imported at module load time. Dynamic runtime imports encapsulate metric evaluations inside try/except blocks.
- **Zero-Cost Air-Gapped Fallback:** If `OPENAI_API_KEY` is absent from the runtime environment, or if `deepeval` is uninstalled, the adapter factory automatically instantiates `FallbackSemanticAdapter`.
- **Fault-Tolerant Execution:** Individual semantic metric failures (such as model timeouts or rate limits) do not cause an evaluation request to fail. The system logs the failure and records `evaluation_available: false` with the diagnostic reason.

---

## 3. Evaluator Subsystem Components

### 3.1 Abstract Base Evaluator (`SemanticEvaluator`)

Defines the contract for all semantic adapters:

```python
class SemanticEvaluator(ABC):
    @abstractmethod
    def evaluate_relevancy(self, input_text: str, actual_output: str, context: list[str] | None = None) -> SemanticFinding: ...
    @abstractmethod
    def evaluate_faithfulness(self, input_text: str, actual_output: str, retrieval_context: list[str]) -> SemanticFinding: ...
    @abstractmethod
    def evaluate_hallucination(self, input_text: str, actual_output: str, contexts: list[str]) -> SemanticFinding: ...
    @abstractmethod
    def evaluate_trace(self, trace: CanonicalTrace) -> SemanticEvaluationResult: ...
```

### 3.2 DeepEval Adapter (`DeepEvalSemanticAdapter`)

Wraps DeepEval's metric suite:

| Metric | DeepEval Class | Target Quality Dimension | Pass Threshold |
| :--- | :--- | :--- | :---: |
| `answer_relevancy` | `AnswerRelevancyMetric` | User intent alignment and answer completeness | $\ge 0.7$ |
| `faithfulness` | `FaithfulnessMetric` | Factual grounding against execution context | $\ge 0.7$ |
| `hallucination` | `HallucinationMetric` | Context contradictions or unsupported assertions | $\le 0.5$ |

#### Trace Payload Extraction Strategy:
- **`input_text`**: Derived from `trace.session.user_intent`.
- **`actual_output`**: Extracted from the final step's `output_state["result"]` or `output_state["response"]`, falling back to `last_step.node_name`.
- **`context`**: Aggregated execution payloads from `tool.execution_result` across all steps in the trace.

### 3.3 Fallback Adapter (`FallbackSemanticAdapter`)

When conditions for semantic evaluation are unmet:
- Returns `SemanticEvaluationResult` with `evaluation_available = False`.
- Reports `provider = "fallback"`.
- Records empty `metrics = []`.
- Returns an informative explanation in `reason` (e.g., `"OPENAI_API_KEY is not set. Operating in fallback mode."`).
- Incurs **0 ms model latency** and **$0.00 model cost**.

---

## 4. Adapter Resolution Factory

The `get_semantic_adapter()` resolver applies precedence rules:

1. **Explicit Override (`override_adapter`):** Used during testing or custom adapter injection.
2. **Explicit Fallback (`force_fallback=True`):** Enforces offline deterministic operation.
3. **Missing Environment Keys (`not os.environ.get("OPENAI_API_KEY")`):** Immediately resolves to `FallbackSemanticAdapter`.
4. **Library Availability Check (`is_deepeval_available()`):** Resolves to fallback if `deepeval` cannot be imported.
5. **Live Adapter:** Instantiates `DeepEvalSemanticAdapter()` only when all prerequisites are satisfied.

---

## 5. API Integration

### Endpoint: `GET /api/v1/evaluations/{evaluation_id}/semantic`

Returns the semantic evaluation results for a completed evaluation run.

#### Example Response (Live DeepEval Mode):
```json
{
  "metrics": [
    {
      "finding_id": "848da66a-115f-4d37-882e-9dfdfbcf3889",
      "metric_name": "answer_relevancy",
      "score": 0.92,
      "passed": true,
      "explanation": "Answer directly addresses user intent with accurate tool-derived figures."
    },
    {
      "finding_id": "4b684cb3-00e1-4c60-aee8-bc8499276566",
      "metric_name": "faithfulness",
      "score": 0.88,
      "passed": true,
      "explanation": "All claims are grounded in tool execution results."
    },
    {
      "finding_id": "8ebbb9b2-be90-48e0-bbd8-f7b57eb6aebf",
      "metric_name": "hallucination",
      "score": 0.05,
      "passed": true,
      "explanation": "No hallucination detected against step contexts."
    }
  ],
  "provider": "deepeval",
  "execution_time_ms": 1420.5,
  "evaluation_available": true,
  "reason": null
}
```

#### Example Response (Fallback Mode):
```json
{
  "metrics": [],
  "provider": "fallback",
  "execution_time_ms": 0.05,
  "evaluation_available": false,
  "reason": "OPENAI_API_KEY is not set. Operating in fallback mode."
}
```

---

## 6. Frontend Integration

The Next.js 14 frontend renders the `SemanticEvaluationCard` component directly on `/evaluations/[evaluationId]`:

- **Dual-State Presentation:**
  - **Available:** Displays provider badge, latency, and a structured table of metrics, pass/fail status pills, percentage scores, and judge explanations.
  - **Fallback:** Renders a clean banner notifying the user that the platform is operating in pure deterministic mode without external model dependencies.
- **Non-blocking Loading:** Semantic evaluation data is retrieved in parallel with summary, scorecard, and findings data.

---

## 7. Capability Maturity Notice

| Component | Status | Notes |
| :--- | :--- | :--- |
| **DeepEval Adapter** | `IMPLEMENTED` | Isolated dynamic imports for relevancy, faithfulness, and hallucination. |
| **Fallback Semantic Adapter** | `IMPLEMENTED` | Zero-cost, zero-latency safe fallback for air-gapped environments. |
| **Lifecycle API Integration** | `IMPLEMENTED` | REST endpoint `GET /evaluations/{id}/semantic` and database column persistence. |
| **Frontend Inspection UI** | `IMPLEMENTED` | `SemanticEvaluationCard` component in evaluation detail page. |
| **Automated Test Coverage** | `IMPLEMENTED` | 100% statement coverage across semantic adapter modules. |

