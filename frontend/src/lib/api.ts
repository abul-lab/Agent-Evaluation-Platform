/**
 * Strongly-typed API client for the Agent Evaluation Platform.
 * Direct mappings to backend FastAPI schemas.
 */

export type DomainStatus = "PASS" | "WARN" | "FAIL";

export type RiskClassification =
  | "EXCELLENT"
  | "GOOD"
  | "WATCH"
  | "POOR"
  | "CRITICAL";

export type FindingSeverity =
  | "INFO"
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL";

export interface DomainScore {
  name: string;
  score: number;
  status: DomainStatus;
  findings_count: number;
}

export interface EvaluationFinding {
  finding_id: string;
  severity: FindingSeverity;
  code: string;
  message: string;
  workflow_id: string;
  affected_steps: number[];
  metadata: Record<string, unknown>;
}

export interface SemanticFinding {
  finding_id: string;
  metric_name: string;
  score: number;
  passed: boolean;
  explanation: string;
}

export interface SemanticEvaluationResult {
  metrics: SemanticFinding[];
  provider: string;
  execution_time_ms: number;
  evaluation_available: boolean;
  reason: string | null;
}

export interface GraphNodeFinding {
  finding_id: string;
  severity: FindingSeverity;
  code: string;
  message: string;
}

export interface GraphToolCall {
  tool_call_id: string;
  tool_name: string;
  raw_arguments: Record<string, unknown>;
  parsed_arguments: Record<string, unknown> | null;
  execution_result: Record<string, unknown> | null;
  is_error: boolean;
  is_hallucinated: boolean;
  is_redundant: boolean;
  execution_time_ms: number;
}

export interface GraphRetry {
  retry_id: string;
  attempt_number: number;
  error_type: string;
  backoff_duration_ms: number;
  resolution: string;
}

export interface WorkflowGraphNode {
  id: string;
  step_id: string;
  step_index: number;
  node_name: string;
  agent_id: string;
  agent_name: string;
  latency_ms: number;
  token_usage: Record<string, number>;
  input_state: Record<string, unknown>;
  output_state: Record<string, unknown>;
  tool_calls: GraphToolCall[];
  retries: GraphRetry[];
  findings: GraphNodeFinding[];
  is_cycle_node: boolean;
}

export interface WorkflowGraphEdge {
  id: string;
  source: string;
  target: string;
  is_cycle_edge: boolean;
  label: string | null;
}

export interface WorkflowGraphResponse {
  evaluation_id: string;
  trace_id: string;
  workflow_id: string;
  workflow_status: string;
  total_steps: number;
  has_cycles: boolean;
  nodes: WorkflowGraphNode[];
  edges: WorkflowGraphEdge[];
}

export interface DomainScoreDelta {
  domain_name: string;
  base_score: number;
  target_score: number;
  score_delta: number;
  base_status: DomainStatus;
  target_status: DomainStatus;
}

export interface FindingDelta {
  new_findings: EvaluationFinding[];
  resolved_findings: EvaluationFinding[];
  persistent_findings: EvaluationFinding[];
  new_count: number;
  resolved_count: number;
  persistent_count: number;
  total_delta: number;
}

export interface RiskTransition {
  base_risk: RiskClassification;
  target_risk: RiskClassification;
  is_improved: boolean;
  is_degraded: boolean;
}

export interface EvaluationComparisonResponse {
  base_evaluation_id: string;
  target_evaluation_id: string;
  base_trace_id: string;
  target_trace_id: string;
  base_score: number;
  target_score: number;
  overall_score_delta: number;
  risk_transition: RiskTransition;
  domain_deltas: Record<string, DomainScoreDelta>;
  finding_delta: FindingDelta;
  compared_at: string;
}

export interface BenchmarkLeaderboardItem {
  rank: number;
  evaluation_id: string;
  trace_id: string;
  overall_score: number;
  risk_classification: RiskClassification;
  finding_count: number;
  workflow_status: string;
  started_at: string;
  completed_at: string | null;
}

export interface BenchmarkSummaryResponse {
  total_evaluations: number;
  mean_score: number;
  min_score: number;
  max_score: number;
  pass_rate: number;
  risk_distribution: Record<string, number>;
  leaderboard: BenchmarkLeaderboardItem[];
}

export interface FindingFrequency {
  code: string;
  count: number;
  severity: FindingSeverity;
  description: string;
}

export interface DailyAnalyticsBucket {
  date: string;
  evaluation_count: number;
  average_score: number;
  risk_counts: Record<string, number>;
  total_findings: number;
  finding_counts: Record<string, number>;
}

