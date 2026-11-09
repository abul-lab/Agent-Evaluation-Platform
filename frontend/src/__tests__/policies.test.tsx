import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import PoliciesPage from "@/app/policies/page";
import { PolicyAuditResponse, PolicyResponse, api } from "@/lib/api";

const mockPolicies: PolicyResponse[] = [
  {
    policy_id: "11111111-1111-1111-1111-111111111111",
    name: "Standard Platform Gate",
    description: "Default release governance policy",
    is_active: true,
    is_default: true,
    rules: {
      min_overall_score: 80.0,
      min_domain_scores: {
        task_quality: 80,
        safety: 90,
      },
      disallowed_risk_tiers: ["CRITICAL", "POOR"],
      prohibited_finding_codes: ["SECRET_EXPOSURE", "CYCLE_DETECTED"],
      max_critical_findings: 0,
      max_high_findings: 1,
      require_semantic_evaluation: false,
    },
    created_at: "2026-11-08T10:00:00Z",
    updated_at: "2026-11-08T10:00:00Z",
  },
  {
    policy_id: "22222222-2222-2222-2222-222222222222",
    name: "Canary Stage Policy",
    description: "Relaxed policy for staging",
    is_active: true,
    is_default: false,
    rules: {
      min_overall_score: 70.0,
      min_domain_scores: {},
      disallowed_risk_tiers: ["CRITICAL"],
      prohibited_finding_codes: [],
      max_critical_findings: 1,
      max_high_findings: 3,
      require_semantic_evaluation: false,
    },
    created_at: "2026-11-08T10:00:00Z",
    updated_at: "2026-11-08T10:00:00Z",
  },
];

const mockAuditApproved: PolicyAuditResponse = {
  audit_id: "33333333-3333-3333-3333-333333333333",
  policy_id: "11111111-1111-1111-1111-111111111111",
  policy_name: "Standard Platform Gate",
  evaluation_id: "44444444-4444-4444-4444-444444444444",
  verdict: "APPROVED",
  passed: true,
  violations: [],
  violations_count: 0,
  critical_violations_count: 0,
  overall_score: 95.0,
  risk_classification: "EXCELLENT",
  audited_at: "2026-11-08T12:00:00Z",
};

describe("PoliciesPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads and displays governance policy profiles", async () => {
    vi.spyOn(api, "listPolicies").mockResolvedValue(mockPolicies);

    render(<PoliciesPage />);
    expect(screen.getByText(/Loading governance policy profiles/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Standard Platform Gate" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Canary Stage Policy" })).toBeInTheDocument();
      expect(screen.getByText("DEFAULT")).toBeInTheDocument();
      expect(screen.getByText("80 pts")).toBeInTheDocument();
    });
  });

  it("opens create modal and saves a new policy profile", async () => {
    vi.spyOn(api, "listPolicies").mockResolvedValue(mockPolicies);
    vi.spyOn(api, "createPolicy").mockResolvedValue(mockPolicies[1]);

    render(<PoliciesPage />);
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Standard Platform Gate" })).toBeInTheDocument();
    });

    // Click "+ Create Policy Profile"
    const openModalBtn = screen.getByRole("button", { name: /\+ Create Policy Profile/i });
    fireEvent.click(openModalBtn);

    expect(screen.getByText("New Governance Policy Profile")).toBeInTheDocument();

    // Fill inputs
    const nameInput = screen.getByPlaceholderText(/e\.g\. Strict Production Gate/i);
    fireEvent.change(nameInput, { target: { value: "New Custom Gate" } });

    const saveBtn = screen.getByRole("button", { name: "Save Policy" });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.createPolicy).toHaveBeenCalled();
    });
  });

  it("submits audit and renders verdict outcome", async () => {
    vi.spyOn(api, "listPolicies").mockResolvedValue(mockPolicies);
    vi.spyOn(api, "auditEvaluation").mockResolvedValue(mockAuditApproved);

    render(<PoliciesPage />);
    await waitFor(() => {
      expect(screen.getByText("Evaluation Governance Audit Console")).toBeInTheDocument();
    });

    const evalInput = screen.getByPlaceholderText(/e\.g\. 550e8400/i);
    fireEvent.change(evalInput, {
      target: { value: "44444444-4444-4444-4444-444444444444" },
    });

    const auditBtn = screen.getByRole("button", { name: "Audit Evaluation" });
    fireEvent.click(auditBtn);

    await waitFor(() => {
      expect(api.auditEvaluation).toHaveBeenCalledWith(
        mockPolicies[0].policy_id,
        "44444444-4444-4444-4444-444444444444"
      );
      expect(screen.getByTestId("audit-result-card")).toBeInTheDocument();
      expect(screen.getByText(/APPROVED — Release Cleared/i)).toBeInTheDocument();
      expect(screen.getByText("95.0 pts")).toBeInTheDocument();
    });
  });
});
