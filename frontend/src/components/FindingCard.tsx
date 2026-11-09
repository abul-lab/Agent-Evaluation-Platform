import React from "react";
import { EvaluationFinding, FindingSeverity } from "@/lib/api";

interface FindingCardProps {
  finding: EvaluationFinding;
}

const SEVERITY_CONFIG: Record<
  FindingSeverity,
  { label: string; bg: string; text: string; border: string; badgeBg: string }
> = {
  INFO: {
    label: "INFO",
    bg: "bg-slate-50",
    text: "text-slate-700",
    border: "border-slate-200",
    badgeBg: "bg-slate-100 text-slate-700 border-slate-300",
  },
  LOW: {
    label: "LOW",
    bg: "bg-blue-50/60",
    text: "text-blue-800",
    border: "border-blue-200",
    badgeBg: "bg-blue-100 text-blue-800 border-blue-200",
  },
  MEDIUM: {
    label: "MEDIUM",
    bg: "bg-amber-50/60",
    text: "text-amber-800",
    border: "border-amber-200",
    badgeBg: "bg-amber-100 text-amber-800 border-amber-200",
  },
  HIGH: {
    label: "HIGH",
    bg: "bg-orange-50/60",
    text: "text-orange-800",
    border: "border-orange-200",
    badgeBg: "bg-orange-100 text-orange-800 border-orange-200",
  },
  CRITICAL: {
    label: "CRITICAL",
    bg: "bg-red-50/70",
    text: "text-red-800",
    border: "border-red-200",
    badgeBg: "bg-red-100 text-red-800 border-red-200",
  },
};

export function FindingCard({ finding }: FindingCardProps) {
  const cfg = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.INFO;
  const hasMetadata = Object.keys(finding.metadata || {}).length > 0;

  return (
    <div
      data-testid="finding-card"
      className={`rounded-xl border ${cfg.border} ${cfg.bg} p-4 shadow-xs transition hover:shadow-sm`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`rounded-md border px-2 py-0.5 text-xs font-bold ${cfg.badgeBg}`}
          >
            {cfg.label}
          </span>
          <span className="font-mono text-sm font-bold text-slate-900">
            {finding.code}
          </span>
        </div>

        {finding.affected_steps.length > 0 && (
          <span className="rounded border border-slate-200 bg-white px-2 py-0.5 font-mono text-xs text-slate-600">
            Steps: [{finding.affected_steps.join(", ")}]
          </span>
        )}
      </div>

      <p className="mt-2 text-sm text-slate-700 leading-relaxed">
        {finding.message}
      </p>

      {hasMetadata && (
        <details className="mt-3 group text-xs" open={finding.severity === "CRITICAL"}>
          <summary className="cursor-pointer font-semibold uppercase tracking-wider text-slate-600 hover:text-slate-900 select-none flex items-center gap-1.5 focus:outline-none">
            <span className="text-[10px] text-slate-500 transition-transform group-open:rotate-90">▶</span>
            <span>Metadata & Debug Context ({Object.keys(finding.metadata).length} {Object.keys(finding.metadata).length === 1 ? "field" : "fields"})</span>
          </summary>
          <div className="mt-2 rounded-lg border border-slate-200 bg-white p-3 shadow-xs">
            <pre className="overflow-x-auto font-mono text-slate-800 text-xs">
              {JSON.stringify(finding.metadata, null, 2)}
            </pre>
          </div>
        </details>
      )}
    </div>
  );
}

