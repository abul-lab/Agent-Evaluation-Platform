import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { RiskBadge } from "@/components/RiskBadge";
import { DomainScoreCard } from "@/components/DomainScoreCard";
import { ScorecardCard } from "@/components/ScorecardCard";
import { FindingCard } from "@/components/FindingCard";
import { FindingsList } from "@/components/FindingsList";
import { EvaluationSummary } from "@/components/EvaluationSummary";
import { TraceTable } from "@/components/TraceTable";
import { SemanticEvaluationCard } from "@/components/SemanticEvaluationCard";
import {
  DomainScore,
  EvaluationFinding,
  EvaluationSummaryResponse,
  Scorecard,
  SemanticEvaluationResult,
  TraceSummaryItem,
} from "@/lib/api";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  usePathname: () => "/",
  useParams: () => ({}),
}));

describe("RiskBadge Component", () => {
  it("renders all risk levels correctly", () => {
    const { rerender } = render(<RiskBadge risk="EXCELLENT" />);
    expect(screen.getByText("EXCELLENT")).toBeInTheDocument();

    rerender(<RiskBadge risk="CRITICAL" />);
    expect(screen.getByText("CRITICAL")).toBeInTheDocument();

    rerender(<RiskBadge risk="WATCH" />);
    expect(screen.getByText("WATCH")).toBeInTheDocument();
  });
});

describe("DomainScoreCard Component", () => {
  const mockDomain: DomainScore = {
    name: "tool_usage",
    score: 85.5,
    status: "PASS",
    findings_count: 0,
  };

  it("renders domain details and score values", () => {
    render(<DomainScoreCard domain={mockDomain} />);
    expect(screen.getByText("tool usage")).toBeInTheDocument();
    expect(screen.getByText("85.5")).toBeInTheDocument();
    expect(screen.getByText("PASS")).toBeInTheDocument();
    expect(screen.getByText("0 findings")).toBeInTheDocument();
  });

  it("renders singular finding text when count is 1", () => {
    const singleFindingDomain: DomainScore = {
      name: "safety",
      score: 50.0,
      status: "FAIL",
      findings_count: 1,
    };
    render(<DomainScoreCard domain={singleFindingDomain} />);
    expect(screen.getByText("1 finding")).toBeInTheDocument();
    expect(screen.getByText("FAIL")).toBeInTheDocument();
  });
});

describe("ScorecardCard Component", () => {
  const mockScorecard: Scorecard = {
    scorecard_id: "s-1",
    workflow_id: "w-1",
    overall_score: 92.5,
    risk_classification: "EXCELLENT",
    task_quality: { name: "task_quality", score: 100, status: "PASS", findings_count: 0 },
    tool_usage: { name: "tool_usage", score: 90, status: "PASS", findings_count: 0 },
    workflow_quality: { name: "workflow_quality", score: 95, status: "PASS", findings_count: 0 },
    reliability: { name: "reliability", score: 85, status: "PASS", findings_count: 0 },
    safety: { name: "safety", score: 100, status: "PASS", findings_count: 0 },
    cost: { name: "cost", score: 80, status: "PASS", findings_count: 0 },
    efficiency: { name: "efficiency", score: 90, status: "PASS", findings_count: 0 },
    findings: [],
  };

  it("renders overall score, risk tier, and 7 domains", () => {
    render(<ScorecardCard scorecard={mockScorecard} />);
    expect(screen.getByText("92.5")).toBeInTheDocument();
    expect(screen.getByText("EXCELLENT")).toBeInTheDocument();
    expect(screen.getByText("task quality")).toBeInTheDocument();
    expect(screen.getByText("safety")).toBeInTheDocument();
  });
});

describe("FindingCard Component", () => {
  const mockFinding: EvaluationFinding = {
    finding_id: "f-1",
    severity: "CRITICAL",
    code: "SECRET_EXPOSURE",
    message: "Detected exposed API key in trace state payload",
    workflow_id: "w-1",
    affected_steps: [1, 2],
    metadata: { pattern_name: "OPENAI_API_KEY" },
  };

  it("renders finding severity, code, message, and affected steps", () => {
    render(<FindingCard finding={mockFinding} />);
    expect(screen.getByText("CRITICAL")).toBeInTheDocument();
    expect(screen.getByText("SECRET_EXPOSURE")).toBeInTheDocument();
    expect(
      screen.getByText("Detected exposed API key in trace state payload")
    ).toBeInTheDocument();
    expect(screen.getByText("Steps: [1, 2]")).toBeInTheDocument();
    expect(screen.getByText(/"pattern_name": "OPENAI_API_KEY"/)).toBeInTheDocument();
  });
});

