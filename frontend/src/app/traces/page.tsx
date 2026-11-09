"use client";

import React, { useEffect, useState } from "react";
import { TraceSummaryItem, api } from "@/lib/api";
import { TraceTable } from "@/components/TraceTable";
import { UploadTraceCard } from "@/components/UploadTraceCard";

export default function TracesPage() {
  const [traces, setTraces] = useState<TraceSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTraces = async () => {
    try {
      setLoading(true);
      setError(null);
      const traceList = await api.getTraces(100, 0);
      setTraces(traceList);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to load traces from API"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTraces();
  }, []);

  const [searchTerm, setSearchTerm] = useState("");

  const filteredTraces = traces.filter((t) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      t.trace_id.toLowerCase().includes(term) ||
      (t.framework && t.framework.toLowerCase().includes(term)) ||
      t.workflow_status.toLowerCase().includes(term)
    );
  });

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
            Ingested Traces
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Browse ingested agent execution traces or upload a new trace for evaluation.
          </p>
        </div>
        <button
          type="button"
          onClick={() => fetchTraces()}
          className="self-start rounded-lg border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-700 shadow-xs transition hover:bg-slate-50 hover:text-slate-900"
        >
          Refresh Traces
        </button>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <UploadTraceCard onUploaded={() => fetchTraces()} />
        </div>

        <div className="lg:col-span-2 space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-lg font-bold text-slate-900">
              All Traces ({traces.length})
            </h2>

            {/* Quick search/filter input */}
            <div className="relative">
              <input
                type="text"
                placeholder="Filter by ID, framework, status..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full sm:w-64 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => setSearchTerm("")}
                  className="absolute right-2.5 top-1.5 text-xs text-slate-400 hover:text-slate-700"
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          {loading ? (
            <div className="rounded-xl border border-slate-200 bg-white p-6 space-y-3 animate-pulse shadow-xs">
              <div className="text-center text-sm text-slate-500">Loading traces...</div>
              <div className="h-8 rounded bg-slate-100" />
              <div className="h-8 rounded bg-slate-100" />
              <div className="h-8 rounded bg-slate-100" />
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-800">
              <p className="font-semibold">Error loading traces:</p>
              <p className="mt-1 font-mono text-xs">{error}</p>
              <button
                type="button"
                onClick={() => fetchTraces()}
                className="mt-3 rounded border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-xs hover:bg-slate-50 hover:text-slate-900"
              >
                Retry
              </button>
            </div>
          ) : (
            <TraceTable traces={filteredTraces} onRefresh={fetchTraces} />
          )}
        </div>
      </div>
    </main>
  );
}

