# Evaluation Policies & Governance Engine

## 1. Overview & Objectives

The **Evaluation Policies & Governance Engine** establishes a release governance layer for autonomous agent deployments. It provides persistent, versioned, configurable quality profiles and deterministic audit pipelines to evaluate agent evaluation records against organizational safety and performance standards.

Key capabilities include:
- **Persistent Policy Profiles**: Store named, customizable governance profiles (e.g. `Standard Governance Policy`, `Strict Release Policy`, `Canary Stage Policy`) in SQLite via SQLModel.
- **Automated Default Auto-Seeding**: Self-bootstraps a platform default policy (`Standard Governance Policy`) if no default exists.
- **Deterministic Release Verdicts**: Maps evaluation scores, domain floors, finding counts, and risk tiers to three formal governance verdicts:
  - `APPROVED`: Meets all organizational criteria; release cleared.
  - `FLAGGED_FOR_REVIEW`: Quality warning or non-critical breach; human review required.
  - `REJECTED`: Critical policy failure, prohibited finding code, or excessive high-severity defects; release blocked.
- **Granular Threshold Enforcement**: Enforces composite score minimums, 7-domain score floors, disallowed risk tiers, and prohibited finding codes (`SECRET_EXPOSURE`, `CYCLE_DETECTED`).
- **Interactive Governance Console**: Next.js 14 interface at `/policies` allowing operators to view profiles, manage policy rules, and run live governance audits on evaluation runs.

---

## 2. Governance Decision Logic & Resolution Matrix

Let $E$ be an Evaluation Record and $P$ be a Governance Policy Profile with rules $R$.

### 2.1 Enforced Quality Rules

1. **Overall Score Floor**:
   $$\text{Score}(E) < R.\text{min\_overall\_score} \implies \text{Violation}(\text{"MIN\_OVERALL\_SCORE\_BREACH"}, \, \text{HIGH})$$

2. **Domain Minimums**:
   $$\forall d \in \text{Domains}: \text{Score}_d(E) < R.\text{min\_domain\_scores}[d] \implies \text{Violation}(\text{"DOMAIN\_SCORE\_FLOOR\_"} + d, \, \text{CRITICAL if } d = \text{safety else HIGH})$$

3. **Disallowed Risk Tiers**:
   $$\text{Risk}(E) \in R.\text{disallowed\_risk\_tiers} \implies \text{Violation}(\text{"DISALLOWED\_RISK\_TIER"}, \, \text{CRITICAL})$$

4. **Prohibited Finding Codes**:
   $$\exists f \in \text{Findings}(E) : f.\text{code} \in R.\text{prohibited\_finding\_codes} \implies \text{Violation}(\text{"PROHIBITED\_FINDING\_CODE"}, \, \text{CRITICAL})$$

5. **Finding Count Quotas**:
   $$|\{f \mid f.\text{severity} = \text{CRITICAL}\}| > R.\text{max\_critical\_findings} \implies \text{Violation}(\text{"EXCESSIVE\_CRITICAL\_FINDINGS"}, \, \text{CRITICAL})$$
   $$|\{f \mid f.\text{severity} = \text{HIGH}\}| > R.\text{max\_high\_findings} \implies \text{Violation}(\text{"EXCESSIVE\_HIGH\_FINDINGS"}, \, \text{HIGH})$$

6. **Semantic Evaluation Requirement**:
   $$R.\text{require\_semantic\_evaluation} \land E.\text{semantic\_json} = \text{null} \implies \text{Violation}(\text{"MISSING\_SEMANTIC\_EVALUATION"}, \, \text{MEDIUM})$$

### 2.2 Verdict Decision Matrix

$$\text{Verdict}(E, P) = \begin{cases}
\text{REJECTED} & \text{if } \text{Count}(\text{CRITICAL Violations}) > 0 \\
\text{FLAGGED\_FOR\_REVIEW} & \text{if } \text{Count}(\text{HIGH or MEDIUM Violations}) > 0 \\
\text{APPROVED} & \text{if } \text{Count}(\text{Total Violations}) = 0
\end{cases}$$

---

## 3. API Specifications

### 3.1 `GET /api/v1/policies`
Lists all governance policies. Supports `?active_only=true` filter.

### 3.2 `GET /api/v1/policies/active`
Retrieves or auto-seeds the platform default active policy profile.

### 3.3 `POST /api/v1/policies`
Creates and persists a new policy profile.

```json
{
  "name": "Strict Governance Policy",
  "description": "High-assurance release policy",
  "is_active": true,
  "is_default": false,
  "rules": {
    "min_overall_score": 85.0,
    "min_domain_scores": {
      "safety": 95.0,
      "task_quality": 85.0
    },
    "disallowed_risk_tiers": ["CRITICAL", "POOR", "WATCH"],
    "prohibited_finding_codes": ["SECRET_EXPOSURE", "CYCLE_DETECTED"],
    "max_critical_findings": 0,
    "max_high_findings": 0
  }
}
```

### 3.4 `GET /api/v1/policies/{policy_id}`
Retrieves a specific policy profile by UUID.

### 3.5 `PUT /api/v1/policies/{policy_id}`
Updates an existing policy profile.

### 3.6 `DELETE /api/v1/policies/{policy_id}`
Deletes a custom policy. Refuses deletion of the default policy with HTTP 400.

### 3.7 `POST /api/v1/policies/{policy_id}/audit/{evaluation_id}`
Audits an evaluation run against the designated policy profile.

#### Response Schema (`PolicyAuditResponse`)
```json
{
  "audit_id": "88888888-8888-8888-8888-888888888888",
  "policy_id": "11111111-1111-1111-1111-111111111111",
  "policy_name": "Standard Platform Gate",
  "evaluation_id": "44444444-4444-4444-4444-444444444444",
  "verdict": "APPROVED",
  "passed": true,
  "violations": [],
  "violations_count": 0,
  "critical_violations_count": 0,
  "overall_score": 95.0,
  "risk_classification": "EXCELLENT",
  "audited_at": "2026-11-08T12:00:00Z"
}
```

---

## 4. Frontend Governance Console

Available at `/policies`:
- **Profile Cards**: Displays all configured policies with `DEFAULT` and `ACTIVE` pills, score thresholds, disallowed tiers, and prohibited codes.
- **Profile Creator**: Modal dialog to configure and save new organizational governance policies.
- **Live Audit Console**: Interactive form to select a policy profile and evaluation ID, displaying real-time compliance results, metric summaries, and itemized violation cards.

---

## 5. Verification & Testing

- **Backend Unit Tests** (`backend/tests/services/test_policy_service.py`):
  - Validates auto-seeding of default policy.
  - Validates policy creation, listing, updating, and deletion guardrails.
  - Validates `APPROVED` verdict on clean evaluation.
  - Validates `REJECTED` verdict on loop trace with prohibited codes.
- **Backend Integration Tests** (`backend/tests/api/test_policy_endpoints.py`):
  - Validates all CRUD endpoints and `POST /policies/{id}/audit/{eval_id}` endpoint.
- **Frontend Vitest Suite** (`frontend/src/__tests__/policies.test.tsx`):
  - Validates policy card rendering, modal creation submission, and audit execution with verdict presentation.

