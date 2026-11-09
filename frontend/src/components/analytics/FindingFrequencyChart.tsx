import React from "react";
import { FindingFrequency } from "@/lib/api";

interface FindingFrequencyChartProps {
  findings: FindingFrequency[];
}

export function FindingFrequencyChart({ findings }: FindingFrequencyChartProps) {
  if (findings.length === 0) {
    return (
      <div
        data-testid="finding-frequency-empty"
        className="rounded-xl border border-dashed border-slate-200 bg-white p-6 text-center text-xs text-slate-500 italic shadow-xs"
      >
        Zero deterministic findings detected across the selected analytical window.
      </div>
    );
  }

  const maxCount = Math.max(...findings.map((f) => f.count), 1);

  return (
    <div
      data-testid="finding-frequency-chart"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-4"
    >
      <div>
        <h3 className="text-sm font-bold text-slate-900">Recurring Finding Distributions</h3>
        <p className="text-xs text-slate-500">
          Frequency of deterministic finding rules triggered across evaluated traces
        </p>
      </div>

      <div className="space-y-3">
        {findings.map((item) => {
          const percent = Math.max(8, Math.min(100, (item.count / maxCount) * 100));

          return (
            <div
              key={item.code}
              className="rounded-lg border border-slate-200 bg-slate-50/70 p-3 space-y-1.5 shadow-2xs"
            >
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-slate-900">
                    {item.code}
                  </span>
                  <span
                    className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold ${
                      item.severity === "CRITICAL" || item.severity === "HIGH"
                        ? "bg-red-50 text-red-700 border-red-200"
                        : "bg-amber-50 text-amber-700 border-amber-200"
                    }`}
                  >
                    {item.severity}
                  </span>
                </div>
                <span className="font-mono text-xs font-bold text-slate-900">
                  {item.count} {item.count === 1 ? "time" : "times"}
                </span>
              </div>

              <p className="text-[11px] text-slate-600">{item.description}</p>

              {/* Progress Bar */}
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    item.severity === "CRITICAL" || item.severity === "HIGH"
                      ? "bg-red-600"
                      : "bg-amber-500"
                  }`}
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

