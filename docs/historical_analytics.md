# Historical Analytics & Quality Trends Engine

## 1. Overview & Objectives

The **Historical Analytics & Quality Trends Engine** aggregates longitudinal evaluation records to track agent quality trajectories, operational reliability, finding frequency distributions, and evaluation volume over configurable time horizons.

Rather than auditing isolated traces or pair-wise evaluations, this engine provides system-level visibility into:
- **Longitudinal Quality Trajectory**: Determining whether agent performance is improving, degrading, or remaining stable over time.
- **Pass Rate Monitoring**: Measuring the proportion of evaluation runs achieving passing scores ($\ge 80.0$) across daily cohorts.
- **Evaluation Throughput**: Quantifying daily evaluation volume and testing cadence.
- **Risk Distribution**: Tracking the composition of risk tiers (`EXCELLENT`, `GOOD`, `WATCH`, `POOR`, `CRITICAL`) over the selected window.
- **Root-Cause Recurrence**: Identifying the most frequently occurring deterministic finding codes (e.g., `GRAPH_CYCLE_DETECTED`, `TOOL_REDUNDANT_CALL`) to guide agent prompt and tool engineering.
- **Domain Health Tracking**: Monitoring mean scores across all 7 evaluation domains (`task_quality`, `tool_usage`, `workflow_quality`, `reliability`, `safety`, `cost`, `efficiency`).

---

## 2. Mathematical & Algorithmic Formulations

### 2.1 Daily Cohort Bucketing

Let $\mathcal{E} = \{e_1, e_2, \dots, e_N\}$ be the chronological set of completed evaluation records within time window $[t_{\text{start}}, t_{\text{end}}]$.

Each evaluation $e_i$ is mapped to a discrete UTC date bucket $D_k$:

$$D_k = \{e \in \mathcal{E} \mid \text{date}(e.\text{completed\_at}) = k\}$$

For each day $k$ with non-empty bucket $D_k$:
- **Evaluation Count**: $N_k = |D_k|$
- **Average Overall Score**: 
  $$\overline{S}_k = \frac{1}{N_k} \sum_{e \in D_k} e.\text{overall\_score}$$
- **Pass Count**: 
  $$P_k = |\{e \in D_k \mid e.\text{overall\_score} \ge 80.0\}|$$
- **Daily Pass Rate**:
  $$\text{PassRate}_k = \frac{P_k}{N_k} \times 100\%$$
- **Total Findings**:
  $$F_k = \sum_{e \in D_k} e.\text{finding\_count}$$
- **Risk Counts**:
  $$R_{k, \text{tier}} = |\{e \in D_k \mid e.\text{risk\_classification} = \text{tier}\}|$$

### 2.2 Quality Trajectory Direction

To determine the overall trajectory without overfitting to day-to-day noise, the engine splits the ordered sequence of evaluations into two equal chronological halves:

Let $\mathcal{E}$ be sorted by `completed_at` ascending with size $N$:
- **First Half**: $\mathcal{E}_1 = \{e_1, \dots, e_{\lfloor N/2 \rfloor}\}$
- **Second Half**: $\mathcal{E}_2 = \{e_{\lfloor N/2 \rfloor + 1}, \dots, e_N\}$

The trajectory delta $\Delta_{\text{trajectory}}$ is defined as:

$$\Delta_{\text{trajectory}} = \overline{S}(\mathcal{E}_2) - \overline{S}(\mathcal{E}_1)$$

The trajectory is classified into three discrete directions using a significance threshold of $\epsilon = 1.5$:

$$\text{trajectory} = \begin{cases} 
\text{"IMPROVING"} & \text{if } \Delta_{\text{trajectory}} > +1.5 \\
\text{"DEGRADING"} & \text{if } \Delta_{\text{trajectory}} < -1.5 \\
\text{"STABLE"} & \text{otherwise}
\end{cases}$$

If $N < 2$, the trajectory defaults to `"STABLE"`.

### 2.3 Domain Averages

For each evaluation domain $d \in \{\text{task\_quality}, \text{tool\_usage}, \text{workflow\_quality}, \text{reliability}, \text{safety}, \text{cost}, \text{efficiency}\}$:

$$\overline{\text{Score}}_d = \frac{1}{|\mathcal{E}_d|} \sum_{e \in \mathcal{E}_d} \text{scorecard}(e)[d].\text{score}$$

where $\mathcal{E}_d \subseteq \mathcal{E}$ represents all evaluations containing a scorecard score for domain $d$.

