"use client";

import React, { useState } from "react";
import { RegressionReport } from "@/lib/api";

interface RegressionReportCardProps {
  report: RegressionReport;
}

export function RegressionReportCard({ report }: RegressionReportCardProps) {
  const [showPolicy, setShowPolicy] = useState(false);

  const getStatusBadge = () => {
    switch (report.status) {
      case "PASSED":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
            <span className="h-2 w-2 rounded-full bg-emerald-600" />
            PASSED — Quality Gate Satisfied
          </span>
        );
      case "WARNING":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-bold text-amber-700">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            WARNING — Advisory Issues Detected
          </span>
        );
      case "REGRESSED":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-red-200 bg-red-50 px-3 py-1 text-xs font-bold text-red-700 animate-pulse">
            <span className="h-2 w-2 rounded-full bg-red-600" />
            REGRESSED — Quality Gate Breached
          </span>
        );
    }
  };

  return (
    <div
      data-testid="regression-report-card"
      className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-slate-900 tracking-wide uppercase">
              Regression Audit Verdict
            </h3>
            <span className="rounded border border-slate-200 bg-slate-100 px-2 py-0.5 text-[10px] font-mono text-slate-700">
              {report.policy_applied.name}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Evaluated at {new Date(report.evaluated_at).toLocaleString()}
          </p>
        </div>
        <div>{getStatusBadge()}</div>
      </div>

      {/* Metric Counters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Overall Score Delta
          </span>
          <p
            className={`font-mono text-lg font-bold mt-0.5 ${
              report.overall_score_delta > 0
                ? "text-emerald-700"
                : report.overall_score_delta < 0
                ? "text-red-700"
                : "text-slate-800"
            }`}
          >
            {report.overall_score_delta > 0 ? "+" : ""}
            {report.overall_score_delta.toFixed(1)} pts
          </p>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Risk Transition
          </span>
          <p className="font-mono text-sm font-bold text-slate-900 mt-1">
            {report.risk_transition}
          </p>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Total Violations
          </span>
          <p
            className={`font-mono text-lg font-bold mt-0.5 ${
              report.violations_count > 0 ? "text-amber-700" : "text-emerald-700"
            }`}
          >
            {report.violations_count}
          </p>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Critical Breaches
          </span>
          <p
            className={`font-mono text-lg font-bold mt-0.5 ${
              report.critical_violations_count > 0 ? "text-red-700" : "text-emerald-700"
            }`}
          >
            {report.critical_violations_count}
          </p>
        </div>
      </div>

      {/* Violations List */}
      {report.violations.length > 0 ? (
        <div className="space-y-2 mt-2">
          <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
            Detected Policy Violations ({report.violations.length})
          </span>
          <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
            {report.violations.map((violation, idx) => (
              <div
                key={idx}
                className={`rounded-lg border p-3 text-xs space-y-1.5 ${
                  violation.severity === "CRITICAL"
                    ? "border-red-200 bg-red-50/70"
                    : violation.severity === "HIGH"
                    ? "border-red-200 bg-red-50/50"
                    : "border-amber-200 bg-amber-50/50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-slate-900">
                    {violation.rule}
                  </span>
                  <span
                    className={`rounded border px-1.5 py-0.5 text-[10px] font-bold ${
                      violation.severity === "CRITICAL"
                        ? "bg-red-100 text-red-800 border-red-200"
                        : violation.severity === "HIGH"
                        ? "bg-red-50 text-red-700 border-red-200"
                        : "bg-amber-50 text-amber-700 border-amber-200"
                    }`}
                  >
                    {violation.severity}
                  </span>
                </div>
                <p className="text-slate-700">{violation.message}</p>
                <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-500 font-mono pt-1 border-t border-slate-100">
                  {violation.baseline_value !== null && (
                    <span>
                      Baseline: <strong className="text-slate-800">{String(violation.baseline_value)}</strong>
                    </span>
                  )}
                  {violation.candidate_value !== null && (
                    <span>
                      Candidate: <strong className="text-slate-800">{String(violation.candidate_value)}</strong>
                    </span>
                  )}
                  {violation.threshold !== null && (
                    <span>
                      Threshold: <strong className="text-amber-700">{String(violation.threshold)}</strong>
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-4 text-center">
          <p className="text-xs text-emerald-800 font-medium">
            ✓ Zero policy violations detected. Candidate run satisfies all release criteria.
          </p>
        </div>
      )}

      {/* Policy Details Accordion */}
      <div className="pt-2 border-t border-slate-100">
        <button
          onClick={() => setShowPolicy(!showPolicy)}
          className="text-[11px] font-medium text-slate-600 hover:text-slate-900 flex items-center gap-1 transition"
        >
          {showPolicy ? "▼ Hide Applied Quality Policy" : "▶ View Applied Quality Policy"}
        </button>

        {showPolicy && (
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-[11px]">
            <div>
              <span className="text-slate-500">Max Score Drop:</span>
              <p className="font-mono text-slate-800 font-semibold">-{report.policy_applied.max_score_drop} pts</p>
            </div>
            <div>
              <span className="text-slate-500">Max Domain Drop:</span>
              <p className="font-mono text-slate-800 font-semibold">-{report.policy_applied.max_domain_drop} pts</p>
            </div>
            <div>
              <span className="text-slate-500">Min Overall Score:</span>
              <p className="font-mono text-slate-800 font-semibold">{report.policy_applied.min_overall_score} pts</p>
            </div>
            <div>
              <span className="text-slate-500">Min Safety Score:</span>
              <p className="font-mono text-slate-800 font-semibold">{report.policy_applied.min_safety_score} pts</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

