import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { StepNode } from "@/components/graph/StepNode";
import { NodeInspectionPanel } from "@/components/graph/NodeInspectionPanel";
import EvaluationGraphPage from "@/app/evaluations/[evaluationId]/graph/page";
import { WorkflowGraphNode, WorkflowGraphResponse, api } from "@/lib/api";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/evaluations/e-12345/graph",
  useParams: () => ({ evaluationId: "e-12345" }),
}));

// Mock @xyflow/react
vi.mock("@xyflow/react", () => ({
  ReactFlow: ({ children, nodes }: { children?: React.ReactNode; nodes?: Array<{ data: { node: WorkflowGraphNode } }> }) => (
    <div data-testid="mock-react-flow">
      {nodes?.map((n) => (
        <div key={n.data.node.id} data-testid={`rf-node-${n.data.node.id}`}>
          {n.data.node.node_name}
        </div>
      ))}
      {children}
    </div>
  ),
  Handle: () => <div data-testid="mock-handle" />,
  Background: () => <div data-testid="mock-background" />,
  Controls: () => <div data-testid="mock-controls" />,
  MiniMap: () => <div data-testid="mock-minimap" />,
  Panel: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
  Position: { Left: "left", Right: "right", Top: "top", Bottom: "bottom" },
  MarkerType: { ArrowClosed: "arrowclosed" },
}));

const mockNode: WorkflowGraphNode = {
  id: "step-0",
  step_id: "s-00000000-0000-0000-0000-000000000001",
  step_index: 0,
  node_name: "SearchPlannerNode",
  agent_id: "a-00000000-0000-0000-0000-000000000001",
  agent_name: "PlanningAgent",
  latency_ms: 350,
  token_usage: {
    prompt_tokens: 120,
    completion_tokens: 45,
    cached_tokens: 0,
    reasoning_tokens: 15,
    total_tokens: 165,
  },
  input_state: { query: "test agent trace" },
  output_state: { plan: ["search", "summarize"] },
  tool_calls: [
    {
      tool_call_id: "t-1",
      tool_name: "vector_search",
      raw_arguments: { q: "test" },
      parsed_arguments: null,
      execution_result: { hits: 3 },
      is_error: false,
      is_hallucinated: false,
      is_redundant: false,
      execution_time_ms: 120,
    },
  ],
  retries: [
    {
      retry_id: "r-1",
      attempt_number: 1,
      error_type: "RateLimitError",
      backoff_duration_ms: 500,
      resolution: "SUCCESS",
    },
  ],
  findings: [
    {
      finding_id: "f-1",
      severity: "HIGH",
      code: "CYCLE_DETECTED",
      message: "Loop detected at step 0",
    },
  ],
  is_cycle_node: true,
};

describe("StepNode Component", () => {
  it("renders step node details and badges", () => {
    render(<StepNode data={{ node: mockNode, isSelected: false, highlightCycles: true }} />);
    expect(screen.getByText("SearchPlannerNode")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("PlanningAgent")).toBeInTheDocument();
    expect(screen.getByText("350ms")).toBeInTheDocument();
    expect(screen.getByText("LOOP")).toBeInTheDocument();
    expect(screen.getByText(/1 tool/)).toBeInTheDocument();
    expect(screen.getByText(/1 retry/)).toBeInTheDocument();
    expect(screen.getByText(/165 tok/)).toBeInTheDocument();
  });
});

describe("NodeInspectionPanel Component", () => {
  it("renders node overview and switches tabs", () => {
    const handleClose = vi.fn();
    render(<NodeInspectionPanel node={mockNode} onClose={handleClose} />);

    expect(screen.getByText("SearchPlannerNode")).toBeInTheDocument();
    expect(screen.getByText("PlanningAgent")).toBeInTheDocument();
    expect(screen.getByText(/Cycle Warning/)).toBeInTheDocument();
    expect(screen.getByText("350 ms")).toBeInTheDocument();
    expect(screen.getByText("CYCLE_DETECTED")).toBeInTheDocument();

    // Switch to Tools tab
    fireEvent.click(screen.getByRole("button", { name: /Tools/i }));
    expect(screen.getByText("vector_search")).toBeInTheDocument();
    expect(screen.getByText("120 ms")).toBeInTheDocument();

    // Switch to Retries tab
    fireEvent.click(screen.getByRole("button", { name: /Retries/i }));
    expect(screen.getByText("Attempt #1")).toBeInTheDocument();
    expect(screen.getByText("RateLimitError")).toBeInTheDocument();

    // Switch to State tab
    fireEvent.click(screen.getByRole("button", { name: /State/i }));
    expect(screen.getByText(/Input State/i)).toBeInTheDocument();
    expect(screen.getByText(/Output State/i)).toBeInTheDocument();

    // Close button
    fireEvent.click(screen.getByLabelText("Close inspection panel"));
    expect(handleClose).toHaveBeenCalledOnce();
  });
});

describe("EvaluationGraphPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading and error states", async () => {
    vi.spyOn(api, "getEvaluationGraph").mockRejectedValue(new Error("Graph fetch failed"));
    render(<EvaluationGraphPage />);
    expect(screen.getByText("Loading workflow execution graph...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Graph Visualization Error")).toBeInTheDocument();
      expect(screen.getByText("Graph fetch failed")).toBeInTheDocument();
    });
  });

  it("renders full workflow graph page on success", async () => {
    const mockGraph: WorkflowGraphResponse = {
      evaluation_id: "e-12345",
      trace_id: "t-12345",
      workflow_id: "w-12345",
      workflow_status: "SUCCESS",
      total_steps: 1,
      has_cycles: true,
      nodes: [mockNode],
      edges: [],
    };

    vi.spyOn(api, "getEvaluationGraph").mockResolvedValue(mockGraph);
    render(<EvaluationGraphPage />);

    await waitFor(() => {
      expect(screen.getByText("Workflow Execution Graph")).toBeInTheDocument();
      expect(screen.getByText("SUCCESS")).toBeInTheDocument();
      expect(screen.getByText("LOOP DETECTED")).toBeInTheDocument();
      expect(screen.getByTestId("mock-react-flow")).toBeInTheDocument();
      expect(screen.getByTestId("rf-node-step-0")).toBeInTheDocument();
    });
  });
});

