"use client";

import React, { useEffect, useState } from "react";
import { AnalyticsTrendsResponse, api } from "@/lib/api";
import { ScoreTrendChart } from "@/components/analytics/ScoreTrendChart";
import { VolumeBarChart } from "@/components/analytics/VolumeBarChart";
import { FindingFrequencyChart } from "@/components/analytics/FindingFrequencyChart";

export default function AnalyticsPage() {
  const [days, setDays] = useState<number>(30);
  const [trends, setTrends] = useState<AnalyticsTrendsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getAnalyticsTrends(days, 500);
        setTrends(data);
      } catch (err: unknown) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load historical analytics"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, [days]);

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-16">
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500 shadow-xs animate-pulse">
          Calculating historical quality trends and evaluation throughput...
        </div>
      </main>
    );
  }

  if (error || !trends) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-12">
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-800 shadow-xs">
          <h2 className="text-base font-bold text-red-900">Analytics Error</h2>
          <p className="mt-1 font-mono text-xs">{error || "Unable to load analytics"}</p>
        </div>
      </main>
    );
  }

  const isImproving = trends.score_trend_direction === "IMPROVING";
  const isDegrading = trends.score_trend_direction === "DEGRADING";

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
      {/* 1. Page Header & Time Window Selectors */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight sm:text-3xl">
            Historical Quality Analytics
          </h1>
          <p className="mt-1 text-xs text-slate-600">
            Track evaluation volume, score trajectories, risk distributions, and recurring finding patterns over time.
          </p>
        </div>

        {/* Time Window Selector Pills */}
        <div className="flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-1 text-xs font-semibold shadow-xs">
          {[
            { label: "7 Days", val: 7 },
            { label: "30 Days", val: 30 },
            { label: "90 Days", val: 90 },
            { label: "All Time", val: 0 },
          ].map((item) => (
            <button
              key={item.label}
              type="button"
              onClick={() => setDays(item.val)}
              className={`rounded-md px-3 py-1.5 transition ${
                days === item.val
                  ? "bg-slate-100 text-slate-900 font-bold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* 2. Top KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500">Total Evaluations</span>
          <p className="mt-2 font-mono text-2xl font-bold text-slate-900">
            {trends.total_evaluations}
          </p>
          <span className="text-[11px] text-slate-500">In selected window</span>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500">Mean Quality Score</span>
          <p className="mt-2 font-mono text-2xl font-bold text-emerald-700">
            {trends.average_score.toFixed(1)}
          </p>
          <span className="text-[11px] text-slate-500">Target baseline: 80.0</span>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500">Trajectory Direction</span>
          <div className="mt-2 flex items-center gap-1.5">
            <span
              className={`font-mono text-xl font-bold ${
                isImproving
                  ? "text-emerald-700"
                  : isDegrading
                  ? "text-red-700"
                  : "text-slate-800"
              }`}
            >
              {isImproving ? "▲ IMPROVING" : isDegrading ? "▼ DEGRADING" : "▬ STABLE"}
            </span>
          </div>
          <span className="text-[11px] text-slate-500">Half-window delta</span>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500">Pass Rate</span>
          <p className="mt-2 font-mono text-2xl font-bold text-slate-900">
            {trends.pass_rate.toFixed(1)}%
          </p>
          <span className="text-[11px] text-slate-500">EXCELLENT or GOOD tiers</span>
        </div>
      </div>

      {/* 3. Risk Distribution Breakdown Bar */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2 shadow-xs">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Risk Tier Distribution
        </span>
        <div className="flex flex-wrap gap-2 text-xs font-mono">
          <span className="rounded-md bg-emerald-50 border border-emerald-200 px-2.5 py-1 text-emerald-700 font-semibold">
            EXCELLENT: {trends.risk_distribution.EXCELLENT || 0}
          </span>
          <span className="rounded-md bg-teal-50 border border-teal-200 px-2.5 py-1 text-teal-700 font-semibold">
            GOOD: {trends.risk_distribution.GOOD || 0}
          </span>
          <span className="rounded-md bg-amber-50 border border-amber-200 px-2.5 py-1 text-amber-700 font-semibold">
            WATCH: {trends.risk_distribution.WATCH || 0}
          </span>
          <span className="rounded-md bg-orange-50 border border-orange-200 px-2.5 py-1 text-orange-700 font-semibold">
            POOR: {trends.risk_distribution.POOR || 0}
          </span>
          <span className="rounded-md bg-red-50 border border-red-200 px-2.5 py-1 text-red-700 font-semibold">
            CRITICAL: {trends.risk_distribution.CRITICAL || 0}
          </span>
        </div>
      </div>

      {/* 4. Score Trajectory Trend Chart */}
      <ScoreTrendChart buckets={trends.daily_metrics} />

      {/* 5. Volume Bar Chart & Recurring Findings Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <VolumeBarChart buckets={trends.daily_metrics} />
        <FindingFrequencyChart findings={trends.finding_distribution} />
      </div>

      {/* 6. Multi-Domain Health Averages */}
      <div className="space-y-3">
        <div>
          <h3 className="text-sm font-bold text-slate-900">Domain Health Averages</h3>
          <p className="text-xs text-slate-500">
            Mean score recorded per evaluation domain across the time window
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {Object.entries(trends.domain_averages).map(([domain, score]) => (
            <div
              key={domain}
              className="rounded-lg border border-slate-200 bg-white p-3 text-center space-y-1 shadow-2xs"
            >
              <span className="block text-[11px] font-semibold capitalize text-slate-600 truncate" title={domain}>
                {domain.replace(/_/g, " ")}
              </span>
              <p
                className={`font-mono text-base font-bold ${
                  score >= 80
                    ? "text-emerald-700"
                    : score >= 60
                    ? "text-amber-700"
                    : "text-red-700"
                }`}
              >
                {score.toFixed(1)}
              </p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}

