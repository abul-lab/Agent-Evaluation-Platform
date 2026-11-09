"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  GovernanceVerdict,
  PolicyAuditResponse,
  PolicyCreateRequest,
  PolicyResponse,
  api,
} from "@/lib/api";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<PolicyResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Policy Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newPolicyName, setNewPolicyName] = useState("");
  const [newPolicyDesc, setNewPolicyDesc] = useState("");
  const [minScore, setMinScore] = useState(80);
  const [minSafetyScore, setMinSafetyScore] = useState(90);
  const [creating, setCreating] = useState(false);

  // Audit Playground State
  const [selectedPolicyId, setSelectedPolicyId] = useState<string>("");
  const [auditEvaluationId, setAuditEvaluationId] = useState<string>("");
  const [auditing, setAuditing] = useState(false);
  const [auditResult, setAuditResult] = useState<PolicyAuditResponse | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);

  const fetchPolicies = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listPolicies();
      setPolicies(data);
      if (data.length > 0 && !selectedPolicyId) {
        const defaultPol = data.find((p) => p.is_default) || data[0];
        setSelectedPolicyId(defaultPol.policy_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load policies");
    } finally {
      setLoading(false);
    }
  }, [selectedPolicyId]);

  useEffect(() => {
    fetchPolicies();
  }, [fetchPolicies]);

  const handleCreatePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPolicyName.trim()) return;

    try {
      setCreating(true);
      const req: PolicyCreateRequest = {
        name: newPolicyName.trim(),
        description: newPolicyDesc.trim(),
        is_active: true,
        is_default: false,
        rules: {
          min_overall_score: minScore,
          min_domain_scores: {
            task_quality: 80,
            tool_usage: 70,
            workflow_quality: 75,
            reliability: 75,
            safety: minSafetyScore,
            cost: 70,
            efficiency: 70,
          },
          disallowed_risk_tiers: ["CRITICAL", "POOR"],
          prohibited_finding_codes: ["SECRET_EXPOSURE", "CYCLE_DETECTED"],
          max_critical_findings: 0,
          max_high_findings: 1,
          require_semantic_evaluation: false,
        },
      };

      await api.createPolicy(req);
      setShowCreateModal(false);
      setNewPolicyName("");
      setNewPolicyDesc("");
      await fetchPolicies();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create policy");
    } finally {
      setCreating(false);
    }
  };

  const handleDeletePolicy = async (policyId: string) => {
    if (!confirm("Are you sure you want to delete this policy profile?")) return;
    try {
      await api.deletePolicy(policyId);
      await fetchPolicies();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete policy");
    }
  };

  const handleRunAudit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPolicyId || !auditEvaluationId.trim()) return;

    try {
      setAuditing(true);
      setAuditError(null);
      setAuditResult(null);
      const res = await api.auditEvaluation(selectedPolicyId, auditEvaluationId.trim());
      setAuditResult(res);
    } catch (err) {
      setAuditError(err instanceof Error ? err.message : "Audit failed");
    } finally {
      setAuditing(false);
    }
  };

  const renderVerdictBadge = (verdict: GovernanceVerdict) => {
    switch (verdict) {
      case "APPROVED":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            APPROVED — Release Cleared
          </span>
        );
      case "FLAGGED_FOR_REVIEW":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-bold text-amber-700">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            FLAGGED — Review Required
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-bold text-rose-700 animate-pulse">
            <span className="h-2 w-2 rounded-full bg-rose-500" />
            REJECTED — Release Blocked
          </span>
        );
    }
  };

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900 sm:text-3xl">
            Evaluation Policies & Governance
          </h1>
          <p className="mt-1 text-xs text-slate-500 sm:text-sm">
            Manage release gating criteria, enforce organizational score floors, and audit agent evaluations.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="self-start rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 transition"
        >
          + Create Policy Profile
        </button>
      </div>

      {/* 2. Error State */}
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {/* 3. Loading State */}
      {loading && (
        <div className="flex h-48 items-center justify-center rounded-xl border border-slate-200 bg-white shadow-sm">
          <span className="text-xs font-mono text-slate-500 animate-pulse">
            Loading governance policy profiles...
          </span>
        </div>
      )}

      {!loading && (
        <>
          {/* 4. Policy Profile Cards Grid */}
          <div className="space-y-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Active Governance Profiles ({policies.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {policies.map((policy) => (
                <div
                  key={policy.policy_id}
                  className="rounded-xl border border-slate-200 bg-white p-5 space-y-4 flex flex-col justify-between shadow-sm hover:shadow transition"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="font-bold text-slate-900 text-sm truncate">{policy.name}</h3>
                      <div className="flex items-center gap-1.5 shrink-0">
                        {policy.is_default && (
                          <span className="rounded bg-purple-50 border border-purple-200 px-2 py-0.5 text-[10px] font-bold text-purple-700">
                            DEFAULT
                          </span>
                        )}
                        <span
                          className={`rounded px-2 py-0.5 text-[10px] font-bold border ${
                            policy.is_active
                              ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                              : "bg-slate-100 border-slate-200 text-slate-600"
                          }`}
                        >
                          {policy.is_active ? "ACTIVE" : "INACTIVE"}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-slate-600 line-clamp-2">
                      {policy.description || "No description provided."}
                    </p>
                  </div>

                  {/* Rules Pill List */}
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-[11px] space-y-1.5 font-mono">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Min Overall Score:</span>
                      <strong className="text-emerald-600 font-bold">
                        {policy.rules.min_overall_score} pts
                      </strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Min Safety Score:</span>
                      <strong className="text-emerald-600 font-bold">
                        {policy.rules.min_domain_scores.safety ?? 90} pts
                      </strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Disallowed Tiers:</span>
                      <span className="text-rose-600 font-semibold truncate max-w-[120px]">
                        {policy.rules.disallowed_risk_tiers.join(", ")}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Prohibited Codes:</span>
                      <span className="text-amber-600 font-semibold truncate max-w-[120px]">
                        {policy.rules.prohibited_finding_codes.join(", ")}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-[10px] text-slate-500">
                    <span>ID: {policy.policy_id.slice(0, 8)}...</span>
                    {!policy.is_default && (
                      <button
                        onClick={() => handleDeletePolicy(policy.policy_id)}
                        className="text-rose-600 hover:text-rose-700 font-semibold transition"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 5. Governance Audit Playground */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-6 shadow-sm">
            <div className="border-b border-slate-100 pb-4">
              <h2 className="text-base font-bold text-slate-900">
                Evaluation Governance Audit Console
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Audit an evaluation against any active policy profile to produce an auditable release compliance verdict.
              </p>
            </div>

            <form onSubmit={handleRunAudit} className="flex flex-col sm:flex-row gap-4 items-end">
              <div className="flex-1 space-y-1.5 w-full">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                  Select Policy Profile
                </label>
                <select
                  value={selectedPolicyId}
                  onChange={(e) => setSelectedPolicyId(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-900 shadow-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  {policies.map((p) => (
                    <option key={p.policy_id} value={p.policy_id}>
                      {p.name} {p.is_default ? "(Default)" : ""}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex-1 space-y-1.5 w-full">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                  Target Evaluation ID (UUID)
                </label>
                <input
                  type="text"
                  placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
                  value={auditEvaluationId}
                  onChange={(e) => setAuditEvaluationId(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-mono text-slate-900 placeholder-slate-400 shadow-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={auditing}
                className="rounded-lg bg-blue-600 px-5 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-blue-700 disabled:opacity-50 transition shrink-0"
              >
                {auditing ? "Auditing..." : "Audit Evaluation"}
              </button>
            </form>

            {auditError && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700 font-medium">
                {auditError}
              </div>
            )}

            {/* Audit Outcome Panel */}
            {auditResult && (
              <div
                data-testid="audit-result-card"
                className="rounded-xl border border-slate-200 bg-slate-50/70 p-5 space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                      Audit Verdict: {auditResult.policy_name}
                    </h3>
                    <p className="text-xs text-slate-500 font-mono mt-0.5">
                      Eval ID: {auditResult.evaluation_id}
                    </p>
                  </div>
                  <div>{renderVerdictBadge(auditResult.verdict)}</div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                    <span className="text-[10px] uppercase text-slate-500 font-semibold">
                      Overall Score
                    </span>
                    <p className="font-mono text-lg font-bold text-slate-900 mt-0.5">
                      {auditResult.overall_score.toFixed(1)} pts
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                    <span className="text-[10px] uppercase text-slate-500 font-semibold">
                      Risk Tier
                    </span>
                    <p className="font-mono text-sm font-bold text-slate-800 mt-1">
                      {auditResult.risk_classification}
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                    <span className="text-[10px] uppercase text-slate-500 font-semibold">
                      Violations
                    </span>
                    <p
                      className={`font-mono text-lg font-bold mt-0.5 ${
                        auditResult.violations_count > 0 ? "text-amber-600" : "text-emerald-600"
                      }`}
                    >
                      {auditResult.violations_count}
                    </p>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
                    <span className="text-[10px] uppercase text-slate-500 font-semibold">
                      Critical Breaches
                    </span>
                    <p
                      className={`font-mono text-lg font-bold mt-0.5 ${
                        auditResult.critical_violations_count > 0
                          ? "text-rose-600"
                          : "text-emerald-600"
                      }`}
                    >
                      {auditResult.critical_violations_count}
                    </p>
                  </div>
                </div>

                {auditResult.violations.length > 0 ? (
                  <div className="space-y-2 pt-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                      Policy Breaches ({auditResult.violations.length})
                    </span>
                    <div className="space-y-2">
                      {auditResult.violations.map((v, i) => (
                        <div
                          key={i}
                          className="rounded-lg border border-rose-200 bg-rose-50/50 p-3 text-xs space-y-1 shadow-sm"
                        >
                          <div className="flex justify-between items-center">
                            <span className="font-mono font-bold text-rose-700">{v.rule_name}</span>
                            <span className="rounded bg-rose-100 border border-rose-200 px-1.5 py-0.5 text-[10px] font-bold text-rose-800">
                              {v.severity}
                            </span>
                          </div>
                          <p className="text-slate-700">{v.message}</p>
                          <div className="text-[11px] text-slate-500 font-mono flex gap-4 pt-1">
                            {v.actual_value !== null && <span>Actual: {String(v.actual_value)}</span>}
                            {v.expected_threshold !== null && (
                              <span>Required: {String(v.expected_threshold)}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-center">
                    <p className="text-xs text-emerald-700 font-semibold">
                      ✓ Zero policy breaches. Candidate execution meets all configured policy criteria.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {/* 6. Modal for Creating Policy Profile */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-slate-900">New Governance Policy Profile</h3>
            <form onSubmit={handleCreatePolicy} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="text-slate-700 font-medium">Policy Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Strict Production Gate"
                  value={newPolicyName}
                  onChange={(e) => setNewPolicyName(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white p-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-700 font-medium">Description</label>
                <textarea
                  placeholder="Purpose of this policy..."
                  value={newPolicyDesc}
                  onChange={(e) => setNewPolicyDesc(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white p-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-700 font-medium">Min Overall Score</label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={minScore}
                    onChange={(e) => setMinScore(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-200 bg-white p-2 text-slate-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-700 font-medium">Min Safety Score</label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={minSafetyScore}
                    onChange={(e) => setMinSafetyScore(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-200 bg-white p-2 text-slate-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-lg border border-slate-200 px-4 py-2 font-semibold text-slate-600 hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="rounded-lg bg-emerald-600 px-4 py-2 font-bold text-white hover:bg-emerald-700 disabled:opacity-50 transition shadow-sm"
                >
                  {creating ? "Creating..." : "Save Policy"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
