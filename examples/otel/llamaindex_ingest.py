"""OpenTelemetry Ingestion Example: LlamaIndex Agent Workflow Trace.

Demonstrates how to send OpenTelemetry spans emitted by LlamaIndex query engines
and agent workflows directly to the Agent Evaluation Platform.
"""

import os

import json
from pathlib import Path
import httpx

AEP_API_KEY = os.getenv("AEP_API_KEY")
# Required when the backend runs with ENVIRONMENT=production (or anonymous access is disabled).
AUTH_HEADERS = {"Authorization": f"Bearer {AEP_API_KEY}"} if AEP_API_KEY else {}

AEP_BASE_URL = "http://localhost:8000"
FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / "fixtures" / "otel" / "llamaindex_trace.json"


def ingest_llamaindex_trace() -> None:
    """Send LlamaIndex OTEL trace to the AEP ingestion endpoint."""
    print(f"[+] Loading LlamaIndex OTEL trace fixture: {FIXTURE_PATH}")
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        payload = json.load(f)

    print(f"[+] Posting to {AEP_BASE_URL}/api/v1/otel/ingest...")
    try:
        response = httpx.post(f"{AEP_BASE_URL}/api/v1/otel/ingest", headers=AUTH_HEADERS, json=payload, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        print("\n[SUCCESS] LlamaIndex Trace Translated and Ingested:")
        print(f"  - CATS Trace ID:        {data['trace_id']}")
        print(f"  - Session ID:           {data['session_id']}")
        print(f"  - Workflow ID:          {data['workflow_id']}")
        print(f"  - Detected Framework:   {data['detected_framework']}")
        print(f"  - Step Count:           {data['step_count']}")
        print(f"  - Workflow Status:      {data['workflow_status']}")
        print(f"\nView details in browser: http://localhost:3000/traces/{data['trace_id']}")
    except httpx.ConnectError:
        print("[!] Backend API not reachable at localhost:8000. Start backend with:")
        print("    py -m uvicorn app.main:app --port 8000")


if __name__ == "__main__":
    ingest_llamaindex_trace()

