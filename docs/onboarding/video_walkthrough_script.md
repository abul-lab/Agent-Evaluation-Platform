# Video Walkthrough Script & Storyboard (3 Minutes)

**Title**: "Auditing Autonomous AI Agents with the Agent Evaluation Platform"  
**Duration**: 3 Minutes (180 Seconds)  
**Target Audience**: Platform Architects, AI Engineers, and Security Officers  
**Visual Style**: Clean light theme, code overlays, high-contrast UI screencasts.

---

## Storyboard Timeline

### Scene 1: The Problem (0:00 - 0:35)
- **Visual**: Visual diagram of an autonomous agent entering an infinite cyclic loop between two tool nodes, draining tokens and exceeding latency budgets.
- **Voiceover**:
  > "Autonomous agents perform multi-step workflows, but in production, failures can occur silently. Infinite execution loops, hallucinated tool schemas, cascading retries, and leaked API credentials impact engineering reliability. Evaluating agents shouldn't rely on expensive, non-deterministic LLM-as-a-judge calls. Meet the Agent Evaluation Platform—a deterministic, framework-agnostic system of record and quality auditor for agent workflows."

### Scene 2: Trace Ingestion & Instant Evaluation (0:35 - 1:15)
- **Visual**: While running the application locally, browser opens `http://localhost:3000`. Quick paste of `clean_success_trace.json`. One click on **Ingest & Evaluate Trace**. Instant transition to `/evaluations/{id}`.
- **Voiceover**:
  > "AEP normalizes traces from LangGraph, CrewAI, AutoGen, and custom runtimes into the Canonical Agent Trace Schema. In less than three milliseconds, our deterministic evaluator suite audits cycles, tool redundancies, retry storms, and secret leaks. The result? A comprehensive 7-domain scorecard, weighted risk tier, and granular defect findings—all calculated with zero LLM API costs."

### Scene 3: Topological Graph & Step Inspection (1:15 - 1:55)
- **Visual**: Click on **View Execution Graph**. React Flow canvas smoothly renders the agent's DAG execution topology. Node drawer slides open displaying tool parameters, latency, and token expenditure.
- **Voiceover**:
  > "Need to understand where an agent deviated? Our interactive DAG visualization maps every step transition. Redundant loops and tool hallucination points are highlighted directly in the graph. Click any step node to inspect raw inputs, structured tool responses, and diagnostic metadata."

### Scene 4: Release Gating & Benchmarking (1:55 - 2:35)
- **Visual**: Transition to `/benchmarks` showing side-by-side comparison of baseline vs candidate. Switch to `/policies` and execute an audit in the Evaluation Governance Audit Console resulting in an `APPROVED — Release Cleared` verdict badge.
- **Voiceover**:
  > "With AEP, deploying agents with confidence is automated. Benchmark candidate agent runs against production baselines to calculate exact mathematical score deltas. Enforce organizational score floors and disallow critical defects before code merges. When an evaluation clears your governance policy, your CI/CD pipeline gets an unambiguous release verdict."

### Scene 5: Outro & Call to Action (2:35 - 3:00)
- **Visual**: Quick sequence displaying Docker command `docker compose up -d`, GitHub repository URL, and light theme dashboard.
- **Voiceover**:
  > "AEP is open-source, strictly typed, and verified with extensive automated test coverage. Deploy today with Docker Compose or integrate via our REST API. Visit github.com/abul-lab/Agent-Evaluation-Platform and take control of your autonomous agent reliability."

