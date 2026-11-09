import React, { useState } from "react";
import { WorkflowGraphNode } from "@/lib/api";

interface NodeInspectionPanelProps {
  node: WorkflowGraphNode | null;
  onClose: () => void;
}

export function NodeInspectionPanel({ node, onClose }: NodeInspectionPanelProps) {
  const [activeTab, setActiveTab] = useState<"overview" | "tools" | "retries" | "state">("overview");

  if (!node) {
    return null;
  }

  return (
    <aside
      data-testid="node-inspection-panel"
      className="flex h-full w-full max-w-md flex-col border-l border-slate-200 bg-white text-slate-800 shadow-xl transition-all"
    >
      {/* Panel Header */}
      <div className="flex items-start justify-between border-b border-slate-100 p-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded bg-slate-100 text-xs font-bold font-mono text-slate-800">
              #{node.step_index}
            </span>
            <h3 className="text-base font-bold text-slate-900 truncate max-w-[260px]" title={node.node_name}>
              {node.node_name}
            </h3>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Agent: <span className="font-semibold text-slate-800">{node.agent_name}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close inspection panel"
          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        >
          ✕
        </button>
      </div>

      {/* Cycle alert banner */}
      {node.is_cycle_node && (
        <div className="border-b border-red-200 bg-red-50 p-3 text-xs text-red-800 flex items-center gap-2">
          <span>⚠️</span>
          <span>
            <strong>Cycle Warning:</strong> This step was identified as participating in a repetitive execution loop.
          </span>
        </div>
      )}

      {/* Tabs navigation */}
      <div className="flex border-b border-slate-200 bg-slate-50 text-xs font-semibold">
        <button
          type="button"
          onClick={() => setActiveTab("overview")}
          className={`flex-1 py-2.5 text-center transition ${
            activeTab === "overview"
              ? "border-b-2 border-emerald-600 text-emerald-700 bg-white font-bold"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          Overview {node.findings.length > 0 && `(${node.findings.length})`}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("tools")}
          className={`flex-1 py-2.5 text-center transition ${
            activeTab === "tools"
              ? "border-b-2 border-emerald-600 text-emerald-700 bg-white font-bold"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          Tools ({node.tool_calls.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("retries")}
          className={`flex-1 py-2.5 text-center transition ${
            activeTab === "retries"
              ? "border-b-2 border-emerald-600 text-emerald-700 bg-white font-bold"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          Retries ({node.retries.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("state")}
          className={`flex-1 py-2.5 text-center transition ${
            activeTab === "state"
              ? "border-b-2 border-emerald-600 text-emerald-700 bg-white font-bold"
              : "text-slate-600 hover:text-slate-900"
          }`}
        >
          State
        </button>
      </div>

      {/* Tab contents */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {/* 1. OVERVIEW TAB */}
        {activeTab === "overview" && (
          <div className="space-y-4">
            {/* Performance metrics */}
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <span className="text-slate-500 text-[11px]">Latency</span>
                <p className="mt-1 font-mono text-sm font-semibold text-slate-900">
                  {node.latency_ms} ms
                </p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <span className="text-slate-500 text-[11px]">Total Tokens</span>
                <p className="mt-1 font-mono text-sm font-semibold text-slate-900">
                  {node.token_usage?.total_tokens || 0}
                </p>
              </div>
            </div>

            {/* Token breakdown */}
            <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 space-y-1.5 font-mono text-[11px]">
              <div className="flex justify-between text-slate-600">
                <span>Prompt Tokens:</span>
                <span className="text-slate-900 font-semibold">{node.token_usage?.prompt_tokens || 0}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Completion Tokens:</span>
                <span className="text-slate-900 font-semibold">{node.token_usage?.completion_tokens || 0}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Reasoning Tokens:</span>
                <span className="text-slate-900 font-semibold">{node.token_usage?.reasoning_tokens || 0}</span>
              </div>
            </div>

            {/* Step ID */}
            <div className="text-[11px] text-slate-500 font-mono break-all">
              Step ID: {node.step_id}
            </div>

            {/* Findings affecting this step */}
            <div>
              <h4 className="font-semibold text-slate-900 mb-2">
                Step Findings ({node.findings.length})
              </h4>
              {node.findings.length === 0 ? (
                <p className="text-slate-500 italic">No findings detected for this step.</p>
              ) : (
                <div className="space-y-2">
                  {node.findings.map((f) => (
                    <div
                      key={f.finding_id}
                      className="rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-red-800">{f.code}</span>
                        <span className="rounded border border-red-200 bg-white px-1.5 py-0.5 text-[10px] font-semibold text-red-700">
                          {f.severity}
                        </span>
                      </div>
                      <p className="text-slate-700">{f.message}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* 2. TOOLS TAB */}
        {activeTab === "tools" && (
          <div className="space-y-3">
            {node.tool_calls.length === 0 ? (
              <p className="text-slate-500 italic">No tools invoked during this step.</p>
            ) : (
              node.tool_calls.map((tool) => (
                <div
                  key={tool.tool_call_id}
                  className="rounded-lg border border-slate-200 bg-slate-50/60 p-3 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-semibold text-slate-900 text-xs">
                      {tool.tool_name}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500">
                      {tool.execution_time_ms} ms
                    </span>
                  </div>

                  {/* Warning pills */}
                  <div className="flex flex-wrap gap-1">
                    {tool.is_hallucinated && (
                      <span className="rounded bg-red-50 border border-red-200 px-1.5 py-0.5 text-[10px] font-bold text-red-700">
                        HALLUCINATED
                      </span>
                    )}
                    {tool.is_redundant && (
                      <span className="rounded bg-amber-50 border border-amber-200 px-1.5 py-0.5 text-[10px] font-bold text-amber-700">
                        REDUNDANT
                      </span>
                    )}
                    {tool.is_error && (
                      <span className="rounded bg-red-50 border border-red-200 px-1.5 py-0.5 text-[10px] font-bold text-red-700">
                        ERROR
                      </span>
                    )}
                  </div>

                  {/* Arguments */}
                  <div>
                    <span className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider">
                      Arguments
                    </span>
                    <pre className="mt-1 max-h-32 overflow-x-auto rounded border border-slate-200 bg-white p-2 font-mono text-[10px] text-slate-800">
                      {JSON.stringify(tool.raw_arguments, null, 2)}
                    </pre>
                  </div>

                  {/* Execution Result */}
                  {tool.execution_result && (
                    <div>
                      <span className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider">
                        Execution Result
                      </span>
                      <pre className="mt-1 max-h-32 overflow-x-auto rounded border border-slate-200 bg-white p-2 font-mono text-[10px] text-slate-800">
                        {JSON.stringify(tool.execution_result, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* 3. RETRIES TAB */}
        {activeTab === "retries" && (
          <div className="space-y-3">
            {node.retries.length === 0 ? (
              <p className="text-slate-500 italic">No retries occurred during this step.</p>
            ) : (
              node.retries.map((r) => (
                <div
                  key={r.retry_id}
                  className="rounded-lg border border-amber-200 bg-amber-50/60 p-3 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-amber-900">
                      Attempt #{r.attempt_number}
                    </span>
                    <span className="rounded border border-amber-200 bg-white px-1.5 py-0.5 font-mono text-[10px] text-amber-800 font-semibold">
                      {r.resolution}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-700">
                    <span className="text-slate-500">Error: </span>
                    <code className="text-red-700 font-semibold">{r.error_type}</code>
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Backoff: <span className="font-mono text-slate-700 font-medium">{r.backoff_duration_ms} ms</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* 4. STATE TAB */}
        {activeTab === "state" && (
          <div className="space-y-4">
            <div>
              <span className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider">
                Input State
              </span>
              <pre className="mt-1.5 max-h-56 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-2.5 font-mono text-[10px] text-slate-800">
                {Object.keys(node.input_state || {}).length === 0
                  ? "{}"
                  : JSON.stringify(node.input_state, null, 2)}
              </pre>
            </div>

            <div>
              <span className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider">
                Output State
              </span>
              <pre className="mt-1.5 max-h-56 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-2.5 font-mono text-[10px] text-slate-800">
                {Object.keys(node.output_state || {}).length === 0
                  ? "{}"
                  : JSON.stringify(node.output_state, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

