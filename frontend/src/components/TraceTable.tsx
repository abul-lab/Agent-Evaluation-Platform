import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { TraceSummaryItem, api } from "@/lib/api";

interface TraceTableProps {
  traces: TraceSummaryItem[];
  onRefresh?: () => void;
}

export function TraceTable({ traces, onRefresh }: TraceTableProps) {
  const router = useRouter();
  const [evaluatingId, setEvaluatingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleEvaluate = async (traceId: string) => {
    try {
      setEvaluatingId(traceId);
      setError(null);
      const res = await api.runEvaluation(traceId);
      router.push(`/evaluations/${res.evaluation_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Evaluation execution failed");
      setEvaluatingId(null);
    }
  };

  if (traces.length === 0) {
    return (
      <div
        data-testid="traces-empty"
        className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white p-12 text-center shadow-xs"
      >
        <p className="text-base font-medium text-slate-800">No Traces Found</p>
        <p className="mt-1 text-sm text-slate-500">
          Upload an execution trace to start evaluating agent workflows.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="trace-table" className="w-full space-y-3">
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
          {error}
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-xs">
        <table className="w-full text-left text-sm text-slate-700">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-600">
            <tr>
              <th scope="col" className="px-5 py-3.5">Trace ID</th>
              <th scope="col" className="px-5 py-3.5">Framework</th>
              <th scope="col" className="px-5 py-3.5">Status</th>
              <th scope="col" className="px-5 py-3.5">Steps</th>
              <th scope="col" className="px-5 py-3.5">Created At</th>
              <th scope="col" className="px-5 py-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-mono text-xs">
            {traces.map((trace) => {
              const isEvaluating = evaluatingId === trace.trace_id;
              const dateStr = new Date(trace.created_at).toLocaleString();

              const statusColor =
                trace.workflow_status === "SUCCESS"
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : "bg-amber-50 text-amber-700 border-amber-200";

              return (
                <tr
                  key={trace.trace_id}
                  className="transition hover:bg-slate-50/80"
                >
                  <td className="px-5 py-3.5 font-semibold">
                    <Link
                      href={`/traces/${trace.trace_id}`}
                      className="text-blue-600 hover:text-blue-700 hover:underline"
                    >
                      {trace.trace_id.slice(0, 8)}...{trace.trace_id.slice(-4)}
                    </Link>
                  </td>
                  <td className="px-5 py-3.5 text-slate-700 font-sans">
                    {trace.framework || "UNKNOWN"}
                  </td>
                  <td className="px-5 py-3.5">
                    <span
                      className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${statusColor}`}
                    >
                      {trace.workflow_status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 font-sans text-slate-700">
                    {trace.step_count}
                  </td>
                  <td className="px-5 py-3.5 font-sans text-slate-500">
                    {dateStr}
                  </td>
                  <td className="px-5 py-3.5 text-right font-sans">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        href={`/traces/${trace.trace_id}`}
                        className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-xs transition hover:bg-slate-50 hover:text-slate-900"
                      >
                        View
                      </Link>
                      <button
                        type="button"
                        onClick={() => handleEvaluate(trace.trace_id)}
                        disabled={isEvaluating}
                        className="rounded-md bg-emerald-600 px-2.5 py-1 text-xs font-semibold text-white shadow-xs transition hover:bg-emerald-700 disabled:opacity-50"
                      >
                        {isEvaluating ? "Evaluating..." : "Evaluate"}
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