export interface AnalyticsTrendsResponse {
  time_window_days: number;
  total_evaluations: number;
  average_score: number;
  score_trend_direction: "IMPROVING" | "DEGRADING" | "STABLE";
  pass_rate: number;
  risk_distribution: Record<string, number>;
  domain_averages: Record<string, number>;
  finding_distribution: FindingFrequency[];
  daily_metrics: DailyAnalyticsBucket[];
}

export type RegressionStatus = "PASSED" | "WARNING" | "REGRESSED";

export interface RegressionPolicy {
  name: string;
  max_score_drop: number;
  max_domain_drop: number;
  fail_on_risk_escalation: boolean;
  fail_on_new_critical_findings: boolean;
  prohibited_finding_codes: string[];
  min_overall_score: number;
  min_safety_score: number;
}

export interface RegressionViolation {
  rule: string;
  severity: FindingSeverity;
  message: string;
  baseline_value: string | number | boolean | null;
  candidate_value: string | number | boolean | null;
  threshold: string | number | boolean | null;
}

export interface RegressionReport {
  status: RegressionStatus;
  is_regression: boolean;
  baseline_evaluation_id: string;
  candidate_evaluation_id: string;
  policy_applied: RegressionPolicy;
  overall_score_delta: number;
  risk_transition: string;
  violations: RegressionViolation[];
  violations_count: number;
  critical_violations_count: number;
  evaluated_at: string;
}

export type GovernanceVerdict = "APPROVED" | "FLAGGED_FOR_REVIEW" | "REJECTED";

export interface PolicyRules {
  min_overall_score: number;
  min_domain_scores: Record<string, number>;
  disallowed_risk_tiers: string[];
  prohibited_finding_codes: string[];
  max_critical_findings: number;
  max_high_findings: number;
  require_semantic_evaluation: boolean;
}

export interface PolicyResponse {
  policy_id: string;
  name: string;
  description: string;
  is_active: boolean;
  is_default: boolean;
  rules: PolicyRules;
  created_at: string;
  updated_at: string;
}

export interface PolicyCreateRequest {
  name: string;
  description?: string;
  is_active?: boolean;
  is_default?: boolean;
  rules?: Partial<PolicyRules>;
}

export interface PolicyViolation {
  rule_name: string;
  severity: string;
  message: string;
  actual_value: string | number | boolean | null;
  expected_threshold: string | number | boolean | null;
}

export interface PolicyAuditResponse {
  audit_id: string;
  policy_id: string;
  policy_name: string;
  evaluation_id: string;
  verdict: GovernanceVerdict;
  passed: boolean;
  violations: PolicyViolation[];
  violations_count: number;
  critical_violations_count: number;
  overall_score: number;
  risk_classification: string;
  audited_at: string;
}

export type WorkspaceRole = "ADMIN" | "ENGINEER" | "VIEWER";
export type ServiceAccountRole = "ADMIN" | "ENGINEER" | "VIEWER";

export interface APIKeyCreateRequest {
  name: string;
  workspace_id?: string;
  role: ServiceAccountRole;
  created_by?: string;
  expires_in_days?: number | null;
}

export interface APIKeyCreateResponse {
  key_id: string;
  workspace_id: string;
  name: string;
  raw_key: string;
  key_prefix: string;
  role: ServiceAccountRole;
  created_by: string;
  created_at: string;
  expires_at: string | null;
  is_active: boolean;
}

export interface APIKeyResponse {
  key_id: string;
  workspace_id: string;
  name: string;
  key_prefix: string;
  role: ServiceAccountRole;
  created_by: string;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
  is_active: boolean;
}

