"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  Bot,
  CalendarRange,
  ClipboardList,
  GitBranch,
  Network,
  Stethoscope,
  Users,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useClinical } from "@/components/providers/clinical-provider";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Panel,
  PanelContent,
  PanelDescription,
  PanelHeader,
  PanelTitle,
} from "@/components/ui/card";
import { ErrorState } from "@/components/ui/empty-error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api";
import { cn, formatDateShort, formatMonthLabel } from "@/lib/utils";
import type { OverviewResponse } from "@/types/clinical";

const TIME_RANGES = [
  { id: "all", label: "All Time" },
  { id: "12m", label: "Last 12M" },
  { id: "6m", label: "Last 6M" },
  { id: "2024", label: "2024" },
  { id: "2023", label: "2023" },
];

const ADMISSION_COLORS: Record<string, string> = {
  "Follow-up": "#2DD4BF",
  Outpatient: "#38BDF8",
  Inpatient: "#818CF8",
  Emergency: "#F87171",
};

const NODE_COLORS: Record<string, string> = {
  Patient: "#2DD4BF",
  Visit: "#38BDF8",
  Doctor: "#818CF8",
  Diagnosis: "#FBBF24",
  Medication: "#34D399",
  LabTest: "#F472B6",
};

function OverviewSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, idx) => (
          <Skeleton key={idx} className="h-28 w-full rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Skeleton className="h-80 lg:col-span-8 rounded-xl" />
        <Skeleton className="h-80 lg:col-span-4 rounded-xl" />
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <Skeleton className="h-72 lg:col-span-6 rounded-xl" />
        <Skeleton className="h-72 lg:col-span-6 rounded-xl" />
      </div>
    </div>
  );
}

