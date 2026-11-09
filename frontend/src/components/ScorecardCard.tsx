import React from "react";
import { Scorecard } from "@/lib/api";
import { RiskBadge } from "./RiskBadge";
import { DomainScoreCard } from "./DomainScoreCard";

interface ScorecardCardProps {
  scorecard: Scorecard;
}

export function ScorecardCard({ scorecard }: ScorecardCardProps) {
  const domains = [
    scorecard.task_quality,
    scorecard.tool_usage,
    scorecard.workflow_quality,
    scorecard.reliability,
    scorecard.safety,
    scorecard.cost,
    scorecard.efficiency,
  ];

  return (
    <div
      data-testid="scorecard-card"
      className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-6">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Evaluation Scorecard
          </span>
          <div className="mt-1 flex items-baseline gap-3">
            <span className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900">
              {scorecard.overall_score.toFixed(1)}
            </span>
            <span className="text-sm font-medium text-slate-500">/ 100 overall score</span>
          </div>
        </div>

        <div className="flex flex-col items-start sm:items-end gap-1.5">
          <span className="text-xs text-slate-500 font-medium">Risk Tier</span>
          <RiskBadge risk={scorecard.risk_classification} size="lg" />
        </div>
      </div>

      <div className="mt-6">
        <h3 className="mb-4 text-xs font-bold uppercase tracking-wider text-slate-500">
          Domain Breakdown
        </h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {domains.map((domain) => (
            <DomainScoreCard key={domain.name} domain={domain} />
          ))}
        </div>
      </div>
    </div>
  );
}

