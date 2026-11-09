"""OpenTelemetry Ingestion Example: AutoGen Conversational Agent Trace.

Demonstrates how to send OpenTelemetry spans emitted by Microsoft AutoGen
conversations directly to the Agent Evaluation Platform for CATS translation.
"""

import os

import json
from pathlib import Path
import httpx

AEP_API_KEY = os.getenv("AEP_API_KEY")
# Required when the backend runs with ENVIRONMENT=production (or anonymous access is disabled).
AUTH_HEADERS = {"Authorization": f"Bearer {AEP_API_KEY}"} if AEP_API_KEY else {}

AEP_BASE_URL = "http://localhost:8000"
FIXTURE_PATH = Path(__file__).resolve().parent.parent.parent / "fixtures" / "otel" / "autogen_trace.json"


def ingest_autogen_trace() -> None:
    """Send AutoGen OTEL trace to the AEP ingestion endpoint."""
    print(f"[+] Loading AutoGen OTEL trace fixture: {FIXTURE_PATH}")
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        payload = json.load(f)

    print(f"[+] Posting to {AEP_BASE_URL}/api/v1/otel/ingest...")
    try:
        response = httpx.post(f"{AEP_BASE_URL}/api/v1/otel/ingest", headers=AUTH_HEADERS, json=payload, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        print("\n[SUCCESS] AutoGen Trace Translated and Ingested:")
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
    ingest_autogen_trace()

