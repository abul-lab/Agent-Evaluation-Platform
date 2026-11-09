"use client";

import React, { useMemo, useState, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
  MarkerType,
  Node,
  Edge,
  NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { WorkflowGraphResponse, WorkflowGraphNode } from "@/lib/api";
import { StepNode, StepNodeData } from "./StepNode";
import { NodeInspectionPanel } from "./NodeInspectionPanel";

interface WorkflowGraphProps {
  graph: WorkflowGraphResponse;
}

const nodeTypes = {
  stepNode: StepNode,
};

export function WorkflowGraph({ graph }: WorkflowGraphProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(
    graph.nodes.length > 0 ? graph.nodes[0].id : null
  );
  const [highlightCycles, setHighlightCycles] = useState<boolean>(true);

  // Map backend nodes into React Flow nodes
  const rfNodes: Node<StepNodeData>[] = useMemo(() => {
    return graph.nodes.map((node, index) => ({
      id: node.id,
      type: "stepNode",
      position: {
        x: index * 300 + 40,
        // Stagger slightly every other step for visual clarity
        y: index % 2 === 0 ? 120 : 160,
      },
      data: {
        node,
        isSelected: selectedNodeId === node.id,
        highlightCycles,
      },
    }));
  }, [graph.nodes, selectedNodeId, highlightCycles]);

  // Map backend edges into React Flow edges
  const rfEdges: Edge[] = useMemo(() => {
    return graph.edges.map((edge) => {
      const isCycle = edge.is_cycle_edge && highlightCycles;
      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        animated: isCycle,
        style: {
          stroke: isCycle ? "#ef4444" : "#94a3b8",
          strokeWidth: isCycle ? 2.5 : 1.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isCycle ? "#ef4444" : "#94a3b8",
        },
      };
    });
  }, [graph.edges, highlightCycles]);

  const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    setSelectedNodeId(node.id);
  }, []);

  const selectedNode = useMemo<WorkflowGraphNode | null>(() => {
    if (!selectedNodeId) return null;
    return graph.nodes.find((n) => n.id === selectedNodeId) || null;
  }, [graph.nodes, selectedNodeId]);

  return (
    <div
      data-testid="workflow-graph-container"
      className="relative flex h-[750px] w-full overflow-hidden rounded-xl border border-slate-200 bg-slate-50 shadow-sm"
    >
      {/* React Flow canvas */}
      <div className="flex-1 h-full w-full">
        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          fitView
          minZoom={0.2}
          maxZoom={2}
          className="bg-slate-50"
        >
          <Background color="#cbd5e1" gap={20} size={1} />
          <Controls className="!bg-white !border-slate-200 !text-slate-700 fill-slate-700 shadow-sm rounded-lg" />
          <MiniMap
            nodeColor={(node) => {
              const data = node.data as unknown as StepNodeData;
              if (data?.node?.is_cycle_node && highlightCycles) return "#ef4444";
              if (data?.node?.findings && data.node.findings.length > 0) return "#f59e0b";
              return "#3b82f6";
            }}
            className="!bg-white !border-slate-200 shadow-sm rounded-lg"
            zoomable
            pannable
          />

          {/* Graph Controls overlay panel */}
          <Panel position="top-left" className="m-3">
            <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white/95 p-2 shadow-sm backdrop-blur-sm text-xs">
              <span className="font-semibold text-slate-900">
                Steps: {graph.total_steps}
              </span>
              <span className="text-slate-300">|</span>
              <button
                type="button"
                onClick={() => setHighlightCycles(!highlightCycles)}
                className={`flex items-center gap-1.5 rounded px-2.5 py-1 font-semibold transition ${
                  highlightCycles && graph.has_cycles
                    ? "bg-red-50 border border-red-200 text-red-700"
                    : "bg-slate-100 border border-slate-200 text-slate-700 hover:bg-slate-200 hover:text-slate-900"
                }`}
              >
                <span>🔄</span>
                <span>{highlightCycles ? "Highlight Cycles: ON" : "Highlight Cycles: OFF"}</span>
              </button>
              {graph.has_cycles && (
                <span className="rounded bg-red-50 border border-red-200 px-2 py-0.5 text-[10px] font-bold text-red-700">
                  CYCLE DETECTED
                </span>
              )}
            </div>
          </Panel>
        </ReactFlow>
      </div>

      {/* Side Inspection Panel */}
      {selectedNode && (
        <NodeInspectionPanel
          node={selectedNode}
          onClose={() => setSelectedNodeId(null)}
        />
      )}
    </div>
  );
}

