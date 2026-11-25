"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowUpDown,
  ChevronDown,
  ChevronUp,
  FlaskConical,
  Users,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useClinical } from "@/components/providers/clinical-provider";
import { Badge } from "@/components/ui/badge";
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
import { cn } from "@/lib/utils";
import type { ConditionInfo, MedicationAnalyticsResponse } from "@/types/clinical";

type SortKey =
  | "medication"
  | "unique_patient_count"
  | "eligible_transitions"
  | "improved_transitions"
  | "worsened_transitions"
  | "betterment_rate_pct";

export function MedicationAnalyticsView() {
  const searchParams = useSearchParams();
  const { openPatient, openGraph } = useClinical();
  const urlCondition = searchParams.get("condition");

  const [conditions, setConditions] = useState<ConditionInfo[]>([]);
  const [selectedCondition, setSelectedCondition] = useState<string>(
    urlCondition || "Type 2 Diabetes"
  );
  const [data, setData] = useState<MedicationAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortKey>("betterment_rate_pct");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [expandedMed, setExpandedMed] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (urlCondition) {
      setSelectedCondition(urlCondition);
    }
  }, [urlCondition]);

  useEffect(() => {
    let active = true;
    apiClient
      .getConditions()
      .then((res) => {
        if (!active) return;
        setConditions(res.conditions);
        if (
          !urlCondition &&
          res.conditions.length > 0 &&
          !res.conditions.some((c) => c.condition === selectedCondition)
        ) {
          setSelectedCondition(res.conditions[0].condition);
        }
      })
      .catch(() => {
        // Fallback condition options remain selectable
      });
    return () => {
      active = false;
    };
  }, [urlCondition, selectedCondition]);

  const loadAnalytics = useCallback(async (cond: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getMedicationAnalytics(cond);
      setData(res);
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : `Failed to retrieve analytics for ${cond}.`
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCondition) {
      loadAnalytics(selectedCondition);
    }
  }, [selectedCondition, loadAnalytics]);

  const sortedMedications = useMemo(() => {
    if (!data?.medications) return [];
    const copy = [...data.medications];
    copy.sort((a, b) => {
      let cmp = 0;
      if (sortBy === "medication") {
        cmp = a.medication.localeCompare(b.medication);
      } else {
        cmp = a[sortBy] - b[sortBy];
      }
      return sortOrder === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [data, sortBy, sortOrder]);

  const handleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortOrder(key === "medication" ? "asc" : "desc");
    }
  };

  const highestObserved = useMemo(() => {
    if (!data?.medications?.length) return null;
    return [...data.medications].sort(
      (a, b) =>
        b.betterment_rate_pct - a.betterment_rate_pct ||
        b.eligible_transitions - a.eligible_transitions
    )[0];
  }, [data]);

  const conditionChoices =
    conditions.length > 0
      ? conditions.map((c) => c.condition)
      : ["Type 2 Diabetes", "Hypertension", "Hyperlipidemia"];

  return (
    <div className="space-y-5">
      {/* Header & Condition Selector */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-[var(--cg-text-primary)]">
            Medication Outcome Analytics
          </h1>
          <p className="text-xs text-[var(--cg-text-secondary)]">
            Synthetic observational biomarker changes across consecutive [:FOLLOWED_BY] visit transitions.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {conditionChoices.map((cond) => (
            <button
              key={cond}
              type="button"
              onClick={() => setSelectedCondition(cond)}
              className={cn(
                "rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer",
                selectedCondition === cond
                  ? "border-[#2DD4BF]/40 bg-[#2DD4BF]/10 text-[var(--cg-accent-teal)]"
                  : "border-[var(--cg-border)] bg-[var(--cg-bg-panel)] text-[var(--cg-text-secondary)] hover:text-[var(--cg-text-primary)]"
              )}
            >
              {cond}
            </button>
          ))}
        </div>
      </div>

      {/* Observational Disclaimer */}
      <div className="flex items-start gap-3 rounded-xl border border-[#FBBF24]/30 bg-[#FBBF24]/10 p-4 text-xs text-[var(--cg-text-primary)]">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--cg-warning)]" />
        <div>
          <strong className="text-[var(--cg-warning)]">
            Academic & Observational Disclaimer:
          </strong>{" "}
          <span className="text-[var(--cg-text-secondary)]">
            {data?.disclaimer ||
              "Synthetic observational outcomes based on consecutive visit transitions where biomarker values decreased. Does not establish medical causality, clinical efficacy, or individual treatment recommendations."}
          </span>
        </div>
      </div>

      {error ? (
        <ErrorState
          title="Could not load medication analytics"
          message={error}
          onRetry={() => loadAnalytics(selectedCondition)}
        />
      ) : loading && !data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-80 rounded-xl" />
        </div>
      ) : data ? (
        <>
          {/* KPI Summary */}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Panel className="p-4">
              <span className="text-[11px] text-[var(--cg-text-secondary)]">
                Analyzed Condition
              </span>
              <div className="mt-1.5 text-base font-semibold text-[var(--cg-text-primary)]">
                {data.condition}
              </div>
            </Panel>

            <Panel className="p-4">
              <span className="text-[11px] text-[var(--cg-text-secondary)]">
                Tracked Biomarker
              </span>
              <div className="mt-1.5 flex items-center gap-1.5 text-base font-semibold text-[var(--cg-accent-teal)]">
                <FlaskConical className="h-4 w-4" />
                <span>
                  {data.biomarker || "N/A"} ({data.unit || ""})
                </span>
              </div>
            </Panel>

            <Panel className="p-4">
              <span className="text-[11px] text-[var(--cg-text-secondary)]">
                Unique Patients
              </span>
              <div className="mt-1.5 flex items-center gap-2 font-mono text-2xl font-semibold tabular-nums">
                <Users className="h-4 w-4 text-[var(--cg-accent-sky)]" />
                {data.total_unique_patients}
              </div>
            </Panel>

            <Panel className="p-4">
              <span className="text-[11px] text-[var(--cg-text-secondary)]">
                Eligible Transitions
              </span>
              <div className="mt-1.5 font-mono text-2xl font-semibold tabular-nums">
                {data.total_eligible_transitions}
              </div>
            </Panel>

            <Panel className="col-span-2 lg:col-span-1 p-4">
              <span className="text-[11px] text-[var(--cg-text-secondary)]">
                Highest Observed Improvement Rate
              </span>
              <div className="mt-1.5 text-sm font-semibold text-[var(--cg-accent-teal)]">
                {highestObserved
                  ? `${highestObserved.medication} (${highestObserved.betterment_rate_pct.toFixed(
                      1
                    )}%, n=${highestObserved.eligible_transitions})`
                  : "N/A"}
              </div>
            </Panel>
          </div>

          {/* Comparison Charts */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Panel>
              <PanelHeader>
                <div>
                  <PanelTitle>Observed Improvement Rate (%)</PanelTitle>
                  <PanelDescription>
                    Share of transitions where {data.biomarker} decreased
                  </PanelDescription>
                </div>
              </PanelHeader>
              <PanelContent>
                <div className="h-[260px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={sortedMedications}
                      layout="vertical"
                      margin={{ top: 6, right: 20, left: 24, bottom: 0 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="var(--cg-chart-grid)"
                        horizontal={false}
                      />
                      <XAxis
                        type="number"
                        domain={[0, 100]}
                        tick={{ fill: "#94A3B8", fontSize: 11 }}
                        unit="%"
                      />
                      <YAxis
                        dataKey="medication"
                        type="category"
                        width={100}
                        tick={{ fill: "#F1F5F9", fontSize: 11 }}
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
                        dataKey="betterment_rate_pct"
                        name="Observed Improvement %"
                        fill="#2DD4BF"
                        radius={[0, 6, 6, 0]}
                        isAnimationActive={false}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </PanelContent>
            </Panel>

            <Panel>
              <PanelHeader>
                <div>
                  <PanelTitle>Transition Outcome Breakdown</PanelTitle>
                  <PanelDescription>
                    Improved, unchanged, and worsened transition counts (not unique patients)
                  </PanelDescription>
                </div>
              </PanelHeader>
              <PanelContent>
                <div className="h-[260px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={sortedMedications}
                      layout="vertical"
                      margin={{ top: 6, right: 20, left: 24, bottom: 0 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="var(--cg-chart-grid)"
                        horizontal={false}
                      />
                      <XAxis
                        type="number"
                        allowDecimals={false}
                        tick={{ fill: "#94A3B8", fontSize: 11 }}
                      />
                      <YAxis
                        dataKey="medication"
                        type="category"
                        width={100}
                        tick={{ fill: "#F1F5F9", fontSize: 11 }}
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
                      <Legend wrapperStyle={{ fontSize: "11px" }} />
                      <Bar
                        dataKey="improved_transitions"
                        name="Improved"
                        stackId="a"
                        fill="#34D399"
                        isAnimationActive={false}
                      />
                      <Bar
                        dataKey="unchanged_transitions"
                        name="Unchanged"
                        stackId="a"
                        fill="#94A3B8"
                        isAnimationActive={false}
                      />
                      <Bar
                        dataKey="worsened_transitions"
                        name="Worsened"
                        stackId="a"
                        fill="#F87171"
                        radius={[0, 6, 6, 0]}
                        isAnimationActive={false}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </PanelContent>
            </Panel>
          </div>

          {/* Sortable Outcomes Table */}
          <Panel>
            <PanelHeader>
              <div>
                <PanelTitle>Comparative Transition Statistics</PanelTitle>
                <PanelDescription>
                  Click column headers to sort; expand any medication to audit underlying visit transitions
                </PanelDescription>
              </div>
            </PanelHeader>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[var(--cg-border)] text-[11px] font-medium uppercase tracking-wider text-[var(--cg-text-muted)]">
                    {(
                      [
                        ["medication", "Medication"],
                        ["unique_patient_count", "Unique Patients"],
                        ["eligible_transitions", "Transitions (n)"],
                        ["improved_transitions", "Improved"],
                        ["worsened_transitions", "Worsened"],
                        ["betterment_rate_pct", "Observed Rate"],
                      ] as Array<[SortKey, string]>
                    ).map(([key, label]) => (
                      <th key={key} className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => handleSort(key)}
                          className="inline-flex items-center gap-1 hover:text-[var(--cg-text-primary)] cursor-pointer"
                        >
                          <span>{label}</span>
                          <ArrowUpDown className="h-3 w-3" />
                        </button>
                      </th>
                    ))}
                    <th className="px-4 py-3 text-right">Evidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--cg-border)]">
                  {sortedMedications.map((m) => {
                    const isOpen = !!expandedMed[m.medication];
                    return (
                      <React.Fragment key={m.medication}>
                        <tr className="hover:bg-[var(--cg-bg-elevated)]/60">
                          <td className="px-4 py-3 font-semibold text-[var(--cg-text-primary)]">
                            {m.medication}
                          </td>
                          <td className="px-4 py-3 font-mono tabular-nums">
                            {m.unique_patient_count}
                          </td>
                          <td className="px-4 py-3 font-mono tabular-nums">
                            {m.eligible_transitions}
                          </td>
                          <td className="px-4 py-3 font-mono tabular-nums text-[var(--cg-success)]">
                            {m.improved_transitions}
                          </td>
                          <td className="px-4 py-3 font-mono tabular-nums text-[var(--cg-error)]">
                            {m.worsened_transitions}
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant="teal" className="font-mono tabular-nums">
                              {m.betterment_rate_pct.toFixed(1)}%
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              type="button"
                              onClick={() =>
                                setExpandedMed((prev) => ({
                                  ...prev,
                                  [m.medication]: !prev[m.medication],
                                }))
                              }
                              className="inline-flex items-center gap-1 rounded border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-2.5 py-1 text-[11px] text-[var(--cg-text-secondary)] hover:text-[var(--cg-text-primary)] cursor-pointer"
                            >
                              <span>Inspect</span>
                              {isOpen ? (
                                <ChevronUp className="h-3 w-3" />
                              ) : (
                                <ChevronDown className="h-3 w-3" />
                              )}
                            </button>
                          </td>
                        </tr>
                        {isOpen && (
                          <tr className="bg-[var(--cg-bg-elevated)]/40">
                            <td colSpan={7} className="px-4 py-3">
                              <div className="space-y-2">
                                <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                                  Sample Pairwise Visit Transitions ({m.medication})
                                </div>
                                {m.evidence_sample.length === 0 ? (
                                  <p className="text-xs text-[var(--cg-text-muted)]">
                                    No sample records available.
                                  </p>
                                ) : (
                                  <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                                    {m.evidence_sample.map((ev) => (
                                      <div
                                        key={`${ev.prescription_id}-${ev.v1_id}`}
                                        className="rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] p-3 text-xs space-y-1"
                                      >
                                        <div className="flex items-center justify-between">
                                          <button
                                            type="button"
                                            onClick={() =>
                                              openPatient(ev.patient_id, "followups")
                                            }
                                            className="font-mono font-semibold text-[var(--cg-accent-teal)] hover:underline cursor-pointer"
                                          >
                                            {ev.patient_id}
                                          </button>
                                          <Badge
                                            variant={
                                              ev.direction === "improved"
                                                ? "success"
                                                : ev.direction === "worsened"
                                                ? "error"
                                                : "neutral"
                                            }
                                          >
                                            {ev.direction}
                                          </Badge>
                                        </div>
                                        <div className="font-mono text-[11px] text-[var(--cg-text-secondary)]">
                                          <button
                                            type="button"
                                            onClick={() =>
                                              openGraph(ev.patient_id, ev.v1_id)
                                            }
                                            className="text-[var(--cg-accent-sky)] hover:underline cursor-pointer"
                                          >
                                            {ev.v1_id}
                                          </button>{" "}
                                          ({ev.v1_value} {m.unit}) →{" "}
                                          <button
                                            type="button"
                                            onClick={() =>
                                              openGraph(ev.patient_id, ev.v2_id)
                                            }
                                            className="text-[var(--cg-accent-sky)] hover:underline cursor-pointer"
                                          >
                                            {ev.v2_id}
                                          </button>{" "}
                                          ({ev.v2_value} {m.unit})
                                        </div>
                                        <div className="flex justify-between font-mono text-[11px]">
                                          <span className="text-[var(--cg-text-muted)]">
                                            Rx: {ev.prescription_id}
                                          </span>
                                          <span className="font-semibold text-[var(--cg-text-primary)]">
                                            Δ {ev.delta > 0 ? "+" : ""}
                                            {ev.delta.toFixed(2)} {m.unit}
                                          </span>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      ) : null}
    </div>
  );
}
