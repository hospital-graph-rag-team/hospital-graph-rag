"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Network, Users, X } from "lucide-react";
import { CytoscapeKnowledgeGraph } from "@/components/graph/cytoscape-graph";
import { useClinical } from "@/components/providers/clinical-provider";
import { usePatientRouteSync } from "@/hooks/use-patient-route-sync";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, PanelContent } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/empty-error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { KnowledgeGraphResponse } from "@/types/clinical";

export function KnowledgeGraphView() {
  const searchParams = useSearchParams();
  const {
    patients,
    openPatient,
    askAssistant,
  } = useClinical();
  const {
    selectedPatientId,
    selectPatientInRoute,
    clearPatientInRoute,
  } = usePatientRouteSync();

  const urlScope = searchParams.get("scope");
  const urlVisitId = searchParams.get("visitId");

  const [scope, setScope] = useState<"patient" | "cohort">(
    urlScope === "cohort" ? "cohort" : "patient"
  );
  const [cohortCondition, setCohortCondition] = useState<string>("all");
  const [cohortLimit, setCohortLimit] = useState<number>(6);
  const [graphData, setGraphData] = useState<KnowledgeGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const requestSeqRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (urlScope === "cohort" || urlScope === "patient") {
      setScope(urlScope);
    }
  }, [urlScope]);

  const loadGraph = useCallback(async () => {
    if (scope === "patient" && !selectedPatientId) {
      requestSeqRef.current += 1;
      abortControllerRef.current?.abort();
      setGraphData(null);
      setError(null);
      setLoading(false);
      return;
    }

    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const reqId = ++requestSeqRef.current;

    setLoading(true);
    setError(null);
    try {
      const res =
        scope === "patient" && selectedPatientId
          ? await apiClient.getPatientGraph(selectedPatientId, controller.signal)
          : await apiClient.getCohortGraph(
              cohortCondition === "all" ? undefined : cohortCondition,
              cohortLimit,
              controller.signal
            );
      if (controller.signal.aborted || reqId !== requestSeqRef.current) {
        return;
      }
      setGraphData(res);
    } catch (err: unknown) {
      if (
        (err instanceof Error && err.name === "AbortError") ||
        controller.signal.aborted ||
        reqId !== requestSeqRef.current
      ) {
        return;
      }
      setError(
        err instanceof Error ? err.message : "Failed to load knowledge graph."
      );
    } finally {
      if (!controller.signal.aborted && reqId === requestSeqRef.current) {
        setLoading(false);
      }
    }
  }, [scope, selectedPatientId, cohortCondition, cohortLimit]);

  useEffect(() => {
    loadGraph();
    return () => {
      abortControllerRef.current?.abort();
    };
  }, [loadGraph]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-[var(--cg-text-primary)]">
              Interactive Knowledge Graph
            </h1>
            <Badge variant="sky">Cytoscape.js</Badge>
          </div>
          <p className="text-xs text-[var(--cg-text-secondary)]">
            Explore real Neo4j clinical topology with shared Diagnosis, Medication, and Doctor entities.
          </p>
        </div>
      </div>

      {/* Scope & Target Selector */}
      <Panel>
        <PanelContent className="flex flex-wrap items-center justify-between gap-3 py-3">
          <div className="inline-flex rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-1 text-xs">
            <button
              type="button"
              onClick={() => setScope("patient")}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium cursor-pointer",
                scope === "patient"
                  ? "bg-[var(--cg-bg-panel)] text-[var(--cg-accent-teal)] shadow-sm"
                  : "text-[var(--cg-text-secondary)]"
              )}
            >
              <Network className="h-3.5 w-3.5" />
              Patient Subgraph
            </button>
            <button
              type="button"
              onClick={() => setScope("cohort")}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium cursor-pointer",
                scope === "cohort"
                  ? "bg-[var(--cg-bg-panel)] text-[var(--cg-accent-teal)] shadow-sm"
                  : "text-[var(--cg-text-secondary)]"
              )}
            >
              <Users className="h-3.5 w-3.5" />
              Multi-Patient Cohort
            </button>
          </div>

          {scope === "patient" ? (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-[var(--cg-text-secondary)]">Patient:</span>
              <select
                aria-label="Select patient for knowledge graph"
                value={selectedPatientId || ""}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val) {
                    selectPatientInRoute(val, { extraParams: { scope: "patient" } });
                  } else {
                    clearPatientInRoute({ extraParams: { scope: "patient" } });
                  }
                }}
                className="h-8 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-2.5 text-xs text-[var(--cg-text-primary)]"
              >
                <option value="">Select a patient...</option>
                {patients.map((p) => (
                  <option key={p.patient_id} value={p.patient_id}>
                    {p.patient_id} — {p.name} ({p.visit_count} visits)
                  </option>
                ))}
              </select>
              {selectedPatientId && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    clearPatientInRoute({ extraParams: { scope: "patient" } })
                  }
                  aria-label="Clear selected patient in graph"
                >
                  <X className="h-3.5 w-3.5" />
                  Clear
                </Button>
              )}
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <select
                aria-label="Filter cohort graph by condition"
                value={cohortCondition}
                onChange={(e) => setCohortCondition(e.target.value)}
                className="h-8 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-2.5 text-xs text-[var(--cg-text-primary)]"
              >
                <option value="all">All Conditions</option>
                <option value="Type 2 Diabetes">Type 2 Diabetes</option>
                <option value="Hypertension">Hypertension</option>
                <option value="Hyperlipidemia">Hyperlipidemia</option>
              </select>
              <select
                aria-label="Cohort patient count"
                value={cohortLimit}
                onChange={(e) => setCohortLimit(Number(e.target.value))}
                className="h-8 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-2.5 text-xs text-[var(--cg-text-primary)]"
              >
                <option value={4}>4 Patients</option>
                <option value={6}>6 Patients</option>
                <option value={8}>8 Patients</option>
                <option value={12}>12 Patients</option>
              </select>
            </div>
          )}
        </PanelContent>
      </Panel>

      {scope === "patient" && !selectedPatientId ? (
        <EmptyState
          title="No patient selected for subgraph view"
          description="Select a patient from the dropdown above or switch to Multi-Patient Cohort to explore shared hospital entities."
          action={
            <Button variant="outline" size="sm" onClick={() => setScope("cohort")}>
              <Users className="h-3.5 w-3.5" />
              View Multi-Patient Cohort
            </Button>
          }
        />
      ) : error ? (
        <ErrorState
          title="Could not load knowledge graph"
          message={error}
          onRetry={loadGraph}
        />
      ) : loading || !graphData ? (
        <Skeleton className="h-[620px] w-full rounded-xl" />
      ) : (
        <CytoscapeKnowledgeGraph
          graphData={graphData}
          highlightEntityId={urlVisitId}
          onSelectPatientNode={(pid) => openPatient(pid, "overview")}
          onAskAboutNode={(prompt, pid) => askAssistant(prompt, pid)}
        />
      )}
    </div>
  );
}
