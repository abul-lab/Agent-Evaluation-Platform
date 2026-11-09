"use client";

import React, { useEffect, useState } from "react";
import {
  BenchmarkSummaryResponse,
  EvaluationComparisonResponse,
  api,
} from "@/lib/api";
import { BenchmarkTable } from "@/components/benchmarks/BenchmarkTable";
import { ComparisonView } from "@/components/benchmarks/ComparisonView";

export default function BenchmarksPage() {
  const [summary, setSummary] = useState<BenchmarkSummaryResponse | null>(null);
  const [baseId, setBaseId] = useState<string>("");
  const [targetId, setTargetId] = useState<string>("");
  const [comparison, setComparison] = useState<EvaluationComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"all" | "comparator" | "leaderboard">("all");

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getBenchmarkSummary(100, 0);
        setSummary(data);

        // Pre-select top 2 for convenient immediate comparison if available
        if (data.leaderboard.length >= 2) {
          setBaseId(data.leaderboard[1].evaluation_id);
          setTargetId(data.leaderboard[0].evaluation_id);
        } else if (data.leaderboard.length === 1) {
          setBaseId(data.leaderboard[0].evaluation_id);
          setTargetId(data.leaderboard[0].evaluation_id);
        }
      } catch (err: unknown) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load benchmark summary"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, []);

  const handleCompare = async () => {
    if (!baseId || !targetId) {
      setComparisonError("Please select both a baseline and candidate evaluation.");
      return;
    }

    try {
      setComparing(true);
      setComparisonError(null);
      const res = await api.compareEvaluations(baseId, targetId);
      setComparison(res);
    } catch (err: unknown) {
      setComparisonError(
        err instanceof Error ? err.message : "Failed to execute evaluation comparison"
      );
    } finally {
      setComparing(false);
    }
  };

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-12 space-y-6">
        <div className="h-8 w-64 rounded bg-slate-200 animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-pulse">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 rounded-xl border border-slate-200 bg-white shadow-xs" />
          ))}
        </div>
        <div className="h-48 rounded-xl border border-slate-200 bg-white shadow-xs animate-pulse flex items-center justify-center">
          <span className="text-sm text-slate-500">Loading benchmarking suite and evaluation leaderboards...</span>
        </div>
      </main>
    );
  }

  if (error || !summary) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-12">
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-800 shadow-xs">
          <h2 className="text-base font-bold text-red-900">Benchmark Error</h2>
          <p className="mt-1 font-mono text-xs">{error || "Unable to load summary"}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
      {/* 1. Header with Segmented View Controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight sm:text-3xl">
            Benchmarking & Comparison
          </h1>
          <p className="mt-1 text-xs text-slate-600 max-w-3xl">
            Evaluation versus evaluation variance analysis, score deltas, finding progression, and ranked dataset leaderboards.
          </p>
        </div>

        {/* View Mode Segmented Controls */}
        <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-1 text-xs font-semibold self-start sm:self-auto shadow-xs">
          {[
            { id: "all", label: "Unified View" },
            { id: "comparator", label: "Comparator" },
            { id: "leaderboard", label: "Leaderboard" },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as "all" | "comparator" | "leaderboard")}
              className={`rounded-md px-3 py-1.5 transition ${
                activeTab === tab.id
                  ? "bg-slate-100 text-slate-900 font-bold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 2. Statistical Metrics Header */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500">Total Evaluations</span>
          <p className="mt-2 font-mono text-2xl font-bold text-slate-900">
            {summary.total_evaluations}
          </p>
          <span className="text-[11px] text-slate-500">Evaluated traces</span>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500">Mean Score</span>
          <p className="mt-2 font-mono text-2xl font-bold text-emerald-600">
            {summary.mean_score.toFixed(1)}
          </p>
          <span className="text-[11px] text-slate-500">Across all runs</span>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500">Top Benchmark Score</span>
          <p className="mt-2 font-mono text-2xl font-bold text-slate-900">
            {summary.max_score.toFixed(1)}
          </p>
          <span className="text-[11px] text-slate-500">Min: {summary.min_score.toFixed(1)}</span>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500">Pass Rate</span>
          <p className="mt-2 font-mono text-2xl font-bold text-slate-900">
            {summary.pass_rate.toFixed(1)}%
          </p>
          <span className="text-[11px] text-slate-500">EXCELLENT or GOOD tiers</span>
        </div>
      </div>

      {/* 3. Comparator Control Card */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Evaluation vs. Evaluation Comparator
            </h2>
            <p className="text-xs text-slate-500">
              Select two evaluation runs to calculate signed score deltas, risk transitions, and finding progression.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Base Selector */}
          <div>
            <label htmlFor="base-eval-select" className="block text-xs font-semibold text-slate-700 mb-1.5">
              Baseline Evaluation
            </label>
            <select
              id="base-eval-select"
              value={baseId}
              onChange={(e) => setBaseId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">Select baseline evaluation...</option>
              {summary.leaderboard.map((item) => (
                <option key={`base-${item.evaluation_id}`} value={item.evaluation_id}>
                  Rank #{item.rank} — Eval: {item.evaluation_id.slice(0, 8)}... (Score: {item.overall_score.toFixed(1)}, {item.risk_classification})
                </option>
              ))}
            </select>
          </div>

          {/* Target Selector */}
          <div>
            <label htmlFor="target-eval-select" className="block text-xs font-semibold text-slate-700 mb-1.5">
              Candidate / Target Evaluation
            </label>
            <select
              id="target-eval-select"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono text-slate-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">Select candidate evaluation...</option>
              {summary.leaderboard.map((item) => (
                <option key={`target-${item.evaluation_id}`} value={item.evaluation_id}>
                  Rank #{item.rank} — Eval: {item.evaluation_id.slice(0, 8)}... (Score: {item.overall_score.toFixed(1)}, {item.risk_classification})
                </option>
              ))}
            </select>
          </div>
        </div>

        {comparisonError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
            {comparisonError}
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleCompare}
            disabled={comparing || !baseId || !targetId}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-xs transition hover:bg-emerald-700 disabled:opacity-50"
          >
            {comparing ? "Comparing..." : "Compare Evaluations →"}
          </button>
        </div>
      </div>

      {/* 4. Comparison Outcome (if executed) */}
      {comparison && <ComparisonView comparison={comparison} />}

      {/* 5. Benchmark Leaderboard Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Evaluation Benchmark Leaderboard
            </h2>
            <p className="text-xs text-slate-500">
              Historical benchmark rankings ordered by overall score descending.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500">
            {summary.leaderboard.length} Ranked Runs
          </span>
        </div>

        <BenchmarkTable
          leaderboard={summary.leaderboard}
          baseId={baseId}
          targetId={targetId}
          onSelectBase={(id) => setBaseId(id)}
          onSelectTarget={(id) => setTargetId(id)}
        />
      </div>
    </main>
  );
}

