# Benchmarking & Comparison Engine

## 1. Overview & Objectives

The **Benchmarking & Comparison Engine** provides comparative analytics, score variance calculations, finding progression tracking, and ranked dataset leaderboards across autonomous agent evaluations.

Rather than viewing evaluations in isolation, this engine enables engineering and safety teams to:
- **Quantify Regressions & Improvements**: Calculate signed score deltas ($\Delta \text{Score}$) between baseline and candidate evaluation runs.
- **Audit Domain-by-Domain Variance**: Compare performance across all 7 evaluation domains (`task_quality`, `tool_usage`, `workflow_quality`, `reliability`, `safety`, `cost`, `efficiency`).
- **Track Finding Progression**: Categorize rule-based findings into newly introduced, resolved, and persistent issues.
- **Monitor Risk Tier Transitions**: Detect risk escalation (e.g. `GOOD → CRITICAL`) or risk de-escalation (e.g. `WATCH → EXCELLENT`).
- **Rank Evaluation Datasets**: Maintain historical leaderboards ordered by overall score with summary metrics (mean score, min/max score, pass rate).

---

## 2. Mathematical & Algorithmic Formulations

### 2.1 Score Delta Calculations

For any two evaluated agent execution runs—a **Baseline Run** ($B$) and a **Candidate/Target Run** ($T$):

$$\Delta \text{Overall Score} = \text{Score}_T - \text{Score}_B$$

For each domain $d \in \text{Domains}$:

$$\Delta \text{Domain Score}_d = \text{Score}_{T, d} - \text{Score}_{B, d}$$

A positive delta ($\Delta > 0$) signifies an improvement; a negative delta ($\Delta < 0$) indicates a quality regression.

### 2.2 Risk Tier Transitions

Risk classification levels are ordered monotonically:

$$\text{CRITICAL (0)} < \text{POOR (1)} < \text{WATCH (2)} < \text{GOOD (3)} < \text{EXCELLENT (4)}$$

Let $\text{Tier}(R)$ be the integer index of risk classification $R$:
- **`is_improved = True`** if $\text{Tier}(R_T) > \text{Tier}(R_B)$
- **`is_degraded = True`** if $\text{Tier}(R_T) < \text{Tier}(R_B)$
- **`Neutral`** if $\text{Tier}(R_T) = \text{Tier}(R_B)$

### 2.3 Finding Signature Categorization

Findings are uniquely identified by their rule code and sorted step scope:

$$\text{Sig}(f) = \left(f.\text{code}, \, \text{tuple}(\text{sorted}(f.\text{affected\_steps}))\right)$$

Given baseline findings set $\mathcal{F}_B$ and target findings set $\mathcal{F}_T$:
- **`new_findings`**: $\{f \in \mathcal{F}_T \mid \text{Sig}(f) \notin \mathcal{F}_B\}$ (Issues introduced in candidate)
- **`resolved_findings`**: $\{f \in \mathcal{F}_B \mid \text{Sig}(f) \notin \mathcal{F}_T\}$ (Issues fixed in candidate)
- **`persistent_findings`**: $\{f \in \mathcal{F}_T \mid \text{Sig}(f) \in \mathcal{F}_B\}$ (Issues remaining unchanged)
- **`total_delta`**: $|\mathcal{F}_T| - |\mathcal{F}_B|$

---

## 3. API Specifications

### 3.1 `POST /api/v1/benchmarks/compare`

Compares two evaluation runs.

#### Request Payload:
```json
{
  "base_evaluation_id": "b0000000-0000-0000-0000-000000000001",
  "target_evaluation_id": "b0000000-0000-0000-0000-000000000002"
}
```

