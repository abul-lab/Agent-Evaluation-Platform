import React from "react";
import { EvaluationFinding } from "@/lib/api";
import { FindingCard } from "./FindingCard";

interface FindingsListProps {
  findings: EvaluationFinding[];
}

export function FindingsList({ findings }: FindingsListProps) {
  if (findings.length === 0) {
    return (
      <div
        data-testid="findings-empty"
        className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white p-12 text-center shadow-xs"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200">
          <svg
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <h3 className="mt-4 text-base font-semibold text-slate-900">
          No Findings Detected
        </h3>
        <p className="mt-1 text-sm text-slate-500 max-w-md">
          Evaluation passed cleanly. No cycle loops, tool hallucinations, retry storms, budget breaches, or secret leaks were identified.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="findings-list" className="space-y-3">
      <div className="flex items-center justify-between pb-1">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Deterministic Findings ({findings.length})
        </h3>
      </div>
      <div className="grid grid-cols-1 gap-3">
        {findings.map((finding) => (
          <FindingCard key={finding.finding_id} finding={finding} />
        ))}
      </div>
    </div>
  );
}

