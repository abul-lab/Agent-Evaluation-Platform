import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface UploadTraceCardProps {
  onUploaded?: (traceId: string) => void;
}

export function UploadTraceCard({ onUploaded }: UploadTraceCardProps) {
  const router = useRouter();
  const [jsonText, setJsonText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setJsonText(content);
    };
    reader.readAsText(file);
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jsonText.trim()) {
      setError("Please select a JSON trace file or paste JSON content.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      const parsed = JSON.parse(jsonText);
      const res = await api.uploadTrace(parsed);

      setSuccess(`Trace uploaded successfully (ID: ${res.trace_id})`);
      setJsonText("");
      if (onUploaded) {
        onUploaded(res.trace_id);
      } else {
        router.push(`/traces/${res.trace_id}`);
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to upload trace"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      data-testid="upload-trace-card"
      className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900">
            Upload Agent Trace
          </h3>
          <p className="mt-0.5 text-xs text-slate-500">
            Upload a trace conforming to Canonical Agent Trace Schema (CATS).
          </p>
        </div>
      </div>

      <form onSubmit={handleUploadSubmit} className="mt-4 space-y-4">
        <div>
          <label
            htmlFor="trace-file-input"
            className="block text-xs font-semibold text-slate-700 mb-1.5"
          >
            Select JSON File
          </label>
          <input
            id="trace-file-input"
            type="file"
            accept=".json,application/json"
            onChange={handleFileUpload}
            className="block w-full text-xs text-slate-600 file:mr-4 file:rounded-md file:border file:border-slate-200 file:bg-slate-50 file:px-3 file:py-1.5 file:text-xs file:font-semibold file:text-slate-700 hover:file:bg-slate-100"
          />
        </div>

        <div>
          <label
            htmlFor="trace-json-textarea"
            className="block text-xs font-semibold text-slate-700 mb-1.5"
          >
            Or Paste Trace JSON
          </label>
          <textarea
            id="trace-json-textarea"
            rows={5}
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            placeholder='{"schema_version": "1.0.0", "session": {...}, "workflow": {...}, "steps": [...]}'
            className="w-full rounded-lg border border-slate-200 bg-slate-50/50 p-3 font-mono text-xs text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
            {error}
          </div>
        )}

        {success && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800">
            {success}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !jsonText.trim()}
          className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-emerald-700 disabled:opacity-50"
        >
          {loading ? "Validating & Uploading..." : "Upload Trace"}
        </button>
      </form>
    </div>
  );
}

