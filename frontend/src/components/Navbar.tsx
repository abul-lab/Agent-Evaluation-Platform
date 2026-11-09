"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api, DemoSeedResponse } from "../lib/api";
import { ProductTour } from "./ProductTour";

export function Navbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isTourOpen, setIsTourOpen] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);
  const [seedSuccessMsg, setSeedSuccessMsg] = useState<string | null>(null);

  const navLinks = [
    { href: "/", label: "Overview" },
    { href: "/traces", label: "Traces" },
    { href: "/benchmarks", label: "Benchmarks" },
    { href: "/analytics", label: "Analytics" },
    { href: "/policies", label: "Policies" },
    { href: "/workspaces", label: "Workspaces" },
    { href: "/architecture", label: "Architecture" },
    { href: "/case-study", label: "Case Study" },
    { href: "/about", label: "Metrics" },
  ];

  const handleSeedDemo = async () => {
    try {
      setIsSeeding(true);
      setSeedSuccessMsg(null);
      const res: DemoSeedResponse = await api.seedDemoWorkspace();
      try {
        localStorage.setItem("aep_active_workspace_id", res.workspace_id);
      } catch {
        // ignore storage errors
      }
      setSeedSuccessMsg(`Demo workspace loaded! (${res.traces_seeded} traces, ${res.evaluations_seeded} evaluations)`);
      setTimeout(() => {
        setSeedSuccessMsg(null);
        window.location.reload();
      }, 1800);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to seed demo workspace";
      alert(msg);
    } finally {
      setIsSeeding(false);
    }
  };

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 py-3">
          <div className="flex items-center gap-5">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 font-bold text-sm shadow-xs">
                AE
              </div>
              <span className="font-bold text-slate-900 text-sm tracking-tight sm:text-base hidden sm:inline">
                Agent Evaluation Platform
              </span>
              <span className="font-bold text-slate-900 text-sm tracking-tight sm:hidden">
                AEP
              </span>
            </Link>

            <nav className="hidden lg:flex items-center gap-1 font-medium text-xs">
              {navLinks.map((link) => {
                const isActive =
                  link.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(link.href);

                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`rounded-md px-2.5 py-1.5 transition ${
                      isActive
                        ? "bg-slate-100 text-slate-900 font-semibold"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {/* Seed Demo Workspace Button */}
            <button
              type="button"
              onClick={handleSeedDemo}
              disabled={isSeeding}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100 text-xs font-semibold shadow-2xs transition disabled:opacity-50"
              title="Preload 6 golden traces, 5 OTEL traces, 2 governance policies, and notifications"
            >
              <span>✨</span>
              <span>{isSeeding ? "Seeding..." : "Load Demo Data"}</span>
            </button>

            {/* Product Tour Button */}
            <button
              type="button"
              onClick={() => setIsTourOpen(true)}
              className="hidden sm:inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 text-xs font-semibold shadow-2xs transition"
            >
              <span>Tour</span>
            </button>

            {/* Health pill */}
            <span className="hidden xl:flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] text-slate-600">
              <span className="h-2 w-2 rounded-full bg-emerald-600" />
              API Ready
            </span>

            {/* Mobile hamburger menu toggle */}
            <button
              type="button"
              aria-label="Toggle Navigation Menu"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-50 lg:hidden"
            >
              {mobileMenuOpen ? (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Demo Seed Success Banner */}
        {seedSuccessMsg && (
          <div className="bg-emerald-500 text-white text-xs font-semibold px-4 py-2 text-center animate-in slide-in-from-top duration-200">
            ✓ {seedSuccessMsg}
          </div>
        )}

        {/* Mobile navigation drawer */}
        {mobileMenuOpen && (
          <div className="border-t border-slate-200 bg-white px-6 py-3 shadow-sm lg:hidden">
            <nav className="flex flex-col gap-1">
              {navLinks.map((link) => {
                const isActive =
                  link.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(link.href);

                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`rounded-md px-3 py-2 text-xs font-medium transition ${
                      isActive
                        ? "bg-slate-100 text-slate-900 font-semibold"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
              <div className="pt-2 border-t border-slate-100 flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    setIsTourOpen(true);
                  }}
                  className="w-full py-2 text-center text-xs font-bold rounded-lg border border-slate-200 bg-slate-50 text-slate-700"
                >
                  Take Guided Tour
                </button>
              </div>
            </nav>
          </div>
        )}
      </header>

      {/* Guided Tour Modal */}
      <ProductTour isOpen={isTourOpen} onClose={() => setIsTourOpen(false)} />
    </>
  );
}
