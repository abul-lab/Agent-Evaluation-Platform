import React, { useState } from "react";
import Link from "next/link";
import { EvaluationComparisonResponse, EvaluationFinding, RegressionReport, api } from "@/lib/api";
import { RiskBadge } from "@/components/RiskBadge";
import { RegressionReportCard } from "@/components/regressions/RegressionReportCard";

interface ComparisonViewProps {
  comparison: EvaluationComparisonResponse;
}

export function ComparisonView({ comparison }: ComparisonViewProps) {
  const [findingTab, setFindingTab] = useState<"new" | "resolved" | "persistent">("new");
  const [regressionReport, setRegressionReport] = useState<RegressionReport | null>(null);
  const [loadingRegression, setLoadingRegression] = useState(false);
  const [regressionError, setRegressionError] = useState<string | null>(null);

  const handleRunRegressionCheck = async () => {
    try {
      setLoadingRegression(true);
      setRegressionError(null);
      const res = await api.checkRegression(
        comparison.base_evaluation_id,
        comparison.target_evaluation_id
      );
      setRegressionReport(res);
    } catch (err) {
      setRegressionError(err instanceof Error ? err.message : "Failed to audit regressions.");
    } finally {
      setLoadingRegression(false);
    }
  };

  const isPositive = comparison.overall_score_delta > 0;
  const isNegative = comparison.overall_score_delta < 0;

  const renderFindingCard = (finding: EvaluationFinding, variant: "new" | "resolved" | "persistent") => (
    <div
      key={finding.finding_id}
      className={`rounded-lg border p-3 text-xs space-y-1.5 transition ${
        variant === "new"
          ? "border-red-200 bg-red-50/50"
          : variant === "resolved"
          ? "border-emerald-200 bg-emerald-50/50"
          : "border-slate-200 bg-slate-50/50"
      }`}
    >
      <div className="flex items-center justify-between">
        <span
          className={`font-mono font-bold ${
            variant === "new"
              ? "text-red-700"
              : variant === "resolved"
              ? "text-emerald-700"
              : "text-slate-800"
          }`}
        >
          {finding.code}
        </span>
        <span
          className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold ${
            finding.severity === "CRITICAL" || finding.severity === "HIGH"
              ? "bg-red-100 text-red-800 border-red-200"
              : "bg-amber-100 text-amber-800 border-amber-200"
          }`}
        >
          {finding.severity}
        </span>
      </div>
      <p className="text-slate-700">{finding.message}</p>
      {finding.affected_steps.length > 0 && (
        <span className="text-[10px] text-slate-500 font-mono">
          Steps affected: {finding.affected_steps.join(", ")}
        </span>
      )}
    </div>
  );

  return (
    <div
      data-testid="comparison-view"
      className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-xs"
    >
      {/* 1. Comparison Summary Hero Banner */}
      <div className="flex flex-col md:flex-row items-stretch justify-between gap-6 border-b border-slate-100 pb-6">
        {/* Baseline Evaluation */}
        <div className="flex-1 rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Baseline Run
            </span>
            <RiskBadge risk={comparison.risk_transition.base_risk} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-3xl font-extrabold text-slate-900">
              {comparison.base_score.toFixed(1)}
            </span>
            <span className="text-xs text-slate-500">/ 100</span>
          </div>
          <Link
            href={`/evaluations/${comparison.base_evaluation_id}`}
            className="inline-block font-mono text-[11px] text-blue-600 hover:underline truncate max-w-full font-semibold"
          >
            Eval: {comparison.base_evaluation_id}
          </Link>
        </div>

        {/* Delta Card */}
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-slate-50 px-6 py-4 text-center min-w-[200px]">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Score Delta
          </span>
          <span
            className={`font-mono text-3xl font-black mt-1 ${
              isPositive
                ? "text-emerald-700"
                : isNegative
                ? "text-red-700"
                : "text-slate-800"
            }`}
          >
            {comparison.overall_score_delta > 0 ? "+" : ""}
            {comparison.overall_score_delta.toFixed(1)}
          </span>

          {/* Risk Transition Pill */}
          <div className="mt-2 flex items-center gap-1.5 text-xs">
            <span className="font-mono font-bold text-slate-800">
              {comparison.risk_transition.base_risk} → {comparison.risk_transition.target_risk}
            </span>
          </div>
          {comparison.risk_transition.is_improved && (
            <span className="mt-1 rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
              Risk Improved
            </span>
          )}
          {comparison.risk_transition.is_degraded && (
            <span className="mt-1 rounded-full bg-red-50 border border-red-200 px-2 py-0.5 text-[10px] font-bold text-red-700">
              Risk Degraded
            </span>
          )}
        </div>

        {/* Target / Candidate Evaluation */}
        <div className="flex-1 rounded-xl border border-slate-200 bg-slate-50/70 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Candidate Run
            </span>
            <RiskBadge risk={comparison.risk_transition.target_risk} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-3xl font-extrabold text-slate-900">
              {comparison.target_score.toFixed(1)}
            </span>
            <span className="text-xs text-slate-500">/ 100</span>
          </div>
          <Link
            href={`/evaluations/${comparison.target_evaluation_id}`}
            className="inline-block font-mono text-[11px] text-blue-600 hover:underline truncate max-w-full font-semibold"
          >
            Eval: {comparison.target_evaluation_id}
          </Link>
        </div>
      </div>

      {/* 2. Automated Regression Audit Trigger & Result */}
      <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h4 className="text-sm font-bold text-slate-900">Quality Gate & Regression Detection</h4>
            <p className="text-xs text-slate-500">
              Audit candidate against release criteria: score thresholds, critical findings, and risk escalations.
            </p>
          </div>
          <button
            onClick={handleRunRegressionCheck}
            disabled={loadingRegression}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-emerald-700 disabled:opacity-50 transition"
          >
            {loadingRegression ? "Auditing Regressions..." : "Run Regression Audit"}
          </button>
        </div>

        {regressionError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
            {regressionError}
          </div>
        )}

        {regressionReport && (
          <div className="pt-2">
            <RegressionReportCard report={regressionReport} />
          </div>
        )}
      </div>

      {/* 3. Domain-by-Domain Variance Grid */}
      <div>
        <h4 className="text-sm font-bold text-slate-900 mb-3">Domain Score Variance</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {Object.values(comparison.domain_deltas).map((d) => {
            const hasImproved = d.score_delta > 0;
            const hasDegraded = d.score_delta < 0;

            return (
              <div
                key={d.domain_name}
                className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 flex flex-col justify-between space-y-2 shadow-2xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-xs capitalize text-slate-800">
                    {d.domain_name.replace(/_/g, " ")}
                  </span>
                  <span
                    className={`font-mono text-xs font-bold ${
                      hasImproved
                        ? "text-emerald-700"
                        : hasDegraded
                        ? "text-red-700"
                        : "text-slate-600"
                    }`}
                  >
                    {d.score_delta > 0 ? "+" : ""}
                    {d.score_delta.toFixed(1)}
                  </span>
                </div>

                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span className="font-mono">
                    {d.base_score.toFixed(0)} → {d.target_score.toFixed(0)}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    {d.base_status} → {d.target_status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Findings Delta Breakdown */}
      <div>
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-bold text-slate-900">Finding Changes</h4>
            <span
              className={`font-mono text-xs font-bold rounded px-1.5 py-0.5 ${
                comparison.finding_delta.total_delta < 0
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  : comparison.finding_delta.total_delta > 0
                  ? "bg-red-50 text-red-700 border border-red-200"
                  : "bg-slate-100 text-slate-600"
              }`}
            >
              Net: {comparison.finding_delta.total_delta > 0 ? "+" : ""}
              {comparison.finding_delta.total_delta}
            </span>
          </div>

          <div className="flex gap-1.5 text-xs font-semibold">
            <button
              type="button"
              onClick={() => setFindingTab("new")}
              className={`rounded-lg px-2.5 py-1 transition ${
                findingTab === "new"
                  ? "bg-red-50 text-red-700 border border-red-200 font-bold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              New ({comparison.finding_delta.new_count})
            </button>
            <button
              type="button"
              onClick={() => setFindingTab("resolved")}
              className={`rounded-lg px-2.5 py-1 transition ${
                findingTab === "resolved"
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Resolved ({comparison.finding_delta.resolved_count})
            </button>
            <button
              type="button"
              onClick={() => setFindingTab("persistent")}
              className={`rounded-lg px-2.5 py-1 transition ${
                findingTab === "persistent"
                  ? "bg-slate-100 text-slate-900 border border-slate-300 font-bold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Persistent ({comparison.finding_delta.persistent_count})
            </button>
          </div>
        </div>

        {/* Tab content */}
        <div className="mt-3">
          {findingTab === "new" && (
            <div>
              {comparison.finding_delta.new_findings.length === 0 ? (
                <p className="text-xs text-slate-500 italic py-2">
                  No new findings introduced in candidate run.
                </p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {comparison.finding_delta.new_findings.map((f) =>
                    renderFindingCard(f, "new")
                  )}
                </div>
              )}
            </div>
          )}

          {findingTab === "resolved" && (
            <div>
              {comparison.finding_delta.resolved_findings.length === 0 ? (
                <p className="text-xs text-slate-500 italic py-2">
                  No findings resolved between baseline and candidate.
                </p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {comparison.finding_delta.resolved_findings.map((f) =>
                    renderFindingCard(f, "resolved")
                  )}
                </div>
              )}
            </div>
          )}

          {findingTab === "persistent" && (
            <div>
              {comparison.finding_delta.persistent_findings.length === 0 ? (
                <p className="text-xs text-slate-500 italic py-2">
                  Zero persisting findings shared across both runs.
                </p>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {comparison.finding_delta.persistent_findings.map((f) =>
                    renderFindingCard(f, "persistent")
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