export function OverviewDashboard() {
  const { patients, openPatient, openGraph, askAssistant, openAnalytics } =
    useClinical();
  const [timeRange, setTimeRange] = useState("all");
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = useCallback(async (range: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getOverview(range);
      setData(res);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to load overview metrics."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview(timeRange);
  }, [fetchOverview, timeRange]);

  const kpis = data
    ? [
        {
          label: "Total Patients",
          value: data.totals.total_patients,
          sub: "Unique cohort entities",
          icon: Users,
          accent: "text-[var(--cg-accent-teal)]",
          href: "/patients",
        },
        {
          label: "Attending Doctors",
          value: data.totals.total_doctors,
          sub: "Cross-visit physicians",
          icon: Stethoscope,
          accent: "text-[var(--cg-accent-violet)]",
          href: "/graph?scope=cohort",
        },
        {
          label: "Hospital Visits",
          value: data.totals.total_visits,
          sub: "Sequential encounters",
          icon: CalendarRange,
          accent: "text-[var(--cg-accent-sky)]",
          href: "/patients",
        },
        {
          label: "Clinical Records",
          value: data.totals.total_clinical_records,
          sub: `${data.totals.total_diagnosis_records} Dx • ${data.totals.total_prescription_records} Rx • ${data.totals.total_lab_records} Labs`,
          icon: ClipboardList,
          accent: "text-[var(--cg-success)]",
          href: "/analytics",
        },
        {
          label: "Graph Nodes",
          value: data.totals.total_nodes,
          sub: "6 distinct Neo4j labels",
          icon: Network,
          accent: "text-[var(--cg-accent-teal)]",
          href: "/graph",
        },
        {
          label: "Graph Relationships",
          value: data.totals.total_relationships,
          sub: "6 typed clinical edges",
          icon: GitBranch,
          accent: "text-[var(--cg-accent-sky)]",
          href: "/graph",
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* Page Header & Actions */}
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-[var(--cg-text-primary)]">
              Hospital Intelligence Overview
            </h1>
            <Badge variant="teal" className="whitespace-nowrap">Live Neo4j Graph</Badge>
          </div>
          <p className="mt-0.5 text-xs text-[var(--cg-text-secondary)]">
            Cohort topology, encounter velocity, and clinical record coverage across synthetic Neo4j AuraDB data.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <div
            role="group"
            aria-label="Visits time range filter"
            className="inline-flex items-center rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] p-0.5"
          >
            {TIME_RANGES.map((tr) => (
              <button
                key={tr.id}
                type="button"
                onClick={() => setTimeRange(tr.id)}
                className={cn(
                  "whitespace-nowrap rounded-md px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer",
                  timeRange === tr.id
                    ? "bg-[var(--cg-bg-elevated)] text-[var(--cg-accent-teal)]"
                    : "text-[var(--cg-text-secondary)] hover:text-[var(--cg-text-primary)]"
                )}
              >
                {tr.label}
              </button>
            ))}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => openGraph(null)}
          >
            <Network className="h-3.5 w-3.5 text-[var(--cg-accent-sky)]" />
            Knowledge Graph
          </Button>
          <Button size="sm" onClick={() => askAssistant(undefined, null)}>
            <Bot className="h-3.5 w-3.5" />
            AI Assistant
          </Button>
        </div>
      </div>

      {error && (
        <ErrorState
          title="Could not load Neo4j overview metrics"
          message={error}
          onRetry={() => fetchOverview(timeRange)}
        />
      )}

      {loading && !data ? (
        <OverviewSkeleton />
      ) : data ? (
        <>
          {/* KPI Bento Grid */}
          <section
            aria-label="Cohort key metrics"
            className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6"
          >
            {kpis.map((kpi) => {
              const Icon = kpi.icon;
              return (
                <Link
                  key={kpi.label}
                  href={kpi.href}
                  className="group rounded-xl border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] p-4 transition-colors hover:border-[var(--cg-border-strong)] hover:bg-[var(--cg-bg-elevated)]"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-[var(--cg-text-secondary)]">
                      {kpi.label}
                    </span>
                    <Icon className={cn("h-4 w-4", kpi.accent)} />
                  </div>
                  <div className="mt-2.5 text-2xl font-semibold tracking-tight text-[var(--cg-text-primary)]">
                    <AnimatedNumber value={kpi.value} />
                  </div>
                  <p className="mt-1 truncate text-[11px] text-[var(--cg-text-muted)]">
                    {kpi.sub}
                  </p>
                </Link>
              );
            })}
          </section>

          {/* Primary Analytics Row */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            {/* Visits Over Time */}
            <Panel className="lg:col-span-8">
              <PanelHeader>
                <div>
                  <PanelTitle>Encounters Over Time</PanelTitle>
                  <PanelDescription>
                    Monthly hospital visits stratified by follow-up and acute care settings
                  </PanelDescription>
                </div>
                <Badge variant="neutral" className="font-mono tabular-nums">
                  {data.visits_over_time.reduce((acc, p) => acc + p.total_visits, 0)}{" "}
                  visits shown
                </Badge>
              </PanelHeader>
              <PanelContent>
                <div className="h-[270px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={data.visits_over_time.map((pt) => ({
                        ...pt,
                        monthLabel: formatMonthLabel(pt.month),
                      }))}
                      margin={{ top: 8, right: 12, left: -16, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="cgTotalGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#2DD4BF" stopOpacity={0.32} />
                          <stop offset="95%" stopColor="#2DD4BF" stopOpacity={0.0} />
                        </linearGradient>
                        <linearGradient id="cgFollowGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.24} />
                          <stop offset="95%" stopColor="#38BDF8" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="var(--cg-chart-grid)"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="monthLabel"
                        tick={{ fill: "#94A3B8", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: "#94A3B8", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        allowDecimals={false}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#101722",
                          border: "1px solid #243041",
                          borderRadius: "10px",
                          fontSize: "12px",
                          color: "#F1F5F9",
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="total_visits"
                        name="Total Visits"
                        stroke="#2DD4BF"
                        strokeWidth={2.2}
                        fill="url(#cgTotalGrad)"
                        isAnimationActive={false}
                      />
                      <Area
                        type="monotone"
                        dataKey="follow_up"
                        name="Follow-up"
                        stroke="#38BDF8"
                        strokeWidth={1.8}
                        fill="url(#cgFollowGrad)"
                        isAnimationActive={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </PanelContent>
            </Panel>

            {/* Admission-Type Distribution */}
            <Panel className="lg:col-span-4">
              <PanelHeader>
                <div>
                  <PanelTitle>Admission Types</PanelTitle>
                  <PanelDescription>
                    Breakdown of {data.totals.total_visits} total encounters
                  </PanelDescription>
                </div>
              </PanelHeader>
              <PanelContent>
                <div className="relative h-[185px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.admission_types}
                        dataKey="count"
                        nameKey="admission_type"
                        cx="50%"
                        cy="50%"
                        innerRadius={54}
                        outerRadius={78}
                        paddingAngle={3}
                        stroke="none"
                        isAnimationActive={false}
                      >
                        {data.admission_types.map((entry) => (
                          <Cell
                            key={entry.admission_type}
                            fill={ADMISSION_COLORS[entry.admission_type] || "#94A3B8"}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#101722",
                          border: "1px solid #243041",
                          borderRadius: "10px",
                          fontSize: "12px",
                          color: "#F1F5F9",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                    <span className="font-mono text-xl font-semibold tabular-nums text-[var(--cg-text-primary)]">
                      {data.totals.total_visits}
                    </span>
                    <span className="text-[10px] uppercase tracking-wider text-[var(--cg-text-muted)]">
                      Visits
                    </span>
                  </div>
                </div>
                <div className="mt-2 grid grid-cols-1 gap-2 xl:grid-cols-2">
                  {data.admission_types.map((adm) => {
                    const pct =
                      data.totals.total_visits > 0
                        ? ((adm.count / data.totals.total_visits) * 100).toFixed(1)
                        : "0.0";
                    return (
                      <div
                        key={adm.admission_type}
                        className="flex items-center justify-between gap-1.5 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-2.5 py-2 text-xs"
                      >
                        <span className="flex items-center gap-1.5 whitespace-nowrap text-[var(--cg-text-secondary)]">
                          <span
                            className="h-2 w-2 shrink-0 rounded-full"
                            style={{
                              backgroundColor:
                                ADMISSION_COLORS[adm.admission_type] || "#94A3B8",
                            }}
                          />
                          {adm.admission_type}
                        </span>
                        <span className="whitespace-nowrap font-mono text-[11px] font-semibold tabular-nums text-[var(--cg-text-primary)]">
                          {adm.count}{" "}
                          <span className="text-[10px] font-normal text-[var(--cg-text-muted)]">
                            {pct}%
                          </span>
                        </span>
                      </div>
                    );
                  })}
                </div>
              </PanelContent>
            </Panel>
          </div>

          {/* Condition Distribution & Graph Schema Preview */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            {/* Condition Distribution */}
            <Panel className="lg:col-span-6">
              <PanelHeader>
                <div>
                  <PanelTitle>Condition Distribution</PanelTitle>
                  <PanelDescription>
                    Unique patients vs encounter records per condition (click bar to explore)
                  </PanelDescription>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openAnalytics()}
                >
                  Medication Analytics
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </PanelHeader>
              <PanelContent>
                <div className="h-[235px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={data.conditions}
                      margin={{ top: 10, right: 12, left: -16, bottom: 0 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="var(--cg-chart-grid)"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="condition"
                        tick={{ fill: "#94A3B8", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: "#94A3B8", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#101722",
                          border: "1px solid #243041",
                          borderRadius: "10px",
                          fontSize: "12px",
                          color: "#F1F5F9",
                        }}
                      />
                      <Bar
                        dataKey="patient_count"
                        name="Unique Patients"
                        fill="#2DD4BF"
                        radius={[6, 6, 0, 0]}
                        className="cursor-pointer"
                        isAnimationActive={false}
                        onClick={(entry) => {
                          const payload = (
                            entry as unknown as { payload?: { condition?: string } }
                          )?.payload;
                          if (payload?.condition) {
                            openAnalytics(payload.condition);
                          }
                        }}
                      />
                      <Bar
                        dataKey="record_count"
                        name="Visit Records"
                        fill="#38BDF8"
                        radius={[6, 6, 0, 0]}
                        className="cursor-pointer"
                        isAnimationActive={false}
                        onClick={(entry) => {
                          const payload = (
                            entry as unknown as { payload?: { condition?: string } }
                          )?.payload;
                          if (payload?.condition) {
                            openAnalytics(payload.condition);
                          }
                        }}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {data.conditions.map((c) => (
                    <button
                      key={c.condition}
                      type="button"
                      onClick={() => openAnalytics(c.condition)}
                      className="inline-flex items-center gap-2 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-3 py-1.5 text-xs hover:border-[#2DD4BF]/50 cursor-pointer"
                    >
                      <span className="font-medium text-[var(--cg-text-primary)]">
                        {c.condition}
                      </span>
                      <span className="font-mono text-[11px] text-[var(--cg-accent-teal)]">
                        {c.patient_count} pts
                      </span>
                    </button>
                  ))}
                </div>
              </PanelContent>
            </Panel>

            {/* Graph Schema Preview */}
            <Panel className="lg:col-span-6">
              <PanelHeader>
                <div>
                  <PanelTitle>Neo4j Property Graph Schema</PanelTitle>
                  <PanelDescription>
                    Live node label and relationship inventory ({data.totals.total_nodes} nodes,{" "}
                    {data.totals.total_relationships} edges)
                  </PanelDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openGraph(null)}
                >
                  Open Explorer
                </Button>
              </PanelHeader>
              <PanelContent className="space-y-4">
                <div>
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                    Node Labels
                  </div>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {data.schema_nodes.map((node) => (
                      <div
                        key={node.label}
                        className="flex items-center justify-between rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-3 py-2 text-xs"
                      >
                        <span className="flex items-center gap-2 font-medium text-[var(--cg-text-primary)]">
                          <span
                            className="h-2.5 w-2.5 rounded-full"
                            style={{
                              backgroundColor: NODE_COLORS[node.label] || "#94A3B8",
                            }}
                          />
                          :{node.label}
                        </span>
                        <span className="font-mono font-semibold tabular-nums text-[var(--cg-text-secondary)]">
                          {node.count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                    Relationship Types
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {data.schema_relationships.map((rel) => (
                      <div
                        key={rel.relationship_type}
                        className="flex items-center justify-between rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-3 py-1.5 text-xs"
                      >
                        <span className="font-mono text-[11px] text-[var(--cg-accent-sky)]">
                          [:{rel.relationship_type}]
                        </span>
                        <span className="font-mono font-semibold tabular-nums text-[var(--cg-text-primary)]">
                          {rel.count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </PanelContent>
            </Panel>
          </div>

          {/* Recent Encounters & Quick Patient Exploration */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
            {/* Recent Encounters */}
            <Panel className="lg:col-span-7">
              <PanelHeader>
                <div>
                  <PanelTitle>Recent Clinical Encounters</PanelTitle>
                  <PanelDescription>
                    Latest recorded hospital visits in Neo4j ordered chronologically
                  </PanelDescription>
                </div>
                <Link
                  href="/patients"
                  className="inline-flex items-center gap-1 text-xs font-medium text-[var(--cg-accent-teal)] hover:underline"
                >
                  All Patients <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </PanelHeader>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-[var(--cg-border)] text-[11px] font-medium uppercase tracking-wider text-[var(--cg-text-muted)]">
                      <th className="px-4 py-3">Visit</th>
                      <th className="px-4 py-3">Patient</th>
                      <th className="px-4 py-3">Condition</th>
                      <th className="px-4 py-3">Setting</th>
                      <th className="px-4 py-3 text-right">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--cg-border)]">
                    {data.recent_encounters.map((enc) => (
                      <tr
                        key={enc.visit_id}
                        className="hover:bg-[var(--cg-bg-elevated)]/60 transition-colors"
                      >
                        <td className="px-4 py-2.5">
                          <button
                            type="button"
                            onClick={() =>
                              openPatient(enc.patient_id, "timeline", enc.visit_id)
                            }
                            className="font-mono font-semibold text-[var(--cg-accent-sky)] hover:underline cursor-pointer"
                          >
                            {enc.visit_id}
                          </button>
                        </td>
                        <td className="px-4 py-2.5">
                          <button
                            type="button"
                            onClick={() => openPatient(enc.patient_id, "overview")}
                            className="text-left hover:underline cursor-pointer"
                          >
                            <span className="font-medium text-[var(--cg-text-primary)]">
                              {enc.patient_name}
                            </span>
                            <span className="ml-1.5 font-mono text-[11px] text-[var(--cg-text-muted)]">
                              {enc.patient_id}
                            </span>
                          </button>
                        </td>
                        <td className="px-4 py-2.5 text-[var(--cg-text-secondary)]">
                          {enc.condition || "—"}
                        </td>
                        <td className="px-4 py-2.5">
                          <Badge
                            variant={
                              enc.admission_type === "Emergency"
                                ? "error"
                                : enc.admission_type === "Follow-up"
                                ? "teal"
                                : enc.admission_type === "Inpatient"
                                ? "violet"
                                : "sky"
                            }
                          >
                            {enc.admission_type}
                          </Badge>
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono tabular-nums text-[var(--cg-text-secondary)]">
                          {formatDateShort(enc.visit_date)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            {/* Quick Patient Exploration */}
            <Panel className="lg:col-span-5">
              <PanelHeader>
                <div>
                  <PanelTitle>Quick Patient Exploration</PanelTitle>
                  <PanelDescription>
                    Jump directly into longitudinal timelines, graphs, or AI Q&A
                  </PanelDescription>
                </div>
                <Activity className="h-4 w-4 text-[var(--cg-accent-teal)]" />
              </PanelHeader>
              <PanelContent className="space-y-2.5">
                {patients.slice(0, 5).map((p) => (
                  <div
                    key={p.patient_id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-3"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-[var(--cg-accent-teal)]">
                          {p.patient_id}
                        </span>
                        <span className="truncate text-sm font-medium text-[var(--cg-text-primary)]">
                          {p.name}
                        </span>
                      </div>
                      <p className="mt-0.5 text-[11px] text-[var(--cg-text-secondary)]">
                        {p.primary_condition || "Unclassified"} • {p.visit_count} visits • Latest{" "}
                        {formatDateShort(p.latest_visit_date)}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openPatient(p.patient_id, "overview")}
                      >
                        Profile
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        title={`Explore graph for ${p.patient_id}`}
                        onClick={() => openGraph(p.patient_id)}
                      >
                        <Network className="h-3.5 w-3.5 text-[var(--cg-accent-sky)]" />
                      </Button>
                    </div>
                  </div>
                ))}
              </PanelContent>
            </Panel>
          </div>
        </>
      ) : null}
    </div>
  );
}
