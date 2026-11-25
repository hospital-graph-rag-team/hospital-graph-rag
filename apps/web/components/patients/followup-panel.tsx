"use client";

import React from "react";
import { ArrowRight, CalendarClock, FlaskConical, Pill } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Panel,
  PanelContent,
  PanelDescription,
  PanelHeader,
  PanelTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-error-state";
import { formatDateShort } from "@/lib/utils";
import type { FollowupComparisonItem } from "@/types/clinical";

export function FollowupComparisonPanel({
  followups,
  onInspectVisitGraph,
}: {
  followups: FollowupComparisonItem[];
  onInspectVisitGraph?: (visitId: string) => void;
}) {
  if (!followups || followups.length === 0) {
    return (
      <EmptyState
        title="No consecutive follow-up transitions"
        description="This patient has fewer than two chronologically linked visits ([:FOLLOWED_BY]) in the knowledge graph."
      />
    );
  }

  return (
    <div className="space-y-4">
      {followups.map((pair, idx) => (
        <Panel key={`${pair.previous_visit.visit_id}-${pair.followup_visit.visit_id}`}>
          <PanelHeader>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="teal" className="font-mono">
                Transition #{idx + 1}
              </Badge>
              <PanelTitle className="flex items-center gap-1.5 font-mono">
                <button
                  type="button"
                  onClick={() => onInspectVisitGraph?.(pair.previous_visit.visit_id)}
                  className="text-[var(--cg-accent-sky)] hover:underline cursor-pointer"
                >
                  {pair.previous_visit.visit_id}
                </button>
                <ArrowRight className="h-3.5 w-3.5 text-[var(--cg-text-muted)]" />
                <button
                  type="button"
                  onClick={() => onInspectVisitGraph?.(pair.followup_visit.visit_id)}
                  className="text-[var(--cg-accent-sky)] hover:underline cursor-pointer"
                >
                  {pair.followup_visit.visit_id}
                </button>
              </PanelTitle>
              <PanelDescription>
                {formatDateShort(pair.previous_visit.visit_date)} to{" "}
                {formatDateShort(pair.followup_visit.visit_date)}
              </PanelDescription>
            </div>
            <Badge variant="neutral" className="font-mono tabular-nums">
              <CalendarClock className="h-3 w-3" />
              {pair.days_between} days elapsed
            </Badge>
          </PanelHeader>

          <PanelContent className="space-y-4">
            {/* Encounter Comparison Cards */}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {[
                { label: "Previous Encounter", v: pair.previous_visit },
                { label: "Follow-up Encounter", v: pair.followup_visit },
              ].map(({ label, v }) => (
                <div
                  key={v.visit_id}
                  className="rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-3.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                      {label}
                    </span>
                    <Badge variant="neutral">{v.admission_type || "Standard"}</Badge>
                  </div>
                  <div className="mt-1.5 font-mono text-sm font-semibold text-[var(--cg-text-primary)]">
                    {v.visit_id}{" "}
                    <span className="text-xs font-normal text-[var(--cg-text-secondary)]">
                      ({formatDateShort(v.visit_date)})
                    </span>
                  </div>
                  {v.doctor && (
                    <p className="mt-1 text-[var(--cg-text-secondary)]">
                      Physician: <span className="text-[var(--cg-text-primary)]">{v.doctor}</span>
                    </p>
                  )}

                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                    {v.diagnoses.map((d, i) => (
                      <Badge key={`${d.diagnosis_id || i}`} variant="warning">
                        {d.condition} ({d.diagnosis_id})
                      </Badge>
                    ))}
                    {v.prescriptions.map((rx, i) => (
                      <Badge key={`${rx.prescription_id || i}`} variant="violet">
                        <Pill className="h-3 w-3" />
                        {rx.medication_name} ({rx.prescription_id})
                      </Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Matched Biomarker Deltas */}
            {pair.lab_comparisons.length > 0 ? (
              <div className="overflow-x-auto rounded-lg border border-[var(--cg-border)]">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] text-[11px] font-medium uppercase tracking-wider text-[var(--cg-text-muted)]">
                      <th className="px-3.5 py-2">Biomarker</th>
                      <th className="px-3.5 py-2">Baseline</th>
                      <th className="px-3.5 py-2">Follow-up</th>
                      <th className="px-3.5 py-2">Delta</th>
                      <th className="px-3.5 py-2 text-right">Direction</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--cg-border)]">
                    {pair.lab_comparisons.map((lc) => (
                      <tr key={`${lc.v1_test_id}-${lc.v2_test_id}`}>
                        <td className="px-3.5 py-2.5 font-medium text-[var(--cg-text-primary)]">
                          <span className="inline-flex items-center gap-1.5">
                            <FlaskConical className="h-3.5 w-3.5 text-[var(--cg-accent-teal)]" />
                            {lc.biomarker}
                          </span>
                        </td>
                        <td className="px-3.5 py-2.5 font-mono tabular-nums text-[var(--cg-text-secondary)]">
                          {lc.v1_value} {lc.unit}{" "}
                          <span className="text-[10px] text-[var(--cg-text-muted)]">
                            ({lc.v1_test_id})
                          </span>
                        </td>
                        <td className="px-3.5 py-2.5 font-mono tabular-nums text-[var(--cg-text-primary)]">
                          {lc.v2_value} {lc.unit}{" "}
                          <span className="text-[10px] text-[var(--cg-text-muted)]">
                            ({lc.v2_test_id})
                          </span>
                        </td>
                        <td className="px-3.5 py-2.5 font-mono font-semibold tabular-nums text-[var(--cg-text-primary)]">
                          {lc.absolute_change > 0 ? "+" : ""}
                          {lc.absolute_change.toFixed(2)} {lc.unit}
                          {lc.percentage_change !== null &&
                            lc.percentage_change !== undefined && (
                              <span className="ml-1 text-[11px] font-normal text-[var(--cg-text-secondary)]">
                                ({lc.percentage_change > 0 ? "+" : ""}
                                {lc.percentage_change.toFixed(1)}%)
                              </span>
                            )}
                        </td>
                        <td className="px-3.5 py-2.5 text-right">
                          <Badge
                            variant={
                              lc.direction === "decreased"
                                ? "teal"
                                : lc.direction === "increased"
                                ? "sky"
                                : "neutral"
                            }
                          >
                            {lc.direction}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-[var(--cg-text-muted)]">
                No matching biomarkers with compatible units between these two encounters.
              </p>
            )}
          </PanelContent>
        </Panel>
      ))}
    </div>
  );
}