### 2.4 Finding Frequency & Distribution

Let $\mathcal{F}_{\text{all}}$ be the multiset of all deterministic findings extracted from completed evaluations in $\mathcal{E}$.

For each distinct finding code $c$:
- **Count**: $C(c) = |\{f \in \mathcal{F}_{\text{all}} \mid f.\text{code} = c\}|$
- **Percentage**: 
  $$\text{Percentage}(c) = \frac{C(c)}{|\mathcal{F}_{\text{all}}|} \times 100\%$$

The results are ordered in descending order by frequency count.

---

## 3. API Specifications

### 3.1 `GET /api/v1/analytics/trends`

Retrieves historical quality metrics, daily time-series buckets, and finding recurrence distributions.

#### Query Parameters
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `days` | `integer` | `30` | Number of past days to query (`0` or negative indicates all historical records). |
| `limit` | `integer` | `500` | Maximum number of completed evaluation records to include. |

#### Response Schema (`AnalyticsTrendsResponse`)
```json
{
  "window_days": 30,
  "total_evaluations": 42,
  "average_overall_score": 84.5,
  "pass_rate": 88.1,
  "trajectory": "IMPROVING",
  "daily_buckets": [
    {
      "date": "2026-11-01",
      "eval_count": 5,
      "avg_overall_score": 82.0,
      "pass_count": 4,
      "pass_rate": 80.0,
      "total_findings": 3,
      "risk_counts": {
        "EXCELLENT": 2,
        "GOOD": 2,
        "WATCH": 1,
        "POOR": 0,
        "CRITICAL": 0
      }
    }
  ],
  "risk_distribution": {
    "EXCELLENT": 18,
    "GOOD": 15,
    "WATCH": 6,
    "POOR": 2,
    "CRITICAL": 1
  },
  "top_findings": [
    {
      "code": "TOOL_REDUNDANT_CALL",
      "count": 7,
      "percentage": 43.8
    },
    {
      "code": "GRAPH_CYCLE_DETECTED",
      "count": 3,
      "percentage": 18.8
    }
  ],
  "domain_averages": {
    "task_quality": 88.5,
    "tool_usage": 79.2,
    "workflow_quality": 85.0,
    "reliability": 90.1,
    "safety": 95.0,
    "cost": 82.4,
    "efficiency": 80.0
  }
}
```

---

## 4. Frontend Implementation

The analytics UI is accessible at `/analytics` and provides interactive, zero-dependency visualizations rendered natively using Tailwind CSS and responsive inline SVG elements.

### 4.1 Key Visual Components

1. **Time Horizon Selector**:
   - Preset pills for `7 Days`, `30 Days`, `90 Days`, and `All Time` that trigger asynchronous refetching without full-page reloads.

2. **Executive KPI Cards**:
   - Total Evaluations, Average Overall Score, System Pass Rate ($\ge 80.0$), and Trajectory Direction badge (`IMPROVING` in green, `DEGRADING` in red, `STABLE` in neutral).

3. **Inline SVG Score Trend Chart (`ScoreTrendChart`)**:
   - Area fill and polyline stroke tracking daily average scores over time.
   - Reference baseline at 80.0 (passing score threshold).
   - Interactive data points with date and score coordinates.

4. **Inline SVG Volume Bar Chart (`VolumeBarChart`)**:
   - Daily evaluation count bars with hover labels and proportional scaling.

5. **Finding Frequency Distribution (`FindingFrequencyChart`)**:
   - Horizontal progress bars visualizing top finding codes, raw counts, and percentage shares.

6. **Domain Health Grid**:
   - Multi-card overview showing average scores across all 7 evaluation dimensions.

---

## 5. Verification & Testing

The analytics engine is fully covered across backend services, API endpoints, and frontend components:

- **Backend Unit Tests** (`backend/tests/services/test_analytics_service.py`):
  - Validates empty database handling.
  - Validates multi-evaluation bucketing, pass rate calculations, and risk aggregation.
  - Validates `IMPROVING` vs `DEGRADING` trajectory direction detection.
- **Backend Integration Tests** (`backend/tests/api/test_analytics_endpoints.py`):
  - Validates `GET /api/v1/analytics/trends` route with default and custom query parameters.
- **Frontend Vitest Tests** (`frontend/src/__tests__/analytics.test.tsx`):
  - Tests rendering of KPI statistics, charts, time window filters, and loading states.

