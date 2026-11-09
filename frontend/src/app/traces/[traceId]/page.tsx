"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { TraceMetadataResponse, api } from "@/lib/api";

export default function TraceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const traceId = params.traceId as string;

  const [trace, setTrace] = useState<TraceMetadataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!traceId) return;

    const fetchTraceDetail = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getTrace(traceId);
        setTrace(data);
      } catch (err: unknown) {
        setError(
          err instanceof Error
            ? err.message
            : `Failed to load trace '${traceId}' from backend`
        );
      } finally {
        setLoading(false);
      }
    };

    fetchTraceDetail();
  }, [traceId]);

  const handleRunEvaluation = async () => {
    try {
      setEvaluating(true);
      setError(null);
      const res = await api.runEvaluation(traceId);
      router.push(`/evaluations/${res.evaluation_id}`);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to execute evaluation against this trace"
      );
      setEvaluating(false);
    }
  };

  if (loading) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12">
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500 shadow-xs animate-pulse">
          Loading trace details...
        </div>
      </main>
    );
  }

  if (error || !trace) {
    return (
      <main className="mx-auto max-w-5xl px-6 py-12 space-y-4">
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-800 shadow-xs">
          <h2 className="text-base font-bold text-red-900">Trace Error</h2>
          <p className="mt-1 font-mono text-xs">{error || "Trace not found"}</p>
        </div>
        <Link
          href="/traces"
          className="inline-block text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline"
        >
          ← Back to traces
        </Link>
      </main>
    );
  }

  const dateStr = new Date(trace.created_at).toLocaleString();
  const statusColor =
    trace.workflow_status === "SUCCESS"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : "bg-amber-50 text-amber-700 border-amber-200";

  return (
    <main className="mx-auto max-w-5xl px-6 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <Link
          href="/traces"
          className="text-xs font-semibold text-slate-600 hover:text-slate-900"
        >
          ← Back to traces
        </Link>
        <span className="font-mono text-xs text-slate-500">ID: {trace.trace_id}</span>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-6">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Agent Trace Detail
            </span>
            <h1 className="mt-1 font-mono text-xl sm:text-2xl font-bold text-slate-900">
              {trace.trace_id}
            </h1>
          </div>
          <button
            type="button"
            onClick={handleRunEvaluation}
            disabled={evaluating}
            className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-5 py-2.5 text-xs font-bold text-white shadow-xs transition hover:bg-emerald-700 disabled:opacity-50"
          >
            {evaluating ? "Running Evaluation..." : "Run Evaluation →"}
          </button>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-6 sm:grid-cols-4 text-xs">
          <div>
            <span className="text-slate-500 font-medium">Framework</span>
            <div className="mt-1.5 text-sm font-semibold text-slate-900">
              {trace.framework || "UNKNOWN"}
            </div>
          </div>

          <div>
            <span className="text-slate-500 font-medium">Workflow Status</span>
            <div className="mt-1.5">
              <span
                className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusColor}`}
              >
                {trace.workflow_status}
              </span>
            </div>
          </div>

          <div>
            <span className="text-slate-500 font-medium">Execution Steps</span>
            <div className="mt-1.5 text-sm font-semibold text-slate-900">
              {trace.step_count}
            </div>
          </div>

          <div>
            <span className="text-slate-500 font-medium">Ingestion Timestamp</span>
            <div className="mt-1.5 font-sans text-xs text-slate-700">
              {dateStr}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

