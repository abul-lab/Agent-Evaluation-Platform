"use client";

import React, { useState } from "react";
import Link from "next/link";

interface LayerDetail {
  id: string;
  name: string;
  tagline: string;
  badge: string;
  badgeColor: string;
  summary: string;
  components: string[];
  invariants: string[];
  latency: string;
}

const LAYERS: LayerDetail[] = [
  {
    id: "frameworks",
    name: "1. Agent Framework Emitters",
    tagline: "Universal runtime telemetry without proprietary vendor lock-in",
    badge: "Zero SDK Changes",
    badgeColor: "bg-emerald-50 text-emerald-700 border-emerald-200",
    summary:
      "Agents running on LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, or LlamaIndex emit standardized OpenTelemetry spans via standard OTLP exporters. No custom AEP client library or code refactoring is required.",
    components: [
      "OpenTelemetry Python SDK (opentelemetry-sdk)",
      "OTLP Exporters (gRPC & HTTP/JSON)",
      "OpenInference & GenAI Semantic Conventions",
      "Agent execution spans, tool calls, LLM completions",
    ],
    invariants: [
      "Zero platform lock-in: works with any OTLP-compatible agent harness",
      "Unmodified user codebase; drops into existing CI/CD or staging environments",
      "Spans carry full prompt strings, tool signatures, and token usage",
    ],
    latency: "< 0.5ms instrumentation overhead",
  },
  {
    id: "collector",
    name: "2. OTLP Collector & Intake Gate",
    tagline: "Workspace-authenticated, rate-limited OTLP HTTP/gRPC receiver",
    badge: "Universal Ingestion",
    badgeColor: "bg-blue-50 text-blue-700 border-blue-200",
    summary:
      "The native collector endpoint accepts OTLP v1/traces payloads over HTTP and gRPC. It verifies workspace API keys with SHA-256 hashes, enforces sliding-window rate limits, and buffers span batches before translation.",
    components: [
      "POST /api/v1/otel/collector (OTLP/HTTP & JSON)",
      "OTLP/gRPC streaming receiver service",
      "Workspace API Key validator (ENGINEER & ADMIN roles)",
      "Sliding-window memory rate limiter (60s window)",
      "Payload size guard (10MB ceiling)",
    ],
    invariants: [
      "Every trace is strictly scoped to an authenticated workspace tenant",
      "Rejects malformed Protobuf/JSON payloads before internal memory allocation",
      "In-memory buffered ingestion with rate limiting and backpressure controls",
    ],
    latency: "< 2.8ms intake & auth latency",
  },
  {
    id: "translator",
    name: "3. Semantic Translation Core (OTEL → CATS)",
    tagline: "Translates heterogeneous span trees into Canonical Agent Trace Schema",
    badge: "Universal Bridge",
    badgeColor: "bg-indigo-50 text-indigo-700 border-indigo-200",
    summary:
      "OTEL traces represent execution as distributed spans. The translator reconstructs chronological parent-child call trees, groups tool invocations under discrete agent reasoning steps, normalizes token counters, and produces a validated CATS v1.0.0 artifact.",
    components: [
      "OtelCatsTranslator engine (backend/app/otel/translator.py)",
      "SpanKind classifier (INTERNAL -> Step, CLIENT -> Tool/LLM)",
      "GenAI convention extractor (gen_ai.prompt, gen_ai.completion)",
      "Hierarchical tree builder & chronological sorter",
      "Pydantic V2 CATS schema validator",
    ],
    invariants: [
      "Evaluators and policies evaluate CATS traces independently of the source framework",
      "Deterministic normalization: identical OTEL inputs produce byte-identical CATS traces",
      "Captures error status, stack traces, and cost metrics faithfully",
    ],
    latency: "< 1.5ms translation duration",
  },
  {
    id: "evaluators",
    name: "4. Deterministic Evaluation Engine",
    tagline: "Seven parallel, zero-LLM evaluators for reproducible agent quality grading",
    badge: "100% Deterministic",
    badgeColor: "bg-purple-50 text-purple-700 border-purple-200",
    summary:
      "Instead of slow, non-deterministic LLM-as-a-judge approaches, AEP runs 7 specialized algorithmic evaluators in parallel. They audit state machines for loops, detect tool hallucination, check security policies, and calculate exact costs.",
    components: [
      "Loop Detection: Exact state hashing & cyclic pattern recognition",
      "Tool Fidelity: Hallucinated tools & JSON schema adherence",
      "Safety & Policy: Secrets leakage & prompt injection fingerprinting",
      "Context & Budget: Context saturation & token consumption ceilings",
      "Latency & Cascades: Retry storms & step latency anomaly detection",
      "Goal Completion: Terminal state verification & outcome assertions",
      "Cost Accounting: Dollar pricing tiers & multi-model budget tracking",
    ],
    invariants: [
      "Zero external API calls or network dependencies during evaluation",
      "Deterministic: identical traces produce identical scores every time",
      "Throughput depends on hardware and workload; measure it with backend/scripts/benchmark_performance.py",
    ],
    latency: "Approximately 2–5ms evaluation execution",
  },
  {
    id: "governance",
    name: "5. Governance & Hard-Gating Engine",
    tagline: "Auditable compliance policy enforcement with automated CI/CD gating",
    badge: "Policy Gatekeeper",
    badgeColor: "bg-rose-50 text-rose-700 border-rose-200",
    summary:
      "Audits evaluation scorecards against environment-specific Governance Policy Profiles. Enforces non-negotiable hard gates (e.g., zero secret leaks or loops) and minimum composite score floors to block flawed agent versions in CI/CD.",
    components: [
      "PolicyEngine auditor (backend/app/services/policy_engine.py)",
      "Multi-environment profiles (Production, Staging, Experimental)",
      "Hard-gate enforcer (Zero tolerance for CRITICAL safety flaws)",
      "Domain score floor verification (Min Safety, Min Fidelity, Min Loop)",
      "GovernanceAuditRecord version-snapshotted compliance trail",
    ],
    invariants: [
      "Hard gates veto deployments regardless of overall composite score",
      "Audit records snapshot exact policy rule definitions at evaluation time",
      "Returns machine-readable CI exit codes (0 for pass, 1 for block)",
    ],
    latency: "< 0.8ms compliance verdict",
  },
  {
    id: "notifications",
    name: "6. Notifications & Alerting Hub",
    tagline: "Multi-channel incident routing for Slack, Microsoft Teams, and SIEM webhooks",
    badge: "Real-time Operations",
    badgeColor: "bg-amber-50 text-amber-700 border-amber-200",
    summary:
      "When evaluations fail or governance policies fail audit, the notification hub sanitizes sensitive payloads and immediately dispatches structured alerts with deep links to Microsoft Teams (Adaptive Cards), Slack (Block Kit), or SIEMs.",
    components: [
      "NotificationService dispatcher (backend/app/services/notification_service.py)",
      "Adaptive Cards v1.5 generator with metadata FactSets",
      "Slack Block Kit generator with interactive action buttons",
      "Generic Webhook emitter (JSON over HTTPS, masked URLs in API responses)",
      "Sensitive credential redactor (API keys, tokens, PII)",
      "Delivery tracking log with HTTP latency & response codes",
    ],
    invariants: [
      "Non-blocking background delivery; does not delay API responses",
      "Automated secret scrubbing filters credentials before delivery to notification channels",
      "Direct deep links allow operators to inspect traces quickly",
    ],
    latency: "< 25ms async dispatch",
  },
];

