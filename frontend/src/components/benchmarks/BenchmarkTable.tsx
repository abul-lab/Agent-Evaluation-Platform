import React from "react";
import Link from "next/link";
import { BenchmarkLeaderboardItem } from "@/lib/api";
import { RiskBadge } from "@/components/RiskBadge";

interface BenchmarkTableProps {
  leaderboard: BenchmarkLeaderboardItem[];
  baseId?: string | null;
  targetId?: string | null;
  onSelectBase: (id: string) => void;
  onSelectTarget: (id: string) => void;
}

export function BenchmarkTable({
  leaderboard,
  baseId,
  targetId,
  onSelectBase,
  onSelectTarget,
}: BenchmarkTableProps) {
  if (leaderboard.length === 0) {
    return (
      <div
        data-testid="benchmark-table-empty"
        className="rounded-xl border border-dashed border-slate-200 bg-white p-8 text-center text-sm text-slate-500 shadow-xs"
      >
        No evaluations found for benchmarking. Upload and evaluate traces to populate the leaderboard.
      </div>
    );
  }

  return (
    <div
      data-testid="benchmark-table"
      className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs"
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-600 uppercase tracking-wider font-semibold">
            <tr>
              <th className="py-3 px-4 w-12 text-center">Rank</th>
              <th className="py-3 px-4">Evaluation</th>
              <th className="py-3 px-4">Trace</th>
              <th className="py-3 px-4 text-center">Score</th>
              <th className="py-3 px-4 text-center">Risk</th>
              <th className="py-3 px-4 text-center">Findings</th>
              <th className="py-3 px-4 text-right">Compare Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-700">
            {leaderboard.map((item) => {
              const isBase = baseId === item.evaluation_id;
              const isTarget = targetId === item.evaluation_id;

              return (
                <tr
                  key={item.evaluation_id}
                  className={`hover:bg-slate-50 transition ${
                    isBase || isTarget ? "bg-blue-50/40" : ""
                  }`}
                >
                  {/* Rank */}
                  <td className="py-3 px-4 text-center font-mono font-bold">
                    <span
                      className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-[11px] ${
                        item.rank === 1
                          ? "bg-amber-100 text-amber-800 border border-amber-300 font-bold"
                          : item.rank === 2
                          ? "bg-slate-200 text-slate-800 border border-slate-300 font-bold"
                          : item.rank === 3
                          ? "bg-amber-50 text-amber-800 border border-amber-200 font-bold"
                          : "bg-slate-100 text-slate-600 font-medium"
                      }`}
                    >
                      {item.rank}
                    </span>
                  </td>

                  {/* Evaluation ID */}
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/evaluations/${item.evaluation_id}`}
                        className="font-mono text-blue-600 hover:text-blue-700 hover:underline truncate max-w-[150px] font-semibold"
                        title={item.evaluation_id}
                      >
                        {item.evaluation_id.slice(0, 8)}...
                      </Link>
                      {isBase && (
                        <span className="rounded bg-blue-100 border border-blue-200 px-1.5 py-0.5 text-[10px] font-bold text-blue-700">
                          BASE
                        </span>
                      )}
                      {isTarget && (
                        <span className="rounded bg-emerald-100 border border-emerald-200 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700">
                          TARGET
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Trace ID */}
                  <td className="py-3 px-4 font-mono text-slate-500">
                    <Link
                      href={`/traces/${item.trace_id}`}
                      className="hover:text-blue-600 hover:underline"
                    >
                      {item.trace_id.slice(0, 8)}...
                    </Link>
                  </td>

                  {/* Overall Score */}
                  <td className="py-3 px-4 text-center font-mono font-bold text-sm">
                    <span
                      className={
                        item.overall_score >= 80
                          ? "text-emerald-700"
                          : item.overall_score >= 60
                          ? "text-amber-700"
                          : "text-red-700"
                      }
                    >
                      {item.overall_score.toFixed(1)}
                    </span>
                  </td>

                  {/* Risk Tier */}
                  <td className="py-3 px-4 text-center">
                    <RiskBadge risk={item.risk_classification} />
                  </td>

                  {/* Finding Count */}
                  <td className="py-3 px-4 text-center font-mono text-slate-800 font-medium">
                    {item.finding_count}
                  </td>

                  {/* Compare Quick-Actions */}
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        type="button"
                        onClick={() => onSelectBase(item.evaluation_id)}
                        className={`rounded px-2.5 py-1 text-[11px] font-semibold transition ${
                          isBase
                            ? "bg-blue-600 text-white"
                            : "border border-slate-200 bg-white text-slate-700 shadow-xs hover:bg-slate-50 hover:text-slate-900"
                        }`}
                      >
                        Base
                      </button>
                      <button
                        type="button"
                        onClick={() => onSelectTarget(item.evaluation_id)}
                        className={`rounded px-2.5 py-1 text-[11px] font-semibold transition ${
                          isTarget
                            ? "bg-emerald-600 text-white"
                            : "border border-slate-200 bg-white text-slate-700 shadow-xs hover:bg-slate-50 hover:text-slate-900"
                        }`}
                      >
                        Target
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