describe("FindingsList Component", () => {
  it("renders empty state when findings list is empty", () => {
    render(<FindingsList findings={[]} />);
    expect(screen.getByText("No Findings Detected")).toBeInTheDocument();
  });

  it("renders findings when present", () => {
    const findings: EvaluationFinding[] = [
      {
        finding_id: "f-1",
        severity: "HIGH",
        code: "CYCLE_DETECTED",
        message: "Loop detected",
        workflow_id: "w-1",
        affected_steps: [1, 2, 3],
        metadata: {},
      },
    ];
    render(<FindingsList findings={findings} />);
    expect(screen.getByText("Deterministic Findings (1)")).toBeInTheDocument();
    expect(screen.getByText("CYCLE_DETECTED")).toBeInTheDocument();
  });
});

describe("EvaluationSummary Component", () => {
  const mockSummary: EvaluationSummaryResponse = {
    evaluation_id: "eval-12345",
    trace_id: "trace-abcde",
    status: "COMPLETED",
    started_at: "2026-11-08T12:00:00Z",
    completed_at: "2026-11-08T12:00:01Z",
    finding_count: 2,
    overall_score: 85.0,
    risk_classification: "GOOD",
  };

  it("renders evaluation run metadata", () => {
    render(<EvaluationSummary summary={mockSummary} />);
    expect(screen.getByText("eval-12345")).toBeInTheDocument();
    expect(screen.getByText("GOOD")).toBeInTheDocument();
    expect(screen.getByText("COMPLETED")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});

describe("TraceTable Component", () => {
  it("renders empty state when no traces provided", () => {
    render(<TraceTable traces={[]} />);
    expect(screen.getByText("No Traces Found")).toBeInTheDocument();
  });

  it("renders rows for traces", () => {
    const traces: TraceSummaryItem[] = [
      {
        trace_id: "12345678-0000-0000-0000-000000009999",
        workflow_status: "SUCCESS",
        step_count: 5,
        created_at: "2026-11-08T12:00:00Z",
        framework: "LANGGRAPH",
      },
    ];
    render(<TraceTable traces={traces} />);
    expect(screen.getByText("12345678...9999")).toBeInTheDocument();
    expect(screen.getByText("SUCCESS")).toBeInTheDocument();
    expect(screen.getByText("LANGGRAPH")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
  });
});

describe("SemanticEvaluationCard Component", () => {
  it("renders fallback notice when evaluation is unavailable", () => {
    const fallbackResult: SemanticEvaluationResult = {
      metrics: [],
      provider: "fallback",
      execution_time_ms: 0.1,
      evaluation_available: false,
      reason: "OPENAI_API_KEY is not configured.",
    };

    render(<SemanticEvaluationCard semanticResult={fallbackResult} />);
    expect(screen.getByText("Semantic Evaluation")).toBeInTheDocument();
    expect(screen.getByText("Provider: fallback")).toBeInTheDocument();
    expect(screen.getByText("Offline Fallback")).toBeInTheDocument();
    expect(screen.getByText("OPENAI_API_KEY is not configured.")).toBeInTheDocument();
  });

  it("renders active semantic metrics when available", () => {
    const activeResult: SemanticEvaluationResult = {
      metrics: [
        {
          finding_id: "sem-1",
          metric_name: "answer_relevancy",
          score: 0.95,
          passed: true,
          explanation: "High relevancy score",
        },
        {
          finding_id: "sem-2",
          metric_name: "hallucination",
          score: 0.1,
          passed: true,
          explanation: "No hallucination detected",
        },
      ],
      provider: "deepeval",
      execution_time_ms: 125.4,
      evaluation_available: true,
      reason: null,
    };

    render(<SemanticEvaluationCard semanticResult={activeResult} />);
    expect(screen.getByText("Semantic Evaluation")).toBeInTheDocument();
    expect(screen.getByText("Provider: deepeval")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getAllByText(/answer relevancy/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/hallucination/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/95\.0%/)).toBeInTheDocument();
    expect(screen.getByText("High relevancy score")).toBeInTheDocument();
  });

  it("renders loading and null states gracefully", () => {
    const { rerender } = render(<SemanticEvaluationCard semanticResult={null} loading={true} />);
    expect(screen.getByText("Loading semantic evaluation results...")).toBeInTheDocument();

    rerender(<SemanticEvaluationCard semanticResult={null} loading={false} />);
    expect(screen.queryByTestId("semantic-evaluation-card")).not.toBeInTheDocument();
  });
});

