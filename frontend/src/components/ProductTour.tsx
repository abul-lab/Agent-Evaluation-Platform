"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";

export interface TourStep {
  title: string;
  badge: string;
  description: string;
  linkText: string;
  linkHref: string;
  highlight: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    title: "1. Canonical Agent Trace (CATS) & OTEL Intake",
    badge: "Ingestion Layer",
    description:
      "AEP captures complete agent trajectories including reasoning steps, prompt strings, and tool invocations. Ingest traces directly via CATS JSON or stream live telemetry from LangGraph, CrewAI, AutoGen, or LlamaIndex via standard OpenTelemetry OTLP collectors.",
    linkText: "Explore Trace Ingestion",
    linkHref: "/traces",
    highlight: "Zero agent code changes needed — native OpenTelemetry support out-of-the-box.",
  },
  {
    title: "2. Deterministic Multi-Domain Evaluation",
    badge: "Evaluation Engine",
    description:
      "Unlike slow and non-deterministic LLM-as-a-judge patterns, AEP audits agent executions through 7 parallel deterministic evaluators: Loop Detection, Tool Fidelity, Safety & Policy, Context & Budget, Latency Cascades, Goal Completion, and Cost Accounting.",
    linkText: "View Evaluation Pipeline",
    linkHref: "/architecture",
    highlight: "Executes in approximately 2–5ms with zero token cost and reproducible algorithmic scoring.",
  },
  {
    title: "3. Granular Scorecards & Actionable Findings",
    badge: "Diagnostic Scorecard",
    description:
      "Each evaluation outputs a structured scorecard with an overall composite score (0-100), domain sub-scores, and categorized findings (CRITICAL, HIGH, MEDIUM) complete with exact step indexes and remediation guidance.",
    linkText: "Inspect Operations Overview",
    linkHref: "/",
    highlight: "Instant root-cause analysis for loops, hallucinated tools, and token bloat.",
  },
  {
    title: "4. Performance Analytics & Regression Benchmarks",
    badge: "Benchmarking",
    description:
      "Compare model versions and prompt iterations across historical runs. Track token cost acceleration, step count distributions, and identify regressions before deploying new agent prompts to production.",
    linkText: "View Platform Analytics",
    linkHref: "/analytics",
    highlight: "Audit multiple runs side-by-side to verify latency and fidelity improvements.",
  },
  {
    title: "5. Automated Governance & Policy Enforcement",
    badge: "Governance Policy",
    description:
      "Configure workspace governance policy profiles. Define score floors and zero-tolerance defect policies for secret leaks or infinite loops. AEP returns machine-readable exit codes to automatically halt failing PRs in GitHub Actions or GitLab CI.",
    linkText: "Manage Governance Policies",
    linkHref: "/policies",
    highlight: "Automated release blocking stops unmonitored agent bugs from reaching end users.",
  },
  {
    title: "6. Multi-Channel Alerting & Workspace Isolation",
    badge: "Workspace Operations",
    description:
      "Manage multi-tenant workspaces with scoped API keys (ADMIN, ENGINEER, VIEWER). Dispatch incident alerts to Microsoft Teams (Adaptive Cards), Slack (Block Kit), or SIEM webhooks with automated credential scrubbing.",
    linkText: "Configure Workspaces & Alerts",
    linkHref: "/workspaces",
    highlight: "Alerts dispatch to Teams and Slack; credential findings are reported as CRITICAL.",
  },
];

interface ProductTourProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ProductTour({ isOpen, onClose }: ProductTourProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "auto";
    }
    return () => {
      document.body.style.overflow = "auto";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const step = TOUR_STEPS[currentStepIndex];
  const progressPercent = ((currentStepIndex + 1) / TOUR_STEPS.length) * 100;

  const handleNext = () => {
    if (currentStepIndex < TOUR_STEPS.length - 1) {
      setCurrentStepIndex(currentStepIndex + 1);
    } else {
      handleComplete();
    }
  };

  const handlePrev = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(currentStepIndex - 1);
    }
  };

  const handleComplete = () => {
    try {
      localStorage.setItem("aep_tour_completed", "true");
    } catch {
      // ignore
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-xl rounded-2xl border border-slate-200 shadow-2xl overflow-hidden flex flex-col">
        {/* Top Progress Bar */}
        <div className="w-full bg-slate-100 h-1.5">
          <div
            className="bg-blue-600 h-1.5 transition-all duration-300 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {/* Modal Header */}
        <div className="p-6 pb-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
              {step.badge}
            </span>
            <span className="text-xs font-semibold text-slate-500">
              Step {currentStepIndex + 1} of {TOUR_STEPS.length}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-sm font-semibold p-1 rounded-md hover:bg-slate-50 transition"
            aria-label="Close Tour"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          <h3 className="text-xl font-extrabold text-slate-900 tracking-tight">{step.title}</h3>
          <p className="text-sm text-slate-600 leading-relaxed">{step.description}</p>

          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-start space-x-2.5">
            <span className="text-blue-600 text-sm font-bold">💡</span>
            <div className="text-xs text-slate-700 font-medium leading-relaxed">
              <strong>Key Advantage:</strong> {step.highlight}
            </div>
          </div>

          <div className="pt-2">
            <Link
              href={step.linkHref}
              onClick={onClose}
              className="inline-flex items-center text-xs font-bold text-blue-600 hover:text-blue-700 hover:underline"
            >
              {step.linkText} →
            </Link>
          </div>
        </div>

        {/* Modal Footer Controls */}
        <div className="p-4 sm:p-6 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <button
            onClick={handleComplete}
            className="text-xs font-medium text-slate-500 hover:text-slate-700 transition"
          >
            Skip Product Tour
          </button>

          <div className="flex items-center space-x-2">
            {currentStepIndex > 0 && (
              <button
                onClick={handlePrev}
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 bg-white hover:bg-slate-50 transition"
              >
                Previous
              </button>
            )}

            <button
              onClick={handleNext}
              className="px-4 py-1.5 text-xs font-bold rounded-lg bg-blue-600 text-white hover:bg-blue-700 shadow-sm transition"
            >
              {currentStepIndex === TOUR_STEPS.length - 1 ? "Finish Tour" : "Next Step →"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

