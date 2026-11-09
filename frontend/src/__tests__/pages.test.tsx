import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import OverviewPage from "@/app/page";
import TracesPage from "@/app/traces/page";
import TraceDetailPage from "@/app/traces/[traceId]/page";
import EvaluationDetailPage from "@/app/evaluations/[evaluationId]/page";
import { api } from "@/lib/api";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/",
  useParams: () => ({ traceId: "t-12345", evaluationId: "e-67890" }),
}));

describe("Page Rendering Tests", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders OverviewPage with metrics and traces", async () => {
    vi.spyOn(api, "getTraces").mockResolvedValue([
      {
        trace_id: "t-1",
        workflow_status: "SUCCESS",
        step_count: 4,
        created_at: "2026-11-08T12:00:00Z",
        framework: "LANGGRAPH",
      },
    ]);

    render(<OverviewPage />);
    expect(screen.getByText("Evaluation Operations Overview")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Total Traces")).toBeInTheDocument();
      expect(screen.getByText("Recent Traces")).toBeInTheDocument();
    });
  });

  it("renders TracesPage with upload card and trace table", async () => {
    vi.spyOn(api, "getTraces").mockResolvedValue([
      {
        trace_id: "t-2",
        workflow_status: "SUCCESS",
        step_count: 2,
        created_at: "2026-11-08T12:00:00Z",
        framework: "CREWAI",
      },
    ]);

    render(<TracesPage />);
    expect(screen.getByText("Ingested Traces")).toBeInTheDocument();
    expect(screen.getByText("Upload Agent Trace")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("All Traces (1)")).toBeInTheDocument();
      expect(screen.getByText("CREWAI")).toBeInTheDocument();
    });
  });

  it("renders TraceDetailPage with trace metadata and evaluation button", async () => {
    vi.spyOn(api, "getTrace").mockResolvedValue({
      trace_id: "t-12345",
      created_at: "2026-11-08T12:00:00Z",
      workflow_status: "SUCCESS",
      step_count: 5,
      framework: "LANGGRAPH",
    });

    render(<TraceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Agent Trace Detail")).toBeInTheDocument();
      expect(screen.getByText("t-12345")).toBeInTheDocument();
      expect(screen.getByText("Run Evaluation →")).toBeInTheDocument();
      expect(screen.getByText("LANGGRAPH")).toBeInTheDocument();
    });
  });

  it("renders EvaluationDetailPage with summary, scorecard, and findings", async () => {
    vi.spyOn(api, "getEvaluation").mockResolvedValue({
      evaluation_id: "e-67890",
      trace_id: "t-12345",
      status: "COMPLETED",
      started_at: "2026-11-08T12:00:00Z",
      completed_at: "2026-11-08T12:00:01Z",
      finding_count: 1,
      overall_score: 85.0,
      risk_classification: "GOOD",
    });

    vi.spyOn(api, "getScorecard").mockResolvedValue({
      scorecard_id: "s-1",
      workflow_id: "w-1",
      overall_score: 85.0,
      risk_classification: "GOOD",
      task_quality: { name: "task_quality", score: 100, status: "PASS", findings_count: 0 },
      tool_usage: { name: "tool_usage", score: 80, status: "PASS", findings_count: 0 },
      workflow_quality: { name: "workflow_quality", score: 85, status: "PASS", findings_count: 0 },
      reliability: { name: "reliability", score: 85, status: "PASS", findings_count: 0 },
      safety: { name: "safety", score: 100, status: "PASS", findings_count: 0 },
      cost: { name: "cost", score: 80, status: "PASS", findings_count: 0 },
      efficiency: { name: "efficiency", score: 80, status: "PASS", findings_count: 1 },
      findings: [],
    });

    vi.spyOn(api, "getFindings").mockResolvedValue([
      {
        finding_id: "f-1",
        severity: "MEDIUM",
        code: "REDUNDANT_TOOL_CALL",
        message: "Duplicate tool call detected",
        workflow_id: "w-1",
        affected_steps: [1, 2],
        metadata: {},
      },
    ]);

    vi.spyOn(api, "getSemanticResult").mockResolvedValue({
      metrics: [],
      provider: "fallback",
      execution_time_ms: 0.1,
      evaluation_available: false,
      reason: "OPENAI_API_KEY is not set.",
    });

    render(<EvaluationDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Evaluation Run Overview")).toBeInTheDocument();
      expect(screen.getByText("e-67890")).toBeInTheDocument();
      expect(screen.getByText("Evaluation Scorecard")).toBeInTheDocument();
      expect(screen.getAllByText("85.0").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Deterministic Findings (1)")).toBeInTheDocument();
      expect(screen.getByText("REDUNDANT_TOOL_CALL")).toBeInTheDocument();
      expect(screen.getByText("Semantic Evaluation")).toBeInTheDocument();
      expect(screen.getByText("Provider: fallback")).toBeInTheDocument();
      expect(screen.getByText("Export JSON")).toBeInTheDocument();
      expect(screen.getByText("Export Markdown")).toBeInTheDocument();
      expect(screen.getByText("Export CSV")).toBeInTheDocument();
    });
  });
});
