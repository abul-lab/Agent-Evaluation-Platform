"use client";

import React from "react";
import Link from "next/link";

export default function CaseStudyPage() {
  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-12">
        {/* Header Breadcrumb */}
        <div className="border-b border-slate-200 pb-8">
          <div className="flex items-center space-x-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            <span>Engineering Case Study</span>
            <span>/</span>
            <span className="text-blue-600">Platform Reliability &amp; Governance</span>
          </div>
          <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight">
            Building an OpenTelemetry Evaluation &amp; Governance Platform for Autonomous AI Agents
          </h1>
          <p className="mt-3 text-lg text-slate-600 leading-relaxed">
            How we designed an OpenTelemetry-native, deterministic evaluation engine capable of auditing agent
            executions, enforcing zero-tolerance safety policies, and halting broken agent releases in CI/CD.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-4 text-xs text-slate-500">
            <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 font-medium">Author: AEP Engineering Lead</span>
            <span>•</span>
            <span>Platform Version: v1.0.0 (Stable)</span>
            <span>•</span>
            <span>Read Time: 8 min</span>
            <span>•</span>
            <span className="text-emerald-600 font-semibold">Benchmark Verified</span>
          </div>
        </div>

        {/* Executive Summary Callout */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8">
          <div className="flex items-center space-x-3 mb-4">
            <span className="px-2.5 py-1 rounded bg-blue-50 text-blue-700 border border-blue-200 text-xs font-bold uppercase tracking-wider">
              Executive Summary
            </span>
          </div>
          <p className="text-slate-700 text-base leading-relaxed mb-4">
            As enterprises deploy autonomous agents for code generation, customer operations, and data pipelines,
            traditional software reliability practices break down. Autonomous agents are non-deterministic state machines:
            they can enter infinite recursive loops, hallucinate tool calls, expose sensitive credentials, or generate
            runaway cloud spend.
          </p>
          <p className="text-slate-700 text-base leading-relaxed">
            The <strong>Agent Evaluation Platform (AEP)</strong> was engineered to solve this challenge. Rather than relying
            on slow, variable, and expensive LLM-as-a-judge patterns, AEP introduces a <strong>100% deterministic, multi-domain
            evaluation engine</strong> that evaluates OpenTelemetry agent traces <strong>without any LLM calls</strong>, enforces strict
            governance scorecards, and provides machine-readable exit codes to automatically gate pull requests and production deployments.
          </p>
        </div>

        {/* Section 1: The Engineering Challenge */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-4">
          <div className="flex items-center space-x-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
            <span>Section 01</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900">
            Why Agent Reliability is Harder than Microservices
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            In traditional microservice architectures, testing revolves around deterministic input-output contracts,
            HTTP status codes, and database constraints. Agentic systems introduce four fundamentally new classes of failure:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-1 text-red-600">
                1. Non-Deterministic Loop Traps
              </h3>
              <p className="text-xs text-slate-600">
                An agent receiving an unexpected tool error may re-try the identical call or oscillate between two tools
                indefinitely. Because each individual LLM call returns 200 OK, standard APM tools report normal operation while
                thousands of dollars in tokens are consumed.
              </p>
            </div>
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-1 text-amber-600">
                2. Tool Call Hallucination
              </h3>
              <p className="text-xs text-slate-600">
                Agents frequently invent function names that do not exist or produce JSON arguments that violate the target
                API schema. Without trajectory-level auditing, these failures manifest as silent drop-offs or corrupted downstream state.
              </p>
            </div>
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-1 text-purple-600">
                3. Credentials Exfiltration &amp; Prompt Leaks
              </h3>
              <p className="text-xs text-slate-600">
                When agents interact with file systems or external databases, sensitive connection strings, JWTs, or API keys
                can accidentally become part of the reasoning prompt and be reflected in user-facing responses or third-party logs.
              </p>
            </div>
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-1 text-blue-600">
                4. Lack of CI/CD Automated Gating
              </h3>
              <p className="text-xs text-slate-600">
                Engineers frequently adjust agent system prompts or update foundation models without knowing whether the change
                degraded tool adherence or introduced safety regressions. Manual QA testing cannot cover millions of potential reasoning paths.
              </p>
            </div>
          </div>
        </div>

        {/* Section 2: Core Architectural Decisions */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
          <div className="flex items-center space-x-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
            <span>Section 02</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900">
            Key Architectural Decisions &amp; Innovations
          </h2>

          {/* Decision 1 */}
          <div className="border-l-4 border-blue-500 pl-4 space-y-2">
            <h3 className="text-base font-bold text-slate-900">
              Decision 1: Deterministic Algorithmic Evaluators over LLM-as-a-Judge
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Many teams evaluate agents using a secondary LLM (e.g. GPT-4 as a judge). While flexible for unstructured text,
              LLM-as-a-judge is unsuitable for automated CI/CD gating:
            </p>
            <div className="bg-slate-50 p-3 rounded-lg text-xs text-slate-700 space-y-1 font-mono">
              <div>• Latency: LLM judges take 1,500ms - 5,000ms. AEP evaluators execute in approximately 2–5ms.</div>
              <div>• Cost: LLM judges cost ~$0.08 per trace. AEP evaluates at $0.00 compute cost.</div>
              <div>• Determinism: LLM judges have temperature noise. AEP produces reproducible, deterministic verdicts without grading drift.</div>
            </div>
          </div>

          {/* Decision 2 */}
          <div className="border-l-4 border-emerald-500 pl-4 space-y-2">
            <h3 className="text-base font-bold text-slate-900">
              Decision 2: OpenTelemetry as the Universal Ingestion Standard
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Rather than forcing developers to rewrite their agent code using a proprietary SDK, AEP adopted OpenTelemetry (OTEL)
              and OpenInference semantic conventions. We built a native OTLP/HTTP &amp; gRPC collector receiver that accepts standard
              traces emitted by LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, and LlamaIndex.
            </p>
            <p className="text-xs text-slate-600 leading-relaxed">
              The internal <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-800">OtelCatsTranslator</code> dynamically reconstructs the hierarchical
              span tree, classifies step kinds, normalizes token usage, and produces a Canonical Agent Trace Schema (CATS) v1.0.0 artifact.
            </p>
          </div>

          {/* Decision 3 */}
          <div className="border-l-4 border-purple-500 pl-4 space-y-2">
            <h3 className="text-base font-bold text-slate-900">
              Decision 3: Zero-Tolerance Hard Gating &amp; Policy Snapshots
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              A high average score can hide critical safety failures. An agent that scores 98% across 10 tasks is still a catastrophic
              liability if it leaks an API key in 1 task. AEP enforces <strong>Hard Gates</strong>: if a critical safety marker
              (secret leak, prompt injection, infinite loop) is detected, the governance verdict is immediately set to <strong>BLOCKED</strong>,
              the build exit code is set to 1, and an incident alert is routed to on-call engineers.
            </p>
          </div>
        </div>

        {/* Section 3: The 7 Evaluator Domains */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
          <div className="flex items-center space-x-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
            <span>Section 03</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900">
            The 7 Parallel Deterministic Evaluator Domains
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            Every trace submitted to AEP passes through seven specialized evaluators running concurrently in memory:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-lg border border-slate-200 bg-white">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200">Domain 1</span>
              <h4 className="text-xs font-bold text-slate-900 mt-2">Loop Detection</h4>
              <p className="text-xs text-slate-600 mt-1">
                Computes cryptographic state hashes across step inputs, tool calls, and outputs. Detects exact repetition cycles,
                alternating ping-pong oscillations, and consecutive repeated tool calls.
              </p>
            </div>

            <div className="p-4 rounded-lg border border-slate-200 bg-white">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">Domain 2</span>
              <h4 className="text-xs font-bold text-slate-900 mt-2">Tool Fidelity</h4>
              <p className="text-xs text-slate-600 mt-1">
                Validates invoked tool names against registered tool catalogs. Checks argument schemas against JSON Schema definitions
                and flags runtime execution exceptions and type mismatches.
              </p>
            </div>

            <div className="p-4 rounded-lg border border-slate-200 bg-white">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">Domain 3</span>
              <h4 className="text-xs font-bold text-slate-900 mt-2">Safety &amp; Policy</h4>
              <p className="text-xs text-slate-600 mt-1">
                Scans trace payloads with high-performance regular expressions for exposed secrets (OpenAI keys, AWS credentials, JWTs,
                private keys) and known prompt injection / jailbreak markers.
              </p>
            </div>

            <div className="p-4 rounded-lg border border-slate-200 bg-white">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">Domain 4</span>
              <h4 className="text-xs font-bold text-slate-900 mt-2">Context &amp; Budget</h4>
              <p className="text-xs text-slate-600 mt-1">
                Monitors cumulative token consumption against context window saturation thresholds. Detects token bloat acceleration
                and enforces maximum allowable reasoning step ceilings.
              </p>
            </div>

            <div className="p-4 rounded-lg border border-slate-200 bg-white">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">Domain 5</span>
              <h4 className="text-xs font-bold text-slate-900 mt-2">Latency &amp; Cascades</h4>
              <p className="text-xs text-slate-600 mt-1">
                Tracks per-step latency deltas, detects exponential backoff retry storms, and identifies bottlenecks in tool response times
                or subagent handoffs.
              </p>
            </div>

            <div className="p-4 rounded-lg border border-slate-200 bg-white">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">Domain 6</span>
              <h4 className="text-xs font-bold text-slate-900 mt-2">Goal Completion</h4>
              <p className="text-xs text-slate-600 mt-1">
                Verifies terminal state transitions, expected output format conformity, and checks whether the agent terminated
                prematurely leaving unfinished subtasks.
              </p>
            </div>

            <div className="p-4 rounded-lg border border-slate-200 bg-white md:col-span-2">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">Domain 7</span>
              <h4 className="text-xs font-bold text-slate-900 mt-2">Cost Accounting</h4>
              <p className="text-xs text-slate-600 mt-1">
                Calculates precise financial dollar cost per execution based on multi-model token pricing tiers (GPT-4o, Claude 3.5 Sonnet,
                Gemini 1.5 Pro). Enforces hard dollar budget ceilings per session.
              </p>
            </div>
          </div>
        </div>

        {/* Section 4: Performance Benchmarks & Results */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-6">
          <div className="flex items-center space-x-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
            <span>Section 04</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900">
            Quality Gates and Measurement
          </h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            The figures below come from the repository&apos;s own checks, which CI runs on every push. Latency and throughput depend on
            hardware, so they are not published as fixed numbers; measure them with <code>backend/scripts/benchmark_performance.py</code>.
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 text-center">
              <div className="text-2xl font-extrabold text-purple-600">368</div>
              <div className="text-xs font-bold text-slate-900 mt-1">Backend Tests</div>
              <div className="text-[11px] text-slate-500 mt-0.5">All passing</div>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 text-center">
              <div className="text-2xl font-extrabold text-emerald-600">92%</div>
              <div className="text-xs font-bold text-slate-900 mt-1">Backend Coverage</div>
              <div className="text-[11px] text-slate-500 mt-0.5">CI gate: 85%</div>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 text-center">
              <div className="text-2xl font-extrabold text-blue-600">50</div>
              <div className="text-xs font-bold text-slate-900 mt-1">Frontend Tests</div>
              <div className="text-[11px] text-slate-500 mt-0.5">Vitest, all passing</div>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 text-center">
              <div className="text-2xl font-extrabold text-slate-900">0</div>
              <div className="text-xs font-bold text-slate-900 mt-1">Type Errors</div>
              <div className="text-[11px] text-slate-500 mt-0.5">mypy strict and tsc</div>
            </div>
          </div>
        </div>

        {/* Section 5: Lessons Learned & What Broke */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-4">
          <div className="flex items-center space-x-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
            <span>Section 05</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900">
            Lessons Learned: What Broke and How We Fixed It
          </h2>

          <div className="space-y-4 text-xs text-slate-700">
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <h4 className="font-bold text-slate-900 mb-1">1. Chronological Deserialization in OTEL Spans</h4>
              <p className="text-slate-600 leading-relaxed">
                <em>Initial issue:</em> Standard OTLP collectors stream spans asynchronously without ordered arrival. Early translator iterations
                sorted steps by span insertion order, causing child tool calls to be orphaned when their parent agent step arrived in a subsequent batch.
                <br />
                <em>Fix:</em> Implemented a two-phase span graph assembler that builds an in-memory adjacency list keyed by <code className="bg-white px-1 py-0.5 rounded border border-slate-200">span_id</code>,
                then walks the tree in top-down topological order using microsecond start timestamps.
              </p>
            </div>

            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <h4 className="font-bold text-slate-900 mb-1">2. Redacting Credentials Before Webhook Payload Generation</h4>
              <p className="text-slate-600 leading-relaxed">
                <em>Initial issue:</em> When a secret leak was flagged by the Safety evaluator, the raw secret string was initially
                included in the violation explanation, which would be transmitted to external webhook listeners.
                <br />
                <em>Fix:</em> The secret finding now stores only a redacted sample of the matched value and is classified CRITICAL,
                so it blocks the release.
              </p>
            </div>
          </div>
        </div>

        {/* Section 6: Future Roadmap */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 sm:p-8 space-y-4">
          <div className="flex items-center space-x-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
            <span>Section 06</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900">
            Future Engineering Roadmap (v1.2+)
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <h4 className="text-xs font-bold text-slate-900">Planned: Redis Limiter</h4>
              <p className="text-xs text-slate-600 mt-1">
                Not implemented. Multiple replicas would need a shared store so rate limits apply across processes.
              </p>
            </div>
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <h4 className="text-xs font-bold text-slate-900">Native Prometheus Exporter</h4>
              <p className="text-xs text-slate-600 mt-1">
                Standard <code className="bg-white px-1 rounded text-slate-800">/metrics</code> endpoint exposing domain score histograms, latency p99s, and hard-gate counters.
              </p>
            </div>
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
              <h4 className="text-xs font-bold text-slate-900">Apache Kafka Ingestion</h4>
              <p className="text-xs text-slate-600 mt-1">
                High-volume streaming buffer for organizations processing over 100,000 agent interactions per hour.
              </p>
            </div>
          </div>
        </div>

        {/* Footer Navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pt-6 border-t border-slate-200 text-xs text-slate-500">
          <div>Agent Evaluation Platform • Case Study v1.0.0</div>
          <div className="flex space-x-4 mt-2 sm:mt-0">
            <Link href="/architecture" className="text-blue-600 hover:underline">
              System Architecture →
            </Link>
            <Link href="/about" className="text-blue-600 hover:underline">
              Technical Metrics →
            </Link>
            <Link href="/traces" className="text-blue-600 hover:underline">
              Explore Live Traces →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

