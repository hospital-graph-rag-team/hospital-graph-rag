"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type cytoscape from "cytoscape";
import {
  Download,
  Eye,
  EyeOff,
  Maximize2,
  Minimize2,
  RotateCcw,
  Search,
  Sparkles,
  ZoomIn,
  ZoomOut,
  Focus,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel, PanelContent, PanelHeader, PanelTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { EdgeType, GraphEdge, GraphNode, KnowledgeGraphResponse, NodeType } from "@/types/clinical";

const NODE_META: Record<
  NodeType,
  { color: string; shape: string; label: string }
> = {
  Patient: { color: "#2DD4BF", shape: "round-rectangle", label: "Patient" },
  Visit: { color: "#38BDF8", shape: "ellipse", label: "Visit" },
  Doctor: { color: "#818CF8", shape: "hexagon", label: "Doctor" },
  Diagnosis: { color: "#FBBF24", shape: "diamond", label: "Diagnosis" },
  Medication: { color: "#34D399", shape: "round-tag", label: "Medication" },
  LabTest: { color: "#F472B6", shape: "ellipse", label: "LabTest" },
};

const EDGE_META: Record<EdgeType, { color: string; label: string }> = {
  HAD_VISIT: { color: "#2DD4BF", label: "HAD_VISIT" },
  FOLLOWED_BY: { color: "#38BDF8", label: "FOLLOWED_BY" },
  ATTENDED_BY: { color: "#818CF8", label: "ATTENDED_BY" },
  DIAGNOSED_WITH: { color: "#FBBF24", label: "DIAGNOSED_WITH" },
  PRESCRIBED: { color: "#34D399", label: "PRESCRIBED" },
  HAD_TEST: { color: "#F472B6", label: "HAD_TEST" },
};

type LayoutMode = "cose" | "breadthfirst" | "concentric" | "circle" | "grid";

const LAYOUT_OPTIONS: Array<{ id: LayoutMode; label: string }> = [
  { id: "breadthfirst", label: "Hierarchy" },
  { id: "cose", label: "Force-Directed" },
  { id: "concentric", label: "Concentric" },
  { id: "circle", label: "Circle" },
  { id: "grid", label: "Grid" },
];

type SelectedElement =
  | { kind: "node"; node: GraphNode; degree: number }
  | { kind: "edge"; edge: GraphEdge; sourceLabel: string; targetLabel: string }
  | null;

export function CytoscapeKnowledgeGraph({
  graphData,
  highlightEntityId,
  compact = false,
  onSelectPatientNode,
  onAskAboutNode,
}: {
  graphData: KnowledgeGraphResponse;
  highlightEntityId?: string | null;
  compact?: boolean;
  onSelectPatientNode?: (patientId: string) => void;
  onAskAboutNode?: (prompt: string, patientId?: string | null) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  const [layoutMode, setLayoutMode] = useState<LayoutMode>(
    graphData.scope === "cohort" ? "cose" : "breadthfirst"
  );
  const [showEdgeLabels, setShowEdgeLabels] = useState(
    graphData.scope === "patient"
  );
  const [nodeSearch, setNodeSearch] = useState("");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selected, setSelected] = useState<SelectedElement>(null);

  const [activeNodeTypes, setActiveNodeTypes] = useState<Record<NodeType, boolean>>({
    Patient: true,
    Visit: true,
    Doctor: true,
    Diagnosis: true,
    Medication: true,
    LabTest: true,
  });

  const [activeEdgeTypes, setActiveEdgeTypes] = useState<Record<EdgeType, boolean>>({
    HAD_VISIT: true,
    FOLLOWED_BY: true,
    ATTENDED_BY: true,
    DIAGNOSED_WITH: true,
    PRESCRIBED: true,
    HAD_TEST: true,
  });

  const nodeMap = useMemo(() => {
    const m = new Map<string, GraphNode>();
    graphData.nodes.forEach((n) => m.set(n.id, n));
    return m;
  }, [graphData.nodes]);

  const edgeMap = useMemo(() => {
    const m = new Map<string, GraphEdge>();
    graphData.edges.forEach((e) => m.set(e.id, e));
    return m;
  }, [graphData.edges]);

  const filteredElements = useMemo(() => {
    const visibleNodeIds = new Set(
      graphData.nodes
        .filter((n) => activeNodeTypes[n.type])
        .map((n) => n.id)
    );
    const nodes = graphData.nodes
      .filter((n) => visibleNodeIds.has(n.id))
      .map((n) => ({
        data: {
          id: n.id,
          entityId: n.entity_id,
          type: n.type,
          label: n.label,
          color: NODE_META[n.type].color,
          shape: NODE_META[n.type].shape,
          size:
            n.type === "Patient"
              ? 42
              : n.type === "Visit"
              ? 34
              : n.type === "Diagnosis" || n.type === "Medication"
              ? 32
              : 28,
        },
      }));

    const edges = graphData.edges
      .filter(
        (e) =>
          activeEdgeTypes[e.type] &&
          visibleNodeIds.has(e.source) &&
          visibleNodeIds.has(e.target)
      )
      .map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          type: e.type,
          label: e.label,
          color: EDGE_META[e.type].color,
        },
      }));

    return [...nodes, ...edges];
  }, [graphData, activeNodeTypes, activeEdgeTypes]);

  const buildLayoutConfig = useCallback(
    (mode: LayoutMode): cytoscape.LayoutOptions => {
      if (mode === "breadthfirst") {
        return {
          name: "breadthfirst",
          directed: true,
          padding: 40,
          spacingFactor: 1.4,
          animate: false,
        };
      }
      if (mode === "concentric") {
        return {
          name: "concentric",
          padding: 36,
          minNodeSpacing: 45,
          animate: false,
        };
      }
      if (mode === "circle") {
        return { name: "circle", padding: 36, animate: false };
      }
      if (mode === "grid") {
        return { name: "grid", padding: 36, animate: false };
      }
      return {
        name: "cose",
        padding: 40,
        nodeRepulsion: () => 9500,
        idealEdgeLength: () => 115,
        animate: false,
      } as cytoscape.LayoutOptions;
    },
    []
  );

  useEffect(() => {
    let mounted = true;

    async function initCytoscape() {
      if (!containerRef.current) return;
      const cytoscapeModule = await import("cytoscape");
      if (!mounted || !containerRef.current) return;

      const cyFactory = cytoscapeModule.default;

      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }

      const cy = cyFactory({
        container: containerRef.current,
        elements: filteredElements,
        minZoom: 0.25,
        maxZoom: 2.8,
        wheelSensitivity: 0.25,
        style: [
          {
            selector: "node",
            style: {
              "background-color": "#101722",
              "border-color": "data(color)",
              "border-width": 2.5,
              label: "data(label)",
              color: "#E2E8F0",
              "font-size": 10,
              "font-weight": 500,
              "font-family": "Inter, system-ui, sans-serif",
              "text-valign": "bottom",
              "text-margin-y": 6,
              "text-background-color": "#080C12",
              "text-background-opacity": 0.78,
              "text-background-padding": "2px",
              "text-wrap": "ellipsis",
              "text-max-width": "150px",
              width: "data(size)",
              height: "data(size)",
              shape: "data(shape)" as unknown as cytoscape.Css.NodeShape,
            },
          },
          {
            selector: "edge",
            style: {
              width: 1.8,
              "line-color": "data(color)",
              "line-opacity": 0.65,
              "target-arrow-color": "data(color)",
              "target-arrow-shape": "triangle",
              "arrow-scale": 0.85,
              "curve-style": "bezier",
              label: showEdgeLabels ? "data(label)" : "",
              "font-size": 8,
              color: "#94A3B8",
              "text-background-color": "#080C12",
              "text-background-opacity": 0.85,
              "text-background-padding": "2px",
              "text-rotation": "autorotate",
            },
          },
          {
            selector: ".dimmed",
            style: {
              opacity: 0.16,
            },
          },
          {
            selector: "node.highlighted",
            style: {
              opacity: 1,
              "border-width": 3.5,
            },
          },
          {
            selector: "edge.highlighted",
            style: {
              opacity: 1,
              "line-opacity": 1,
              width: 2.8,
            },
          },
          {
            selector: "node:selected",
            style: {
              "background-color": "#151E2B",
              "border-width": 4,
              "border-color": "#FFFFFF",
            },
          },
          {
            selector: "edge:selected",
            style: {
              width: 3,
              "line-opacity": 1,
            },
          },
        ],
        layout: buildLayoutConfig(layoutMode),
      });

      cy.on("tap", "node", (evt) => {
        const target = evt.target;
        const id = target.id();
        const rawNode = nodeMap.get(id);
        if (!rawNode) return;

        cy.elements().removeClass("highlighted dimmed");
        const neighborhood = target.closedNeighborhood();
        cy.elements().not(neighborhood).addClass("dimmed");
        neighborhood.addClass("highlighted");

        setSelected({
          kind: "node",
          node: rawNode,
          degree: target.connectedEdges().length,
        });
      });

      cy.on("tap", "edge", (evt) => {
        const target = evt.target;
        const id = target.id();
        const rawEdge = edgeMap.get(id);
        if (!rawEdge) return;

        cy.elements().removeClass("highlighted dimmed");
        const endpoints = target.connectedNodes().union(target);
        cy.elements().not(endpoints).addClass("dimmed");
        endpoints.addClass("highlighted");

        setSelected({
          kind: "edge",
          edge: rawEdge,
          sourceLabel: nodeMap.get(rawEdge.source)?.label || rawEdge.source,
          targetLabel: nodeMap.get(rawEdge.target)?.label || rawEdge.target,
        });
      });

      cy.on("tap", (evt) => {
        if (evt.target === cy) {
          cy.elements().removeClass("highlighted dimmed");
          setSelected(null);
        }
      });

      if (highlightEntityId) {
        const match = cy
          .nodes()
          .filter((n) => n.data("entityId") === highlightEntityId);
        if (match.length > 0) {
          const first = match[0];
          const rawNode = nodeMap.get(first.id());
          const neighborhood = first.closedNeighborhood();
          cy.elements().not(neighborhood).addClass("dimmed");
          neighborhood.addClass("highlighted");
          first.select();
          if (rawNode) {
            setSelected({
              kind: "node",
              node: rawNode,
              degree: first.connectedEdges().length,
            });
          }
        }
      }

      cyRef.current = cy;
    }

    initCytoscape();

    return () => {
      mounted = false;
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [
    filteredElements,
    layoutMode,
    showEdgeLabels,
    buildLayoutConfig,
    nodeMap,
    edgeMap,
    highlightEntityId,
  ]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const q = nodeSearch.trim().toLowerCase();
    cy.elements().removeClass("highlighted dimmed");
    if (!q) return;

    const matched = cy.nodes().filter((n) => {
      const entity = String(n.data("entityId") || "").toLowerCase();
      const label = String(n.data("label") || "").toLowerCase();
      return entity.includes(q) || label.includes(q);
    });

    if (matched.length > 0) {
      const scope = matched.closedNeighborhood();
      cy.elements().not(scope).addClass("dimmed");
      scope.addClass("highlighted");
      cy.fit(scope, 60);
    }
  }, [nodeSearch]);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [isFullscreen]);

  const handleZoom = (factor: number) => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({
      level: cy.zoom() * factor,
      renderedPosition: {
        x: cy.width() / 2,
        y: cy.height() / 2,
      },
    });
  };

  const handleFit = () => {
    cyRef.current?.fit(undefined, 36);
  };

  const handleResetLayout = () => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("highlighted dimmed");
    cy.layout(buildLayoutConfig(layoutMode)).run();
    cy.fit(undefined, 36);
    setSelected(null);
  };

  const handleExportPng = () => {
    const cy = cyRef.current;
    if (!cy) return;
    const dataUrl = cy.png({
      full: true,
      bg: "#080C12",
      scale: 2,
    });
    const a = document.createElement("a");
    a.href = dataUrl;
    a.download = `clinicalgraph-${graphData.patient_id || "cohort"}.png`;
    a.click();
  };

  const toggleNodeType = (nt: NodeType) => {
    setActiveNodeTypes((prev) => ({ ...prev, [nt]: !prev[nt] }));
  };

  const toggleEdgeType = (et: EdgeType) => {
    setActiveEdgeTypes((prev) => ({ ...prev, [et]: !prev[et] }));
  };

  return (
    <div
      className={cn(
        "space-y-3",
        isFullscreen &&
          "fixed inset-0 z-50 flex flex-col bg-[var(--cg-bg-main)] p-4 sm:p-6 overflow-y-auto"
      )}
    >
      {/* Toolbar */}
      <Panel>
        <PanelContent className="flex flex-wrap items-center justify-between gap-3 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative w-48 sm:w-56">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--cg-text-muted)]" />
              <Input
                value={nodeSearch}
                onChange={(e) => setNodeSearch(e.target.value)}
                placeholder="Find node (e.g. V301, T0001)..."
                aria-label="Search graph nodes"
                className="h-8 pl-8 text-xs"
              />
            </div>

            <select
              aria-label="Graph layout"
              value={layoutMode}
              onChange={(e) => setLayoutMode(e.target.value as LayoutMode)}
              className="h-8 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] px-2.5 text-xs text-[var(--cg-text-primary)]"
            >
              {LAYOUT_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  Layout: {opt.label}
                </option>
              ))}
            </select>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowEdgeLabels((v) => !v)}
            >
              {showEdgeLabels ? (
                <Eye className="h-3.5 w-3.5 text-[var(--cg-accent-teal)]" />
              ) : (
                <EyeOff className="h-3.5 w-3.5" />
              )}
              Edge Labels
            </Button>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => handleZoom(1.25)}
              title="Zoom in"
              aria-label="Zoom in"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => handleZoom(0.8)}
              title="Zoom out"
              aria-label="Zoom out"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleFit}
              title="Fit graph to view"
            >
              <Focus className="h-3.5 w-3.5" />
              Fit
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleResetLayout}
              title="Reset graph layout"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportPng}
              title="Export graph as PNG"
            >
              <Download className="h-3.5 w-3.5" />
              PNG
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => setIsFullscreen((f) => !f)}
              title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
              aria-label={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              {isFullscreen ? (
                <Minimize2 className="h-3.5 w-3.5" />
              ) : (
                <Maximize2 className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
        </PanelContent>
      </Panel>

      {/* Node & Relationship Filters / Legend */}
      <div className="flex flex-col gap-2 rounded-xl border border-[var(--cg-border)] bg-[var(--cg-bg-panel)] p-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)] mr-1">
            Nodes:
          </span>
          {(Object.keys(NODE_META) as NodeType[]).map((nt) => {
            const count = graphData.stats.node_counts_by_type[nt] || 0;
            const active = activeNodeTypes[nt];
            return (
              <button
                key={nt}
                type="button"
                onClick={() => toggleNodeType(nt)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium transition-opacity cursor-pointer",
                  active
                    ? "border-[var(--cg-border-strong)] bg-[var(--cg-bg-elevated)] text-[var(--cg-text-primary)]"
                    : "border-[var(--cg-border)] bg-transparent text-[var(--cg-text-muted)] opacity-50"
                )}
              >
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: NODE_META[nt].color }}
                />
                <span>{NODE_META[nt].label}</span>
                <span className="font-mono text-[10px] text-[var(--cg-text-secondary)]">
                  ({count})
                </span>
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)] mr-1">
            Edges:
          </span>
          {(Object.keys(EDGE_META) as EdgeType[]).map((et) => {
            const count = graphData.stats.edge_counts_by_type[et] || 0;
            const active = activeEdgeTypes[et];
            return (
              <button
                key={et}
                type="button"
                onClick={() => toggleEdgeType(et)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-[10px] transition-opacity cursor-pointer",
                  active
                    ? "border-[var(--cg-border-strong)] bg-[var(--cg-bg-elevated)] text-[var(--cg-text-primary)]"
                    : "border-[var(--cg-border)] bg-transparent text-[var(--cg-text-muted)] opacity-50"
                )}
              >
                <span
                  className="h-1.5 w-3 rounded-full"
                  style={{ backgroundColor: EDGE_META[et].color }}
                />
                <span>{EDGE_META[et].label}</span>
                <span className="text-[var(--cg-text-secondary)]">({count})</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Graph Canvas + Property Inspector */}
      <div
        className={cn(
          "grid grid-cols-1 gap-4 lg:grid-cols-12",
          isFullscreen && "flex-1"
        )}
      >
        <Panel className="lg:col-span-8 xl:col-span-9 relative overflow-hidden">
          <div
            ref={containerRef}
            aria-label="Interactive Clinical Knowledge Graph canvas"
            className={cn(
              "w-full bg-[#080C12]",
              isFullscreen
                ? "h-[calc(100vh-250px)] min-h-[480px]"
                : compact
                ? "h-[460px]"
                : "h-[580px]"
            )}
          />
          <div className="pointer-events-none absolute bottom-3 left-3 rounded-lg border border-[#243041] bg-[#0C111A]/90 px-3 py-1.5 text-[11px] text-[#94A3B8]">
            Drag nodes • Scroll to zoom • Click node or edge to inspect properties
          </div>
        </Panel>

        <Panel className="lg:col-span-4 xl:col-span-3 flex flex-col">
          <PanelHeader>
            <PanelTitle>Property Inspector</PanelTitle>
            {selected && (
              <button
                type="button"
                onClick={() => {
                  cyRef.current?.elements().removeClass("highlighted dimmed");
                  setSelected(null);
                }}
                aria-label="Clear selection"
                className="rounded p-1 text-[var(--cg-text-muted)] hover:text-[var(--cg-text-primary)] cursor-pointer"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </PanelHeader>
          <PanelContent className="flex-1 space-y-4 text-xs overflow-y-auto max-h-[540px]">
            {!selected ? (
              <div className="space-y-3 text-[var(--cg-text-secondary)]">
                <p>
                  Select any <strong className="text-[var(--cg-text-primary)]">node</strong> or{" "}
                  <strong className="text-[var(--cg-text-primary)]">relationship</strong> in the graph canvas to inspect its Neo4j identifiers, properties, and linked records.
                </p>
                <div className="rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-3 space-y-1.5">
                  <div className="font-semibold text-[var(--cg-text-primary)]">
                    Active Subgraph Summary
                  </div>
                  <div className="flex justify-between">
                    <span>Nodes rendered</span>
                    <span className="font-mono font-semibold text-[var(--cg-accent-teal)]">
                      {graphData.stats.node_count}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Relationships rendered</span>
                    <span className="font-mono font-semibold text-[var(--cg-accent-sky)]">
                      {graphData.stats.edge_count}
                    </span>
                  </div>
                </div>
              </div>
            ) : selected.kind === "node" ? (
              <div className="space-y-4">
                <div>
                  <Badge
                    variant="teal"
                    style={{
                      borderColor: `${NODE_META[selected.node.type].color}55`,
                      color: NODE_META[selected.node.type].color,
                    }}
                  >
                    :{selected.node.type}
                  </Badge>
                  <h4 className="mt-2 text-base font-semibold text-[var(--cg-text-primary)]">
                    {selected.node.label}
                  </h4>
                  <p className="font-mono text-[11px] text-[var(--cg-text-secondary)]">
                    Entity ID: {selected.node.entity_id} • {selected.degree} connections
                  </p>
                </div>

                <div className="space-y-1.5 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-3">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                    Node Properties
                  </div>
                  {Object.entries(selected.node.properties).map(([k, v]) => (
                    <div
                      key={k}
                      className="flex items-start justify-between gap-2 border-t border-[var(--cg-border)]/60 pt-1.5 first:border-t-0 first:pt-0"
                    >
                      <span className="font-mono text-[11px] text-[var(--cg-text-secondary)]">
                        {k}
                      </span>
                      <span className="text-right font-mono text-[11px] text-[var(--cg-text-primary)] break-all">
                        {v === null || v === undefined ? "—" : String(v)}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="flex flex-col gap-2">
                  {selected.node.type === "Patient" && onSelectPatientNode && (
                    <Button
                      size="sm"
                      onClick={() => onSelectPatientNode(selected.node.entity_id)}
                    >
                      Open Patient Profile
                    </Button>
                  )}
                  {onAskAboutNode && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        onAskAboutNode(
                          `Explain the clinical context for ${selected.node.type} ${selected.node.entity_id}.`,
                          selected.node.type === "Patient"
                            ? selected.node.entity_id
                            : graphData.patient_id
                        )
                      }
                    >
                      <Sparkles className="h-3.5 w-3.5 text-[var(--cg-accent-teal)]" />
                      Ask AI about this entity
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <Badge variant="sky" className="font-mono">
                    [:{selected.edge.type}]
                  </Badge>
                  <div className="mt-2 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-2.5 font-mono text-[11px]">
                    <div className="text-[var(--cg-text-primary)]">
                      {selected.sourceLabel}
                    </div>
                    <div className="my-1 text-[var(--cg-accent-sky)]">
                      ──[:{selected.edge.type}]──▶
                    </div>
                    <div className="text-[var(--cg-text-primary)]">
                      {selected.targetLabel}
                    </div>
                  </div>
                </div>

                <div className="space-y-1.5 rounded-lg border border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] p-3">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-[var(--cg-text-muted)]">
                    Relationship Properties
                  </div>
                  {Object.entries(selected.edge.properties).map(([k, v]) => (
                    <div
                      key={k}
                      className="flex items-start justify-between gap-2 border-t border-[var(--cg-border)]/60 pt-1.5 first:border-t-0 first:pt-0"
                    >
                      <span className="font-mono text-[11px] text-[var(--cg-text-secondary)]">
                        {k}
                      </span>
                      <span className="text-right font-mono text-[11px] text-[var(--cg-text-primary)] break-all">
                        {v === null || v === undefined ? "—" : String(v)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </PanelContent>
        </Panel>
      </div>
    </div>
  );
}
