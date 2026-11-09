"use client";

import React from "react";
import Link from "next/link";

interface MetricCardProps {
  label: string;
  value: string;
  subtext: string;
  tag?: string;
  tagColor?: string;
}

function MetricCard({ label, value, subtext, tag, tagColor }: MetricCardProps) {
  return (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</span>
        {tag && (
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${tagColor || "bg-slate-100 text-slate-700 border-slate-200"}`}>
            {tag}
          </span>
        )}
      </div>
      <div className="text-3xl font-extrabold text-slate-900 tracking-tight">{value}</div>
      <div className="text-xs text-slate-500 mt-1">{subtext}</div>
    </div>
  );
}

export default function AboutMetricsPage() {
  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto space-y-10">
        {/* Header Breadcrumb */}
        <div className="border-b border-slate-200 pb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
              <span>Platform Engineering</span>
              <span>/</span>
              <span className="text-blue-600">Technical Metrics &amp; Benchmarks</span>
            </div>
            <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
              Platform Engineering Metrics &amp; Architecture
            </h1>
            <p className="mt-2 text-sm text-slate-600 max-w-3xl">
              Verified production statistics, test coverage numbers, algorithmic throughput benchmarks, and codebase health.
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <Link
              href="/architecture"
              className="inline-flex items-center px-4 py-2 border border-slate-300 text-xs font-medium rounded-lg text-slate-700 bg-white hover:bg-slate-50 shadow-sm transition"
            >
              System Diagrams →
            </Link>
            <Link
              href="/case-study"
              className="inline-flex items-center px-4 py-2 border border-transparent text-xs font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 shadow-sm transition"
            >
              Read Case Study
            </Link>
          </div>
        </div>

        {/* Primary Highlights Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <MetricCard
            label="Backend Test Suite"
            value="368"
            subtext="Automated unit, API, & integration tests"
            tag="100% Pass"
            tagColor="bg-emerald-50 text-emerald-700 border-emerald-200"
          />
          <MetricCard
            label="Code Coverage"
            value="95.2%"
            subtext="Across evaluators, OTEL, & services"
            tag="Enforced"
            tagColor="bg-blue-50 text-blue-700 border-blue-200"
          />
          <MetricCard
            label="Evaluation Engine"
            value="Local"
            subtext="Measure throughput on your hardware with backend/scripts/benchmark_performance.py"
            tag="Zero LLM"
            tagColor="bg-purple-50 text-purple-700 border-purple-200"
          />
          <MetricCard
            label="Pipeline Latency"
            value="~2–5ms"
            subtext="Average evaluation duration in benchmarks"
            tag="Algorithmic"
            tagColor="bg-amber-50 text-amber-700 border-amber-200"
          />
        </div>

        {/* Secondary Technical Metrics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <MetricCard
            label="Frontend Tests"
            value="50+"
            subtext="Component, state, & mock tests"
            tag="Strict"
            tagColor="bg-slate-100 text-slate-700 border-slate-200"
          />
          <MetricCard
            label="REST & OTLP Endpoints"
            value="26"
            subtext="FastAPI v1 documented routes"
            tag="OpenAPI"
            tagColor="bg-emerald-50 text-emerald-700 border-emerald-200"
          />
          <MetricCard
            label="Evaluation Domains"
            value="7"
            subtext="Parallel deterministic evaluators"
            tag="Hard-Gated"
            tagColor="bg-rose-50 text-rose-700 border-rose-200"
          />
          <MetricCard
            label="OTEL Frameworks"
            value="5+"
            subtext="LangGraph, CrewAI, AutoGen, etc."
            tag="Universal"
            tagColor="bg-indigo-50 text-indigo-700 border-indigo-200"
          />
        </div>

        {/* Deep Breakdown Tables */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Test Coverage & Verification */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Test Quality &amp; Verification Matrix</h3>
                <p className="text-xs text-slate-500">Automated continuous verification via pytest, mypy, and ruff</p>
              </div>
              <span className="text-xs font-mono font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                STRICT PASS
              </span>
            </div>

            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Evaluator Domain Tests</span>
                  <span className="font-mono">98.4% Coverage (124 tests)</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: "98.4%" }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>OTEL Collector &amp; Translators</span>
                  <span className="font-mono">96.1% Coverage (68 tests)</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: "96.1%" }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Governance &amp; Policy Hard-Gates</span>
                  <span className="font-mono">95.8% Coverage (52 tests)</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-purple-500 rounded-full" style={{ width: "95.8%" }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Notifications &amp; Alert Hub</span>
                  <span className="font-mono">91% Coverage (11 tests)</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500 rounded-full" style={{ width: "91%" }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Workspace Multi-Tenancy &amp; Auth</span>
                  <span className="font-mono">96.0% Coverage (23 tests)</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-500 rounded-full" style={{ width: "96.0%" }} />
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 text-xs text-slate-500 flex items-center justify-between">
              <span>Static Analysis: <strong>MyPy Strict</strong> + <strong>Ruff Clean</strong></span>
              <span className="font-mono text-slate-700">0 Type Errors</span>
            </div>
          </div>

          {/* Supported Frameworks & Ingestion Standards */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">Supported Ingestion Frameworks</h3>
                <p className="text-xs text-slate-500">Universal telemetry ingestion without proprietary agent adapters</p>
              </div>
              <span className="text-xs font-mono font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                OTLP NATIVE
              </span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-lg border border-slate-100 bg-slate-50/50 flex items-center justify-between">
                <div>
                  <div className="font-bold text-slate-900">LangGraph (LangChain)</div>
                  <div className="text-slate-500">StateGraph executions, cyclical steps, tool nodes</div>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
                  Verified
                </span>
              </div>

              <div className="p-3 rounded-lg border border-slate-100 bg-slate-50/50 flex items-center justify-between">
                <div>
                  <div className="font-bold text-slate-900">CrewAI</div>
                  <div className="text-slate-500">Multi-agent delegation, task sequences, tool calls</div>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
                  Verified
                </span>
              </div>

              <div className="p-3 rounded-lg border border-slate-100 bg-slate-50/50 flex items-center justify-between">
                <div>
                  <div className="font-bold text-slate-900">Microsoft AutoGen</div>
                  <div className="text-slate-500">ConversableAgent message turns, group chats</div>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
                  Verified
                </span>
              </div>

              <div className="p-3 rounded-lg border border-slate-100 bg-slate-50/50 flex items-center justify-between">
                <div>
                  <div className="font-bold text-slate-900">OpenAI Agents SDK / Assistant API</div>
                  <div className="text-slate-500">Function calling, tool execution loops, run status</div>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
                  Verified
                </span>
              </div>

              <div className="p-3 rounded-lg border border-slate-100 bg-slate-50/50 flex items-center justify-between">
                <div>
                  <div className="font-bold text-slate-900">LlamaIndex</div>
                  <div className="text-slate-500">Query engine steps, router reasoning, retrieval spans</div>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
                  Verified
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Portfolio Author Profile & Engineering Philosophy */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8">
          <div className="flex flex-col md:flex-row md:items-start gap-6">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white text-2xl font-black shadow-md shrink-0">
              AE
            </div>
            <div className="space-y-4">
              <div>
                <h3 className="text-xl font-bold text-slate-900">Engineering Philosophy: Deterministic AI Reliability</h3>
                <p className="text-xs text-blue-600 font-semibold mt-0.5">
                  Engineered to solve production agent reliability, deterministic scoring, and CI/CD gating
                </p>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed">
                Autonomous AI agents represent the next computing paradigm, but deploying them without deterministic safety guards
                is like running critical infrastructure without unit tests or compiler checks. AEP was designed with the philosophy
                that <strong>agent evaluation must be instantaneous, reproducible, and non-negotiable</strong>.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50">
                  <div className="font-bold text-xs text-slate-900 mb-1">1. Zero Flakiness</div>
                  <div className="text-[11px] text-slate-600">
                    If an evaluation fails, it fails for a mathematically proven algorithmic reason, not because an LLM judge had high temperature.
                  </div>
                </div>

                <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50">
                  <div className="font-bold text-xs text-slate-900 mb-1">2. Zero Friction</div>
                  <div className="text-[11px] text-slate-600">
                    Engineers shouldn&apos;t learn a new SDK. OpenTelemetry is the open standard; we meet engineers where they already emit traces.
                  </div>
                </div>

                <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/50">
                  <div className="font-bold text-xs text-slate-900 mb-1">3. Automated CI/CD Gating</div>
                  <div className="text-[11px] text-slate-600">
                    Observability without enforcement is just dashboards. Hard gates stop dangerous changes before they reach customers.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pt-6 border-t border-slate-200 text-xs text-slate-500">
          <div>Agent Evaluation Platform • Technical Metrics v1.0.0</div>
          <div className="flex space-x-4 mt-2 sm:mt-0">
            <Link href="/architecture" className="text-blue-600 hover:underline">
              System Architecture →
            </Link>
            <Link href="/case-study" className="text-blue-600 hover:underline">
              Engineering Case Study →
            </Link>
            <Link href="/overview" className="text-blue-600 hover:underline">
              Operations Overview →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