export interface WorkspaceResponse {
  workspace_id: string;
  name: string;
  slug: string;
  description: string;
  is_default: boolean;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface DemoSeedResponse {
  workspace_id: string;
  name: string;
  slug: string;
  traces_seeded: number;
  evaluations_seeded: number;
  policies_seeded: number;
  channels_seeded: number;
  api_key_prefix: string;
  status: string;
}

export interface WorkspaceCreateRequest {
  name: string;
  slug?: string;
  description?: string;
  is_default?: boolean;
}

export interface WorkspaceMemberResponse {
  member_id: string;
  workspace_id: string;
  user_email: string;
  role: WorkspaceRole;
  joined_at: string;
}

export interface WorkspaceMemberAddRequest {
  user_email: string;
  role?: WorkspaceRole;
}

export interface WorkspaceAuditLogResponse {
  log_id: string;
  workspace_id: string;
  actor_email: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
  created_at: string;
}

export type NotificationChannelType = "TEAMS" | "SLACK" | "WEBHOOK";

export type NotificationEventType =
  | "EVALUATION_COMPLETED"
  | "EVALUATION_FAILED"
  | "REGRESSION_DETECTED"
  | "POLICY_APPROVED"
  | "POLICY_REJECTED"
  | "SECRET_EXPOSURE"
  | "CRITICAL_FINDING"
  | "API_KEY_CREATED"
  | "API_KEY_REVOKED";

export interface NotificationChannelCreateRequest {
  name: string;
  channel_type: NotificationChannelType;
  webhook_url: string;
  events?: NotificationEventType[];
}

export interface NotificationChannelResponse {
  channel_id: string;
  workspace_id: string;
  name: string;
  channel_type: NotificationChannelType;
  webhook_url_masked: string;
  events: NotificationEventType[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationDeliveryResponse {
  delivery_id: string;
  channel_id: string;
  workspace_id: string;
  event_type: string;
  status: "PENDING" | "DELIVERED" | "FAILED";
  http_status: number | null;
  error_message: string | null;
  delivered_at: string | null;
  created_at: string;
}

export interface NotificationTestResponse {
  status: string;
  channel_id: string;
  channel_name: string;
  channel_type: NotificationChannelType;
  http_status: number | null;
  message: string;
}

export interface Scorecard {
  scorecard_id: string;
  workflow_id: string;
  task_quality: DomainScore;
  tool_usage: DomainScore;
  workflow_quality: DomainScore;
  reliability: DomainScore;
  safety: DomainScore;
  cost: DomainScore;
  efficiency: DomainScore;
  overall_score: number;
  risk_classification: RiskClassification;
  findings: EvaluationFinding[];
}

export interface TraceValidationResponse {
  valid: boolean;
  step_count: number;
  workflow_status: string;
  warnings: string[];
}

export interface TraceUploadResponse {
  trace_id: string;
  stored: boolean;
  step_count: number;
  workflow_status: string;
}

export interface TraceSummaryItem {
  trace_id: string;
  workflow_status: string;
  step_count: number;
  created_at: string;
  framework: string;
}

export interface TraceMetadataResponse {
  trace_id: string;
  created_at: string;
  workflow_status: string;
  step_count: number;
  framework: string;
}

export interface EvaluationRunRequest {
  trace_id: string;
}

export interface EvaluationRunResponse {
  evaluation_id: string;
  status: string;
  finding_count: number;
  overall_score: number;
  risk_classification: RiskClassification;
}

export interface EvaluationSummaryResponse {
  evaluation_id: string;
  trace_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  finding_count: number;
  overall_score: number;
  risk_classification: RiskClassification;
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/**
 * Optional API key for browser sessions against a backend that requires authentication.
 * It is read from localStorage under "aep_api_key" (set it in the browser console for now).
 * Never bake keys into NEXT_PUBLIC_* variables: those are shipped to every visitor.
 */
const API_KEY_STORAGE_KEY = "aep_api_key";

function authHeaders(): Record<string, string> {
  try {
    const key = typeof window !== "undefined" ? window.localStorage.getItem(API_KEY_STORAGE_KEY) : null;
    return key ? { Authorization: `Bearer ${key}` } : {};
  } catch {
    return {};
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...options?.headers,
      },
    });

    if (!res.ok) {
      let detail = `Request failed with status ${res.status}`;
      try {
        const errorBody = (await res.json()) as { detail?: unknown };
        if (typeof errorBody.detail === "string") {
          detail = errorBody.detail;
        } else if (Array.isArray(errorBody.detail)) {
          detail = JSON.stringify(errorBody.detail);
        }
      } catch {
        // Fallback to text status
      }
      throw new ApiError(res.status, detail);
    }

    return (await res.json()) as T;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : "Network failure";
    throw new ApiError(0, message);
  }
}

export const api = {
  getTraces: (limit = 100, offset = 0): Promise<TraceSummaryItem[]> =>
    request<TraceSummaryItem[]>(`/traces?limit=${limit}&offset=${offset}`),

  getTrace: (traceId: string): Promise<TraceMetadataResponse> =>
    request<TraceMetadataResponse>(`/traces/${traceId}`),

  validateTrace: (tracePayload: Record<string, unknown>): Promise<TraceValidationResponse> =>
    request<TraceValidationResponse>("/traces/validate", {
      method: "POST",
      body: JSON.stringify(tracePayload),
    }),

  uploadTrace: (tracePayload: Record<string, unknown>): Promise<TraceUploadResponse> =>
    request<TraceUploadResponse>("/traces/upload", {
      method: "POST",
      body: JSON.stringify(tracePayload),
    }),

  runEvaluation: (traceId: string): Promise<EvaluationRunResponse> =>
    request<EvaluationRunResponse>("/evaluations/run", {
      method: "POST",
      body: JSON.stringify({ trace_id: traceId }),
    }),

  getEvaluation: (evaluationId: string): Promise<EvaluationSummaryResponse> =>
    request<EvaluationSummaryResponse>(`/evaluations/${evaluationId}`),

  getScorecard: (evaluationId: string): Promise<Scorecard> =>
    request<Scorecard>(`/evaluations/${evaluationId}/scorecard`),

  getFindings: (evaluationId: string): Promise<EvaluationFinding[]> =>
    request<EvaluationFinding[]>(`/evaluations/${evaluationId}/findings`),

  getSemanticResult: (evaluationId: string): Promise<SemanticEvaluationResult> =>
    request<SemanticEvaluationResult>(`/evaluations/${evaluationId}/semantic`),

  getEvaluationGraph: (evaluationId: string): Promise<WorkflowGraphResponse> =>
    request<WorkflowGraphResponse>(`/evaluations/${evaluationId}/graph`),

  compareEvaluations: (
    baseEvaluationId: string,
    targetEvaluationId: string
  ): Promise<EvaluationComparisonResponse> =>
    request<EvaluationComparisonResponse>("/benchmarks/compare", {
      method: "POST",
      body: JSON.stringify({
        base_evaluation_id: baseEvaluationId,
        target_evaluation_id: targetEvaluationId,
      }),
    }),

  getBenchmarkSummary: (
    limit = 100,
    offset = 0
  ): Promise<BenchmarkSummaryResponse> =>
    request<BenchmarkSummaryResponse>(
      `/benchmarks/summary?limit=${limit}&offset=${offset}`
    ),

  getAnalyticsTrends: (
    days = 30,
    limit = 500
  ): Promise<AnalyticsTrendsResponse> =>
    request<AnalyticsTrendsResponse>(
      `/analytics/trends?days=${days}&limit=${limit}`
    ),

  getDefaultRegressionPolicy: (): Promise<RegressionPolicy> =>
    request<RegressionPolicy>("/regressions/policy/default"),

  checkRegression: (
    baselineEvaluationId: string,
    candidateEvaluationId: string,
    policy?: RegressionPolicy
  ): Promise<RegressionReport> =>
    request<RegressionReport>("/regressions/check", {
      method: "POST",
      body: JSON.stringify({
        baseline_evaluation_id: baselineEvaluationId,
        candidate_evaluation_id: candidateEvaluationId,
        policy: policy ?? null,
      }),
    }),

  listPolicies: (activeOnly = false): Promise<PolicyResponse[]> =>
    request<PolicyResponse[]>(`/policies?active_only=${activeOnly}`),

  getActivePolicy: (): Promise<PolicyResponse> =>
    request<PolicyResponse>("/policies/active"),

  getPolicy: (policyId: string): Promise<PolicyResponse> =>
    request<PolicyResponse>(`/policies/${policyId}`),

  createPolicy: (req: PolicyCreateRequest): Promise<PolicyResponse> =>
    request<PolicyResponse>("/policies", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  updatePolicy: (
    policyId: string,
    req: Partial<PolicyCreateRequest>
  ): Promise<PolicyResponse> =>
    request<PolicyResponse>(`/policies/${policyId}`, {
      method: "PUT",
      body: JSON.stringify(req),
    }),

  deletePolicy: (policyId: string): Promise<void> =>
    request<void>(`/policies/${policyId}`, {
      method: "DELETE",
    }),

  auditEvaluation: (
    policyId: string,
    evaluationId: string
  ): Promise<PolicyAuditResponse> =>
    request<PolicyAuditResponse>(`/policies/${policyId}/audit/${evaluationId}`, {
      method: "POST",
    }),

  listWorkspaces: (): Promise<WorkspaceResponse[]> =>
    request<WorkspaceResponse[]>("/workspaces"),

  seedDemoWorkspace: (): Promise<DemoSeedResponse> =>
    request<DemoSeedResponse>("/workspaces/demo/seed", {
      method: "POST",
    }),

  getDefaultWorkspace: (): Promise<WorkspaceResponse> =>
    request<WorkspaceResponse>("/workspaces/default"),

  getWorkspace: (workspaceId: string): Promise<WorkspaceResponse> =>
    request<WorkspaceResponse>(`/workspaces/${workspaceId}`),

  createWorkspace: (req: WorkspaceCreateRequest): Promise<WorkspaceResponse> =>
    request<WorkspaceResponse>("/workspaces", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  updateWorkspace: (
    workspaceId: string,
    req: Partial<WorkspaceCreateRequest>
  ): Promise<WorkspaceResponse> =>
    request<WorkspaceResponse>(`/workspaces/${workspaceId}`, {
      method: "PUT",
      body: JSON.stringify(req),
    }),

  deleteWorkspace: (workspaceId: string): Promise<void> =>
    request<void>(`/workspaces/${workspaceId}`, {
      method: "DELETE",
    }),

  listWorkspaceMembers: (
    workspaceId: string
  ): Promise<WorkspaceMemberResponse[]> =>
    request<WorkspaceMemberResponse[]>(`/workspaces/${workspaceId}/members`),

  addWorkspaceMember: (
    workspaceId: string,
    req: WorkspaceMemberAddRequest
  ): Promise<WorkspaceMemberResponse> =>
    request<WorkspaceMemberResponse>(`/workspaces/${workspaceId}/members`, {
      method: "POST",
      body: JSON.stringify(req),
    }),

  removeWorkspaceMember: (
    workspaceId: string,
    memberId: string
  ): Promise<void> =>
    request<void>(`/workspaces/${workspaceId}/members/${memberId}`, {
      method: "DELETE",
    }),

  listWorkspaceAuditLogs: (
    workspaceId: string,
    limit = 50
  ): Promise<WorkspaceAuditLogResponse[]> =>
    request<WorkspaceAuditLogResponse[]>(
      `/workspaces/${workspaceId}/audit-logs?limit=${limit}`
    ),

  listApiKeys: (workspaceId?: string): Promise<APIKeyResponse[]> =>
    request<APIKeyResponse[]>(
      workspaceId ? `/auth/api-keys?workspace_id=${workspaceId}` : `/auth/api-keys`
    ),

  createApiKey: (req: APIKeyCreateRequest): Promise<APIKeyCreateResponse> =>
    request<APIKeyCreateResponse>(`/auth/api-keys`, {
      method: "POST",
      body: JSON.stringify(req),
    }),

  revokeApiKey: (keyId: string): Promise<{ key_id: string; revoked: boolean }> =>
    request<{ key_id: string; revoked: boolean }>(`/auth/api-keys/${keyId}`, {
      method: "DELETE",
    }),

  listNotificationChannels: (
    workspaceId: string
  ): Promise<NotificationChannelResponse[]> =>
    request<NotificationChannelResponse[]>(
      `/workspaces/${workspaceId}/notifications/channels`
    ),

  createNotificationChannel: (
    workspaceId: string,
    req: NotificationChannelCreateRequest
  ): Promise<NotificationChannelResponse> =>
    request<NotificationChannelResponse>(
      `/workspaces/${workspaceId}/notifications/channels`,
      {
        method: "POST",
        body: JSON.stringify(req),
      }
    ),

  deleteNotificationChannel: (
    workspaceId: string,
    channelId: string
  ): Promise<void> =>
    request<void>(
      `/workspaces/${workspaceId}/notifications/channels/${channelId}`,
      {
        method: "DELETE",
      }
    ),

  testNotificationChannel: (
    workspaceId: string,
    channelId: string,
    customMessage?: string
  ): Promise<NotificationTestResponse> =>
    request<NotificationTestResponse>(
      `/workspaces/${workspaceId}/notifications/channels/${channelId}/test`,
      {
        method: "POST",
        body: JSON.stringify({ custom_message: customMessage }),
      }
    ),

  listNotificationHistory: (
    workspaceId: string,
    limit = 50
  ): Promise<NotificationDeliveryResponse[]> =>
    request<NotificationDeliveryResponse[]>(
      `/workspaces/${workspaceId}/notifications/history?limit=${limit}`
    ),

  getExportUrl: (evaluationId: string, format: "json" | "markdown" | "csv"): string =>
    `${API_BASE}/evaluations/${evaluationId}/export/${format}`,

  downloadExport: async (
    evaluationId: string,
    format: "json" | "markdown" | "csv"
  ): Promise<void> => {
    const url = `${API_BASE}/evaluations/${evaluationId}/export/${format}`;
    const res = await fetch(url, { headers: authHeaders() });
    if (!res.ok) {
      throw new ApiError(res.status, `Export download failed with status ${res.status}`);
    }
    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = downloadUrl;
    const ext = format === "markdown" ? "md" : format;
    a.download = `evaluation_${evaluationId}.${ext}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },
};

