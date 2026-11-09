"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { WorkflowGraphResponse, api } from "@/lib/api";
import { WorkflowGraph } from "@/components/graph/WorkflowGraph";

export default function EvaluationGraphPage() {
  const params = useParams();
  const evaluationId = params.evaluationId as string;

  const [graph, setGraph] = useState<WorkflowGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!evaluationId) return;

    const fetchGraphData = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getEvaluationGraph(evaluationId);
        setGraph(data);
      } catch (err: unknown) {
        setError(
          err instanceof Error
            ? err.message
            : `Failed to load workflow graph for evaluation '${evaluationId}'`
        );
      } finally {
        setLoading(false);
      }
    };

    fetchGraphData();
  }, [evaluationId]);

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-16">
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500 shadow-xs animate-pulse">
          Loading workflow execution graph...
        </div>
      </main>
    );
  }

  if (error || !graph) {
    return (
      <main className="mx-auto max-w-7xl px-6 py-12 space-y-4">
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-800 shadow-xs">
          <h2 className="text-base font-bold text-red-900">Graph Visualization Error</h2>
          <p className="mt-1 font-mono text-xs">{error || "Workflow graph not found"}</p>
        </div>
        <Link
          href={`/evaluations/${evaluationId}`}
          className="inline-block text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline"
        >
          ← Back to Evaluation Scorecard
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 space-y-6">
      {/* Header & Navigation */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <Link
              href={`/evaluations/${evaluationId}`}
              className="font-semibold text-slate-600 hover:text-slate-900 transition"
            >
              ← Back to Scorecard
            </Link>
            <span>/</span>
            <span className="font-mono text-slate-500 truncate max-w-[200px]">
              Eval: {evaluationId}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Workflow Execution Graph
          </h1>
          <p className="text-xs text-slate-600">
            Visual inspection of chronological step execution, tool invocations, retries, and cycle loops.
          </p>
        </div>

        {/* Metadata badges */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 font-mono text-xs text-slate-700 shadow-xs">
            Steps: <strong className="text-slate-900">{graph.total_steps}</strong>
          </span>
          <span
            className={`rounded-lg border px-3 py-1.5 font-semibold text-xs ${
              graph.workflow_status === "SUCCESS"
                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                : "border-red-200 bg-red-50 text-red-700"
            }`}
          >
            {graph.workflow_status}
          </span>
          {graph.has_cycles && (
            <span className="rounded-lg border border-red-300 bg-red-100 px-3 py-1.5 font-bold text-xs text-red-800 animate-pulse">
              LOOP DETECTED
            </span>
          )}
        </div>
      </div>

      {/* Graph Visualizer Canvas */}
      <WorkflowGraph graph={graph} />
    </main>
  );
}

