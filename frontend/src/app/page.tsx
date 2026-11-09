"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { TraceSummaryItem, api } from "@/lib/api";
import { UploadTraceCard } from "@/components/UploadTraceCard";
import { TraceTable } from "@/components/TraceTable";

export default function OverviewPage() {
  const [traces, setTraces] = useState<TraceSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverviewData = async () => {
    try {
      setLoading(true);
      setError(null);
      const traceList = await api.getTraces(100, 0);
      setTraces(traceList);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load platform overview from backend"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverviewData();
  }, []);

  const totalSteps = traces.reduce((acc, t) => acc + t.step_count, 0);
  const successfulTraces = traces.filter((t) => t.workflow_status === "SUCCESS").length;

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
      {/* Hero Header */}
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Evaluation Operations Overview
        </h1>
        <p className="mt-2 text-sm text-slate-600 max-w-2xl">
          Continuous evaluation engine auditing agent workflows, tool selection fidelity,
          loop lockups, retry cascades, and safety compliance.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Total Traces
          </span>
          <div className="mt-2 text-3xl font-bold text-slate-900">
            {loading ? "..." : traces.length}
          </div>
          <p className="mt-1 text-xs text-slate-500">Persisted in CATS format</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Successful Workflows
          </span>
          <div className="mt-2 text-3xl font-bold text-emerald-600">
            {loading ? "..." : successfulTraces}
          </div>
          <p className="mt-1 text-xs text-slate-500">Nominal completion status</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Total Steps Audited
          </span>
          <div className="mt-2 text-3xl font-bold text-blue-600">
            {loading ? "..." : totalSteps}
          </div>
          <p className="mt-1 text-xs text-slate-500">Across all agent sessions</p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Evaluation Engine
          </span>
          <div className="mt-2 text-sm font-bold text-emerald-700 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-600" />
            7 Domains Active
          </div>
          <p className="mt-1 text-xs text-slate-500">Deterministic scoring & hard-gates</p>
        </div>
      </div>

      {/* Upload and Quick Access */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <UploadTraceCard onUploaded={() => fetchOverviewData()} />
        </div>

        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900">Recent Traces</h2>
            <Link
              href="/traces"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline"
            >
              View all traces →
            </Link>
          </div>

          {loading ? (
            <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-3 animate-pulse shadow-xs">
              <div className="text-center text-sm text-slate-500">Loading traces from API...</div>
              <div className="h-8 rounded bg-slate-100" />
              <div className="h-8 rounded bg-slate-100" />
              <div className="h-8 rounded bg-slate-100" />
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-800">
              <p className="font-semibold">Unable to fetch traces from backend:</p>
              <p className="mt-1 font-mono text-xs">{error}</p>
              <button
                type="button"
                onClick={() => fetchOverviewData()}
                className="mt-3 rounded border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-xs hover:bg-slate-50 hover:text-slate-900"
              >
                Retry Request
              </button>
            </div>
          ) : (
            <TraceTable traces={traces.slice(0, 5)} onRefresh={fetchOverviewData} />
          )}
        </div>
      </div>
    </main>
  );
}
