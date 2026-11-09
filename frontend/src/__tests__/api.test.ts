import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api, ApiError } from "@/lib/api";

describe("API Client", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("fetches trace list successfully", async () => {
    const mockTraces = [
      {
        trace_id: "t-1",
        workflow_status: "SUCCESS",
        step_count: 3,
        created_at: "2026-11-08T12:00:00Z",
        framework: "LANGGRAPH",
      },
    ];

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockTraces,
    } as Response);

    const result = await api.getTraces();
    expect(result).toEqual(mockTraces);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/traces?limit=100&offset=0"),
      expect.any(Object)
    );
  });

  it("fetches single trace metadata", async () => {
    const mockTrace = {
      trace_id: "t-1",
      created_at: "2026-11-08T12:00:00Z",
      workflow_status: "SUCCESS",
      step_count: 3,
      framework: "LANGGRAPH",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockTrace,
    } as Response);

    const result = await api.getTrace("t-1");
    expect(result).toEqual(mockTrace);
  });

  it("triggers evaluation run via POST", async () => {
    const mockResponse = {
      evaluation_id: "e-1",
      status: "COMPLETED",
      finding_count: 0,
      overall_score: 100.0,
      risk_classification: "EXCELLENT",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const result = await api.runEvaluation("t-1");
    expect(result).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/evaluations/run"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ trace_id: "t-1" }),
      })
    );
  });

  it("throws ApiError on HTTP 404 response", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Trace not found" }),
    } as Response);

    await expect(api.getTrace("missing-id")).rejects.toThrow(ApiError);
    await expect(api.getTrace("missing-id")).rejects.toMatchObject({
      status: 404,
      detail: "Trace not found",
    });
  });

  it("throws ApiError on HTTP 422 response with array detail", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [{ loc: ["body", "trace_id"], msg: "Field required" }],
      }),
    } as Response);

    await expect(api.runEvaluation("invalid")).rejects.toThrow(ApiError);
  });

  it("handles network failure and wraps in ApiError", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("Failed to fetch"));

    await expect(api.getTraces()).rejects.toThrow(ApiError);
    await expect(api.getTraces()).rejects.toMatchObject({
      status: 0,
      detail: "Failed to fetch",
    });
  });
});

