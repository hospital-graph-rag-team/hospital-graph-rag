"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bot,
  ChevronRight,
  Database,
  FlaskConical,
  LayoutDashboard,
  Lock,
  Menu,
  Moon,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Sparkles,
  Sun,
  UserRound,
  Users,
  X,
} from "lucide-react";
import { useClinical } from "@/components/providers/clinical-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard, key: "overview" },
  { href: "/patients", label: "Patient Explorer", icon: Users, key: "patients" },
  { href: "/graph", label: "Knowledge Graph", icon: Network, key: "graph" },
  { href: "/assistant", label: "AI Assistant", icon: Bot, key: "assistant" },
  {
    href: "/analytics",
    label: "Medication Analytics",
    icon: FlaskConical,
    key: "analytics",
  },
];

function ClinicalGraphLogo({ collapsed }: { collapsed: boolean }) {
  return (
    <Link
      href="/"
      className="flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--cg-accent-teal)] rounded-lg"
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[#2DD4BF]/30 bg-[#2DD4BF]/10 text-[var(--cg-accent-teal)]">
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="6" cy="12" r="2.2" stroke="currentColor" strokeWidth="1.8" />
          <circle cx="17.5" cy="6.5" r="2.2" stroke="#38BDF8" strokeWidth="1.8" />
          <circle cx="17.5" cy="17.5" r="2.2" stroke="#818CF8" strokeWidth="1.8" />
          <path
            d="M8 11L15.5 7.3M8 13L15.5 16.7M17.5 8.8V15.2"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            opacity="0.8"
          />
        </svg>
      </div>
      {!collapsed && (
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold tracking-tight text-[var(--cg-text-primary)]">
              ClinicalGraph
            </span>
            <span className="rounded bg-[#2DD4BF]/15 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-[var(--cg-accent-teal)]">
              2.0
            </span>
          </div>
          <p className="truncate text-[11px] text-[var(--cg-text-secondary)]">
            Hospital Graph RAG
          </p>
        </div>
      )}
    </Link>
  );
}

function DemoAccessModal() {
  const { demoGateRequired, demoUnlocked, unlockDemo } = useClinical();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!demoGateRequired || demoUnlocked) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await unlockDemo(code);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid access code.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-xs">
      <div className="w-full max-w-md rounded-xl border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] p-6 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#2DD4BF]/10 text-[var(--cg-accent-teal)]">
            <Lock className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-[var(--cg-text-primary)]">
              ClinicalGraph 2.0 Demo Access
            </h2>
            <p className="text-xs text-[var(--cg-text-secondary)]">
              Enter the demonstration passcode to access synthetic clinical data & AI queries.
            </p>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="mt-5 space-y-3">
          <Input
            type="password"
            placeholder="Enter access code..."
            value={code}
            onChange={(e) => setCode(e.target.value)}
            autoFocus
          />
          {error && (
            <p className="text-xs text-[var(--cg-error)]">{error}</p>
          )}
          <Button type="submit" className="w-full" disabled={submitting || !code.trim()}>
            {submitting ? "Verifying..." : "Unlock Platform"}
          </Button>
        </form>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const {
    theme,
    toggleTheme,
    sidebarCollapsed,
    setSidebarCollapsed,
    selectedPatient,
    selectedPatientId,
    clearSelectedPatient,
    patients,
    health,
    openPatient,
    askAssistant,
    demoGateRequired,
    demoUnlocked,
  } = useClinical();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchFocused(false);
      }
    }
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  const searchResults = useMemo(() => {
    const q = searchTerm.trim().toLowerCase();
    if (!q) return patients.slice(0, 6);
    return patients
      .filter(
        (p) =>
          p.patient_id.toLowerCase().includes(q) ||
          p.name.toLowerCase().includes(q) ||
          p.conditions.some((c) => c.toLowerCase().includes(q))
      )
      .slice(0, 8);
  }, [patients, searchTerm]);

  const activeNav =
    NAV_ITEMS.find((item) =>
      item.href === "/" ? pathname === "/" : pathname.startsWith(item.href)
    ) || NAV_ITEMS[0];

  const neo4jConnected = health?.neo4j_connected ?? false;
  const groqConfigured = health?.groq_configured ?? false;

  const sidebarContent = (isMobile: boolean) => (
    <div className="flex h-full flex-col justify-between bg-[var(--cg-bg-sidebar)]">
      <div>
        <div
          className={cn(
            "flex h-16 items-center border-b border-[var(--cg-border)] px-4",
            sidebarCollapsed && !isMobile ? "justify-center" : "justify-between"
          )}
        >
          <ClinicalGraphLogo collapsed={sidebarCollapsed && !isMobile} />
          {!isMobile && !sidebarCollapsed && (
            <button
              type="button"
              onClick={() => setSidebarCollapsed(true)}
              aria-label="Collapse sidebar"
              className="rounded-md p-1.5 text-[var(--cg-text-secondary)] hover:bg-[var(--cg-bg-elevated)] hover:text-[var(--cg-text-primary)] cursor-pointer"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
          {isMobile && (
            <button
              type="button"
              onClick={() => setMobileMenuOpen(false)}
              aria-label="Close navigation menu"
              className="rounded-md p-1.5 text-[var(--cg-text-secondary)] hover:bg-[var(--cg-bg-elevated)] cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {!isMobile && sidebarCollapsed && (
          <div className="flex justify-center border-b border-[var(--cg-border)] py-2">
            <button
              type="button"
              onClick={() => setSidebarCollapsed(false)}
              aria-label="Expand sidebar"
              className="rounded-md p-1.5 text-[var(--cg-text-secondary)] hover:bg-[var(--cg-bg-elevated)] hover:text-[var(--cg-text-primary)] cursor-pointer"
            >
              <PanelLeftOpen className="h-4 w-4" />
            </button>
          </div>
        )}

        <nav aria-label="Primary navigation" className="space-y-1 p-3">
          {!sidebarCollapsed || isMobile ? (
            <div className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
              Clinical Platform
            </div>
          ) : null}
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                title={sidebarCollapsed && !isMobile ? item.label : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "border border-[#2DD4BF]/25 bg-[#2DD4BF]/10 text-[var(--cg-accent-teal)]"
                    : "border border-transparent text-[var(--cg-text-secondary)] hover:bg-[var(--cg-bg-elevated)] hover:text-[var(--cg-text-primary)]",
                  sidebarCollapsed && !isMobile && "justify-center px-2"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {(!sidebarCollapsed || isMobile) && (
                  <span className="truncate">{item.label}</span>
                )}
              </Link>
            );
          })}
        </nav>

        {(!sidebarCollapsed || isMobile) && selectedPatient && (
          <div className="mx-3 mt-2 rounded-xl border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--cg-accent-teal)]">
                Active Context
              </span>
              <button
                type="button"
                onClick={clearSelectedPatient}
                aria-label="Clear active patient context"
                className="text-[11px] text-[var(--cg-text-muted)] hover:text-[var(--cg-text-primary)] cursor-pointer"
              >
                Clear
              </button>
            </div>
            <div className="mt-1.5 flex items-center gap-2">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-[var(--cg-bg-elevated)] text-[var(--cg-accent-sky)]">
                <UserRound className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-[var(--cg-text-primary)]">
                  {selectedPatient.name}
                </p>
                <p className="font-mono text-[11px] text-[var(--cg-text-secondary)]">
                  {selectedPatient.patient_id} • {selectedPatient.visit_count} visits
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="space-y-3 border-t border-[var(--cg-border)] p-3">
        {!sidebarCollapsed || isMobile ? (
          <>
            <div className="rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] p-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-[var(--cg-text-secondary)]">
                  <Database className="h-3.5 w-3.5" />
                  Neo4j AuraDB
                </span>
                <span className="flex items-center gap-1.5 font-medium">
                  <span
                    className={cn(
                      "h-2 w-2 rounded-full",
                      neo4jConnected ? "bg-[var(--cg-success)]" : "bg-[var(--cg-warning)]"
                    )}
                  />
                  <span className="text-[11px] text-[var(--cg-text-primary)]">
                    {health ? (neo4jConnected ? "Connected" : "Degraded") : "Checking"}
                  </span>
                </span>
              </div>
              <div className="mt-1.5 flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-[var(--cg-text-secondary)]">
                  <Activity className="h-3.5 w-3.5" />
                  Groq ReAct
                </span>
                <span className="font-mono text-[10px] text-[var(--cg-accent-sky)]">
                  {groqConfigured ? "gpt-oss-120b" : "Offline"}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={toggleTheme}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] px-3 py-2 text-xs font-medium text-[var(--cg-text-secondary)] hover:border-[var(--cg-border-strong)] hover:text-[var(--cg-text-primary)] cursor-pointer"
              >
                {theme === "dark" ? (
                  <>
                    <Sun className="h-3.5 w-3.5 text-[var(--cg-warning)]" />
                    Light Mode
                  </>
                ) : (
                  <>
                    <Moon className="h-3.5 w-3.5 text-[var(--cg-accent-violet)]" />
                    Dark Mode
                  </>
                )}
              </button>
            </div>

            <p className="px-1 text-[10px] leading-relaxed text-[var(--cg-text-muted)]">
              Academic demonstration using synthetic clinical data. Not for diagnostic or medical decisions.
            </p>
          </>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <span
              title={neo4jConnected ? "Neo4j AuraDB Connected" : "Neo4j Status"}
              className={cn(
                "h-2.5 w-2.5 rounded-full",
                neo4jConnected ? "bg-[var(--cg-success)]" : "bg-[var(--cg-warning)]"
              )}
            />
            <button
              type="button"
              onClick={toggleTheme}
              aria-label="Toggle color theme"
              className="rounded-lg border border-[var(--cg-border)] p-2 text-[var(--cg-text-secondary)] hover:text-[var(--cg-text-primary)] cursor-pointer"
            >
              {theme === "dark" ? (
                <Sun className="h-4 w-4 text-[var(--cg-warning)]" />
              ) : (
                <Moon className="h-4 w-4 text-[var(--cg-accent-violet)]" />
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-[var(--cg-bg-main)] text-[var(--cg-text-primary)]">
      <DemoAccessModal />

      {/* Desktop persistent collapsible sidebar */}
      <aside
        className={cn(
          "hidden lg:block shrink-0 border-r border-[var(--cg-border)] transition-all duration-200 sticky top-0 h-screen",
          sidebarCollapsed ? "w-[72px]" : "w-[252px]"
        )}
      >
        {sidebarContent(false)}
      </aside>

      {/* Mobile slide-over drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div
            className="fixed inset-0 bg-black/60"
            onClick={() => setMobileMenuOpen(false)}
          />
          <aside className="relative z-10 h-full w-72 border-r border-[var(--cg-border)] bg-[var(--cg-bg-sidebar)]">
            {sidebarContent(true)}
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top Navigation Bar */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-[var(--cg-border)] bg-[var(--cg-bg-main)]/90 px-4 sm:px-6 backdrop-blur-md">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open navigation menu"
              className="rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] p-2 text-[var(--cg-text-secondary)] hover:text-[var(--cg-text-primary)] lg:hidden cursor-pointer"
            >
              <Menu className="h-4 w-4" />
            </button>

            <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs min-w-0">
              <Link
                href="/"
                className="hidden sm:inline text-[var(--cg-text-secondary)] hover:text-[var(--cg-text-primary)]"
              >
                ClinicalGraph
              </Link>
              <ChevronRight className="hidden sm:inline h-3.5 w-3.5 text-[var(--cg-text-muted)]" />
              <span className="truncate font-semibold text-[var(--cg-text-primary)]">
                {activeNav.label}
              </span>
              {selectedPatientId && (
                <>
                  <ChevronRight className="h-3.5 w-3.5 text-[var(--cg-text-muted)]" />
                  <Badge variant="teal" className="font-mono">
                    {selectedPatientId}
                  </Badge>
                </>
              )}
            </nav>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Global Patient Search */}
            <div ref={searchRef} className="relative w-48 sm:w-68 md:w-80">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--cg-text-muted)]" />
              <Input
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setSearchFocused(true);
                }}
                onFocus={() => setSearchFocused(true)}
                placeholder="Search patient ID, name, condition..."
                aria-label="Global patient search"
                className="pl-8 pr-3 text-xs"
              />
              {searchFocused && searchResults.length > 0 && (
                <div className="absolute right-0 top-11 z-40 w-full min-w-[280px] rounded-xl border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] p-1.5 shadow-xl">
                  <div className="px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                    Jump to Patient Record
                  </div>
                  <div className="max-h-72 overflow-y-auto">
                    {searchResults.map((p) => (
                      <button
                        key={p.patient_id}
                        type="button"
                        onClick={() => {
                          setSearchFocused(false);
                          setSearchTerm("");
                          openPatient(p.patient_id, "overview");
                        }}
                        className="flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-left text-xs hover:bg-[var(--cg-bg-elevated)] cursor-pointer"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-semibold text-[var(--cg-accent-teal)]">
                              {p.patient_id}
                            </span>
                            <span className="truncate font-medium text-[var(--cg-text-primary)]">
                              {p.name}
                            </span>
                          </div>
                          <span className="text-[11px] text-[var(--cg-text-secondary)]">
                            {p.primary_condition || "No condition"} • {p.visit_count} visits
                          </span>
                        </div>
                        <ChevronRight className="h-3.5 w-3.5 shrink-0 text-[var(--cg-text-muted)]" />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <Button
              variant="secondary"
              size="sm"
              className="hidden sm:inline-flex"
              onClick={() => askAssistant(undefined, selectedPatientId)}
            >
              <Sparkles className="h-3.5 w-3.5 text-[var(--cg-accent-teal)]" />
              <span>Ask AI</span>
            </Button>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1440px] flex-1 p-4 sm:p-6">
          {demoGateRequired && !demoUnlocked ? null : children}
        </main>
      </div>
    </div>
  );
}
