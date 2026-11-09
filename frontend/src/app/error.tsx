"use client";

import React, { useEffect } from "react";
import Link from "next/link";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled platform application error:", error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-[70vh] max-w-7xl flex-col items-center justify-center px-6 py-16 text-center">
      <div className="rounded-xl border border-rose-200 bg-white p-8 shadow-sm sm:p-12 max-w-lg w-full space-y-6">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-rose-50 text-rose-600 font-black text-xl border border-rose-200">
          !
        </div>

        <div className="space-y-2">
          <h1 className="text-2xl font-black text-slate-900 sm:text-3xl">
            Application Error
          </h1>
          <p className="text-xs text-slate-500 sm:text-sm">
            An unexpected error occurred while communicating with the evaluation platform services.
          </p>
          {error.message && (
            <div className="rounded-lg border border-rose-200 bg-rose-50/50 p-3 text-left font-mono text-[11px] text-rose-700">
              {error.message}
            </div>
          )}
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <button
            onClick={() => reset()}
            className="w-full sm:w-auto rounded-lg bg-rose-600 px-5 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-rose-700 transition"
          >
            Retry Request
          </button>
          <Link
            href="/"
            className="w-full sm:w-auto rounded-lg border border-slate-200 bg-white px-5 py-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
          >
            Return to Dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}

