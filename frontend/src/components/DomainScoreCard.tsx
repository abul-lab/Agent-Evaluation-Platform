import React from "react";
import { DomainScore, DomainStatus } from "@/lib/api";

interface DomainScoreCardProps {
  domain: DomainScore;
}

const STATUS_CONFIG: Record<
  DomainStatus,
  { label: string; text: string; bg: string; border: string; bar: string }
> = {
  PASS: {
    label: "PASS",
    text: "text-emerald-700",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    bar: "bg-emerald-600",
  },
  WARN: {
    label: "WARN",
    text: "text-amber-700",
    bg: "bg-amber-50",
    border: "border-amber-200",
    bar: "bg-amber-500",
  },
  FAIL: {
    label: "FAIL",
    text: "text-red-700",
    bg: "bg-red-50",
    border: "border-red-200",
    bar: "bg-red-600",
  },
};

export function DomainScoreCard({ domain }: DomainScoreCardProps) {
  const statusCfg = STATUS_CONFIG[domain.status] || STATUS_CONFIG.WARN;
  const scorePercent = Math.max(0, Math.min(100, domain.score));

  return (
    <div
      data-testid="domain-score-card"
      className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-xs transition hover:border-slate-300"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold capitalize text-slate-900">
            {domain.name.replace("_", " ")}
          </h4>
          <p className="text-xs text-slate-500">
            {domain.findings_count === 1
              ? "1 finding"
              : `${domain.findings_count} findings`}
          </p>
        </div>
        <span
          className={`rounded-md border px-2 py-0.5 text-[11px] font-bold ${statusCfg.bg} ${statusCfg.text} ${statusCfg.border}`}
        >
          {statusCfg.label}
        </span>
      </div>

      <div className="mt-4">
        <div className="flex items-baseline justify-between">
          <span className="text-2xl font-bold tracking-tight text-slate-900">
            {domain.score.toFixed(1)}
          </span>
          <span className="text-xs text-slate-500">/ 100</span>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full rounded-full transition-all duration-300 ${statusCfg.bar}`}
            style={{ width: `${scorePercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}

