import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RegressionReportCard } from "@/components/regressions/RegressionReportCard";
import { ComparisonView } from "@/components/benchmarks/ComparisonView";
import { EvaluationComparisonResponse, RegressionReport, api } from "@/lib/api";

const mockPolicy = {
  name: "Standard Quality Gate",
  max_score_drop: 5.0,
  max_domain_drop: 10.0,
  fail_on_risk_escalation: true,
  fail_on_new_critical_findings: true,
  prohibited_finding_codes: ["SECRET_EXPOSURE", "CYCLE_DETECTED"],
  min_overall_score: 75.0,
  min_safety_score: 90.0,
};

const mockPassedReport: RegressionReport = {
  status: "PASSED",
  is_regression: false,
  baseline_evaluation_id: "11111111-1111-1111-1111-111111111111",
  candidate_evaluation_id: "22222222-2222-2222-2222-222222222222",
  policy_applied: mockPolicy,
  overall_score_delta: 2.5,
  risk_transition: "GOOD -> GOOD",
  violations: [],
  violations_count: 0,
  critical_violations_count: 0,
  evaluated_at: "2026-11-08T12:00:00Z",
};

const mockRegressedReport: RegressionReport = {
  status: "REGRESSED",
  is_regression: true,
  baseline_evaluation_id: "11111111-1111-1111-1111-111111111111",
  candidate_evaluation_id: "33333333-3333-3333-3333-333333333333",
  policy_applied: mockPolicy,
  overall_score_delta: -15.0,
  risk_transition: "EXCELLENT -> CRITICAL",
  violations: [
    {
      rule: "OVERALL_SCORE_DROP",
      severity: "HIGH",
      message: "Overall score dropped by 15.0 points (threshold: -5.0)",
      baseline_value: 95.0,
      candidate_value: 80.0,
      threshold: -5.0,
    },
    {
      rule: "PROHIBITED_FINDING_CODE",
      severity: "CRITICAL",
      message: "Prohibited finding code 'CYCLE_DETECTED' detected",
      baseline_value: null,
      candidate_value: "CYCLE_DETECTED",
      threshold: "PROHIBITED",
    },
  ],
  violations_count: 2,
  critical_violations_count: 2,
  evaluated_at: "2026-11-08T12:00:00Z",
};

const mockComparison: EvaluationComparisonResponse = {
  base_evaluation_id: "11111111-1111-1111-1111-111111111111",
  target_evaluation_id: "33333333-3333-3333-3333-333333333333",
  base_trace_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  target_trace_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  base_score: 95.0,
  target_score: 80.0,
  overall_score_delta: -15.0,
  risk_transition: {
    base_risk: "EXCELLENT",
    target_risk: "CRITICAL",
    is_improved: false,
    is_degraded: true,
  },
  domain_deltas: {
    task_quality: {
      domain_name: "task_quality",
      base_score: 100,
      target_score: 80,
      score_delta: -20,
      base_status: "PASS",
      target_status: "WARN",
    },
  },
  finding_delta: {
    total_delta: 1,
    new_count: 1,
    resolved_count: 0,
    persistent_count: 0,
    new_findings: [],
    resolved_findings: [],
    persistent_findings: [],
  },
  compared_at: "2026-11-08T12:00:00Z",
};

describe("RegressionReportCard Component", () => {
  it("renders PASSED verdict with zero violations", () => {
    render(<RegressionReportCard report={mockPassedReport} />);
    expect(screen.getByText(/PASSED — Quality Gate Satisfied/i)).toBeInTheDocument();
    expect(screen.getByText("+2.5 pts")).toBeInTheDocument();
    expect(screen.getByText(/Zero policy violations detected/i)).toBeInTheDocument();
  });

  it("renders REGRESSED verdict with violations and toggles policy drawer", () => {
    render(<RegressionReportCard report={mockRegressedReport} />);
    expect(screen.getByText(/REGRESSED — Quality Gate Breached/i)).toBeInTheDocument();
    expect(screen.getByText("-15.0 pts")).toBeInTheDocument();
    expect(screen.getByText("OVERALL_SCORE_DROP")).toBeInTheDocument();
    expect(screen.getByText("PROHIBITED_FINDING_CODE")).toBeInTheDocument();

    // Toggle policy view
    const toggleBtn = screen.getByRole("button", { name: /View Applied Quality Policy/i });
    fireEvent.click(toggleBtn);
    expect(screen.getByText("Max Score Drop:")).toBeInTheDocument();
  });
});

describe("ComparisonView Regression Integration", () => {
  it("executes regression audit and renders report on click", async () => {
    vi.spyOn(api, "checkRegression").mockResolvedValue(mockRegressedReport);

    render(<ComparisonView comparison={mockComparison} />);
    expect(screen.getByText("Quality Gate & Regression Detection")).toBeInTheDocument();

    const auditBtn = screen.getByRole("button", { name: "Run Regression Audit" });
    fireEvent.click(auditBtn);

    await waitFor(() => {
      expect(api.checkRegression).toHaveBeenCalledWith(
        mockComparison.base_evaluation_id,
        mockComparison.target_evaluation_id
      );
      expect(screen.getByTestId("regression-report-card")).toBeInTheDocument();
    });
  });
});
