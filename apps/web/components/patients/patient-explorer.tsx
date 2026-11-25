"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  ArrowUpDown,
  Bot,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  FlaskConical,
  Network,
  Pill,
  Search,
  Stethoscope,
  UserRound,
  X,
} from "lucide-react";
import { useClinical } from "@/components/providers/clinical-provider";
import { usePatientRouteSync } from "@/hooks/use-patient-route-sync";
import { FollowupComparisonPanel } from "@/components/patients/followup-panel";
import { LabTrendsPanel } from "@/components/patients/lab-trends-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Panel,
  PanelContent,
  PanelDescription,
  PanelHeader,
  PanelTitle,
} from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/empty-error-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiClient } from "@/lib/api";
import { cn, formatDateShort } from "@/lib/utils";
import type {
  FollowupComparisonItem,
  KnowledgeGraphResponse,
  LabTrendGroup,
  PatientProfile,
  VisitRecord,
} from "@/types/clinical";

const PAGE_SIZE = 10;

export function PatientExplorer({
  GraphRenderer,
}: {
  GraphRenderer?: React.ComponentType<{
    graphData: KnowledgeGraphResponse;
    highlightEntityId?: string | null;
    compact?: boolean;
  }>;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const {
    patients,
    patientsLoading,
    openGraph,
    askAssistant,
  } = useClinical();
  const {
    selectedPatientId,
    selectPatientInRoute,
    clearPatientInRoute,
  } = usePatientRouteSync();

  const urlTab = searchParams.get("tab");
  const urlCondition = searchParams.get("condition");
  const urlVisitId = searchParams.get("visitId");
  const urlVisitIdRef = useRef<string | null>(urlVisitId);
  urlVisitIdRef.current = urlVisitId;

  const [activeTab, setActiveTab] = useState("overview");
  const [search, setSearch] = useState("");
  const [conditionFilter, setConditionFilter] = useState("all");
  const [genderFilter, setGenderFilter] = useState("all");
  const [sortBy, setSortBy] = useState<"patient_id" | "name" | "visit_count" | "latest_visit_date">("patient_id");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);

  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [timeline, setTimeline] = useState<VisitRecord[]>([]);
  const [labTrends, setLabTrends] = useState<LabTrendGroup[]>([]);
  const [followups, setFollowups] = useState<FollowupComparisonItem[]>([]);
  const [graphData, setGraphData] = useState<KnowledgeGraphResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [expandedVisits, setExpandedVisits] = useState<Record<string, boolean>>({});

  const requestSeqRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (
      urlTab &&
      ["overview", "timeline", "labs", "followups", "graph"].includes(urlTab)
    ) {
      setActiveTab(urlTab);
    }
  }, [urlTab]);

  useEffect(() => {
    if (urlCondition) {
      setConditionFilter(urlCondition);
    }
  }, [urlCondition]);

  const loadPatientBundle = useCallback(async (pid: string) => {
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const reqId = ++requestSeqRef.current;

    setDetailLoading(true);
    setDetailError(null);
    try {
      const [profRes, timeRes, labRes, folRes, graphRes] = await Promise.all([
        apiClient.getPatientProfile(pid, controller.signal),
        apiClient.getPatientTimeline(pid, controller.signal),
        apiClient.getPatientLabTrends(pid, undefined, controller.signal),
        apiClient.getPatientFollowups(pid, controller.signal),
        apiClient.getPatientGraph(pid, controller.signal),
      ]);
      if (controller.signal.aborted || reqId !== requestSeqRef.current) {
        return;
      }
      setProfile(profRes);
      setTimeline(timeRes.visits);
      setLabTrends(labRes.trends);
      setFollowups(folRes.followups);
      setGraphData(graphRes);

      const initialExpanded: Record<string, boolean> = {};
      const targetVisit = urlVisitIdRef.current;
      if (targetVisit) {
        initialExpanded[targetVisit] = true;
      } else if (timeRes.visits.length > 0) {
        initialExpanded[timeRes.visits[0].visit_id] = true;
      }
      setExpandedVisits(initialExpanded);
    } catch (err: unknown) {
      if (
        (err instanceof Error && err.name === "AbortError") ||
        controller.signal.aborted ||
        reqId !== requestSeqRef.current
      ) {
        return;
      }
      setDetailError(
        err instanceof Error
          ? err.message
          : `Failed to retrieve records for ${pid}.`
      );
    } finally {
      if (!controller.signal.aborted && reqId === requestSeqRef.current) {
        setDetailLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (selectedPatientId) {
      loadPatientBundle(selectedPatientId);
    } else {
      requestSeqRef.current += 1;
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      setProfile(null);
      setTimeline([]);
      setLabTrends([]);
      setFollowups([]);
      setGraphData(null);
      setDetailError(null);
      setDetailLoading(false);
      setExpandedVisits({});
    }
    return () => {
      abortControllerRef.current?.abort();
    };
  }, [selectedPatientId, loadPatientBundle]);

  const handleSelectPatient = useCallback(
    (pid: string) => {
      selectPatientInRoute(pid, {
        extraParams: { tab: activeTab },
      });
    },
    [activeTab, selectPatientInRoute]
  );

  const handleClearPatient = useCallback(() => {
    clearPatientInRoute({
      extraParams: { tab: null },
    });
  }, [clearPatientInRoute]);

  const handleTabChange = useCallback(
    (nextTab: string) => {
      setActiveTab(nextTab);
      if (selectedPatientId) {
        const sp = new URLSearchParams(searchParams.toString());
        sp.set("patientId", selectedPatientId);
        sp.set("tab", nextTab);
        router.replace(`${pathname}?${sp.toString()}`, { scroll: false });
      }
    },
    [pathname, router, searchParams, selectedPatientId]
  );

  const availableConditions = useMemo(() => {
    const set = new Set<string>();
    patients.forEach((p) => p.conditions.forEach((c) => set.add(c)));
    return Array.from(set).sort();
  }, [patients]);

  const filteredPatients = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = patients.filter((p) => {
      if (q) {
        const hit =
          p.patient_id.toLowerCase().includes(q) ||
          p.name.toLowerCase().includes(q) ||
          p.conditions.some((c) => c.toLowerCase().includes(q));
        if (!hit) return false;
      }
      if (
        conditionFilter !== "all" &&
        !p.conditions.includes(conditionFilter)
      ) {
        return false;
      }
      if (genderFilter !== "all" && p.gender !== genderFilter) {
        return false;
      }
      return true;
    });

    list.sort((a, b) => {
      let cmp = 0;
      if (sortBy === "name") cmp = a.name.localeCompare(b.name);
      else if (sortBy === "visit_count") cmp = a.visit_count - b.visit_count;
      else if (sortBy === "latest_visit_date")
        cmp = (a.latest_visit_date || "").localeCompare(b.latest_visit_date || "");
      else cmp = a.patient_id.localeCompare(b.patient_id);
      return sortOrder === "asc" ? cmp : -cmp;
    });

    return list;
  }, [patients, search, conditionFilter, genderFilter, sortBy, sortOrder]);

  const totalPages = Math.max(1, Math.ceil(filteredPatients.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pagedPatients = filteredPatients.slice(
    (safePage - 1) * PAGE_SIZE,
    safePage * PAGE_SIZE
  );

  useEffect(() => {
    setPage(1);
  }, [search, conditionFilter, genderFilter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[var(--cg-text-primary)]">
            Patient Explorer
          </h1>
          <p className="text-xs text-[var(--cg-text-secondary)]">
            Filter cohort patients, inspect chronological timelines, analyze lab trajectories, and verify follow-up deltas.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
        {/* Left Directory Panel */}
        <Panel className="xl:col-span-4 flex flex-col">
          <PanelHeader className="flex-col items-stretch gap-3">
            <div className="flex items-center justify-between">
              <PanelTitle>Patient Directory</PanelTitle>
              <Badge variant="neutral" className="font-mono tabular-nums">
                {filteredPatients.length} / {patients.length}
              </Badge>
            </div>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--cg-text-muted)]" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search ID, name, or condition..."
                className="pl-8 text-xs"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <select
                aria-label="Filter by condition"
                value={conditionFilter}
                onChange={(e) => setConditionFilter(e.target.value)}
                className="h-8 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-2 text-xs text-[var(--cg-text-primary)]"
              >
                <option value="all">All Conditions</option>
                {availableConditions.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <select
                aria-label="Filter by gender"
                value={genderFilter}
                onChange={(e) => setGenderFilter(e.target.value)}
                className="h-8 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-2 text-xs text-[var(--cg-text-primary)]"
              >
                <option value="all">All Genders</option>
                <option value="M">Male (M)</option>
                <option value="F">Female (F)</option>
              </select>
            </div>
            <div className="flex items-center justify-between gap-2 text-[11px]">
              <div className="flex items-center gap-1.5">
                <span className="text-[var(--cg-text-muted)]">Sort:</span>
                <select
                  aria-label="Sort patients"
                  value={sortBy}
                  onChange={(e) =>
                    setSortBy(
                      e.target.value as
                        | "patient_id"
                        | "name"
                        | "visit_count"
                        | "latest_visit_date"
                    )
                  }
                  className="rounded border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-2 py-0.5 text-[11px] text-[var(--cg-text-primary)]"
                >
                  <option value="patient_id">Patient ID</option>
                  <option value="name">Name</option>
                  <option value="visit_count">Visit Count</option>
                  <option value="latest_visit_date">Latest Encounter</option>
                </select>
              </div>
              <button
                type="button"
                onClick={() =>
                  setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"))
                }
                className="inline-flex items-center gap-1 rounded border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-2 py-0.5 text-[var(--cg-text-secondary)] hover:text-[var(--cg-text-primary)] cursor-pointer"
              >
                <ArrowUpDown className="h-3 w-3" />
                {sortOrder.toUpperCase()}
              </button>
            </div>
          </PanelHeader>

          <div className="flex-1 divide-y divide-[var(--cg-border)] overflow-y-auto max-h-[640px]">
            {patientsLoading ? (
              <div className="space-y-2 p-4">
                {Array.from({ length: 6 }).map((_, idx) => (
                  <Skeleton key={idx} className="h-14 w-full" />
                ))}
              </div>
            ) : pagedPatients.length === 0 ? (
              <div className="p-6 text-center text-xs text-[var(--cg-text-muted)]">
                No patients match your active search or filters.
              </div>
            ) : (
              pagedPatients.map((p) => {
                const isSelected = p.patient_id === selectedPatientId;
                return (
                  <button
                    key={p.patient_id}
                    type="button"
                    onClick={() => handleSelectPatient(p.patient_id)}
                    className={cn(
                      "flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors cursor-pointer",
                      isSelected
                        ? "bg-[#2DD4BF]/10 border-l-2 border-l-[var(--cg-accent-teal)]"
                        : "hover:bg-[var(--cg-bg-elevated)]"
                    )}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            "font-mono text-xs font-semibold",
                            isSelected
                              ? "text-[var(--cg-accent-teal)]"
                              : "text-[var(--cg-accent-sky)]"
                          )}
                        >
                          {p.patient_id}
                        </span>
                        <span className="truncate text-sm font-medium text-[var(--cg-text-primary)]">
                          {p.name}
                        </span>
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-[var(--cg-text-secondary)]">
                        <span>{p.primary_condition || "No Dx"}</span>
                        <span>•</span>
                        <span className="font-mono">
                          Latest {formatDateShort(p.latest_visit_date)}
                        </span>
                      </div>
                    </div>
                    <Badge variant={isSelected ? "teal" : "neutral"} className="shrink-0 font-mono">
                      {p.visit_count}v
                    </Badge>
                  </button>
                );
              })
            )}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between border-t border-[var(--cg-border)] px-4 py-2.5 text-xs text-[var(--cg-text-secondary)]">
            <span className="font-mono">
              Page {safePage} of {totalPages}
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon"
                className="h-7 w-7"
                disabled={safePage <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                aria-label="Previous patient page"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-7 w-7"
                disabled={safePage >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                aria-label="Next patient page"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </Panel>

        {/* Right Patient Workspace */}
        <div className="xl:col-span-8 space-y-4">
          {!selectedPatientId ? (
            <EmptyState
              title="No patient selected"
              description="Select any patient from the directory on the left to inspect their clinical profile, chronological encounters, lab trajectories, follow-up comparisons, and knowledge graph."
              action={
                patients.length > 0 ? (
                  <div className="flex flex-wrap justify-center gap-2">
                    {patients.slice(0, 3).map((p) => (
                      <Button
                        key={p.patient_id}
                        variant="outline"
                        size="sm"
                        onClick={() => handleSelectPatient(p.patient_id)}
                      >
                        <span className="font-mono text-[var(--cg-accent-teal)]">
                          {p.patient_id}
                        </span>
                        <span>{p.name}</span>
                      </Button>
                    ))}
                  </div>
                ) : undefined
              }
            />
          ) : detailError ? (
            <ErrorState
              title="Unable to load patient profile"
              message={detailError}
              onRetry={() =>
                selectedPatientId && loadPatientBundle(selectedPatientId)
              }
            />
          ) : detailLoading || !profile ? (
            <div className="space-y-4">
              <Skeleton className="h-32 w-full rounded-xl" />
              <Skeleton className="h-96 w-full rounded-xl" />
            </div>
          ) : (
            <>
              {/* Patient Header Card */}
              <Panel>
                <PanelContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-start gap-3.5">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-[#2DD4BF]/30 bg-[#2DD4BF]/10 text-[var(--cg-accent-teal)]">
                      <UserRound className="h-6 w-6" />
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-lg font-semibold text-[var(--cg-text-primary)]">
                          {profile.name}
                        </h2>
                        <Badge variant="teal" className="font-mono">
                          {profile.patient_id}
                        </Badge>
                        {profile.conditions.map((c) => (
                          <Badge key={c} variant="warning">
                            {c}
                          </Badge>
                        ))}
                      </div>
                      <p className="mt-1 text-xs text-[var(--cg-text-secondary)]">
                        Gender:{" "}
                        <strong className="text-[var(--cg-text-primary)]">
                          {profile.gender || "N/A"}
                        </strong>{" "}
                        • DOB:{" "}
                        <span className="font-mono">
                          {profile.dob || "N/A"}
                        </span>{" "}
                        • Derived Age:{" "}
                        <strong className="text-[var(--cg-text-primary)]">
                          {profile.age !== null && profile.age !== undefined
                            ? `${profile.age} yrs`
                            : "N/A"}
                        </strong>
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleClearPatient}
                      aria-label="Clear selected patient"
                      title="Clear active patient and return to directory"
                    >
                      <X className="h-3.5 w-3.5" />
                      Clear Patient
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openGraph(profile.patient_id)}
                    >
                      <Network className="h-3.5 w-3.5 text-[var(--cg-accent-sky)]" />
                      Full Graph
                    </Button>
                    <Button
                      size="sm"
                      onClick={() =>
                        askAssistant(
                          `Summarize the longitudinal clinical history and lab trends for patient ${profile.patient_id}.`,
                          profile.patient_id
                        )
                      }
                    >
                      <Bot className="h-3.5 w-3.5" />
                      Ask AI
                    </Button>
                  </div>
                </PanelContent>
              </Panel>

              {/* Profile Tabs */}
              <Tabs value={activeTab} onValueChange={handleTabChange}>
                <TabsList className="w-full justify-start overflow-x-auto">
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="timeline">
                    Visit History ({timeline.length})
                  </TabsTrigger>
                  <TabsTrigger value="labs">
                    Lab Trends ({labTrends.length})
                  </TabsTrigger>
                  <TabsTrigger value="followups">
                    Follow-Up Comparison ({followups.length})
                  </TabsTrigger>
                  <TabsTrigger value="graph">Knowledge Graph</TabsTrigger>
                </TabsList>

                {/* Tab 1: Overview */}
                <TabsContent value="overview" className="space-y-4">
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    <Panel className="p-4">
                      <span className="text-xs text-[var(--cg-text-secondary)]">
                        Total Encounters
                      </span>
                      <div className="mt-1.5 font-mono text-2xl font-semibold tabular-nums">
                        {profile.visit_count}
                      </div>
                    </Panel>
                    <Panel className="p-4">
                      <span className="text-xs text-[var(--cg-text-secondary)]">
                        First Recorded Visit
                      </span>
                      <div className="mt-1.5 font-mono text-base font-semibold">
                        {formatDateShort(profile.first_visit_date)}
                      </div>
                    </Panel>
                    <Panel className="p-4">
                      <span className="text-xs text-[var(--cg-text-secondary)]">
                        Latest Recorded Visit
                      </span>
                      <div className="mt-1.5 font-mono text-base font-semibold">
                        {formatDateShort(profile.latest_visit_date)}
                      </div>
                    </Panel>
                  </div>

                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <Panel>
                      <PanelHeader>
                        <PanelTitle>Care Team & Diagnoses</PanelTitle>
                      </PanelHeader>
                      <PanelContent className="space-y-3 text-xs">
                        <div>
                          <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                            Attending Physicians
                          </span>
                          <div className="mt-1.5 flex flex-wrap gap-1.5">
                            {profile.attending_doctors.length > 0 ? (
                              profile.attending_doctors.map((doc) => (
                                <Badge key={doc} variant="violet">
                                  <Stethoscope className="h-3 w-3" />
                                  {doc}
                                </Badge>
                              ))
                            ) : (
                              <span className="text-[var(--cg-text-muted)]">None recorded</span>
                            )}
                          </div>
                        </div>
                        <div>
                          <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                            Recorded Conditions
                          </span>
                          <div className="mt-1.5 flex flex-wrap gap-1.5">
                            {profile.conditions.length > 0 ? (
                              profile.conditions.map((cond) => (
                                <Badge key={cond} variant="warning">
                                  {cond}
                                </Badge>
                              ))
                            ) : (
                              <span className="text-[var(--cg-text-muted)]">None recorded</span>
                            )}
                          </div>
                        </div>
                      </PanelContent>
                    </Panel>

                    <Panel>
                      <PanelHeader>
                        <PanelTitle>Biomarker Summary</PanelTitle>
                      </PanelHeader>
                      <PanelContent className="space-y-2 text-xs">
                        {labTrends.length === 0 ? (
                          <p className="text-[var(--cg-text-muted)]">
                            No lab records recorded.
                          </p>
                        ) : (
                          labTrends.map((t) => (
                            <div
                              key={`${t.biomarker}-${t.unit}`}
                              className="flex items-center justify-between rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-3 py-2"
                            >
                              <div>
                                <div className="font-medium text-[var(--cg-text-primary)]">
                                  {t.biomarker}
                                </div>
                                <div className="text-[11px] text-[var(--cg-text-muted)]">
                                  {t.initial_value} → {t.latest_value} {t.unit}
                                </div>
                              </div>
                              <Badge
                                variant={
                                  t.direction === "decreased"
                                    ? "teal"
                                    : t.direction === "increased"
                                    ? "sky"
                                    : "neutral"
                                }
                              >
                                {t.percentage_change !== null &&
                                t.percentage_change !== undefined
                                  ? `${t.percentage_change > 0 ? "+" : ""}${t.percentage_change.toFixed(1)}%`
                                  : t.direction}
                              </Badge>
                            </div>
                          ))
                        )}
                      </PanelContent>
                    </Panel>
                  </div>
                </TabsContent>

                {/* Tab 2: Chronological Visit Timeline */}
                <TabsContent value="timeline" className="space-y-3">
                  {timeline.length === 0 ? (
                    <EmptyState
                      title="No visits recorded"
                      description="This patient has no Visit nodes in the hospital knowledge graph."
                    />
                  ) : (
                    <div className="relative space-y-3 pl-5 before:absolute before:left-2 before:top-3 before:bottom-3 before:w-px before:bg-[var(--cg-border)]">
                      {timeline.map((visit, idx) => {
                        const isOpen = !!expandedVisits[visit.visit_id];
                        const isHighlighted = urlVisitId === visit.visit_id;
                        return (
                          <div key={visit.visit_id} className="relative">
                            <span
                              className={cn(
                                "absolute -left-[17px] top-4 h-2.5 w-2.5 rounded-full border-2 border-[var(--cg-bg-main)]",
                                isHighlighted
                                  ? "bg-[var(--cg-accent-teal)] ring-4 ring-[#2DD4BF]/25"
                                  : "bg-[var(--cg-accent-sky)]"
                              )}
                            />
                            <Panel
                              className={cn(
                                isHighlighted && "border-[#2DD4BF]/50"
                              )}
                            >
                              <button
                                type="button"
                                onClick={() =>
                                  setExpandedVisits((prev) => ({
                                    ...prev,
                                    [visit.visit_id]: !prev[visit.visit_id],
                                  }))
                                }
                                className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left cursor-pointer"
                              >
                                <div className="flex flex-wrap items-center gap-2">
                                  <Badge variant="neutral" className="font-mono">
                                    #{idx + 1}
                                  </Badge>
                                  <span className="font-mono text-sm font-semibold text-[var(--cg-accent-sky)]">
                                    {visit.visit_id}
                                  </span>
                                  <span className="text-xs font-medium text-[var(--cg-text-primary)]">
                                    {formatDateShort(visit.visit_date)}
                                  </span>
                                  <Badge
                                    variant={
                                      visit.admission_type === "Emergency"
                                        ? "error"
                                        : visit.admission_type === "Follow-up"
                                        ? "teal"
                                        : "sky"
                                    }
                                  >
                                    {visit.admission_type}
                                  </Badge>
                                </div>
                                <div className="flex items-center gap-2 text-xs text-[var(--cg-text-secondary)]">
                                  {visit.doctor?.name && (
                                    <span className="hidden sm:inline">
                                      {visit.doctor.name}
                                    </span>
                                  )}
                                  {isOpen ? (
                                    <ChevronUp className="h-4 w-4" />
                                  ) : (
                                    <ChevronDown className="h-4 w-4" />
                                  )}
                                </div>
                              </button>

                              {isOpen && (
                                <div className="border-t border-[var(--cg-border)] px-4 py-4 space-y-4">
                                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                                    <div className="flex items-center gap-2 text-[var(--cg-text-secondary)]">
                                      <Stethoscope className="h-3.5 w-3.5 text-[var(--cg-accent-violet)]" />
                                      <span>
                                        Attending:{" "}
                                        <strong className="text-[var(--cg-text-primary)]">
                                          {visit.doctor?.name || "Unassigned"}
                                        </strong>{" "}
                                        {visit.doctor?.doctor_id && (
                                          <span className="font-mono text-[var(--cg-text-muted)]">
                                            ({visit.doctor.doctor_id} • {visit.doctor.specialty})
                                          </span>
                                        )}
                                      </span>
                                    </div>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() =>
                                        openGraph(profile.patient_id, visit.visit_id)
                                      }
                                    >
                                      <Network className="h-3.5 w-3.5 text-[var(--cg-accent-sky)]" />
                                      Inspect Visit in Graph
                                    </Button>
                                  </div>

                                  <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                                    <div className="rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-3 text-xs">
                                      <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                                        Diagnoses
                                      </div>
                                      {visit.diagnoses.length > 0 ? (
                                        <div className="space-y-1.5">
                                          {visit.diagnoses.map((dx, i) => (
                                            <div key={`${dx.diagnosis_id || i}`}>
                                              <div className="font-medium text-[var(--cg-text-primary)]">
                                                {dx.condition}
                                              </div>
                                              <div className="font-mono text-[11px] text-[var(--cg-text-secondary)]">
                                                {dx.diagnosis_id} • {dx.status}
                                              </div>
                                            </div>
                                          ))}
                                        </div>
                                      ) : (
                                        <span className="text-[var(--cg-text-muted)]">
                                          None recorded
                                        </span>
                                      )}
                                    </div>

                                    <div className="rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-3 text-xs">
                                      <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                                        Prescriptions
                                      </div>
                                      {visit.medications.length > 0 ? (
                                        <div className="space-y-1.5">
                                          {visit.medications.map((rx, i) => (
                                            <div key={`${rx.prescription_id || i}`}>
                                              <div className="flex items-center gap-1.5 font-medium text-[var(--cg-text-primary)]">
                                                <Pill className="h-3 w-3 text-[var(--cg-success)]" />
                                                {rx.medication_name}
                                              </div>
                                              <div className="font-mono text-[11px] text-[var(--cg-text-secondary)]">
                                                {rx.prescription_id} • {rx.dosage}
                                              </div>
                                            </div>
                                          ))}
                                        </div>
                                      ) : (
                                        <span className="text-[var(--cg-text-muted)]">
                                          None prescribed
                                        </span>
                                      )}
                                    </div>

                                    <div className="rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-3 text-xs">
                                      <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                                        Laboratory Tests
                                      </div>
                                      {visit.lab_tests.length > 0 ? (
                                        <div className="space-y-1.5">
                                          {visit.lab_tests.map((lab) => (
                                            <div key={lab.test_id}>
                                              <div className="flex items-center gap-1.5 font-medium text-[var(--cg-text-primary)]">
                                                <FlaskConical className="h-3 w-3 text-[var(--cg-accent-teal)]" />
                                                {lab.test_name}:{" "}
                                                <span className="font-mono">
                                                  {lab.value} {lab.unit}
                                                </span>
                                              </div>
                                              <div className="font-mono text-[11px] text-[var(--cg-text-secondary)]">
                                                {lab.test_id}
                                              </div>
                                            </div>
                                          ))}
                                        </div>
                                      ) : (
                                        <span className="text-[var(--cg-text-muted)]">
                                          No labs performed
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </Panel>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </TabsContent>

                {/* Tab 3: Lab Trends */}
                <TabsContent value="labs">
                  <LabTrendsPanel
                    trends={labTrends}
                    onSelectVisit={(vid) => {
                      setExpandedVisits((prev) => ({ ...prev, [vid]: true }));
                      setActiveTab("timeline");
                    }}
                  />
                </TabsContent>

                {/* Tab 4: Follow-Up Comparison */}
                <TabsContent value="followups">
                  <FollowupComparisonPanel
                    followups={followups}
                    onInspectVisitGraph={(vid) =>
                      openGraph(profile.patient_id, vid)
                    }
                  />
                </TabsContent>

                {/* Tab 5: Embedded Knowledge Graph */}
                <TabsContent value="graph">
                  {graphData && GraphRenderer ? (
                    <GraphRenderer
                      graphData={graphData}
                      highlightEntityId={urlVisitId}
                      compact
                    />
                  ) : (
                    <Panel>
                      <PanelContent className="flex items-center justify-between">
                        <div>
                          <PanelTitle>Patient Knowledge Graph</PanelTitle>
                          <PanelDescription>
                            {graphData?.stats.node_count || 0} nodes and{" "}
                            {graphData?.stats.edge_count || 0} relationships ready for inspection.
                          </PanelDescription>
                        </div>
                        <Button onClick={() => openGraph(profile.patient_id)}>
                          <Network className="h-4 w-4" />
                          Open Knowledge Graph Explorer
                        </Button>
                      </PanelContent>
                    </Panel>
                  )}
                </TabsContent>
              </Tabs>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
