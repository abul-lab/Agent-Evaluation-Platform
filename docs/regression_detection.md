# Regression Detection & Quality Gate Policy Engine

## 1. Overview & Objectives

The **Regression Detection & Quality Gate Policy Engine** automates quality regression testing between baseline reference runs and candidate agent execution runs. It enforces deterministic policies and release criteria before agent modifications, prompt updates, or tool registry changes are promoted to production environments.

The engine provides:
- **Quality Gate Classification**: Classifies candidate evaluation status into `PASSED`, `WARNING`, or `REGRESSED`.
- **Score Regression Detection**: Enforces maximum allowable drop in overall score ($\Delta \le -\text{threshold}$) and individual domain scores.
- **Risk Escalation Checks**: Detects if candidate evaluations degrade into worse risk tiers (e.g. `GOOD → CRITICAL`).
- **Prohibited Finding Enforcements**: Automatically rejects traces that trigger non-negotiable failure codes (e.g. `SECRET_EXPOSURE`, `CYCLE_DETECTED`).
- **New Critical Issue Tracking**: Detects any newly introduced `CRITICAL` or `HIGH` severity findings absent from the baseline run.
- **Score Floors**: Validates that candidate evaluation score and safety score satisfy configured baseline minimums.

---

## 2. Mathematical & Algorithmic Formulations

Let $B$ represent the Baseline Evaluation Record and $C$ represent the Candidate Evaluation Record.

### 2.1 Score Delta Checks

The signed overall score delta is defined as:

$$\Delta_{\text{overall}} = C.\text{overall\_score} - B.\text{overall\_score}$$

Given policy threshold $\tau_{\text{score}} = \text{policy}.\text{max\_score\_drop}$:

$$\text{Violation}(\text{"OVERALL\_SCORE\_DROP"}) \iff \Delta_{\text{overall}} < -\tau_{\text{score}}$$

For each domain $d \in \{\text{task\_quality}, \text{tool\_usage}, \text{workflow\_quality}, \text{reliability}, \text{safety}, \text{cost}, \text{efficiency}\}$:

$$\Delta_d = C.\text{domain\_score}_d - B.\text{domain\_score}_d$$

Given domain threshold $\tau_{\text{domain}} = \text{policy}.\text{max\_domain\_drop}$:

$$\text{Violation}(\text{"DOMAIN\_SCORE\_DROP\_"} + d) \iff \Delta_d < -\tau_{\text{domain}}$$

### 2.2 Risk Tier Escalation

Risk tiers are mapped to ordinal rank values:

$$\text{CRITICAL (0)} < \text{POOR (1)} < \text{WATCH (2)} < \text{GOOD (3)} < \text{EXCELLENT (4)}$$

$$\text{Violation}(\text{"RISK\_ESCALATION"}) \iff \text{Rank}(C.\text{risk}) < \text{Rank}(B.\text{risk})$$

### 2.3 Finding Signatures & Critical Finding Introduction

Each evaluation finding $f$ has a unique signature based on its code and affected steps:

$$\text{Sig}(f) = (f.\text{code}, \, \text{tuple}(\text{sorted}(f.\text{affected\_steps})))$$

- **Prohibited Codes**:
  $$\forall f \in C.\text{findings}: f.\text{code} \in \text{policy}.\text{prohibited\_codes} \implies \text{Violation}(\text{"PROHIBITED\_FINDING\_CODE"})$$
- **New Critical/High Findings**:
  $$\forall f \in C.\text{findings} \setminus B.\text{findings}: f.\text{severity} \in \{\text{HIGH}, \text{CRITICAL}\} \implies \text{Violation}(\text{"NEW\_CRITICAL\_FINDING"})$$

### 2.4 Absolute Score Floors

- **Overall Floor**:
  $$C.\text{overall\_score} < \text{policy}.\text{min\_overall\_score} \implies \text{Violation}(\text{"MIN\_OVERALL\_SCORE\_BREACH"})$$
- **Safety Floor**:
  $$C.\text{safety\_score} < \text{policy}.\text{min\_safety\_score} \implies \text{Violation}(\text{"MIN\_SAFETY\_SCORE\_BREACH"})$$

### 2.5 Status Resolution Matrix

| Critical / High Violations | Medium / Low Violations | Status | `is_regression` | Action |
| :---: | :---: | :---: | :---: | :--- |
| $> 0$ | Any | `REGRESSED` | `true` | Block release; automated regression alert triggered |
| $0$ | $> 0$ | `WARNING` | `false` | Release permitted with warning; advisory review needed |
| $0$ | $0$ | `PASSED` | `false` | Quality gate satisfied; release approved |

