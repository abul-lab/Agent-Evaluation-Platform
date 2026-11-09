"use client";

import React from "react";
import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[70vh] max-w-7xl flex-col items-center justify-center px-6 py-16 text-center">
      <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm sm:p-12 max-w-lg w-full space-y-6">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-slate-700 font-black text-xl border border-slate-200">
          404
        </div>
        
        <div className="space-y-2">
          <h1 className="text-2xl font-black text-slate-900 sm:text-3xl">
            Resource Not Found
          </h1>
          <p className="text-xs text-slate-500 sm:text-sm">
            The requested agent evaluation, trace record, or navigation route could not be located.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <Link
            href="/"
            className="w-full sm:w-auto rounded-lg bg-emerald-600 px-5 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-emerald-700 transition"
          >
            Dashboard Overview
          </Link>
          <Link
            href="/traces"
            className="w-full sm:w-auto rounded-lg border border-slate-200 bg-white px-5 py-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
          >
            Browse Traces
          </Link>
        </div>
      </div>
    </main>
  );
}

