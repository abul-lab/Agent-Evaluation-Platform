import React from "react";
import { RiskClassification } from "@/lib/api";

interface RiskBadgeProps {
  risk: RiskClassification;
  size?: "sm" | "md" | "lg";
}

const RISK_CONFIG: Record<
  RiskClassification,
  { label: string; bg: string; text: string; border: string; dot: string }
> = {
  EXCELLENT: {
    label: "EXCELLENT",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
    dot: "bg-emerald-600",
  },
  GOOD: {
    label: "GOOD",
    bg: "bg-teal-50",
    text: "text-teal-700",
    border: "border-teal-200",
    dot: "bg-teal-600",
  },
  WATCH: {
    label: "WATCH",
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
    dot: "bg-amber-500",
  },
  POOR: {
    label: "POOR",
    bg: "bg-orange-50",
    text: "text-orange-700",
    border: "border-orange-200",
    dot: "bg-orange-500",
  },
  CRITICAL: {
    label: "CRITICAL",
    bg: "bg-red-50",
    text: "text-red-700",
    border: "border-red-200",
    dot: "bg-red-600",
  },
};

export function RiskBadge({ risk, size = "md" }: RiskBadgeProps) {
  const config = RISK_CONFIG[risk] || RISK_CONFIG.WATCH;

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs font-medium",
    md: "px-2.5 py-1 text-xs font-semibold",
    lg: "px-3.5 py-1.5 text-sm font-bold",
  }[size];

  return (
    <span
      data-testid="risk-badge"
      className={`inline-flex items-center gap-1.5 rounded-full border ${config.bg} ${config.text} ${config.border} ${sizeClasses}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
      {config.label}
    </span>
  );
}

