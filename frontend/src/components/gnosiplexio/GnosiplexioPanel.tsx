"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import cytoscape, { type Core, type EventObject } from "cytoscape";
import { useTranslations } from "next-intl";
import {
  Network,
  Search,
  BarChart3,
  X,
  ZoomIn,
  ZoomOut,
  Maximize2,
  GitCompare,
  Loader2,
} from "lucide-react";
import {
  exportGraph,
  getNeighborhood,
  getNode,
  getStats,
  searchGraph,
  compareNodes,
  type GnosiplexioNode,
  type GraphStats,
  type SearchResult,
  type CompareResult,
} from "@/lib/api/gnosiplexio";
import { CredibilityBadge } from "./CredibilityBadge";
import { TimelineView } from "./TimelineView";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const NODE_COLORS: Record<string, string> = {
  Work: "#3b82f6",
  Concept: "#22c55e",
  Author: "#f97316",
  Domain: "#a855f7",
  Method: "#ef4444",
};

const DEFAULT_COLOR = "#6b7280";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function GnosiplexioPanel() {
  const t = useTranslations("gnosiplexio");
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [selectedNode, setSelectedNode] = useState<GnosiplexioNode | null>(null);
  const [compareSelection, setCompareSelection] = useState<string[]>([]);
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [showTimeline, setShowTimeline] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --- Cytoscape init & data load ---
  const initCytoscape = useCallback((elements: cytoscape.ElementDefinition[]) => {
    if (!containerRef.current) return;
    cyRef.current?.destroy();

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "background-color": "data(color)",
            color: "#e5e7eb",
            "font-size": "10px",
            "text-valign": "bottom",
            "text-margin-y": 4,
            width: 28,
            height: 28,
            "border-width": 2,
            "border-color": "#374151",
          },
        },
        {
          selector: "node:selected",
          style: { "border-color": "#facc15", "border-width": 3 },
        },
        {
          selector: "node.highlighted",
          style: { "border-color": "#facc15", "border-width": 3, width: 36, height: 36 },
        },
        {
          selector: "edge",
          style: {
            label: "data(label)",
            "font-size": "8px",
            color: "#9ca3af",
            "line-color": "#4b5563",
            "target-arrow-color": "#4b5563",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            width: 1.5,
          },
        },
      ],
      layout: { name: "cose", animate: true, animationDuration: 800 } as cytoscape.LayoutOptions,
      minZoom: 0.2,
      maxZoom: 5,
    });

    cy.on("tap", "node", async (e: EventObject) => {
      const id = e.target.id();
      if (compareMode) {
        setCompareSelection((prev) => {
          if (prev.includes(id)) return prev.filter((x) => x !== id);
          if (prev.length >= 2) return [prev[1], id];
          return [...prev, id];
        });
        return;
      }
      try {
        const node = await getNode(id);
        setSelectedNode(node);
      } catch {
        setSelectedNode({ id, type: e.target.data("type") ?? "Unknown", properties: e.target.data(), network_citations: [] });
      }
    });

    cy.on("dbltap", "node", async (e: EventObject) => {
      const id = e.target.id();
      try {
        const neighborhood = await getNeighborhood(id, 1);
        addElements(cy, neighborhood.nodes, neighborhood.edges);
      } catch (err) {
        console.error("Failed to load neighborhood", err);
      }
    });

    cyRef.current = cy;
  }, [compareMode]);

  const addElements = (cy: Core, nodes: Record<string, unknown>[], edges: Record<string, unknown>[]) => {
    const existing = new Set(cy.nodes().map((n) => n.id()));
    const newEles: cytoscape.ElementDefinition[] = [];
    for (const n of nodes) {
      const id = String((n as { data?: { id?: string } }).data?.id ?? n.id ?? "");
      if (!id || existing.has(id)) continue;
      const type = String((n as { data?: { type?: string } }).data?.type ?? n.type ?? "");
      const label = String((n as { data?: { label?: string } }).data?.label ?? n.label ?? id);
      newEles.push({ data: { id, label, type, color: NODE_COLORS[type] ?? DEFAULT_COLOR } });
    }
    for (const e of edges) {
      const ed = (e as { data?: Record<string, unknown> }).data ?? e;
      const source = String(ed.source ?? "");
      const target = String(ed.target ?? "");
      const label = String(ed.label ?? ed.type ?? "");
      if (source && target) newEles.push({ data: { source, target, label } });
    }
    if (newEles.length) {
      cy.add(newEles);
      cy.layout({ name: "cose", animate: true, animationDuration: 600 } as cytoscape.LayoutOptions).run();
    }
  };

  // --- Load initial graph ---
  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [graph, graphStats] = await Promise.all([exportGraph("cytoscape"), getStats()]);
        setStats(graphStats);

        const elements: cytoscape.ElementDefinition[] = [];
        for (const n of graph.nodes) {
          const d = (n as { data?: Record<string, unknown> }).data ?? n;
          const id = String(d.id ?? "");
          const type = String(d.type ?? "");
          const label = String(d.label ?? d.title ?? id);
          elements.push({ data: { id, label, type, color: NODE_COLORS[type] ?? DEFAULT_COLOR } });
        }
        for (const e of graph.edges) {
          const d = (e as { data?: Record<string, unknown> }).data ?? e;
          const source = String(d.source ?? "");
          const target = String(d.target ?? "");
          const label = String(d.label ?? d.type ?? "");
          if (source && target) elements.push({ data: { source, target, label } });
        }
        initCytoscape(elements);
      } catch (err) {
        setError(err instanceof Error ? err.message : t("errors.failedToLoadGraph"));
      } finally {
        setLoading(false);
      }
    })();
    return () => { cyRef.current?.destroy(); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Search ---
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    try {
      const results = await searchGraph(searchQuery);
      setSearchResults(results);
      // highlight matching nodes
      const cy = cyRef.current;
      if (cy) {
        cy.nodes().removeClass("highlighted");
        for (const r of results) {
          cy.getElementById(r.id).addClass("highlighted");
        }
      }
    } catch (err) {
      console.error("Search failed", err);
    }
  };

  // --- Compare ---
  const handleCompare = async () => {
    if (compareSelection.length !== 2) return;
    try {
      const result = await compareNodes(compareSelection[0], compareSelection[1]);
      setCompareResult(result);
    } catch (err) {
      console.error("Compare failed", err);
    }
  };

  // --- Timeline data ---
  const timelineData = useMemo(() => {
    const cy = cyRef.current;
    if (!cy) return { nodes: [], citations: [] as Array<{ sourceId: string; targetId: string; sourceYear: number; targetYear: number }> };

    const workNodes = cy.nodes().filter((n) => n.data("type") === "Work");
    const yearByNode = new Map<string, number>();

    const nodes = workNodes.map((n) => {
      const year = Number(n.data("year") ?? 2020);
      yearByNode.set(n.id(), year);
      return {
        id: n.id(),
        title: String(n.data("label") ?? n.id()),
        year,
        citations: (n as cytoscape.NodeSingular).indegree(false),
        credibility: Number(n.data("credibility_score") ?? n.data("credibility") ?? 0.5),
      };
    });

    const citationEdgeTypes = new Set(["CITES", "CITED_FOR", "EXTENDS"]);
    const citations = cy
      .edges()
      .filter((e) => citationEdgeTypes.has(String(e.data("type") ?? "")))
      .map((e) => {
        const sourceId = String(e.data("source") ?? "");
        const targetId = String(e.data("target") ?? "");
        return {
          sourceId,
          targetId,
          sourceYear: yearByNode.get(sourceId) ?? 2020,
          targetYear: yearByNode.get(targetId) ?? 2020,
        };
      })
      .filter((c) => c.sourceId && c.targetId);

    return { nodes, citations };
  }, [stats]); // recalc when stats change (proxy for graph loaded)

  const handleTimelineSelect = (id: string) => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes().removeClass("highlighted");
    const node = cy.getElementById(id);
    if (node.length) {
      node.addClass("highlighted");
      cy.animate({ center: { eles: node }, zoom: 2 } as unknown as cytoscape.AnimateOptions, { duration: 400 });
    }
  };

  // --- Zoom controls ---
  const zoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.3);
  const zoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() / 1.3);
  const fitGraph = () => cyRef.current?.fit(undefined, 40);

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-gray-200">
          <Network className="w-5 h-5 text-blue-500" />
          {t("title")}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowTimeline((v) => !v)}
            className={`p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-800 ${showTimeline ? "bg-gray-200 dark:bg-gray-800" : ""}`}
            title={t("timeline.title")}
          >
            <BarChart3 className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>
          <button
            onClick={() => { setCompareMode((v) => !v); setCompareSelection([]); setCompareResult(null); }}
            className={`p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-800 ${compareMode ? "bg-blue-100 dark:bg-blue-900/40" : ""}`}
            title={t("compare.mode")}
          >
            <GitCompare className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-800">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder={t("search.placeholder")}
              className="w-full pl-8 pr-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button onClick={handleSearch} className="px-3 py-1.5 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700">
            {t("search.button")}
          </button>
        </div>
        {searchResults.length > 0 && (
          <div className="mt-2 max-h-32 overflow-y-auto space-y-1">
            {searchResults.map((r) => (
              <button
                key={r.id}
                onClick={() => handleTimelineSelect(r.id)}
                className="w-full text-left text-xs px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
              >
                <span className="font-medium">{r.label}</span>
                <span className="ml-2 text-gray-400">{r.type}</span>
                {r.snippet && <span className="block text-gray-400 truncate">{r.snippet}</span>}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Compare bar */}
      {compareMode && (
        <div className="px-4 py-2 bg-blue-50 dark:bg-blue-950/30 border-b border-blue-200 dark:border-blue-800 flex items-center gap-3 text-xs">
          <GitCompare className="w-4 h-4 text-blue-500" />
          <span className="text-gray-600 dark:text-gray-400">
            {t("compare.hint", { selected: compareSelection.length })}
          </span>
          {compareSelection.length === 2 && (
            <button onClick={handleCompare} className="px-2 py-0.5 rounded bg-blue-600 text-white hover:bg-blue-700">
              {t("compare.action")}
            </button>
          )}
        </div>
      )}

      {/* Stats bar */}
      {stats && (
        <div className="px-4 py-1.5 border-b border-gray-200 dark:border-gray-800 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
          <span>{t("stats.nodes", { count: stats.total_nodes })}</span>
          <span>{t("stats.edges", { count: stats.total_edges })}</span>
          <span>{t("stats.density", { value: stats.density.toFixed(4) })}</span>
          <span>{t("stats.avgDegree", { value: stats.avg_degree.toFixed(1) })}</span>
        </div>
      )}

      {/* Main area */}
      <div className="flex flex-1 min-h-0">
        {/* Graph */}
        <div className="relative flex-1">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/60 dark:bg-gray-950/60 z-10">
              <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
            </div>
          )}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center z-10">
              <p className="text-red-500 text-sm">{error}</p>
            </div>
          )}
          <div ref={containerRef} className="w-full h-full" />
          {/* Zoom controls */}
          <div className="absolute bottom-3 right-3 flex flex-col gap-1">
            <button onClick={zoomIn} className="p-1.5 rounded bg-white dark:bg-gray-800 shadow border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700">
              <ZoomIn className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
            <button onClick={zoomOut} className="p-1.5 rounded bg-white dark:bg-gray-800 shadow border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700">
              <ZoomOut className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
            <button onClick={fitGraph} className="p-1.5 rounded bg-white dark:bg-gray-800 shadow border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700">
              <Maximize2 className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
          </div>
        </div>

        {/* Detail sidebar */}
        {selectedNode && (
          <div className="w-72 border-l border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-y-auto p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 truncate">
                {String(selectedNode.properties.title ?? selectedNode.properties.label ?? selectedNode.id)}
              </h3>
              <button onClick={() => setSelectedNode(null)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>
            <span className="inline-block mb-3 px-2 py-0.5 rounded-full text-xs font-medium" style={{ backgroundColor: NODE_COLORS[selectedNode.type] ?? DEFAULT_COLOR, color: "#fff" }}>
              {selectedNode.type}
            </span>
            {selectedNode.network_credibility && (
              <div className="mb-3">
                <CredibilityBadge
                  score={Number((selectedNode.network_credibility as Record<string, unknown>).score ?? 0.5)}
                  breakdown={selectedNode.network_credibility}
                />
              </div>
            )}
            <div className="space-y-2 text-xs">
              {Object.entries(selectedNode.properties).map(([k, v]) => (
                <div key={k}>
                  <span className="text-gray-400 dark:text-gray-500">{k}</span>
                  <p className="text-gray-700 dark:text-gray-300 break-words">{String(v)}</p>
                </div>
              ))}
            </div>
            {selectedNode.network_citations.length > 0 && (
              <div className="mt-4">
                <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{t("node.networkCitations", { count: selectedNode.network_citations.length })}</h4>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {selectedNode.network_citations.map((c, i) => (
                    <div key={i} className="text-xs text-gray-600 dark:text-gray-400 p-1.5 rounded bg-gray-50 dark:bg-gray-800">
                      {String((c as Record<string, unknown>).title ?? JSON.stringify(c))}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Compare result sidebar */}
        {compareResult && (
          <div className="w-72 border-l border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-y-auto p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">{t("compare.title")}</h3>
              <button onClick={() => setCompareResult(null)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>
            <div className="text-xs space-y-3">
              <div>
                <span className="text-gray-400">{t("compare.similarity")}</span>
                <p className="text-lg font-bold text-blue-500">{(compareResult.similarity_score * 100).toFixed(1)}%</p>
              </div>
              <div>
                <span className="text-gray-400">{t("compare.sharedConcepts", { count: compareResult.shared_concepts.length })}</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {compareResult.shared_concepts.map((c) => (
                    <span key={c} className="px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs">{c}</span>
                  ))}
                </div>
              </div>
              <div>
                <span className="text-gray-400">{t("compare.sharedCitations", { count: compareResult.shared_citations.length })}</span>
                <div className="space-y-1 mt-1 max-h-40 overflow-y-auto">
                  {compareResult.shared_citations.map((n, i) => (
                    <div key={i} className="text-xs p-1.5 rounded bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                      {String(n)}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Timeline */}
      {showTimeline && (
        <div className="border-t border-gray-200 dark:border-gray-800 p-4">
          <TimelineView nodes={timelineData.nodes} citations={timelineData.citations} onSelectNode={handleTimelineSelect} />
        </div>
      )}
    </div>
  );
}