const DIAGRAMS = [
  {
    id: "system_architecture",
    title: "System Architecture",
    description: "End-to-end platform architecture from agent emitters down to governance and alerting.",
    path: "/diagrams/system_architecture.svg",
  },
  {
    id: "evaluation_pipeline",
    title: "Deterministic Evaluation Pipeline",
    description: "Detailed breakdown of the 7 parallel evaluation domains, intake validation, and scorecard assembly.",
    path: "/diagrams/evaluation_pipeline.svg",
  },
  {
    id: "otel_translation_flow",
    title: "OTEL → CATS Translation Flow",
    description: "OpenTelemetry span ingestion, semantic parsing, and canonical schema transformation.",
    path: "/diagrams/otel_translation_flow.svg",
  },
  {
    id: "governance_flow",
    title: "Governance & Hard-Gating Engine",
    description: "Policy profile verification, zero-tolerance hard-gating, and CI/CD automated release blocking.",
    path: "/diagrams/governance_flow.svg",
  },
  {
    id: "notification_flow",
    title: "Notifications & Alerting Hub",
    description: "Multi-channel alert dispatching to Teams, Slack, and webhooks with payload sanitization.",
    path: "/diagrams/notification_flow.svg",
  },
];

export default function ArchitecturePage() {
  const [selectedLayer, setSelectedLayer] = useState<string>("translator");
  const [activeDiagram, setActiveDiagram] = useState<string>("system_architecture");

  const currentLayer = LAYERS.find((l) => l.id === selectedLayer) || LAYERS[0];
  const currentDiagram = DIAGRAMS.find((d) => d.id === activeDiagram) || DIAGRAMS[0];

  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-12">
        {/* Header Breadcrumb */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between border-b border-slate-200 pb-6">
          <div>
            <div className="flex items-center space-x-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
              <span>Platform Engineering</span>
              <span>/</span>
              <span className="text-blue-600">Architecture &amp; System Design</span>
            </div>
            <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
              Platform Architecture &amp; Technical Specifications
            </h1>
            <p className="mt-2 text-base text-slate-600 max-w-3xl">
              A deterministic evaluation harness and automated governance gateway for autonomous AI agents, designed using production-oriented patterns.
              Engineered for predictable evaluation latency, reproducible scoring, and standard OpenTelemetry ingestion.
            </p>
          </div>
          <div className="mt-4 md:mt-0 flex items-center space-x-3">
            <Link
              href="/case-study"
              className="inline-flex items-center px-4 py-2 border border-slate-300 text-sm font-medium rounded-lg text-slate-700 bg-white hover:bg-slate-50 shadow-sm transition"
            >
              Read Case Study →
            </Link>
            <Link
              href="/about"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 shadow-sm transition"
            >
              Technical Metrics
            </Link>
          </div>
        </div>

        {/* Executive Summary Cards: Problem vs Solution */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Problem */}
          <div className="bg-white rounded-xl border border-red-100 shadow-sm p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-red-500" />
            <div className="flex items-center space-x-3 mb-4">
              <span className="p-2 rounded-lg bg-red-50 text-red-600 font-mono font-bold text-sm">
                01
              </span>
              <h2 className="text-lg font-bold text-slate-900">The Problem: Silent Agent Failures</h2>
            </div>
            <p className="text-sm text-slate-600 mb-4 leading-relaxed">
              AI agents are dynamic, non-deterministic state machines. When deployed in production environments,
              they can exhibit operational failure modes that standard telemetry metrics do not capture:
            </p>
            <ul className="space-y-2.5 text-xs text-slate-700">
              <li className="flex items-start">
                <span className="text-red-500 mr-2 font-bold">✕</span>
                <span><strong>Unbounded Loops:</strong> Agents getting trapped in repetitive self-talk and tool loops, burning tokens.</span>
              </li>
              <li className="flex items-start">
                <span className="text-red-500 mr-2 font-bold">✕</span>
                <span><strong>Tool Hallucination:</strong> Invoking non-existent APIs or passing invalid arguments that crash background jobs.</span>
              </li>
              <li className="flex items-start">
                <span className="text-red-500 mr-2 font-bold">✕</span>
                <span><strong>Security &amp; Secret Leaks:</strong> Exposing database credentials, Bearer tokens, or internal system prompts.</span>
              </li>
              <li className="flex items-start">
                <span className="text-red-500 mr-2 font-bold">✕</span>
                <span><strong>Unregulated Releases:</strong> Lack of automated CI/CD gating to catch degraded prompts before deployment.</span>
              </li>
            </ul>
          </div>

          {/* Solution */}
          <div className="bg-white rounded-xl border border-emerald-100 shadow-sm p-6 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-1 bg-emerald-500" />
            <div className="flex items-center space-x-3 mb-4">
              <span className="p-2 rounded-lg bg-emerald-50 text-emerald-600 font-mono font-bold text-sm">
                02
              </span>
              <h2 className="text-lg font-bold text-slate-900">The Solution: Agent Evaluation Platform</h2>
            </div>
            <p className="text-sm text-slate-600 mb-4 leading-relaxed">
              AEP introduces an OpenTelemetry-native evaluation pipeline paired with a deterministic,
              policy-driven governance engine that enforces quality standards for autonomous agents:
            </p>
            <ul className="space-y-2.5 text-xs text-slate-700">
              <li className="flex items-start">
                <span className="text-emerald-600 mr-2 font-bold">✓</span>
                <span><strong>Universal OTEL Ingestion:</strong> Connects directly to LangGraph, CrewAI, AutoGen, and OpenAI SDK with zero code changes.</span>
              </li>
              <li className="flex items-start">
                <span className="text-emerald-600 mr-2 font-bold">✓</span>
                <span><strong>Deterministic Evaluation:</strong> 7 parallel algorithmic evaluators running in &lt;5ms without slow, noisy LLM-as-a-judge.</span>
              </li>
              <li className="flex items-start">
                <span className="text-emerald-600 mr-2 font-bold">✓</span>
                <span><strong>Automated CI/CD Gating:</strong> Enforces environment score floors and zero-tolerance hard-gates with exit codes.</span>
              </li>
              <li className="flex items-start">
                <span className="text-emerald-600 mr-2 font-bold">✓</span>
                <span><strong>Multi-Channel Alerting:</strong> Real-time incident routing to Slack Block Kit and Teams Adaptive Cards.</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Section 1: System Diagram Viewer */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-slate-200 bg-white flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900">System Architecture Diagrams</h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Interactive vector specifications documenting the complete end-to-end data flow and governance engine.
              </p>
            </div>
            {/* Diagram Switcher Tabs */}
            <div className="flex flex-wrap gap-2">
              {DIAGRAMS.map((diag) => (
                <button
                  key={diag.id}
                  onClick={() => setActiveDiagram(diag.id)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
                    activeDiagram === diag.id
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {diag.title}
                </button>
              ))}
            </div>
          </div>

          {/* Active Diagram Details Banner */}
          <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider mr-2">Viewing:</span>
              <span className="text-sm font-semibold text-slate-900">{currentDiagram.title}</span>
              <span className="text-xs text-slate-500 ml-2">— {currentDiagram.description}</span>
            </div>
            <a
              href={currentDiagram.path}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline inline-flex items-center"
            >
              Open Raw SVG ↗
            </a>
          </div>

          {/* SVG Frame */}
          <div className="p-4 sm:p-6 bg-slate-50 flex items-center justify-center overflow-auto max-h-[750px]">
            <div className="w-full max-w-5xl bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={currentDiagram.path}
                alt={currentDiagram.title}
                className="w-full h-auto object-contain"
              />
            </div>
          </div>
        </div>

        {/* Section 2: Interactive Layer Inspector */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-slate-900">Interactive Architecture Layer Inspector</h2>
            <p className="text-sm text-slate-500 mt-1">
              Select any architecture layer below to inspect its design invariants, components, and target performance SLAs.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Layer Selector */}
            <div className="lg:col-span-5 space-y-2">
              {LAYERS.map((layer) => {
                const isSelected = selectedLayer === layer.id;
                return (
                  <button
                    key={layer.id}
                    onClick={() => setSelectedLayer(layer.id)}
                    className={`w-full text-left p-3.5 rounded-xl border transition flex items-center justify-between ${
                      isSelected
                        ? "bg-blue-50/60 border-blue-400 shadow-sm"
                        : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/70"
                    }`}
                  >
                    <div>
                      <div className="text-xs font-bold text-slate-900">{layer.name}</div>
                      <div className="text-xs text-slate-500 truncate max-w-xs">{layer.tagline}</div>
                    </div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${layer.badgeColor}`}
                    >
                      {layer.badge}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Right Column: Layer Deep-Dive Inspector */}
            <div className="lg:col-span-7 bg-slate-50 rounded-xl border border-slate-200 p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-slate-200 pb-4 mb-4">
                  <div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${currentLayer.badgeColor} uppercase tracking-wider`}
                    >
                      {currentLayer.badge}
                    </span>
                    <h3 className="text-lg font-extrabold text-slate-900 mt-1.5">{currentLayer.name}</h3>
                    <p className="text-xs text-slate-600">{currentLayer.tagline}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
                      Target SLA
                    </span>
                    <span className="text-xs font-mono font-bold text-blue-600">{currentLayer.latency}</span>
                  </div>
                </div>

                <p className="text-sm text-slate-700 leading-relaxed mb-6">{currentLayer.summary}</p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Key Components */}
                  <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
                    <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2.5">
                      Key Components
                    </h4>
                    <ul className="space-y-1.5 text-xs text-slate-600">
                      {currentLayer.components.map((comp, idx) => (
                        <li key={idx} className="flex items-start">
                          <span className="text-blue-500 mr-2">•</span>
                          <span>{comp}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Architectural Invariants */}
                  <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-2xs">
                    <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2.5">
                      Design Invariants
                    </h4>
                    <ul className="space-y-1.5 text-xs text-slate-600">
                      {currentLayer.invariants.map((inv, idx) => (
                        <li key={idx} className="flex items-start">
                          <span className="text-emerald-500 mr-2">✓</span>
                          <span>{inv}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
                <span>Deterministic Layer Verification</span>
                <span className="font-mono text-emerald-600 font-bold">STATUS: STABLE (v1.0.0)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Technology Stack Grid */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-slate-900">Technology Stack &amp; Dependencies</h2>
            <p className="text-sm text-slate-500 mt-1">
              Engineered with a strictly-typed foundation designed for in-memory execution.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Backend */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
              <div className="flex items-center space-x-2 mb-3">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                <h3 className="text-sm font-bold text-slate-900">Core Backend</h3>
              </div>
              <ul className="space-y-2 text-xs text-slate-600">
                <li><strong className="text-slate-900">Python 3.11:</strong> Type unions and asynchronous concurrency</li>
                <li><strong className="text-slate-900">FastAPI:</strong> Asynchronous ASGI endpoints</li>
                <li><strong className="text-slate-900">Pydantic v2:</strong> Rust-backed validation &amp; serialization</li>
                <li><strong className="text-slate-900">SQLModel:</strong> Unified schema definition with SQLAlchemy</li>
                <li><strong className="text-slate-900">Uvicorn:</strong> Production ASGI server</li>
              </ul>
            </div>

            {/* Frontend */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
              <div className="flex items-center space-x-2 mb-3">
                <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
                <h3 className="text-sm font-bold text-slate-900">Web User Interface</h3>
              </div>
              <ul className="space-y-2 text-xs text-slate-600">
                <li><strong className="text-slate-900">Next.js 14:</strong> React App Router &amp; client components</li>
                <li><strong className="text-slate-900">TypeScript (Strict):</strong> Type-checked frontend contracts</li>
                <li><strong className="text-slate-900">Tailwind CSS:</strong> Consistent light UI design system</li>
                <li><strong className="text-slate-900">Lucide Icons:</strong> Consistent semantic icon set</li>
                <li><strong className="text-slate-900">Responsive Grid:</strong> Desktop &amp; mobile layouts</li>
              </ul>
            </div>

            {/* Telemetry & Standards */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
              <div className="flex items-center space-x-2 mb-3">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <h3 className="text-sm font-bold text-slate-900">Telemetry &amp; Protocols</h3>
              </div>
              <ul className="space-y-2 text-xs text-slate-600">
                <li><strong className="text-slate-900">OpenTelemetry (OTEL):</strong> Universal trace specification</li>
                <li><strong className="text-slate-900">OTLP/HTTP &amp; gRPC:</strong> Dual-protocol collector intake</li>
                <li><strong className="text-slate-900">OpenInference:</strong> Semantic GenAI trace conventions</li>
                <li><strong className="text-slate-900">CATS v1.0.0:</strong> Canonical Agent Trace Schema</li>
                <li><strong className="text-slate-900">HTTPS-only:</strong> Webhook destinations; URLs masked in API responses</li>
              </ul>
            </div>

            {/* Quality & Reliability */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50">
              <div className="flex items-center space-x-2 mb-3">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
                <h3 className="text-sm font-bold text-slate-900">Reliability &amp; QA</h3>
              </div>
              <ul className="space-y-2 text-xs text-slate-600">
                <li><strong className="text-slate-900">Pytest (368 tests):</strong> 92% backend code coverage</li>
                <li><strong className="text-slate-900">Ruff:</strong> Blazing fast Python linter &amp; formatter</li>
                <li><strong className="text-slate-900">MyPy (Strict):</strong> Zero runtime type coercion bugs</li>
                <li><strong className="text-slate-900">Vitest / Jest:</strong> 50+ passing frontend unit tests</li>
                <li><strong className="text-slate-900">Benchmarking:</strong> Microsecond profiling harness</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Section 4: Architectural Trade-Offs & Decisions */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-slate-900">Key Engineering Trade-offs &amp; Decisions</h2>
            <p className="text-sm text-slate-500 mt-1">
              Every architectural decision balances latency, cost, determinism, and developer friction.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Decision 1 */}
            <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-2xs">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-slate-900">
                  Deterministic Evaluators vs. LLM-as-a-Judge
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Deterministic Chosen
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed mb-3">
                <strong>Trade-off:</strong> Using LLMs to evaluate other LLMs introduces non-determinism (evaluator variance),
                high and variable cost per evaluation, and variable latency.
              </p>
              <div className="bg-slate-50 p-3 rounded-lg text-xs text-slate-700 space-y-1">
                <div><strong>Why AEP chose deterministic:</strong></div>
                <div className="text-slate-600">• Sub-millisecond execution (&lt;5ms vs 2,500ms) enables inline CI/CD blocking.</div>
                <div className="text-slate-600">• $0.00 compute cost per evaluation run.</div>
                <div className="text-slate-600">• 100% reproducible: zero variance across regression runs.</div>
              </div>
            </div>

            {/* Decision 2 */}
            <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-2xs">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-slate-900">
                  OpenTelemetry vs. Proprietary Agent SDK
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                  OTEL Chosen
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed mb-3">
                <strong>Trade-off:</strong> Building a proprietary Python SDK provides tighter control over payload schemas,
                but imposes massive developer friction and adoption barriers.
              </p>
              <div className="bg-slate-50 p-3 rounded-lg text-xs text-slate-700 space-y-1">
                <div><strong>Why AEP chose OpenTelemetry:</strong></div>
                <div className="text-slate-600">• Zero code changes required for agent developers already using OTEL exporters.</div>
                <div className="text-slate-600">• Universal support across LangGraph, CrewAI, AutoGen, and custom harnesses.</div>
                <div className="text-slate-600">• Aligns with standard OpenTelemetry collectors and observability pipelines.</div>
              </div>
            </div>

            {/* Decision 3 */}
            <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-2xs">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-slate-900">
                  Synchronous Gating vs. Asynchronous Task Queue
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
                  Hybrid Chosen
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed mb-3">
                <strong>Trade-off:</strong> Asynchronous evaluation decouples execution from network latency, but requires
                synchronous exit codes (0 or 1) when integrating into CI/CD gating checks.
              </p>
              <div className="bg-slate-50 p-3 rounded-lg text-xs text-slate-700 space-y-1">
                <div><strong>Why AEP chose a hybrid architecture:</strong></div>
                <div className="text-slate-600">• Synchronous path executes in &lt;5ms for immediate CI/CD command-line decisions.</div>
                <div className="text-slate-600">• Asynchronous dispatch handles slow external webhooks (Teams, Slack) out-of-band.</div>
                <div className="text-slate-600">• Zero blocking overhead on the core API response.</div>
              </div>
            </div>

            {/* Decision 4 */}
            <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-2xs">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-slate-900">
                  Embedded In-Memory Limiter vs. External Redis
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                  Self-Contained
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed mb-3">
                <strong>Trade-off:</strong> Redis enables distributed token bucket synchronization across multiple API nodes,
                but requires external infrastructure, provisioning, and network roundtrips.
              </p>
              <div className="bg-slate-50 p-3 rounded-lg text-xs text-slate-700 space-y-1">
                <div><strong>Why AEP uses sliding-window in-memory:</strong></div>
                <div className="text-slate-600">• Zero external dependencies: platform runs self-contained out-of-the-box.</div>
                <div className="text-slate-600">• Rate limit checks run in-process, with no network round trip.</div>
                <div className="text-slate-600">• No Redis adapter is implemented; multiple replicas would need one.</div>
              </div>
            </div>

            {/* Decision 5 */}
            <div className="p-5 rounded-xl border border-slate-200 bg-white shadow-2xs md:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-slate-900">
                  SQLite (WAL Mode) vs. Hosted PostgreSQL
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                  Dialect-Neutral
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed mb-3">
                <strong>Trade-off:</strong> Managed PostgreSQL provides multi-writer clustering and connection pooling,
                while SQLite provides zero-ops portability and instant local evaluation without Docker overhead.
              </p>
              <div className="bg-slate-50 p-3 rounded-lg text-xs text-slate-700 space-y-1">
                <div><strong>Why AEP defaults to SQLite with SQLModel:</strong></div>
                <div className="text-slate-600">• Single-command local startup for developer evaluation pipelines and tests.</div>
                <div className="text-slate-600">• WAL (Write-Ahead Logging) mode provides concurrent reads without blocking writer transactions.</div>
                <div className="text-slate-600">• Built with SQLModel/SQLAlchemy, so the storage layer could target another SQL database; only SQLite is tested.</div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pt-6 border-t border-slate-200 text-xs text-slate-500">
          <div>Agent Evaluation Platform • System Architecture v1.0.0</div>
          <div className="flex space-x-4 mt-2 sm:mt-0">
            <Link href="/case-study" className="text-blue-600 hover:underline">
              Engineering Case Study →
            </Link>
            <Link href="/about" className="text-blue-600 hover:underline">
              Platform Metrics →
            </Link>
            <Link href="/traces" className="text-blue-600 hover:underline">
              Trace Explorer →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
