"use client";

import React, { useEffect, useState } from "react";
import { Activity, ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import {
  Panel,
  PanelContent,
  PanelDescription,
  PanelHeader,
  PanelTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-error-state";
import { cn, formatDateShort } from "@/lib/utils";
import type { LabTrendGroup } from "@/types/clinical";

export function LabTrendsPanel({
  trends,
  onSelectVisit,
}: {
  trends: LabTrendGroup[];
  onSelectVisit?: (visitId: string) => void;
}) {
  const [selectedKey, setSelectedKey] = useState<string>("");
  const [chartType, setChartType] = useState<"area" | "line">("area");

  useEffect(() => {
    if (trends.length > 0) {
      setSelectedKey(`${trends[0].biomarker}::${trends[0].unit}`);
    } else {
      setSelectedKey("");
    }
  }, [trends]);

  if (!trends || trends.length === 0) {
    return (
      <EmptyState
        title="No laboratory measurements recorded"
        description="This patient does not have any LabTest observations linked to their visits in the Neo4j graph."
      />
    );
  }

  const activeGroup =
    trends.find((g) => `${g.biomarker}::${g.unit}` === selectedKey) || trends[0];

  const firstObs = activeGroup.observations[0];
  const lastObs = activeGroup.observations[activeGroup.observations.length - 1];
  const isSingleObs = activeGroup.observation_count < 2;

  const pctDisplay =
    activeGroup.percentage_change !== null &&
    activeGroup.percentage_change !== undefined
      ? `${activeGroup.percentage_change > 0 ? "+" : ""}${activeGroup.percentage_change.toFixed(1)}%`
      : "N/A";

  const absDisplay = isSingleObs
    ? "N/A"
    : `${activeGroup.absolute_change > 0 ? "+" : ""}${activeGroup.absolute_change.toFixed(2)} ${activeGroup.unit}`;

  const chartData = activeGroup.observations.map((obs) => ({
    ...obs,
    dateLabel: formatDateShort(obs.visit_date),
  }));

  return (
    <div className="space-y-4">
      {/* Biomarker Selector & Chart Style Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {trends.map((g) => {
            const key = `${g.biomarker}::${g.unit}`;
            const active =
              key === `${activeGroup.biomarker}::${activeGroup.unit}`;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setSelectedKey(key)}
                className={cn(
                  "inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer",
                  active
                    ? "border-[#2DD4BF]/40 bg-[#2DD4BF]/10 text-[var(--cg-accent-teal)]"
                    : "border-[var(--cg-border)] bg-[var(--cg-bg-panel)] text-[var(--cg-text-secondary)] hover:text-[var(--cg-text-primary)]"
                )}
              >
                <Activity className="h-3.5 w-3.5" />
                <span>{g.biomarker}</span>
                <span className="font-mono text-[10px] opacity-80">
                  ({g.unit}) • {g.observation_count}
                </span>
              </button>
            );
          })}
        </div>

        <div className="inline-flex rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] p-0.5 text-xs">
          <button
            type="button"
            onClick={() => setChartType("area")}
            className={cn(
              "rounded-md px-2.5 py-1 font-medium cursor-pointer",
              chartType === "area"
                ? "bg-[var(--cg-bg-elevated)] text-[var(--cg-accent-teal)]"
                : "text-[var(--cg-text-secondary)]"
            )}
          >
            Area
          </button>
          <button
            type="button"
            onClick={() => setChartType("line")}
            className={cn(
              "rounded-md px-2.5 py-1 font-medium cursor-pointer",
              chartType === "line"
                ? "bg-[var(--cg-bg-elevated)] text-[var(--cg-accent-teal)]"
                : "text-[var(--cg-text-secondary)]"
            )}
          >
            Line
          </button>
        </div>
      </div>

      {/* Biomarker KPI Summary */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Panel className="p-4">
          <span className="text-[11px] font-medium text-[var(--cg-text-secondary)]">
            Initial Measurement
          </span>
          <div className="mt-1.5 font-mono text-xl font-semibold tabular-nums text-[var(--cg-text-primary)]">
            {activeGroup.initial_value}{" "}
            <span className="text-xs font-normal text-[var(--cg-text-secondary)]">
              {activeGroup.unit}
            </span>
          </div>
          <p className="mt-1 text-[11px] text-[var(--cg-text-muted)]">
            {firstObs ? `${formatDateShort(firstObs.visit_date)} (${firstObs.visit_id})` : "—"}
          </p>
        </Panel>

        <Panel className="p-4">
          <span className="text-[11px] font-medium text-[var(--cg-text-secondary)]">
            Latest Measurement
          </span>
          <div className="mt-1.5 font-mono text-xl font-semibold tabular-nums text-[var(--cg-text-primary)]">
            {activeGroup.latest_value}{" "}
            <span className="text-xs font-normal text-[var(--cg-text-secondary)]">
              {activeGroup.unit}
            </span>
          </div>
          <p className="mt-1 text-[11px] text-[var(--cg-text-muted)]">
            {lastObs ? `${formatDateShort(lastObs.visit_date)} (${lastObs.visit_id})` : "—"}
          </p>
        </Panel>

        <Panel className="p-4">
          <span className="text-[11px] font-medium text-[var(--cg-text-secondary)]">
            Absolute Change
          </span>
          <div className="mt-1.5 font-mono text-xl font-semibold tabular-nums text-[var(--cg-text-primary)]">
            {absDisplay}
          </div>
          <p className="mt-1 text-[11px] text-[var(--cg-text-muted)]">
            Across {activeGroup.observation_count} observation(s)
          </p>
        </Panel>

        <Panel className="p-4">
          <span className="text-[11px] font-medium text-[var(--cg-text-secondary)]">
            Relative Change
          </span>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="font-mono text-xl font-semibold tabular-nums text-[var(--cg-text-primary)]">
              {isSingleObs ? "Single" : pctDisplay}
            </span>
            <Badge
              variant={
                activeGroup.direction === "decreased"
                  ? "teal"
                  : activeGroup.direction === "increased"
                  ? "sky"
                  : "neutral"
              }
            >
              {activeGroup.direction === "decreased" && (
                <ArrowDownRight className="h-3 w-3" />
              )}
              {activeGroup.direction === "increased" && (
                <ArrowUpRight className="h-3 w-3" />
              )}
              {activeGroup.direction === "unchanged" && (
                <Minus className="h-3 w-3" />
              )}
              {activeGroup.direction.replace("_", " ")}
            </Badge>
          </div>
          <p className="mt-1 text-[11px] text-[var(--cg-text-muted)]">
            Observed direction (non-diagnostic)
          </p>
        </Panel>
      </div>

      {/* Trajectory Chart */}
      <Panel>
        <PanelHeader>
          <div>
            <PanelTitle>
              {activeGroup.biomarker} Trajectory ({activeGroup.unit})
            </PanelTitle>
            <PanelDescription>
              Recorded values plotted chronologically by encounter date
            </PanelDescription>
          </div>
        </PanelHeader>
        <PanelContent>
          {isSingleObs ? (
            <div className="rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-5 text-xs text-[var(--cg-text-secondary)]">
              Only a single observation ({activeGroup.initial_value} {activeGroup.unit} on{" "}
              {formatDateShort(firstObs?.visit_date)}) is available for{" "}
              <strong className="text-[var(--cg-text-primary)]">
                {activeGroup.biomarker}
              </strong>
              . At least two observations with matching units are required to plot a longitudinal trajectory.
            </div>
          ) : (
            <div className="h-[260px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                {chartType === "area" ? (
                  <AreaChart
                    data={chartData}
                    margin={{ top: 10, right: 16, left: -8, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="cgLabArea" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2DD4BF" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#2DD4BF" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="var(--cg-chart-grid)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="dateLabel"
                      tick={{ fill: "#94A3B8", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      domain={["auto", "auto"]}
                      tick={{ fill: "#94A3B8", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const pt = payload[0].payload;
                        return (
                          <div className="rounded-lg border border-[#243041] bg-[#101722] p-3 text-xs text-[#F1F5F9] shadow-lg">
                            <div className="font-semibold text-[#2DD4BF]">
                              {activeGroup.biomarker}: {pt.value} {pt.unit}
                            </div>
                            <div className="mt-1 font-mono text-[11px] text-[#94A3B8]">
                              Visit: {pt.visit_id} • Lab: {pt.test_id}
                            </div>
                            <div className="text-[11px] text-[#94A3B8]">
                              Date: {formatDateShort(pt.visit_date)}
                            </div>
                          </div>
                        );
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#2DD4BF"
                      strokeWidth={2.5}
                      fill="url(#cgLabArea)"
                      isAnimationActive={false}
                      dot={{ r: 4, fill: "#080C12", stroke: "#2DD4BF", strokeWidth: 2 }}
                      activeDot={{ r: 6, fill: "#2DD4BF" }}
                    />
                  </AreaChart>
                ) : (
                  <LineChart
                    data={chartData}
                    margin={{ top: 10, right: 16, left: -8, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="var(--cg-chart-grid)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="dateLabel"
                      tick={{ fill: "#94A3B8", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      domain={["auto", "auto"]}
                      tick={{ fill: "#94A3B8", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const pt = payload[0].payload;
                        return (
                          <div className="rounded-lg border border-[#243041] bg-[#101722] p-3 text-xs text-[#F1F5F9] shadow-lg">
                            <div className="font-semibold text-[#38BDF8]">
                              {activeGroup.biomarker}: {pt.value} {pt.unit}
                            </div>
                            <div className="mt-1 font-mono text-[11px] text-[#94A3B8]">
                              Visit: {pt.visit_id} • Lab: {pt.test_id}
                            </div>
                            <div className="text-[11px] text-[#94A3B8]">
                              Date: {formatDateShort(pt.visit_date)}
                            </div>
                          </div>
                        );
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#38BDF8"
                      strokeWidth={2.5}
                      isAnimationActive={false}
                      dot={{ r: 4, fill: "#080C12", stroke: "#38BDF8", strokeWidth: 2 }}
                      activeDot={{ r: 6, fill: "#38BDF8" }}
                    />
                  </LineChart>
                )}
              </ResponsiveContainer>
            </div>
          )}
        </PanelContent>
      </Panel>

      {/* Lab Evidence Table */}
      <Panel>
        <PanelHeader>
          <div>
            <PanelTitle>Laboratory Record Evidence</PanelTitle>
            <PanelDescription>
              Direct Neo4j LabTest observations linked via [:HAD_TEST]
            </PanelDescription>
          </div>
        </PanelHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[var(--cg-border)] text-[11px] font-medium uppercase tracking-wider text-[var(--cg-text-muted)]">
                <th className="px-4 py-2.5">Test ID</th>
                <th className="px-4 py-2.5">Visit ID</th>
                <th className="px-4 py-2.5">Date</th>
                <th className="px-4 py-2.5 text-right">Measurement</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--cg-border)]">
              {activeGroup.observations.map((obs) => (
                <tr key={obs.test_id} className="hover:bg-[var(--cg-bg-elevated)]/60">
                  <td className="px-4 py-2.5 font-mono text-[var(--cg-accent-teal)]">
                    {obs.test_id}
                  </td>
                  <td className="px-4 py-2.5">
                    {onSelectVisit ? (
                      <button
                        type="button"
                        onClick={() => onSelectVisit(obs.visit_id)}
                        className="font-mono font-semibold text-[var(--cg-accent-sky)] hover:underline cursor-pointer"
                      >
                        {obs.visit_id}
                      </button>
                    ) : (
                      <span className="font-mono text-[var(--cg-accent-sky)]">
                        {obs.visit_id}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-mono tabular-nums text-[var(--cg-text-secondary)]">
                    {formatDateShort(obs.visit_date)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono font-semibold tabular-nums text-[var(--cg-text-primary)]">
                    {obs.value} {obs.unit}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
