import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ScoreTrendChart } from "@/components/analytics/ScoreTrendChart";
import { VolumeBarChart } from "@/components/analytics/VolumeBarChart";
import { FindingFrequencyChart } from "@/components/analytics/FindingFrequencyChart";
import AnalyticsPage from "@/app/analytics/page";
import { AnalyticsTrendsResponse, DailyAnalyticsBucket, api } from "@/lib/api";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/analytics",
  useParams: () => ({}),
}));

const mockBuckets: DailyAnalyticsBucket[] = [
  {
    date: "2026-11-01",
    evaluation_count: 3,
    average_score: 72.5,
    risk_counts: { GOOD: 2, WATCH: 1 },
    total_findings: 2,
    finding_counts: { CYCLE_DETECTED: 1, REDUNDANT_TOOL_CALL: 1 },
  },
  {
    date: "2026-11-02",
    evaluation_count: 5,
    average_score: 88.0,
    risk_counts: { EXCELLENT: 4, GOOD: 1 },
    total_findings: 0,
    finding_counts: {},
  },
];

describe("ScoreTrendChart Component", () => {
  it("renders empty state when no buckets", () => {
    render(<ScoreTrendChart buckets={[]} />);
    expect(screen.getByText(/No historical score data available/i)).toBeInTheDocument();
  });

  it("renders SVG trend line with points and baseline", () => {
    render(<ScoreTrendChart buckets={mockBuckets} />);
    expect(screen.getByText("Score Trajectory Over Time")).toBeInTheDocument();
    expect(screen.getByText("Pass Baseline (80.0)")).toBeInTheDocument();
    expect(screen.getByText("72.5")).toBeInTheDocument();
    expect(screen.getByText("88.0")).toBeInTheDocument();
  });
});

describe("VolumeBarChart Component", () => {
  it("renders empty state when no buckets", () => {
    render(<VolumeBarChart buckets={[]} />);
    expect(screen.getByText(/No execution volume recorded/i)).toBeInTheDocument();
  });

  it("renders SVG bars and counts", () => {
    render(<VolumeBarChart buckets={mockBuckets} />);
    expect(screen.getByText("Daily Evaluation Throughput")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });
});

describe("FindingFrequencyChart Component", () => {
  it("renders empty state when no findings", () => {
    render(<FindingFrequencyChart findings={[]} />);
    expect(screen.getByText(/Zero deterministic findings detected/i)).toBeInTheDocument();
  });

  it("renders finding meters and codes", () => {
    const mockFindings = [
      {
        code: "CYCLE_DETECTED",
        count: 4,
        severity: "HIGH" as const,
        description: "Execution loop detected in workflow graph",
      },
    ];
    render(<FindingFrequencyChart findings={mockFindings} />);
    expect(screen.getByText("CYCLE_DETECTED")).toBeInTheDocument();
    expect(screen.getByText("HIGH")).toBeInTheDocument();
    expect(screen.getByText(/4 times/)).toBeInTheDocument();
    expect(screen.getByText("Execution loop detected in workflow graph")).toBeInTheDocument();
  });
});

describe("AnalyticsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads and renders analytics KPI metrics and charts", async () => {
    const mockTrends: AnalyticsTrendsResponse = {
      time_window_days: 30,
      total_evaluations: 8,
      average_score: 82.5,
      score_trend_direction: "IMPROVING",
      pass_rate: 87.5,
      risk_distribution: { EXCELLENT: 5, GOOD: 2, WATCH: 1, POOR: 0, CRITICAL: 0 },
      domain_averages: {
        task_quality: 95.0,
        tool_usage: 85.0,
        workflow_quality: 80.0,
        reliability: 82.0,
        safety: 100.0,
        cost: 75.0,
        efficiency: 78.0,
      },
      finding_distribution: [
        {
          code: "REDUNDANT_TOOL_CALL",
          count: 2,
          severity: "MEDIUM",
          description: "Duplicate tool invocation",
        },
      ],
      daily_metrics: mockBuckets,
    };

    vi.spyOn(api, "getAnalyticsTrends").mockResolvedValue(mockTrends);

    render(<AnalyticsPage />);
    expect(screen.getByText(/Calculating historical quality trends/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Historical Quality Analytics")).toBeInTheDocument();
      expect(screen.getByText("8")).toBeInTheDocument();
      expect(screen.getByText("82.5")).toBeInTheDocument();
      expect(screen.getByText("▲ IMPROVING")).toBeInTheDocument();
      expect(screen.getByText("87.5%")).toBeInTheDocument();
      expect(screen.getByText(/EXCELLENT: 5/)).toBeInTheDocument();
      expect(screen.getByText("task quality")).toBeInTheDocument();
      expect(screen.getByText("95.0")).toBeInTheDocument();
    });

    // Test filter pill click
    const pill7d = screen.getByRole("button", { name: "7 Days" });
    fireEvent.click(pill7d);
    await waitFor(() => {
      expect(api.getAnalyticsTrends).toHaveBeenCalledWith(7, 500);
    });
  });
});