#### Response Payload (`EvaluationComparisonResponse`):
```json
{
  "base_evaluation_id": "b0000000-0000-0000-0000-000000000001",
  "target_evaluation_id": "b0000000-0000-0000-0000-000000000002",
  "base_trace_id": "a0000000-0000-0000-0000-000000000001",
  "target_trace_id": "a0000000-0000-0000-0000-000000000002",
  "base_score": 68.5,
  "target_score": 87.0,
  "overall_score_delta": 18.5,
  "risk_transition": {
    "base_risk": "WATCH",
    "target_risk": "GOOD",
    "is_improved": true,
    "is_degraded": false
  },
  "domain_deltas": {
    "workflow_quality": {
      "domain_name": "workflow_quality",
      "base_score": 60.0,
      "target_score": 85.0,
      "score_delta": 25.0,
      "base_status": "WARN",
      "target_status": "PASS"
    }
  },
  "finding_delta": {
    "new_findings": [],
    "resolved_findings": [
      {
        "finding_id": "f-1",
        "severity": "HIGH",
        "code": "CYCLE_DETECTED",
        "message": "Cyclic loop resolved"
      }
    ],
    "persistent_findings": [],
    "new_count": 0,
    "resolved_count": 1,
    "persistent_count": 0,
    "total_delta": -1
  },
  "compared_at": "2026-11-08T15:45:00Z"
}
```

---

### 3.2 `GET /api/v1/benchmarks/summary`

Retrieves statistical aggregates across all evaluations and a ranked leaderboard.

#### Parameters:
- `limit: int = 100` (1..500)
- `offset: int = 0` (0..)

#### Response Payload (`BenchmarkSummaryResponse`):
```json
{
  "total_evaluations": 12,
  "mean_score": 84.2,
  "min_score": 45.0,
  "max_score": 98.5,
  "pass_rate": 83.3,
  "risk_distribution": {
    "EXCELLENT": 6,
    "GOOD": 4,
    "WATCH": 1,
    "POOR": 0,
    "CRITICAL": 1
  },
  "leaderboard": [
    {
      "rank": 1,
      "evaluation_id": "b0000000-0000-0000-0000-000000000002",
      "trace_id": "a0000000-0000-0000-0000-000000000002",
      "overall_score": 98.5,
      "risk_classification": "EXCELLENT",
      "finding_count": 0,
      "workflow_status": "SUCCESS",
      "started_at": "2026-11-08T12:00:00Z",
      "completed_at": "2026-11-08T12:00:01Z"
    }
  ]
}
```

---

## 4. Frontend Experience (`/benchmarks`)

The Next.js 14 frontend renders the Benchmarking dashboard at `/benchmarks`:
1. **Header KPI Cards**: Displays total evaluations, dataset mean score, top score, and overall pass rate percentage.
2. **Interactive Comparator**:
   - Baseline and Candidate evaluation selection dropdowns.
   - Quick-select "Base" and "Target" action buttons in the leaderboard rows.
3. **Comparison Outcome View (`ComparisonView.tsx`)**:
   - Large score delta banner with colored pills (+emerald for improvement, -rose for regression).
   - Risk transition pill displaying base and candidate risk tiers with improved/degraded badges.
   - Domain-by-domain variance grid comparing scores and statuses across all 7 domains.
   - Finding tabs categorizing new, resolved, and persistent findings.
4. **Ranked Leaderboard Table (`BenchmarkTable.tsx`)**:
   - Ordered by score descending with rank badges (`#1`, `#2`, `#3`), score coloring, risk badges, and direct links to evaluation and trace detail pages.

---

## 5. Capability Maturity Status

| Subsystem Component | Maturity Level | Notes |
| :--- | :---: | :--- |
| **Score Delta Analysis** | `IMPLEMENTED` | Signed delta calculation across overall score and all 7 domains. |
| **Risk Transition Analysis** | `IMPLEMENTED` | Monotonic tier comparison (`EXCELLENT` down to `CRITICAL`). |
| **Finding Progression Categorization** | `IMPLEMENTED` | Classifies new, resolved, and persistent findings by code/scope signature. |
| **Benchmark Summary & Leaderboard** | `IMPLEMENTED` | Statistical aggregates (mean, min, max, pass rate) and ranked table. |
| **Web UI Dashboard** | `IMPLEMENTED` | Route `/benchmarks` with live comparison view and interactive selectors. |
| **Automated Test Coverage** | `IMPLEMENTED` | 100% statement coverage across benchmark service and schemas. |

