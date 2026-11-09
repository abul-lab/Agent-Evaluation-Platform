import React from "react";
import { SemanticEvaluationResult } from "@/lib/api";

interface SemanticEvaluationCardProps {
  semanticResult: SemanticEvaluationResult | null;
  loading?: boolean;
}

export function SemanticEvaluationCard({
  semanticResult,
  loading = false,
}: SemanticEvaluationCardProps) {
  if (loading) {
    return (
      <div
        data-testid="semantic-evaluation-card"
        className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm"
      >
        Loading semantic evaluation results...
      </div>
    );
  }

  if (!semanticResult) {
    return null;
  }

  const isAvailable = semanticResult.evaluation_available;

  return (
    <div
      data-testid="semantic-evaluation-card"
      className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-base font-semibold text-slate-900">
              Semantic Evaluation
            </h3>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                isAvailable
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  : "bg-slate-100 text-slate-600 border border-slate-200"
              }`}
            >
              Provider: {semanticResult.provider}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Additive semantic quality judges (Answer Relevancy, Faithfulness, Hallucination)
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>Execution: {semanticResult.execution_time_ms} ms</span>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-medium text-xs border ${
              isAvailable
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : "bg-amber-50 text-amber-700 border-amber-200"
            }`}
          >
            {isAvailable ? "Active" : "Offline Fallback"}
          </span>
        </div>
      </div>

      {/* Fallback state notice */}
      {!isAvailable ? (
        <div
          data-testid="semantic-fallback-banner"
          className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900"
        >
          <div className="flex items-start gap-2">
            <span className="font-semibold text-amber-800">Notice:</span>
            <div className="space-y-1">
              <p>
                {semanticResult.reason ||
                  "Semantic evaluation unavailable. Platform operating in pure deterministic mode."}
              </p>
              <p className="text-slate-600">
                Deterministic evaluation remains primary and fully functional. Semantic evaluation is optional and additive.
              </p>
            </div>
          </div>
        </div>
      ) : (
        /* Semantic findings table */
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 uppercase tracking-wider">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Metric</th>
                <th className="py-2.5 px-3 font-semibold">Status</th>
                <th className="py-2.5 px-3 font-semibold">Score</th>
                <th className="py-2.5 px-3 font-semibold">Explanation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {semanticResult.metrics.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-4 px-3 text-center text-slate-400">
                    No semantic metric findings recorded.
                  </td>
                </tr>
              ) : (
                semanticResult.metrics.map((metric) => (
                  <tr key={metric.finding_id} className="hover:bg-slate-50 transition">
                    <td className="py-3 px-3 font-semibold capitalize text-slate-900">
                      {metric.metric_name.replace(/_/g, " ")}
                    </td>
                    <td className="py-3 px-3">
                      <span
                        className={`inline-block rounded-md px-2 py-0.5 text-xs font-semibold ${
                          metric.passed
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : "bg-red-50 text-red-700 border border-red-200"
                        }`}
                      >
                        {metric.passed ? "PASS" : "FAIL"}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-900 font-medium">
                      {(metric.score * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 px-3 text-slate-600 max-w-md">
                      {metric.explanation}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

