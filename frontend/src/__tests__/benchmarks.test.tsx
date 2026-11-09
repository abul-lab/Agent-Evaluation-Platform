import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ComparisonView } from "@/components/benchmarks/ComparisonView";
import { BenchmarkTable } from "@/components/benchmarks/BenchmarkTable";
import BenchmarksPage from "@/app/benchmarks/page";
import {
  BenchmarkSummaryResponse,
  EvaluationComparisonResponse,
  api,
} from "@/lib/api";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/benchmarks",
  useParams: () => ({}),
}));

const mockComparison: EvaluationComparisonResponse = {
  base_evaluation_id: "e-base-0001",
  target_evaluation_id: "e-target-0002",
  base_trace_id: "t-base-0001",
  target_trace_id: "t-target-0002",
  base_score: 65.0,
  target_score: 82.5,
  overall_score_delta: 17.5,
  risk_transition: {
    base_risk: "WATCH",
    target_risk: "GOOD",
    is_improved: true,
    is_degraded: false,
  },
  domain_deltas: {
    workflow_quality: {
      domain_name: "workflow_quality",
      base_score: 60.0,
      target_score: 85.0,
      score_delta: 25.0,
      base_status: "WARN",
      target_status: "PASS",
    },
    safety: {
      domain_name: "safety",
      base_score: 100.0,
      target_score: 100.0,
      score_delta: 0.0,
      base_status: "PASS",
      target_status: "PASS",
    },
  },
  finding_delta: {
    new_findings: [],
    resolved_findings: [
      {
        finding_id: "f-resolved-1",
        severity: "HIGH",
        code: "CYCLE_DETECTED",
        message: "Loop resolved in candidate run",
        workflow_id: "w-1",
        affected_steps: [1, 2],
        metadata: {},
      },
    ],
    persistent_findings: [],
    new_count: 0,
    resolved_count: 1,
    persistent_count: 0,
    total_delta: -1,
  },
  compared_at: "2026-11-08T12:00:00Z",
};

describe("ComparisonView Component", () => {
  it("renders score deltas, risk transitions, and domain comparisons", () => {
    render(<ComparisonView comparison={mockComparison} />);

    expect(screen.getByText("Score Delta")).toBeInTheDocument();
    expect(screen.getByText("+17.5")).toBeInTheDocument();
    expect(screen.getByText("WATCH → GOOD")).toBeInTheDocument();
    expect(screen.getByText("Risk Improved")).toBeInTheDocument();
    expect(screen.getByText("workflow quality")).toBeInTheDocument();
    expect(screen.getByText("+25.0")).toBeInTheDocument();

    // Check findings tabs
    expect(screen.getByText(/Resolved \(1\)/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Resolved \(1\)/i }));
    expect(screen.getByText("CYCLE_DETECTED")).toBeInTheDocument();
    expect(screen.getByText("Loop resolved in candidate run")).toBeInTheDocument();
  });
});

describe("BenchmarkTable Component", () => {
  const leaderboardItems = [
    {
      rank: 1,
      evaluation_id: "e-001",
      trace_id: "t-001",
      overall_score: 95.0,
      risk_classification: "EXCELLENT" as const,
      finding_count: 0,
      workflow_status: "SUCCESS",
      started_at: "2026-11-08T12:00:00Z",
      completed_at: "2026-11-08T12:00:01Z",
    },
    {
      rank: 2,
      evaluation_id: "e-002",
      trace_id: "t-002",
      overall_score: 75.0,
      risk_classification: "WATCH" as const,
      finding_count: 2,
      workflow_status: "SUCCESS",
      started_at: "2026-11-08T12:00:00Z",
      completed_at: "2026-11-08T12:00:01Z",
    },
  ];

  it("renders empty state when no items exist", () => {
    render(
      <BenchmarkTable
        leaderboard={[]}
        onSelectBase={vi.fn()}
        onSelectTarget={vi.fn()}
      />
    );
    expect(screen.getByText(/No evaluations found for benchmarking/i)).toBeInTheDocument();
  });

  it("renders rows and triggers base/target selection", () => {
    const handleBase = vi.fn();
    const handleTarget = vi.fn();

    render(
      <BenchmarkTable
        leaderboard={leaderboardItems}
        baseId="e-002"
        targetId="e-001"
        onSelectBase={handleBase}
        onSelectTarget={handleTarget}
      />
    );

    expect(screen.getByText("95.0")).toBeInTheDocument();
    expect(screen.getByText("75.0")).toBeInTheDocument();
    expect(screen.getByText("EXCELLENT")).toBeInTheDocument();

    const baseButtons = screen.getAllByRole("button", { name: "Base" });
    fireEvent.click(baseButtons[0]);
    expect(handleBase).toHaveBeenCalledWith("e-001");

    const targetButtons = screen.getAllByRole("button", { name: "Target" });
    fireEvent.click(targetButtons[1]);
    expect(handleTarget).toHaveBeenCalledWith("e-002");
  });
});

describe("BenchmarksPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads and displays benchmark summary with stats", async () => {
    const mockSummary: BenchmarkSummaryResponse = {
      total_evaluations: 2,
      mean_score: 85.0,
      min_score: 75.0,
      max_score: 95.0,
      pass_rate: 100.0,
      risk_distribution: { EXCELLENT: 1, GOOD: 1, WATCH: 0, POOR: 0, CRITICAL: 0 },
      leaderboard: [
        {
          rank: 1,
          evaluation_id: "e-001",
          trace_id: "t-001",
          overall_score: 95.0,
          risk_classification: "EXCELLENT",
          finding_count: 0,
          workflow_status: "SUCCESS",
          started_at: "2026-11-08T12:00:00Z",
          completed_at: "2026-11-08T12:00:01Z",
        },
      ],
    };

    vi.spyOn(api, "getBenchmarkSummary").mockResolvedValue(mockSummary);
    vi.spyOn(api, "compareEvaluations").mockResolvedValue(mockComparison);

    render(<BenchmarksPage />);
    expect(screen.getByText(/Loading benchmarking suite/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Benchmarking & Comparison")).toBeInTheDocument();
      expect(screen.getByText("85.0")).toBeInTheDocument();
      expect(screen.getByText("100.0%")).toBeInTheDocument();
      expect(screen.getByText("Compare Evaluations →")).toBeInTheDocument();
    });

    // Click Compare
    fireEvent.click(screen.getByText("Compare Evaluations →"));

    await waitFor(() => {
      expect(screen.getByText("Score Delta")).toBeInTheDocument();
      expect(screen.getByText("+17.5")).toBeInTheDocument();
    });
  });
});

