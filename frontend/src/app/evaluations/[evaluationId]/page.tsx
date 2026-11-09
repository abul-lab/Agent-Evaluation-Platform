"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  EvaluationFinding,
  EvaluationSummaryResponse,
  Scorecard,
  SemanticEvaluationResult,
  api,
} from "@/lib/api";
import { EvaluationSummary } from "@/components/EvaluationSummary";
import { ScorecardCard } from "@/components/ScorecardCard";
import { FindingsList } from "@/components/FindingsList";
import { SemanticEvaluationCard } from "@/components/SemanticEvaluationCard";

export default function EvaluationDetailPage() {
  const params = useParams();
  const evaluationId = params.evaluationId as string;

  const [summary, setSummary] = useState<EvaluationSummaryResponse | null>(null);
  const [scorecard, setScorecard] = useState<Scorecard | null>(null);
  const [findings, setFindings] = useState<EvaluationFinding[]>([]);
  const [semanticResult, setSemanticResult] = useState<SemanticEvaluationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);

  useEffect(() => {
    if (!evaluationId) return;

    const fetchEvaluationData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [summaryData, scorecardData, findingsData, semanticData] =
          await Promise.all([
            api.getEvaluation(evaluationId),
            api.getScorecard(evaluationId),
            api.getFindings(evaluationId),
            api.getSemanticResult(evaluationId).catch(() => null),
          ]);

        setSummary(summaryData);
        setScorecard(scorecardData);
        setFindings(findingsData);
        setSemanticResult(semanticData);
      } catch (err: unknown) {
        setError(
          err instanceof Error
            ? err.message
            : `Failed to load evaluation '${evaluationId}'`
        );
      } finally {
        setLoading(false);
      }
    };

    fetchEvaluationData();
  }, [evaluationId]);

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-12 space-y-6">
        <div className="flex items-center justify-between animate-pulse">
          <div className="h-4 w-32 rounded bg-slate-200" />
          <div className="h-8 w-64 rounded bg-slate-200" />
        </div>
        <div className="h-48 rounded-xl border border-slate-200 bg-white p-6 shadow-xs animate-pulse flex items-center justify-center">
          <span className="text-sm text-slate-500">Loading evaluation scorecard and findings...</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 rounded-xl border border-slate-200 bg-white shadow-xs" />
          ))}
        </div>
      </main>
    );
  }

  if (error || !summary || !scorecard) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-12 space-y-4">
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-800 shadow-xs">
          <h2 className="text-base font-bold text-red-900">Evaluation Error</h2>
          <p className="mt-1 font-mono text-xs">{error || "Evaluation not found"}</p>
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

  const handleExport = async (format: "json" | "markdown" | "csv") => {
    try {
      setExportingFormat(format);
      await api.downloadExport(evaluationId, format);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExportingFormat(null);
    }
  };

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
      {/* Navigation breadcrumb & Export Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/traces"
            className="text-xs font-semibold text-slate-600 hover:text-slate-900"
          >
            ← Back to traces
          </Link>
          <span className="font-mono text-xs text-slate-500">
            Evaluation: {evaluationId}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={`/evaluations/${evaluationId}/graph`}
            className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 shadow-xs transition hover:bg-emerald-100 hover:text-emerald-800"
          >
            Inspect Workflow Graph →
          </Link>
          <button
            type="button"
            onClick={() => handleExport("json")}
            disabled={exportingFormat !== null}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs transition hover:bg-slate-50 hover:text-slate-900 disabled:opacity-50"
          >
            {exportingFormat === "json" ? "Exporting..." : "Export JSON"}
          </button>
          <button
            type="button"
            onClick={() => handleExport("markdown")}
            disabled={exportingFormat !== null}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs transition hover:bg-slate-50 hover:text-slate-900 disabled:opacity-50"
          >
            {exportingFormat === "markdown" ? "Exporting..." : "Export Markdown"}
          </button>
          <button
            type="button"
            onClick={() => handleExport("csv")}
            disabled={exportingFormat !== null}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-xs transition hover:bg-slate-50 hover:text-slate-900 disabled:opacity-50"
          >
            {exportingFormat === "csv" ? "Exporting..." : "Export CSV"}
          </button>
        </div>
      </div>

      {/* 1. Evaluation Summary Component */}
      <EvaluationSummary summary={summary} />

      {/* 2. Scorecard Component */}
      <ScorecardCard scorecard={scorecard} />

      {/* 3. Semantic Evaluation Component */}
      <SemanticEvaluationCard semanticResult={semanticResult} />

      {/* 4. Findings Component */}
      <FindingsList findings={findings} />
    </main>
  );
}

