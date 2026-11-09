import React, { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import { WorkflowGraphNode } from "@/lib/api";

export type StepNodeData = {
  node: WorkflowGraphNode;
  isSelected?: boolean;
  highlightCycles?: boolean;
  [key: string]: unknown;
};

interface StepNodeProps {
  data: StepNodeData;
}

function StepNodeComponent({ data }: StepNodeProps) {
  const { node, isSelected, highlightCycles } = data;
  const isCycle = node.is_cycle_node && highlightCycles !== false;
  const hasFindings = node.findings.length > 0;
  const hasRetries = node.retries.length > 0;
  const hasTools = node.tool_calls.length > 0;

  // Determine highest severity
  const severityOrder = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"];
  let highestSeverity = "INFO";
  for (const f of node.findings) {
    if (severityOrder.indexOf(f.severity) > severityOrder.indexOf(highestSeverity)) {
      highestSeverity = f.severity;
    }
  }

  return (
    <div
      data-testid={`step-node-${node.step_index}`}
      className={`min-w-[220px] max-w-[260px] rounded-xl border p-3.5 shadow-xs transition-all cursor-pointer ${
        isSelected
          ? "border-emerald-600 bg-white ring-2 ring-emerald-500/30 shadow-md"
          : isCycle
          ? "border-red-300 bg-red-50/70 shadow-xs"
          : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm"
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-slate-400 !w-2.5 !h-2.5 !border-none"
      />

      {/* Top row: step index, node name, cycle flag */}
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2">
        <div className="flex items-center gap-1.5 overflow-hidden">
          <span className="flex h-5 w-5 items-center justify-center rounded bg-slate-100 text-[10px] font-bold font-mono text-slate-700">
            {node.step_index}
          </span>
          <span className="truncate text-xs font-semibold text-slate-900" title={node.node_name}>
            {node.node_name}
          </span>
        </div>
        {node.is_cycle_node && (
          <span className="rounded bg-red-100 border border-red-200 px-1.5 py-0.5 text-[9px] font-bold text-red-700 uppercase tracking-wider animate-pulse">
            LOOP
          </span>
        )}
      </div>

      {/* Middle row: Agent label */}
      <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
        <span className="truncate" title={node.agent_name}>
          {node.agent_name}
        </span>
        <span className="font-mono text-[10px] text-slate-500">
          {node.latency_ms}ms
        </span>
      </div>

      {/* Badges footer */}
      <div className="mt-2.5 flex flex-wrap items-center gap-1.5 pt-1 text-[10px]">
        {hasTools && (
          <span className="rounded bg-blue-50 border border-blue-200 px-1.5 py-0.5 font-medium text-blue-700">
            🛠️ {node.tool_calls.length} {node.tool_calls.length === 1 ? "tool" : "tools"}
          </span>
        )}

        {hasRetries && (
          <span className="rounded bg-amber-50 border border-amber-200 px-1.5 py-0.5 font-medium text-amber-700">
            🔁 {node.retries.length} {node.retries.length === 1 ? "retry" : "retries"}
          </span>
        )}

        {hasFindings && (
          <span
            className={`rounded px-1.5 py-0.5 font-semibold border ${
              highestSeverity === "CRITICAL" || highestSeverity === "HIGH"
                ? "bg-red-50 text-red-700 border-red-200"
                : "bg-amber-50 text-amber-700 border-amber-200"
            }`}
          >
            ⚠️ {node.findings.length}
          </span>
        )}

        <span className="ml-auto font-mono text-[9px] text-slate-400">
          {node.token_usage?.total_tokens || 0} tok
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!bg-slate-400 !w-2.5 !h-2.5 !border-none"
      />
    </div>
  );
}

export const StepNode = memo(StepNodeComponent);