---

## 3. API Specifications

### 3.1 `GET /api/v1/regressions/policy/default`

Retrieves the standard baseline regression quality gate policy.

#### Response Schema (`RegressionPolicy`)
```json
{
  "name": "Standard Quality Gate",
  "max_score_drop": 5.0,
  "max_domain_drop": 10.0,
  "fail_on_risk_escalation": true,
  "fail_on_new_critical_findings": true,
  "prohibited_finding_codes": [
    "SECRET_EXPOSURE",
    "CYCLE_DETECTED"
  ],
  "min_overall_score": 75.0,
  "min_safety_score": 90.0
}
```

### 3.2 `POST /api/v1/regressions/check`

Audits a candidate evaluation against a baseline evaluation using standard or caller-defined policy criteria.

#### Request Schema (`RegressionCheckRequest`)
```json
{
  "baseline_evaluation_id": "11111111-1111-1111-1111-111111111111",
  "candidate_evaluation_id": "22222222-2222-2222-2222-222222222222",
  "policy": null
}
```

#### Response Schema (`RegressionReport`)
```json
{
  "status": "REGRESSED",
  "is_regression": true,
  "baseline_evaluation_id": "11111111-1111-1111-1111-111111111111",
  "candidate_evaluation_id": "22222222-2222-2222-2222-222222222222",
  "policy_applied": {
    "name": "Standard Quality Gate",
    "max_score_drop": 5.0,
    "max_domain_drop": 10.0,
    "fail_on_risk_escalation": true,
    "fail_on_new_critical_findings": true,
    "prohibited_finding_codes": [
      "SECRET_EXPOSURE",
      "CYCLE_DETECTED"
    ],
    "min_overall_score": 75.0,
    "min_safety_score": 90.0
  },
  "overall_score_delta": -15.0,
  "risk_transition": "EXCELLENT -> CRITICAL",
  "violations": [
    {
      "rule": "OVERALL_SCORE_DROP",
      "severity": "HIGH",
      "message": "Overall score dropped by 15.0 points (threshold: -5.0)",
      "baseline_value": 95.0,
      "candidate_value": 80.0,
      "threshold": -5.0
    },
    {
      "rule": "PROHIBITED_FINDING_CODE",
      "severity": "CRITICAL",
      "message": "Prohibited finding code 'CYCLE_DETECTED' detected: Cyclic execution loop detected across steps 2..7",
      "baseline_value": null,
      "candidate_value": "CYCLE_DETECTED",
      "threshold": "PROHIBITED"
    }
  ],
  "violations_count": 2,
  "critical_violations_count": 2,
  "evaluated_at": "2026-11-08T12:00:00Z"
}
```

---

## 4. Frontend Integration

1. **`RegressionReportCard` Component**:
   - Visual badges for `PASSED`, `WARNING`, and `REGRESSED`.
   - KPI counters for score delta, risk transition, total violations, and critical breaches.
   - Detailed violation cards with rule names, severity tags, human-readable explanations, baseline vs candidate values, and policy thresholds.
   - Expandable applied policy viewer.

2. **Benchmarking Comparison View Integration**:
   - `ComparisonView` includes an interactive **"Run Regression Audit"** action trigger that queries the API and dynamically mounts the `RegressionReportCard` directly within the evaluation comparison flow.

---

## 5. Verification & Testing

- **Backend Unit Tests** (`backend/tests/services/test_regression_service.py`):
  - Validates missing evaluation handling (returns `None`).
  - Validates identical baseline and candidate runs pass with 0 violations.
  - Validates loop traces trigger score drop, risk escalation, and prohibited finding code rules.
  - Validates secret leak traces trigger safety floor breach and prohibited code rules.
  - Validates customizable permissive policies avoid false alarms.
- **Backend Integration Tests** (`backend/tests/api/test_regression_endpoints.py`):
  - Tests `GET /api/v1/regressions/policy/default`.
  - Tests `POST /api/v1/regressions/check` with 404 validation and end-to-end evaluation runs.
- **Frontend Vitest Suite** (`frontend/src/__tests__/regressions.test.tsx`):
  - Tests rendering of `PASSED` and `REGRESSED` verdicts, violation listings, and interactive policy accordion.
  - Tests integration with `ComparisonView`.

