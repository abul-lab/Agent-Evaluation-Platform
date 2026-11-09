import React from "react";
import Link from "next/link";
import { EvaluationSummaryResponse } from "@/lib/api";
import { RiskBadge } from "./RiskBadge";

interface EvaluationSummaryProps {
  summary: EvaluationSummaryResponse;
}

export function EvaluationSummary({ summary }: EvaluationSummaryProps) {
  const startedStr = new Date(summary.started_at).toLocaleString();
  const completedStr = summary.completed_at
    ? new Date(summary.completed_at).toLocaleString()
    : "In progress";

  return (
    <div
      data-testid="evaluation-summary"
      className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-5">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Evaluation Run Overview
          </span>
          <h2 className="mt-1 font-mono text-lg font-bold text-slate-900">
            {summary.evaluation_id}
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <RiskBadge risk={summary.risk_classification} size="md" />
          <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
            {summary.status}
          </span>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
        <div>
          <span className="text-slate-500 font-medium">Trace Reference</span>
          <div className="mt-1 font-mono font-medium truncate">
            <Link
              href={`/traces/${summary.trace_id}`}
              className="text-blue-600 hover:text-blue-700 hover:underline font-semibold"
            >
              {summary.trace_id.slice(0, 8)}...{summary.trace_id.slice(-4)}
            </Link>
          </div>
        </div>

        <div>
          <span className="text-slate-500 font-medium">Findings Count</span>
          <div className="mt-1 text-sm font-bold text-slate-900">
            {summary.finding_count}
          </div>
        </div>

        <div>
          <span className="text-slate-500 font-medium">Started At</span>
          <div className="mt-1 font-sans text-slate-700">{startedStr}</div>
        </div>

        <div>
          <span className="text-slate-500 font-medium">Completed At</span>
          <div className="mt-1 font-sans text-slate-700">{completedStr}</div>
        </div>
      </div>
    </div>
  );
}

